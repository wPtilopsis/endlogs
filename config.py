from __future__ import annotations

import json
import sys
from pathlib import Path


def app_base_dir() -> Path:
    """源码运行：项目根目录；PyInstaller 打包：可执行文件所在目录。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def resource_dir() -> Path:
    """静态资源目录（打包后可能在临时解压目录）。"""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return app_base_dir()


BASE_DIR = app_base_dir()
RESOURCE_DIR = resource_dir()
DATA_DIR = BASE_DIR / "data"
TOKEN_PATH = DATA_DIR / "tokens.json"
WEB_DIR = RESOURCE_DIR / "web"
CHANGE_REASONS_PATH = BASE_DIR / "change_reasons.json"
CHANGE_REASONS_FILENAME = "change_reasons.json"

API_BASE = "https://customer-service.hypergryph.com"
CURRENCY_LOG_PATH = "/api/center/open/v1/endfield/game_logs/currency"
LOGIN_URL = "https://customer-service.hypergryph.com/app/endfield/gamelogs/2"
BINDING_LIST_URL = (
    "https://binding-api-account-prod.hypergryph.com/account/binding/v1/binding_list"
)
BINDING_PAGE_URL = "https://user.hypergryph.com/bindCharacters"
BINDING_APP_CODE = "endfield"

HOST = "127.0.0.1"
PORT = 8787

DEFAULT_LIMIT = 50
REQUEST_INTERVAL_MS = 250
REQUEST_TIMEOUT_S = 30

CURRENCY_TYPES = {
    1: "源石",
    2: "嵌晶玉",
    3: "武库配额",
}

CHANGE_TYPES = {
    0: "全部",
    1: "获取",
    2: "消耗",
}

# 内置兜底：外部 change_reasons.json 缺失或损坏时使用
_DEFAULT_CHANGE_REASONS: dict[str, str] = {
    "0": "其他",
    "2": "邮件领取",
    "4": "采购中心-组合包",
    "5": "购买月卡立得",
    "6": "解锁源石配给",
    "8": "衍质源石兑换武库配额",
    "10": "干员寻访",
    "12": "协议通行证奖励",
    "13": "任务奖励",
    "14": "世界探索奖励",
    "15": "副本奖励",
    "16": "活动中心奖励",
    "17": "提交醚质后获得",
    "19": "行动手册日常活跃度奖励",
    "21": "月卡每日领取",
    "22": "信用交易所兑换",
    "24": "系统玩法奖励",
    "25": "武库交易所消耗",
}

_change_reasons_cache: tuple[float | None, dict[str, str]] | None = None


def _normalize_reasons(raw: object) -> dict[str, str] | None:
    if not isinstance(raw, dict):
        return None
    reasons = raw.get("reasons", raw)
    if not isinstance(reasons, dict):
        return None
    out: dict[str, str] = {}
    for key, value in reasons.items():
        if str(key).startswith("_"):
            continue
        if value is None:
            continue
        out[str(key).strip()] = str(value).strip()
    return out or None


def _read_change_reasons_file(path: Path) -> dict[str, str] | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return _normalize_reasons(raw)


def _bundled_change_reasons_path() -> Path:
    return RESOURCE_DIR / CHANGE_REASONS_FILENAME


def ensure_change_reasons_file() -> Path:
    """保证可执行文件/项目根目录旁有可编辑的 change_reasons.json。"""
    if CHANGE_REASONS_PATH.exists():
        return CHANGE_REASONS_PATH

    bundled = _bundled_change_reasons_path()
    payload = {
        "_comment": (
            "三币种共用 changeReason 码表。放在 Endlogs.exe 同目录；"
            "改完保存后重新查询即可，无需重新打包。"
            "未收录的码会显示为「未知原因(码)」。"
        ),
        "reasons": dict(sorted(_DEFAULT_CHANGE_REASONS.items(), key=lambda kv: int(kv[0]))),
    }
    if bundled.exists() and bundled.resolve() != CHANGE_REASONS_PATH.resolve():
        try:
            CHANGE_REASONS_PATH.write_text(bundled.read_text(encoding="utf-8"), encoding="utf-8")
            return CHANGE_REASONS_PATH
        except OSError:
            pass

    try:
        CHANGE_REASONS_PATH.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError:
        pass
    return CHANGE_REASONS_PATH


def load_change_reasons(*, force: bool = False) -> dict[str, str]:
    """加载三币种共用的 changeReason 映射；优先读 exe/项目旁配置文件。"""
    global _change_reasons_cache

    ensure_change_reasons_file()
    path = CHANGE_REASONS_PATH if CHANGE_REASONS_PATH.exists() else _bundled_change_reasons_path()
    mtime: float | None
    try:
        mtime = path.stat().st_mtime if path.exists() else None
    except OSError:
        mtime = None

    if (
        not force
        and _change_reasons_cache is not None
        and _change_reasons_cache[0] == mtime
    ):
        return _change_reasons_cache[1]

    reasons = None
    if path.exists():
        reasons = _read_change_reasons_file(path)
    if reasons is None and path != _bundled_change_reasons_path():
        bundled = _bundled_change_reasons_path()
        if bundled.exists():
            reasons = _read_change_reasons_file(bundled)
    if reasons is None:
        reasons = dict(_DEFAULT_CHANGE_REASONS)

    _change_reasons_cache = (mtime, reasons)
    return reasons


# 兼容旧导入名；运行时应优先调用 load_change_reasons()
CHANGE_REASONS = load_change_reasons()

TIMEZONE = "Asia/Shanghai"
