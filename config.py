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
CHANGE_REASONS_REMOTE_URL = (
    "https://raw.githubusercontent.com/wPtilopsis/endlogs/main/change_reasons.json"
)
# GitHub 直连超时/失败时的备用镜像
CHANGE_REASONS_REMOTE_MIRRORS = (
    "https://cdn.jsdelivr.net/gh/wPtilopsis/endlogs@main/change_reasons.json",
)
# 从该页面发现当前前端 chunk（哈希会变，不写死文件名）
CHANGE_REASONS_OFFICIAL_PAGE_URL = (
    "https://customer-service.hypergryph.com/app/endfield/gamelogs/2"
)
CHANGE_REASONS_OFFICIAL_CDN_BASE = (
    "https://web.hycdn.cn/customer-service/web-cn"
)

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
# 码表热更下载超时（秒）
CHANGE_REASONS_DOWNLOAD_TIMEOUT_S = 30
CHANGE_REASONS_CONNECT_TIMEOUT_S = 10
# 页面常挂十余个 chunk，目标映射未必靠前；再留余量给二次发现
CHANGE_REASONS_OFFICIAL_CHUNK_TRY_LIMIT = 48

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

# 内置兜底：对齐客服中心前端枚举；外部 change_reasons.json 缺失或损坏时使用
_DEFAULT_CHANGE_REASONS: dict[str, str] = {
    "0": "其他",
    "2": "邮件领取",
    "3": "源石交易所获取",
    "4": "采购中心-组合包",
    "5": "购买月卡立得",
    "6": "解锁源石配给",
    "7": "兑换嵌晶玉",
    "8": "衍质源石兑换武库配额",
    "9": "恢复理智",
    "10": "干员寻访赠送",
    "11": "寻访消耗剩余",
    "12": "协议通行证奖励",
    "13": "任务奖励",
    "14": "世界探索奖励",
    "15": "副本奖励",
    "16": "活动中心奖励",
    "17": "提交醚质后获得",
    "18": "行动手册节点奖励",
    "19": "行动手册日常活跃度奖励",
    "20": "权限等阶提升奖励",
    "21": "月卡每日领取",
    "22": "信用交易所兑换",
    "23": "购买通行证等级",
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


def _read_change_reasons_meta(path: Path) -> dict[str, str]:
    """读取码表元数据（如 version），失败返回空。"""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    version = raw.get("version")
    if version is None or str(version).strip() == "":
        return {}
    return {"version": str(version).strip()}


def _default_change_reasons_payload() -> dict[str, object]:
    from datetime import date

    return {
        "_comment": (
            "三币种共用 changeReason 码表。放在 Endlogs.exe 同目录；"
            "改完保存后重新查询即可，无需重新打包。"
            "未收录的码会显示为「未知原因(码)」。"
            "version 为码表版本（日期）。"
        ),
        "version": date.today().isoformat(),
        "reasons": dict(sorted(_DEFAULT_CHANGE_REASONS.items(), key=lambda kv: int(kv[0]))),
    }


def _bundled_change_reasons_path() -> Path:
    return RESOURCE_DIR / CHANGE_REASONS_FILENAME


def ensure_change_reasons_file() -> Path:
    """保证可执行文件/项目根目录旁有可编辑的 change_reasons.json。"""
    if CHANGE_REASONS_PATH.exists():
        return CHANGE_REASONS_PATH

    bundled = _bundled_change_reasons_path()
    payload = _default_change_reasons_payload()
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


def change_reasons_summary() -> dict[str, object]:
    """当前本地码表摘要，供 API / 前端展示。"""
    ensure_change_reasons_file()
    reasons = load_change_reasons()
    meta = _read_change_reasons_meta(CHANGE_REASONS_PATH) if CHANGE_REASONS_PATH.exists() else {}
    return {
        "path": str(CHANGE_REASONS_PATH),
        "count": len(reasons),
        "version": meta.get("version") or "",
        "remoteUrl": CHANGE_REASONS_REMOTE_URL,
        "officialPageUrl": CHANGE_REASONS_OFFICIAL_PAGE_URL,
        "exists": CHANGE_REASONS_PATH.exists(),
    }


def apply_change_reasons_text(text: str) -> dict[str, object]:
    """校验并原子写入 change_reasons.json，然后强制重载缓存。"""
    from datetime import date

    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"远端码表不是合法 JSON：{exc}") from exc

    reasons = _normalize_reasons(raw)
    if not reasons:
        raise ValueError("远端码表缺少非空 reasons 映射")

    # 保留远端原文结构；若无 reasons 字段则包一层便于本地手改
    if isinstance(raw, dict) and isinstance(raw.get("reasons"), dict):
        if not str(raw.get("version") or "").strip():
            raw = dict(raw)
            raw["version"] = date.today().isoformat()
            payload_text = json.dumps(raw, ensure_ascii=False, indent=2) + "\n"
        else:
            payload_text = text if text.endswith("\n") else text + "\n"
        version = str(raw.get("version") or "").strip()
    else:
        version = date.today().isoformat()
        payload = _default_change_reasons_payload()
        payload["version"] = version
        payload["reasons"] = dict(
            sorted(reasons.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else kv[0])
        )
        payload_text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    tmp_path = CHANGE_REASONS_PATH.with_suffix(CHANGE_REASONS_PATH.suffix + ".tmp")
    try:
        tmp_path.write_text(payload_text, encoding="utf-8")
        # 再读一遍确认落盘内容可解析
        if _read_change_reasons_file(tmp_path) is None:
            raise ValueError("写入校验失败，已取消更新")
        tmp_path.replace(CHANGE_REASONS_PATH)
    except OSError as exc:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass
        raise ValueError(f"写入本地码表失败：{exc}") from exc

    loaded = load_change_reasons(force=True)
    version = version or _read_change_reasons_meta(CHANGE_REASONS_PATH).get("version", "")
    msg = f"码表已更新，共 {len(loaded)} 条"
    if version:
        msg += f"（版本 {version}）"
    return {
        "updated": True,
        "count": len(loaded),
        "version": version,
        "path": str(CHANGE_REASONS_PATH),
        "message": msg,
    }


