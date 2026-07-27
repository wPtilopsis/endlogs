from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qs, urlparse

from config import BINDING_APP_CODE, BINDING_PAGE_URL, LOGIN_URL
from .profile import (
    RoleProfile,
    extract_profile_from_json,
    merge_profile,
    profile_from_binding_list,
    profile_from_local_storage,
)
from .tokens import SessionTokens, save_tokens


@dataclass
class LoginState:
    status: str = "idle"  # idle | waiting | success | failed | cancelled
    message: str = ""
    updated_at: str = ""
    tokens: SessionTokens | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def set(self, status: str, message: str = "", tokens: SessionTokens | None = None) -> None:
        with self._lock:
            self.status = status
            self.message = message
            self.tokens = tokens
            self.updated_at = datetime.now(timezone.utc).isoformat()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            profile = self.tokens.profile.to_dict() if self.tokens else None
            return {
                "status": self.status,
                "message": self.message,
                "updated_at": self.updated_at,
                "logged_in": self.tokens is not None and self.tokens.is_ready(),
                "role_server_id": self.tokens.role_server_id if self.tokens else None,
                "profile": profile,
            }


_login_state = LoginState()
_login_thread: threading.Thread | None = None


def get_login_status() -> dict[str, Any]:
    return _login_state.snapshot()


def start_browser_login(timeout_s: int = 300) -> dict[str, Any]:
    global _login_thread
    snap = _login_state.snapshot()
    if snap["status"] == "waiting":
        return snap
    if _login_thread and _login_thread.is_alive():
        return _login_state.snapshot()

    _login_state.set("waiting", "正在打开浏览器，请在页面中完成登录并选择角色…")
    _login_thread = threading.Thread(
        target=_run_login_sync,
        kwargs={"timeout_s": timeout_s},
        daemon=True,
    )
    _login_thread.start()
    return _login_state.snapshot()


def _run_login_sync(timeout_s: int) -> None:
    try:
        asyncio.run(_capture_tokens(timeout_s))
    except Exception as exc:  # noqa: BLE001
        _login_state.set("failed", f"登录失败：{exc}")


def _token_from_binding_url(url: str) -> str:
    try:
        query = parse_qs(urlparse(url).query)
        values = query.get("token") or []
        return values[0] if values else ""
    except Exception:  # noqa: BLE001
        return ""


async def _read_storage_profile(page) -> RoleProfile:
    try:
        items = await page.evaluate(
            """() => {
              const out = {};
              for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                if (!key) continue;
                if (/role|account/i.test(key)) out[key] = localStorage.getItem(key);
              }
              for (let i = 0; i < sessionStorage.length; i++) {
                const key = sessionStorage.key(i);
                if (!key) continue;
                if (/role|account/i.test(key)) out['session:' + key] = sessionStorage.getItem(key);
              }
              return out;
            }"""
        )
    except Exception:  # noqa: BLE001
        return RoleProfile()
    if not isinstance(items, dict):
        return RoleProfile()
    return profile_from_local_storage({str(k): str(v or "") for k, v in items.items()})


async def _sync_binding_profile(page, captured: dict[str, str], profile: RoleProfile) -> RoleProfile:
    """在已登录浏览器上下文中打开绑定页，抓取 binding_list。"""
    result = profile
    try:
        _login_state.set("waiting", "正在同步角色绑定信息（渠道 / 区服 / UID / 昵称 / 等级）…")
        await page.goto(BINDING_PAGE_URL, wait_until="domcontentloaded")
        deadline = asyncio.get_event_loop().time() + 20
        while asyncio.get_event_loop().time() < deadline:
            if captured.get("binding_token") and result.is_ready() and result.channel_name:
                break
            if result.is_ready() and result.level is not None and result.channel_name:
                break
            await asyncio.sleep(0.4)

        if captured.get("binding_token") and not (result.is_ready() and result.channel_name):
            from client.binding import fetch_binding_profile

            try:
                fetched = await fetch_binding_profile(
                    captured["binding_token"],
                    app_code=BINDING_APP_CODE,
                    preferred_server_id=captured.get("role_server_id"),
                )
                result = merge_profile(result, fetched)
            except Exception:  # noqa: BLE001
                pass
    except Exception:  # noqa: BLE001
        return result
    return result


async def _launch_chromium(playwright: Any) -> Any:
    """优先用本机 Edge/Chrome，避免依赖数百 MB 的 Playwright Chromium。"""
    last_error: Exception | None = None
    for channel in ("msedge", "chrome"):
        try:
            return await playwright.chromium.launch(headless=False, channel=channel)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
    try:
        return await playwright.chromium.launch(headless=False)
    except Exception as exc:  # noqa: BLE001
        hint = (
            "未找到可用浏览器。请安装 Microsoft Edge / Google Chrome，"
            "或执行：python -m playwright install chromium --no-shell"
        )
        if last_error is not None:
            raise RuntimeError(f"{hint}（系统浏览器：{last_error}；Chromium：{exc}）") from exc
        raise RuntimeError(f"{hint}（{exc}）") from exc


