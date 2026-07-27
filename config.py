from __future__ import annotations

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

# changeReason 按币种映射；未收录的展示为「未知原因(码)」
CHANGE_REASONS_BY_CURRENCY: dict[int, dict[str, str]] = {
    1: {  # 源石
        "12": "协议通行证奖励",
        "5": "购买月卡立得",
        "17": "提交醚质后获得",
        "14": "世界探索奖励",
        "6": "解锁源石配给",
        "13": "任务奖励",
        "4": "采购中心-组合包",
    },
    2: {  # 嵌晶玉
        "10": "干员寻访消耗",
        "24": "系统玩法奖励",
        "0": "其他",
        "19": "行动手册日常活跃度奖励",
        "22": "信用交易所兑换",
        "21": "月卡每日领取",
        "14": "世界探索奖励",
        "16": "活动中心奖励",
        "2": "邮件领取",
        "13": "任务奖励",
        "12": "协议通行证奖励",
        "15": "副本奖励",
    },
    3: {  # 武库配额
        "10": "干员寻访赠送",
        "25": "武库交易所消耗",
    },
}

TIMEZONE = "Asia/Shanghai"
