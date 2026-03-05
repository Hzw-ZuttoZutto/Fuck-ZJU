from __future__ import annotations

import argparse
import concurrent.futures
import json
import sys
from typing import Optional

import requests

from src.auth.cas_client import ZJUAuthClient
from src.common.constants import API_BASE
from src.common.http import get_thread_session


def parse_course_data(raw: dict) -> Optional[dict]:
    if raw.get("code") == 0 and isinstance(raw.get("data"), dict):
        return raw["data"]
    if (
        raw.get("success")
        and isinstance(raw.get("result"), dict)
        and raw["result"].get("err") == 0
        and isinstance(raw["result"].get("data"), dict)
    ):
        return raw["result"]["data"]
    return None


def course_teachers(course_data: dict) -> list[str]:
    names: list[str] = []
    if isinstance(course_data.get("teachers"), list):
        for item in course_data["teachers"]:
            if not isinstance(item, dict):
                continue
            realname = item.get("realname") or item.get("name")
            if realname and realname not in names:
                names.append(realname)

    realname = course_data.get("realname")
    if realname and realname not in names:
        names.insert(0, realname)
    return names


def query_course_detail(
    session: requests.Session,
    token: str,
    timeout: int,
    course_id: int,
    retries: int,
) -> Optional[dict]:
    headers = {"Accept-Language": "zh_cn"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    attempts = max(retries, 0) + 1
    for _ in range(attempts):
        try:
            resp = session.get(
                f"{API_BASE}/courseapi/v3/multi-search/get-course-detail",
                params={"course_id": course_id},
                headers=headers,
                timeout=timeout,
            )
        except requests.RequestException:
            continue

        if resp.status_code != 200:
            continue

        try:
            payload = resp.json()
        except json.JSONDecodeError:
            continue

        return parse_course_data(payload)

    return None


def query_course_worker(
    token: str,
    timeout: int,
    retries: int,
    course_id: int,
) -> tuple[int, Optional[dict]]:
    session = get_thread_session()
    data = query_course_detail(session, token, timeout, course_id, retries)
    return course_id, data


def run_scan(args: argparse.Namespace) -> int:
    auth = ZJUAuthClient(timeout=args.timeout, tenant_code=args.tenant_code)
    login_session = requests.Session()

    try:
        token = auth.login_and_get_token(
            session=login_session,
            username=args.username,
            password=args.password,
            center_course_id=args.center,
            authcode=args.authcode,
        )
    except Exception as exc:
        print(f"Login failed: {exc}", file=sys.stderr)
        return 1

    if not token:
        print("Login succeeded but token is empty; cannot continue scan.", file=sys.stderr)
        return 1

    start_id = args.center - args.radius
    end_id = args.center + args.radius
    course_ids = list(range(start_id, end_id + 1))

    found: list[dict] = []
    scanned = 0

    def handle_result(cid: int, data: Optional[dict]) -> None:
        nonlocal scanned
        scanned += 1
        if not data:
            if args.verbose:
                print(f"[{cid}] no data")
            return

        title = data.get("title", "")
        teachers = course_teachers(data)

        if title == args.title and args.teacher in teachers:
            print(f"[MATCH] course_id={cid} title={title} teachers={','.join(teachers)}")
            found.append(
                {
                    "course_id": cid,
                    "title": title,
                    "teachers": teachers,
                }
            )
        elif args.verbose:
            print(f"[{cid}] title={title} teachers={','.join(teachers)}")

    if args.workers <= 1:
        single_session = requests.Session()
        for cid in course_ids:
            data = query_course_detail(single_session, token, args.timeout, cid, args.retries)
            handle_result(cid, data)
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            future_map = {
                pool.submit(query_course_worker, token, args.timeout, args.retries, cid): cid
                for cid in course_ids
            }
            for fut in concurrent.futures.as_completed(future_map):
                cid = future_map[fut]
                try:
                    result_cid, data = fut.result()
                except Exception:
                    result_cid, data = cid, None
                handle_result(result_cid, data)

    found.sort(key=lambda x: x["course_id"])

    print(
        json.dumps(
            {
                "mode": "scan",
                "center": args.center,
                "radius": args.radius,
                "scanned": scanned,
                "teacher": args.teacher,
                "title": args.title,
                "matches": found,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0