async def _capture_tokens(timeout_s: int) -> None:
    from playwright.async_api import async_playwright

    captured = {
        "account_token": "",
        "role_token": "",
        "role_server_id": "1",
        "binding_token": "",
    }
    profile = RoleProfile()
    binding_fetched = False

    def on_request(request) -> None:
        nonlocal profile
        headers = {k.lower(): v for k, v in request.headers.items()}
        account = headers.get("x-account-token")
        role = headers.get("x-role-token")
        server_id = headers.get("x-role-server-id")
        if account:
            captured["account_token"] = account
        if role:
            captured["role_token"] = role
        if server_id:
            captured["role_server_id"] = server_id
            profile = merge_profile(profile, RoleProfile(server_id=str(server_id)))

        url = request.url or ""
        if "binding_list" in url:
            token = _token_from_binding_url(url)
            if token:
                captured["binding_token"] = token

    async def on_response(response) -> None:
        nonlocal profile
        url = response.url or ""
        try:
            ctype = (response.headers or {}).get("content-type", "")
            if "json" not in ctype.lower() and "binding_list" not in url:
                return
            data = await response.json()
        except Exception:  # noqa: BLE001
            return

        if "binding_list" in url:
            token = _token_from_binding_url(url)
            if token:
                captured["binding_token"] = token
            bound = profile_from_binding_list(
                data,
                app_code=BINDING_APP_CODE,
                preferred_server_id=captured.get("role_server_id"),
            )
            if bound.is_ready() or bound.channel_name or bound.server_name:
                profile = merge_profile(profile, bound)
            return

        profile = merge_profile(profile, extract_profile_from_json(data))

    async with async_playwright() as p:
        browser = await _launch_chromium(p)
        context = await browser.new_context()
        page = await context.new_page()
        page.on("request", on_request)
        page.on("response", on_response)
        await page.goto(LOGIN_URL, wait_until="domcontentloaded")
        _login_state.set(
            "waiting",
            "请在弹出的浏览器中登录鹰角账号，并进入终末地游戏日志页面；程序会自动捕获 token 与角色信息。",
        )

        deadline = asyncio.get_event_loop().time() + timeout_s
        token_ready_at: float | None = None
        try:
            while asyncio.get_event_loop().time() < deadline:
                storage_profile = await _read_storage_profile(page)
                profile = merge_profile(profile, storage_profile)
                if captured.get("role_server_id"):
                    profile = merge_profile(
                        profile,
                        RoleProfile(server_id=str(captured["role_server_id"])),
                    )

                tokens_ok = bool(captured["account_token"] and captured["role_token"])
                if tokens_ok and token_ready_at is None:
                    token_ready_at = asyncio.get_event_loop().time()
                    _login_state.set("waiting", "已捕获客服 token，继续同步角色绑定信息…")

                if tokens_ok:
                    waited = asyncio.get_event_loop().time() - (token_ready_at or 0)
                    profile_ok = (
                        profile.is_ready()
                        and bool(profile.channel_name)
                        and bool(profile.server_name)
                        and profile.level is not None
                    )

                    if not binding_fetched and waited >= 1.5:
                        binding_fetched = True
                        profile = await _sync_binding_profile(page, captured, profile)
                        profile_ok = (
                            profile.is_ready()
                            and bool(profile.channel_name)
                            and bool(profile.server_name)
                        )

                    if profile_ok or waited >= 25:
                        if not profile.server_id and captured.get("role_server_id"):
                            profile.server_id = str(captured["role_server_id"])
                        tokens = SessionTokens(
                            account_token=captured["account_token"],
                            role_token=captured["role_token"],
                            role_server_id=str(
                                profile.server_id or captured["role_server_id"] or "1"
                            ),
                            binding_token=captured.get("binding_token") or "",
                            profile=profile,
                        )
                        save_tokens(tokens)
                        if profile.is_ready():
                            msg = (
                                f"登录成功：{profile.nick_name or '-'} / "
                                f"UID {profile.uid or '-'} / "
                                f"{profile.channel_name or '-'} / "
                                f"{profile.server_name or '-'} / "
                                f"Lv.{profile.level if profile.level is not None else '-'}"
                            )
                        else:
                            msg = "登录成功，token 已保存（未完整捕获角色信息，可点「刷新角色信息」）。"
                        _login_state.set("success", msg, tokens)
                        await asyncio.sleep(1.0)
                        await browser.close()
                        return
                await asyncio.sleep(0.5)

            _login_state.set("failed", f"登录超时（{timeout_s}s），未捕获到完整 token。")
            await browser.close()
        except Exception as exc:  # noqa: BLE001
            _login_state.set("failed", f"登录过程异常：{exc}")
            try:
                await browser.close()
            except Exception:  # noqa: BLE001
                pass