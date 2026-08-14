from __future__ import annotations

import csv
import io
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from auth import clear_tokens, get_login_status, load_tokens, save_tokens, start_browser_login
from auth.tokens import SessionTokens
from client import CurrencyLogClient
from client.binding import fetch_binding_profile
from config import (
    CHANGE_TYPES,
    CURRENCY_TYPES,
    DATA_DIR,
    WEB_DIR,
    apply_change_reasons_text,
    change_reasons_summary,
    update_change_reasons_from_remote,
)
from stats import aggregate_logs, date_bounds

app = FastAPI(title="终末地资源日志助手", version="0.1.0")
DATA_DIR.mkdir(parents=True, exist_ok=True)


class ManualTokenBody(BaseModel):
    account_token: str = Field(min_length=1)
    role_token: str = Field(min_length=1)
    role_server_id: str = "1"
    language: str = "zh-cn"
    binding_token: str = ""


class BindingTokenBody(BaseModel):
    binding_token: str = Field(min_length=1)


class QueryBody(BaseModel):
    start_date: date
    end_date: date
    currency_types: list[int] = Field(default_factory=lambda: [1, 2, 3])
    change_type: int = 0


class ChangeReasonsManualBody(BaseModel):
    content: str = Field(min_length=2)


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    index_path = WEB_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="前端页面缺失")
    return HTMLResponse(index_path.read_text(encoding="utf-8"))


@app.get("/api/meta")
async def meta() -> dict[str, Any]:
    summary = change_reasons_summary()
    return {
        "currencyTypes": [{"id": k, "name": v} for k, v in CURRENCY_TYPES.items()],
        "changeTypes": [{"id": k, "name": v} for k, v in CHANGE_TYPES.items()],
        "changeReasonsCount": summary["count"],
        "changeReasonsVersion": summary.get("version") or "",
    }


@app.get("/api/change-reasons")
async def get_change_reasons() -> dict[str, Any]:
    return change_reasons_summary()


@app.post("/api/change-reasons/update")
def update_change_reasons() -> dict[str, Any]:
    try:
        return update_change_reasons_from_remote()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/change-reasons/update-manual")
def update_change_reasons_manual(body: ChangeReasonsManualBody) -> dict[str, Any]:
    try:
        return apply_change_reasons_text(body.content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/auth/status")
async def auth_status() -> dict[str, Any]:
    tokens = load_tokens()
    browser = get_login_status()
    profile = tokens.profile.to_dict() if tokens else None
    return {
        "logged_in": tokens is not None and tokens.is_ready(),
        "role_server_id": tokens.role_server_id if tokens else None,
        "has_binding_token": bool(tokens and tokens.binding_token),
        "profile": profile,
        "browser_login": browser,
    }


@app.post("/api/auth/browser-login")
async def auth_browser_login() -> dict[str, Any]:
    return start_browser_login()


@app.post("/api/auth/manual")
async def auth_manual(body: ManualTokenBody) -> dict[str, Any]:
    tokens = SessionTokens(
        account_token=body.account_token.strip(),
        role_token=body.role_token.strip(),
        role_server_id=body.role_server_id.strip() or "1",
        language=body.language or "zh-cn",
        binding_token=body.binding_token.strip(),
    )
    if tokens.binding_token:
        try:
            tokens.profile = await fetch_binding_profile(
                tokens.binding_token,
                preferred_server_id=tokens.role_server_id,
            )
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=502, detail=f"binding_list 查询失败：{exc}") from exc
    save_tokens(tokens)
    return {
        "ok": True,
        "logged_in": True,
        "role_server_id": tokens.role_server_id,
        "profile": tokens.profile.to_dict(),
    }


