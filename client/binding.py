from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from auth.profile import RoleProfile, profile_from_binding_list
from config import BINDING_LIST_URL, REQUEST_TIMEOUT_S


async def fetch_binding_profile(
    binding_token: str,
    *,
    app_code: str = "endfield",
    preferred_server_id: str | None = None,
) -> RoleProfile:
    token = binding_token.strip()
    if not token:
        raise ValueError("缺少 binding token")

    params = {"token": token, "appCode": app_code}
    headers = {
        "accept": "application/json, text/plain, */*",
        "origin": "https://user.hypergryph.com",
        "referer": "https://user.hypergryph.com/",
    }
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_S, headers=headers) as client:
        resp = await client.get(BINDING_LIST_URL, params=params)
        resp.raise_for_status()
        payload: dict[str, Any] = resp.json()

    if payload.get("status") not in (0, "0", None):
        raise RuntimeError(payload.get("msg") or f"binding_list 失败: {payload}")

    profile = profile_from_binding_list(
        payload,
        app_code=app_code,
        preferred_server_id=preferred_server_id,
    )
    if not profile.is_ready():
        raise RuntimeError("binding_list 未返回终末地角色信息")
    return profile


def binding_list_url(binding_token: str, app_code: str = "endfield") -> str:
    return f"{BINDING_LIST_URL}?token={quote(binding_token, safe='')}&appCode={app_code}"