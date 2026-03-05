from __future__ import annotations

import os
import re
import subprocess
import urllib.parse

import requests

from src.common.constants import CAS_BASE, TG_LOGIN_BASE


def extract_form_fields(html: str) -> tuple[str, str]:
    action_match = re.search(
        r'<form[^>]*id="fm1"[^>]*action="([^"]+)"', html, flags=re.IGNORECASE
    )
    execution_match = re.search(r'name="execution"\s+value="([^"]+)"', html)
    if not action_match or not execution_match:
        raise RuntimeError("Failed to parse CAS login form action/execution.")
    return action_match.group(1), execution_match.group(1)


def encrypt_password_with_node(
    security_js: str,
    modulus: str,
    exponent: str,
    plain_password: str,
) -> str:
    node_script = r"""
const vm = require("vm");
const securityJs = process.env.SECURITY_JS || "";
const modulus = process.env.MODULUS || "";
const exponent = process.env.EXPONENT || "";
const password = process.env.PLAIN_PASSWORD || "";
const sandbox = { window: {}, navigator: { appName: "Netscape" }, console };
vm.createContext(sandbox);
vm.runInContext(securityJs, sandbox);
const RSAUtils = sandbox.window.RSAUtils;
if (!RSAUtils) {
  console.error("RSAUtils is unavailable");
  process.exit(2);
}
const reversed = password.split("").reverse().join("");
const key = new RSAUtils.getKeyPair(exponent, "", modulus);
const encrypted = RSAUtils.encryptedString(key, reversed);
process.stdout.write(encrypted);
"""

    env = os.environ.copy()
    env["SECURITY_JS"] = security_js
    env["MODULUS"] = modulus
    env["EXPONENT"] = exponent
    env["PLAIN_PASSWORD"] = plain_password

    proc = subprocess.run(
        ["node", "-e", node_script],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        stderr = proc.stderr.strip() or "unknown node error"
        raise RuntimeError(f"Password encryption failed: {stderr}")

    encrypted = proc.stdout.strip()
    if not encrypted:
        raise RuntimeError("Password encryption returned empty result.")
    return encrypted


def extract_bearer_token_from_cookie_value(cookie_value: str) -> str:
    decoded = urllib.parse.unquote(cookie_value)
    match = re.search(r'{i:\d+;s:\d+:"_token";i:\d+;s:\d+:"(.+?)";}', decoded)
    if match:
        return match.group(1)
    return ""


class ZJUAuthClient:
    def __init__(self, timeout: int, tenant_code: str) -> None:
        self.timeout = timeout
        self.tenant_code = tenant_code

    def login_and_get_token(
        self,
        session: requests.Session,
        username: str,
        password: str,
        center_course_id: int,
        authcode: str,
    ) -> str:
        forward_url = (
            "https://classroom.zju.edu.cn/coursedetail?"
            f"course_id={center_course_id}&tenant_code={self.tenant_code}"
        )
        login_url = (
            f"{TG_LOGIN_BASE}/index.php?r=auth/login&auType=cmc"
            f"&tenant_code={self.tenant_code}"
            f"&forward={urllib.parse.quote(forward_url, safe='')}"
        )

        login_page = session.get(login_url, timeout=self.timeout, allow_redirects=True)
        login_page.raise_for_status()
        action, execution = extract_form_fields(login_page.text)

        kaptcha_status = session.get(
            f"{CAS_BASE}/v2/getKaptchaStatus", timeout=self.timeout
        ).text.strip()
        if kaptcha_status.lower() == "true" and not authcode:
            raise RuntimeError("CAS requires captcha now. Re-run with --authcode <code>.")

        pubkey_resp = session.get(f"{CAS_BASE}/v2/getPubKey", timeout=self.timeout)
        pubkey_resp.raise_for_status()
        pubkey = pubkey_resp.json()

        modulus = pubkey.get("modulus", "")
        exponent = pubkey.get("exponent", "")
        if not modulus or not exponent:
            raise RuntimeError("CAS public key is missing.")

        security_js_resp = session.get(f"{CAS_BASE}/js/login/security.js", timeout=self.timeout)
        security_js_resp.raise_for_status()

        encrypted_pwd = encrypt_password_with_node(
            security_js_resp.text,
            modulus,
            exponent,
            password,
        )

        post_url = urllib.parse.urljoin("https://zjuam.zju.edu.cn", action)
        payload = {
            "username": username,
            "password": encrypted_pwd,
            "authcode": authcode,
            "execution": execution,
            "_eventId": "submit",
        }
        post_resp = session.post(post_url, data=payload, timeout=self.timeout, allow_redirects=True)
        post_resp.raise_for_status()

        for cookie in session.cookies:
            if cookie.name == "_token":
                token = extract_bearer_token_from_cookie_value(cookie.value)
                if token:
                    return token
        return ""