def apply_change_reasons_map(
    reasons: dict[str, str],
    *,
    source: str = "manual",
) -> dict[str, object]:
    """用映射字典生成标准 JSON 并写入本地。"""
    from datetime import date

    if not reasons:
        raise ValueError("原因映射为空")
    # 官网缺省回退「其他」；本地始终保留 0
    merged = dict(reasons)
    merged.setdefault("0", "其他")
    payload = {
        "_comment": (
            "三币种共用 changeReason 码表。文案对齐客服中心前端；"
            "也可从官网 JS / GitHub 自动更新。"
            "未收录的码会显示为「未知原因(码)」。"
        ),
        "version": date.today().isoformat(),
        "source": source,
        "reasons": dict(
            sorted(merged.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else kv[0])
        ),
    }
    return apply_change_reasons_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def _parse_official_reason_map(js_text: str) -> dict[str, str] | None:
    """从客服中心前端 JS 中提取 changeReason 映射表。"""
    import re

    # 典型形态：m={2:"邮件领取",3:"源石交易所获取",...,25:"武库交易所消耗"}
    block = re.search(
        r'\{[^{}]*2\s*:\s*"邮件领取"[^{}]*25\s*:\s*"[^"]+"[^{}]*\}',
        js_text,
    )
    if not block:
        # 宽松：包含若干特征文案的对象
        block = re.search(
            r'\{[^{}]*"邮件领取"[^{}]*"武库交易所消耗"[^{}]*\}',
            js_text,
        )
    if not block:
        return None

    pairs = re.findall(r'(\d+)\s*:\s*"((?:\\.|[^"\\])*)"', block.group(0))
    if len(pairs) < 10:
        return None
    out: dict[str, str] = {}
    for key, value in pairs:
        label = value.replace(r"\"", '"').replace(r"\\", "\\").strip()
        out[str(key)] = label
    return out or None


def _normalize_chunk_url(url: str) -> str:
    url = url.strip()
    if url.startswith("http://") or url.startswith("https://"):
        return url
    if url.startswith("/"):
        return CHANGE_REASONS_OFFICIAL_CDN_BASE + url
    return f"{CHANGE_REASONS_OFFICIAL_CDN_BASE}/_next/static/chunks/{url}"


def _extract_chunk_urls(text: str) -> list[str]:
    """从 HTML/JS 文本中提取客服中心前端 chunk URL。"""
    import re

    urls: list[str] = []
    patterns = (
        r'https://web\.hycdn\.cn/customer-service/web-cn/_next/static/chunks/[^"\'\s>]+\.js',
        r'/_next/static/chunks/[^"\'\s>]+\.js',
        r'static/chunks/([a-f0-9]{8,}\.js)',
    )
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            raw = match.group(1) if pattern.startswith("static/chunks/") else match.group(0)
            url = _normalize_chunk_url(raw)
            if url not in urls:
                urls.append(url)
    return urls


def _change_reasons_http_timeout():
    import httpx

    return httpx.Timeout(
        CHANGE_REASONS_DOWNLOAD_TIMEOUT_S,
        connect=CHANGE_REASONS_CONNECT_TIMEOUT_S,
    )


def _format_download_error(exc: Exception, *, where: str) -> str:
    name = type(exc).__name__
    text = str(exc).strip() or name
    if "timed out" in text.lower() or "timeout" in name.lower():
        return (
            f"{where}下载超时（{text}）。"
            "可改用另一来源、手动更新，或检查网络/代理后重试。"
        )
    return f"{where}下载失败：{text}"


