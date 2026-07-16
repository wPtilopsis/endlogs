from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from config import DATA_DIR, TOKEN_PATH
from .profile import RoleProfile


@dataclass
class SessionTokens:
    account_token: str
    role_token: str
    role_server_id: str = "1"
    language: str = "zh-cn"
    binding_token: str = ""
    profile: RoleProfile = field(default_factory=RoleProfile)

    def is_ready(self) -> bool:
        return bool(self.account_token and self.role_token)

    def to_headers(self) -> dict[str, str]:
        return {
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json",
            "origin": "https://customer-service.hypergryph.com",
            "referer": "https://customer-service.hypergryph.com/app/endfield/gamelogs/2",
            "x-account-token": self.account_token,
            "x-role-token": self.role_token,
            "x-role-server-id": self.role_server_id,
            "x-hg-language": self.language,
        }


def load_tokens(path: Path = TOKEN_PATH) -> SessionTokens | None:
    if not path.exists():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    tokens = SessionTokens(
        account_token=raw.get("account_token", ""),
        role_token=raw.get("role_token", ""),
        role_server_id=str(raw.get("role_server_id", "1")),
        language=raw.get("language", "zh-cn"),
        binding_token=raw.get("binding_token", ""),
        profile=RoleProfile.from_dict(raw.get("profile")),
    )
    if not tokens.is_ready():
        return None
    return tokens


def save_tokens(tokens: SessionTokens, path: Path = TOKEN_PATH) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "account_token": tokens.account_token,
        "role_token": tokens.role_token,
        "role_server_id": tokens.role_server_id,
        "language": tokens.language,
        "binding_token": tokens.binding_token,
        "profile": asdict(tokens.profile),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def clear_tokens(path: Path = TOKEN_PATH) -> None:
    if path.exists():
        path.unlink()