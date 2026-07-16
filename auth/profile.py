from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class RoleProfile:
    uid: str = ""  # 展示用，取 roles.roleId
    nick_name: str = ""
    channel_name: str = ""
    server_id: str = ""
    server_name: str = ""
    level: int | None = None
    account_uid: str = ""  # bindingList.uid，仅备份

    def is_ready(self) -> bool:
        return bool(self.uid or self.nick_name)

    def display_server(self) -> str:
        if self.server_name:
            return self.server_name
        if self.server_id:
            return f"区服 {self.server_id}"
        return ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "uid": self.uid,
            "nick_name": self.nick_name,
            "channel_name": self.channel_name,
            "server_id": self.server_id,
            "server_name": self.server_name,
            "server_display": self.display_server(),
            "level": self.level,
            "account_uid": self.account_uid,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> "RoleProfile":
        if not raw:
            return cls()
        level_raw = raw.get("level")
        level: int | None
        try:
            level = int(level_raw) if level_raw is not None and level_raw != "" else None
        except (TypeError, ValueError):
            level = None
        return cls(
            uid=str(raw.get("uid") or raw.get("roleId") or ""),
            nick_name=str(raw.get("nick_name") or raw.get("nickName") or ""),
            channel_name=str(raw.get("channel_name") or raw.get("channelName") or ""),
            server_id=str(raw.get("server_id") or raw.get("serverId") or ""),
            server_name=str(raw.get("server_name") or raw.get("serverName") or ""),
            level=level,
            account_uid=str(raw.get("account_uid") or raw.get("accountUid") or ""),
        )


def merge_profile(base: RoleProfile, patch: RoleProfile) -> RoleProfile:
    return RoleProfile(
        uid=patch.uid or base.uid,
        nick_name=patch.nick_name or base.nick_name,
        channel_name=patch.channel_name or base.channel_name,
        server_id=patch.server_id or base.server_id,
        server_name=patch.server_name or base.server_name,
        level=patch.level if patch.level is not None else base.level,
        account_uid=patch.account_uid or base.account_uid,
    )


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def profile_from_binding_list(
    payload: dict[str, Any],
    *,
    app_code: str = "endfield",
    preferred_server_id: str | None = None,
) -> RoleProfile:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    app_list = data.get("list") if isinstance(data, dict) else None
    if not isinstance(app_list, list):
        return RoleProfile()

    for app in app_list:
        if not isinstance(app, dict):
            continue
        if app.get("appCode") and app.get("appCode") != app_code:
            continue
        bindings = app.get("bindingList") or []
        if not isinstance(bindings, list):
            continue
        for binding in bindings:
            if not isinstance(binding, dict) or binding.get("isDeleted"):
                continue
            roles = binding.get("roles") or []
            if not isinstance(roles, list) or not roles:
                continue

            selected = None
            if preferred_server_id:
                for role in roles:
                    if isinstance(role, dict) and str(role.get("serverId")) == str(preferred_server_id):
                        selected = role
                        break
            if selected is None:
                selected = next(
                    (r for r in roles if isinstance(r, dict) and r.get("isDefault")),
                    None,
                )
            if selected is None:
                selected = next((r for r in roles if isinstance(r, dict)), None)
            if not isinstance(selected, dict):
                continue

            level_raw = selected.get("level")
            try:
                level = int(level_raw) if level_raw is not None else None
            except (TypeError, ValueError):
                level = None

            return RoleProfile(
                uid=_as_text(selected.get("roleId")),
                nick_name=_as_text(selected.get("nickName")),
                channel_name=_as_text(binding.get("channelName")),
                server_id=_as_text(selected.get("serverId")),
                server_name=_as_text(selected.get("serverName")),
                level=level,
                account_uid=_as_text(binding.get("uid")),
            )
    return RoleProfile()


def extract_profile_from_json(payload: Any) -> RoleProfile:
    if isinstance(payload, dict):
        # 优先识别 binding_list 响应
        data = payload.get("data")
        if isinstance(data, dict) and isinstance(data.get("list"), list):
            bound = profile_from_binding_list(payload)
            if bound.is_ready():
                return bound

    found = RoleProfile()

    def walk(node: Any) -> None:
        nonlocal found
        if isinstance(node, list):
            for item in node:
                walk(item)
            return
        if not isinstance(node, dict):
            return

        # roles + roleId 形态
        roles = node.get("roles")
        if isinstance(roles, list) and roles:
            role = next((r for r in roles if isinstance(r, dict)), None)
            if role:
                level_raw = role.get("level")
                try:
                    level = int(level_raw) if level_raw is not None else None
                except (TypeError, ValueError):
                    level = None
                patch = RoleProfile(
                    uid=_as_text(role.get("roleId") or node.get("uid")),
                    nick_name=_as_text(role.get("nickName")),
                    channel_name=_as_text(node.get("channelName")),
                    server_id=_as_text(role.get("serverId")),
                    server_name=_as_text(role.get("serverName")),
                    level=level,
                    account_uid=_as_text(node.get("uid")) if role.get("roleId") else "",
                )
                if patch.is_ready() or patch.server_name or patch.channel_name:
                    found = merge_profile(found, patch)

        for value in node.values():
            if isinstance(value, (dict, list)):
                walk(value)

    walk(payload)
    return found


def profile_from_local_storage(items: dict[str, str]) -> RoleProfile:
    import json

    found = RoleProfile()
    for key, raw in items.items():
        if "ROLE" not in key.upper() and "ACCOUNT" not in key.upper():
            continue
        try:
            data = json.loads(raw)
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(data, dict):
            continue
        patch = RoleProfile(
            server_id=_as_text(data.get("serverId") or data.get("server_id")),
        )
        nested = extract_profile_from_json(data)
        found = merge_profile(found, merge_profile(patch, nested))
    return found


def dump_profile(profile: RoleProfile) -> dict[str, Any]:
    return asdict(profile)