def update_change_reasons_from_official() -> dict[str, object]:
    """从客服中心前端 JS 解析最新 changeReason 映射并覆盖本地。

    不写死 chunk 哈希：从流水页出发，BFS 发现并下载 JS，解析到映射即停止。
    """
    import httpx

    try:
        with httpx.Client(
            timeout=_change_reasons_http_timeout(),
            follow_redirects=True,
        ) as client:
            try:
                page_resp = client.get(CHANGE_REASONS_OFFICIAL_PAGE_URL)
                page_resp.raise_for_status()
                page_text = page_resp.text
            except Exception as exc:  # noqa: BLE001
                raise ValueError(_format_download_error(exc, where="官网页面")) from exc

            import re

            primary = _extract_chunk_urls(page_text)
            for match in re.finditer(
                r'(?:https://web\.hycdn\.cn/customer-service/web-cn)?/_next/static/[^"\'\s>]+/_buildManifest\.js',
                page_text,
            ):
                manifest_url = _normalize_chunk_url(match.group(0))
                if manifest_url not in primary:
                    primary.append(manifest_url)

            if not primary:
                raise ValueError(
                    "未能从客服中心页面发现前端 chunk。可改用 GitHub 更新或手动粘贴。"
                )

            # 先扫页面列出的 chunk，再扫二次发现的；框架脚本往后排
            def _chunk_priority(url: str) -> int:
                name = url.rsplit("/", 1)[-1].lower()
                if name.startswith("turbopack-") or "framework" in name or "polyfill" in name:
                    return 1
                return 0

            primary.sort(key=_chunk_priority)
            secondary: list[str] = []
            seen: set[str] = set()
            tried = 0
            last_error = ""
            phase = "primary"
            queue = primary
            while tried < CHANGE_REASONS_OFFICIAL_CHUNK_TRY_LIMIT:
                if not queue:
                    if phase == "primary" and secondary:
                        phase = "secondary"
                        queue = secondary
                        secondary = []
                    else:
                        break
                url = queue.pop(0)
                if url in seen:
                    continue
                seen.add(url)
                tried += 1
                try:
                    resp = client.get(url)
                    resp.raise_for_status()
                    text = resp.text
                except Exception as exc:  # noqa: BLE001
                    last_error = _format_download_error(exc, where="官网")
                    continue

                # 页面直链扫完前，新发现的 URL 进 secondary，避免插队挤掉页面后半段
                for next_url in _extract_chunk_urls(text):
                    if next_url in seen:
                        continue
                    if phase == "primary":
                        if next_url not in primary and next_url not in secondary:
                            secondary.append(next_url)
                    elif next_url not in queue:
                        queue.append(next_url)

                reasons = _parse_official_reason_map(text)
                if reasons:
                    result = apply_change_reasons_map(reasons, source="official")
                    result["message"] = (
                        f"已从官网解析码表，共 {result['count']} 条"
                        + (f"（版本 {result.get('version')}）" if result.get("version") else "")
                    )
                    result["source"] = "official"
                    result["chunkUrl"] = url
                    return result

                if "邮件领取" in text and "武库交易所消耗" in text:
                    last_error = f"{url} 含特征文案但解析失败"
                else:
                    last_error = f"{url} 未解析到原因映射"

    except httpx.HTTPError as exc:
        raise ValueError(_format_download_error(exc, where="官网")) from exc
    except ValueError:
        raise

    raise ValueError(
        "未能从官网前端解析出原因码表。可改用 GitHub 更新或手动粘贴。"
        + (f"（{last_error}）" if last_error else "")
    )


def update_change_reasons_from_remote() -> dict[str, object]:
    """从 GitHub raw（及镜像）拉取最新码表并覆盖本地文件。"""
    import httpx

    urls = (CHANGE_REASONS_REMOTE_URL, *CHANGE_REASONS_REMOTE_MIRRORS)
    errors: list[str] = []
    try:
        with httpx.Client(
            timeout=_change_reasons_http_timeout(),
            follow_redirects=True,
        ) as client:
            for url in urls:
                try:
                    resp = client.get(url)
                    resp.raise_for_status()
                    result = apply_change_reasons_text(resp.text)
                    result["source"] = "git"
                    if url != CHANGE_REASONS_REMOTE_URL:
                        result["message"] = (
                            f"{result.get('message', '码表已更新')}（经镜像）"
                        )
                    result["remoteUrl"] = url
                    return result
                except Exception as exc:  # noqa: BLE001
                    errors.append(_format_download_error(exc, where=url))
                    continue
    except httpx.HTTPError as exc:
        raise ValueError(_format_download_error(exc, where="GitHub")) from exc

    detail = "；".join(errors[-3:]) if errors else "未知错误"
    raise ValueError(f"下载码表失败：{detail}（可改用官网或手动更新）")


def update_change_reasons(source: str = "git") -> dict[str, object]:
    """按来源更新码表：git | official。"""
    key = (source or "git").strip().lower()
    if key in {"official", "官网", "hycdn", "web"}:
        return update_change_reasons_from_official()
    if key in {"git", "github", "remote"}:
        return update_change_reasons_from_remote()
    raise ValueError(f"未知更新来源：{source}（可用 official / git）")


TIMEZONE = "Asia/Shanghai"
