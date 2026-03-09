from __future__ import annotations

import argparse
import concurrent.futures
import json
import sys
from dataclasses import dataclass, field
from typing import Callable, Optional

import requests

from src.auth.cas_client import ZJUAuthClient
from src.common.account import resolve_credentials
from src.common.course_meta import (
    course_teachers,
    query_course_detail,
)
from src.common.http import get_thread_session
from src.scan.live_check import check_course_live_status


@dataclass(frozen=True)
class CourseScanTarget:
    teacher: str
    title: str

    @property
    def key(self) -> tuple[str, str]:
        return self.title, self.teacher


@dataclass
class CourseScanMatch:
    course_id: int
    title: str
    teachers: list[str]
    target_teacher: str


@dataclass
class CourseBatchScanResult:
    center: int
    radius: int
    total_candidates: int
    scanned: int
    matches: dict[tuple[str, str], CourseScanMatch]
    target_keys: list[tuple[str, str]] = field(default_factory=list)

    @property
    def matched_count(self) -> int:
        return len(self.matches)

    @property
    def missing_keys(self) -> list[tuple[str, str]]:
        return [key for key in self.target_keys if key not in self.matches]


def query_course_worker(
    token: str,
    timeout: int,
    retries: int,
    course_id: int,
) -> tuple[int, Optional[dict]]:
    session = get_thread_session()
    data = query_course_detail(session, token, timeout, course_id, retries)
    return course_id, data


def scan_courses_batch(
    *,
    token: str,
    timeout: int,
    retries: int,
    center: int,
    radius: int,
    targets: list[CourseScanTarget],
    workers: int,
    reverse: bool = True,
    stop_when_all_found: bool = True,
    verbose: bool = False,
    on_progress: Optional[Callable[[int, int, int, int], None]] = None,
) -> CourseBatchScanResult:
    start_id = int(center) - int(radius)
    end_id = int(center) + int(radius)
    ordered_ids = list(range(start_id, end_id + 1))
    if reverse:
        ordered_ids.reverse()

    unique_targets: dict[tuple[str, str], CourseScanTarget] = {}
    for target in targets:
        key = target.key
        if key in unique_targets:
            continue
        unique_targets[key] = target

    target_keys = list(unique_targets.keys())
    if not target_keys:
        result = CourseBatchScanResult(
            center=int(center),
            radius=int(radius),
            total_candidates=len(ordered_ids),
            scanned=0,
            matches={},
            target_keys=[],
        )
        return result

    matches: dict[tuple[str, str], CourseScanMatch] = {}
    scanned = 0
    total = len(ordered_ids)

    def progress_hook() -> None:
        if on_progress is None:
            return
        try:
            on_progress(scanned, total, len(matches), len(target_keys))
        except Exception:
            return

    def handle_result(course_id: int, data: Optional[dict]) -> bool:
        nonlocal scanned
        scanned += 1
        if not data:
            progress_hook()
            return False

        title = str(data.get("title", "") or "").strip()
        teachers = course_teachers(data)
        if verbose:
            print(f"[batch-scan] cid={course_id} title={title} teachers={','.join(teachers)}")

        for key, target in unique_targets.items():
            if key in matches:
                continue
            if title != target.title:
                continue
            if target.teacher not in teachers:
                continue
            matches[key] = CourseScanMatch(
                course_id=int(course_id),
                title=title,
                teachers=list(teachers),
                target_teacher=target.teacher,
            )
            if verbose:
                print(
                    f"[batch-scan][MATCH] cid={course_id} title={title} "
                    f"teacher={target.teacher} teachers={','.join(teachers)}"
                )
        progress_hook()
        return stop_when_all_found and len(matches) >= len(target_keys)

    if workers <= 1:
        single_session = requests.Session()
        for cid in ordered_ids:
            data = query_course_detail(single_session, token, timeout, cid, retries)
            should_stop = handle_result(cid, data)
            if should_stop:
                break
    else:
        max_workers = max(1, int(workers))
        max_in_flight = max(max_workers * 4, max_workers)
        next_index = 0
        pending: dict[concurrent.futures.Future, int] = {}
        should_stop = False
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
            while True:
                while (not should_stop) and next_index < total and len(pending) < max_in_flight:
                    cid = ordered_ids[next_index]
                    next_index += 1
                    future = pool.submit(query_course_worker, token, timeout, retries, cid)
                    pending[future] = cid

                if not pending:
                    break

                done, _ = concurrent.futures.wait(
                    pending.keys(),
                    return_when=concurrent.futures.FIRST_COMPLETED,
                )
                for future in done:
                    cid = pending.pop(future)
                    try:
                        result_cid, data = future.result()
                    except Exception:
                        result_cid, data = cid, None
                    should_stop = handle_result(result_cid, data) or should_stop

                if should_stop:
                    for outstanding in list(pending.keys()):
                        outstanding.cancel()
                    pending.clear()
                    break

    result = CourseBatchScanResult(
        center=int(center),
        radius=int(radius),
        total_candidates=total,
        scanned=scanned,
        matches=matches,
        target_keys=target_keys,
    )
    return result