@app.post("/api/auth/binding-token")
async def auth_save_binding_token(body: BindingTokenBody) -> dict[str, Any]:
    tokens = load_tokens()
    if tokens is None or not tokens.is_ready():
        raise HTTPException(status_code=401, detail="请先完成客服登录")
    tokens.binding_token = body.binding_token.strip()
    try:
        tokens.profile = await fetch_binding_profile(
            tokens.binding_token,
            preferred_server_id=tokens.role_server_id,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"binding_list 查询失败：{exc}") from exc
    save_tokens(tokens)
    return {"ok": True, "profile": tokens.profile.to_dict()}


@app.post("/api/auth/refresh-profile")
async def auth_refresh_profile() -> dict[str, Any]:
    tokens = load_tokens()
    if tokens is None or not tokens.is_ready():
        raise HTTPException(status_code=401, detail="未登录")
    if not tokens.binding_token:
        raise HTTPException(
            status_code=400,
            detail="缺少 binding token。请重新「浏览器登录」，或手动粘贴 binding_list 的 token",
        )
    try:
        tokens.profile = await fetch_binding_profile(
            tokens.binding_token,
            preferred_server_id=tokens.role_server_id,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"刷新失败：{exc}") from exc
    save_tokens(tokens)
    return {"ok": True, "profile": tokens.profile.to_dict()}


@app.post("/api/auth/logout")
async def auth_logout() -> dict[str, Any]:
    clear_tokens()
    return {"ok": True, "logged_in": False}


@app.post("/api/query")
async def query_logs(body: QueryBody) -> dict[str, Any]:
    tokens = load_tokens()
    if tokens is None or not tokens.is_ready():
        raise HTTPException(status_code=401, detail="未登录，请先完成浏览器登录或手动粘贴 token")
    if body.start_date > body.end_date:
        raise HTTPException(status_code=400, detail="开始日期不能晚于结束日期")
    if not body.currency_types:
        raise HTTPException(status_code=400, detail="至少选择一种资源")

    start_ts, end_ts = date_bounds(body.start_date, body.end_date)
    client = CurrencyLogClient(tokens)
    results = []
    try:
        for currency_type in body.currency_types:
            items = await client.fetch_range(
                currency_type=currency_type,
                start_ts=start_ts,
                end_ts=end_ts,
                change_type=body.change_type,
            )
            results.append(
                aggregate_logs(
                    items=items,
                    currency_type=currency_type,
                    start=body.start_date,
                    end=body.end_date,
                )
            )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"查询失败：{exc}") from exc

    return {"ok": True, "results": results}


@app.get("/api/export.csv")
async def export_csv(
    start_date: date = Query(...),
    end_date: date = Query(...),
    currency_type: int = Query(1),
    change_type: int = Query(0),
) -> StreamingResponse:
    tokens = load_tokens()
    if tokens is None or not tokens.is_ready():
        raise HTTPException(status_code=401, detail="未登录")
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="开始日期不能晚于结束日期")

    start_ts, end_ts = date_bounds(start_date, end_date)
    client = CurrencyLogClient(tokens)
    try:
        items = await client.fetch_range(
            currency_type=currency_type,
            start_ts=start_ts,
            end_ts=end_ts,
            change_type=change_type,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"导出失败：{exc}") from exc

    agg = aggregate_logs(items, currency_type, start_date, end_date)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["时间", "资源", "变动类型", "原因码", "原因", "变动数量", "变动后存量", "seqId"]
    )
    currency_name = CURRENCY_TYPES.get(currency_type, str(currency_type))
    for row in agg["records"]:
        writer.writerow(
            [
                row["changeTimeText"],
                currency_name,
                row["changeTypeName"],
                row["changeReason"],
                row["changeReasonLabel"],
                row["changeNum"],
                row["after"],
                row["seqId"],
            ]
        )
    buf.seek(0)
    filename = f"endfield_{currency_type}_{start_date}_{end_date}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


def run() -> None:
    import uvicorn

    from config import HOST, PORT

    # reload 关闭，避免浏览器登录线程状态被热重载清空
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=False)


if __name__ == "__main__":
    run()