def run_scan(args: argparse.Namespace) -> int:
    username, password, cred_error = resolve_credentials(args.username, args.password)
    if cred_error:
        print(f"Credential error: {cred_error}", file=sys.stderr)
        return 1

    auth = ZJUAuthClient(timeout=args.timeout, tenant_code=args.tenant_code)
    login_session = requests.Session()

    try:
        token = auth.login_and_get_token(
            session=login_session,
            username=username,
            password=password,
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
    require_live = bool(getattr(args, "require_live", False))
    live_check_timeout = max(0.0, float(getattr(args, "live_check_timeout", 30.0)))
    live_check_interval = max(0.0, float(getattr(args, "live_check_interval", 2.0)))

    found: list[dict] = []
    matched_candidates: list[dict] = []
    live_check_failures: list[dict] = []
    live_checked_candidates = 0
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
            candidate = {
                "course_id": cid,
                "title": title,
                "teachers": teachers,
            }
            if require_live:
                matched_candidates.append(candidate)
                if args.verbose:
                    print(
                        f"[CANDIDATE] course_id={cid} title={title} "
                        f"teachers={','.join(teachers)} (pending live check)"
                    )
            else:
                print(f"[MATCH] course_id={cid} title={title} teachers={','.join(teachers)}")
                found.append(candidate)
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

    if require_live:
        matched_candidates.sort(key=lambda x: x["course_id"])
        live_session = requests.Session()
        for candidate in matched_candidates:
            live_checked_candidates += 1
            live_result = check_course_live_status(
                session=live_session,
                token=token,
                timeout=args.timeout,
                tenant_code=args.tenant_code,
                course_id=int(candidate["course_id"]),
                max_wait_sec=live_check_timeout,
                interval_sec=live_check_interval,
            )
            if live_result.checked and live_result.is_live:
                live_match = dict(candidate)
                live_match["sub_id"] = live_result.sub_id
                print(
                    f"[MATCH] course_id={candidate['course_id']} "
                    f"sub_id={live_result.sub_id or 'N/A'} title={candidate['title']} "
                    f"teachers={','.join(candidate['teachers'])} live=直播中"
                )
                found.append(live_match)
                continue

            if live_result.checked:
                if args.verbose:
                    print(
                        f"[FILTERED-NOT-LIVE] course_id={candidate['course_id']} "
                        f"title={candidate['title']} teachers={','.join(candidate['teachers'])}"
                    )
                continue

            failure = {
                "course_id": candidate["course_id"],
                "title": candidate["title"],
                "teacher": args.teacher,
                "attempts": live_result.attempts,
                "elapsed_sec": live_result.elapsed_sec,
                "last_error": live_result.last_error,
                "hint": live_result.hint,
            }
            live_check_failures.append(failure)
            print(
                f"[LIVE-CHECK-FAIL] course_id={candidate['course_id']} title={candidate['title']} "
                f"teacher={args.teacher} attempts={live_result.attempts} "
                f"elapsed_sec={live_result.elapsed_sec} last_error={live_result.last_error} "
                f"hint={live_result.hint}",
                file=sys.stderr,
            )

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
                "require_live": require_live,
                "live_check_timeout_sec": live_check_timeout,
                "live_check_interval_sec": live_check_interval,
                "live_checked_candidates": live_checked_candidates,
                "live_check_failures": live_check_failures,
                "matches": found,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0
