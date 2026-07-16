from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any, AsyncIterator
from zoneinfo import ZoneInfo

import httpx

from auth.tokens import SessionTokens
from config import (
    API_BASE,
    CURRENCY_LOG_PATH,
    DEFAULT_LIMIT,
    REQUEST_INTERVAL_MS,
    REQUEST_TIMEOUT_S,
    TIMEZONE,
)


@dataclass
class CurrencyLogItem:
    currency_type: int
    change_type: int
    change_reason: str
    change_num: int
    after: int
    change_time: int
    seq_id: int

    @classmethod
    def from_api(cls, raw: dict[str, Any]) -> "CurrencyLogItem":
        return cls(
            currency_type=int(raw["currencyType"]),
            change_type=int(raw["changeType"]),
            change_reason=str(raw["changeReason"]),
            change_num=int(raw["changeNum"]),
            after=int(raw["after"]),
            change_time=int(raw["changeTime"]),
            seq_id=int(raw["seqId"]),
        )

    def to_dict(self) -> dict[str, Any]:
        tz = ZoneInfo(TIMEZONE)
        dt = datetime.fromtimestamp(self.change_time, tz=tz)
        return {
            "currencyType": self.currency_type,
            "changeType": self.change_type,
            "changeReason": self.change_reason,
            "changeNum": self.change_num,
            "after": self.after,
            "changeTime": self.change_time,
            "changeTimeText": dt.strftime("%Y-%m-%d %H:%M:%S"),
            "seqId": self.seq_id,
        }


class CurrencyLogClient:
    def __init__(self, tokens: SessionTokens) -> None:
        self.tokens = tokens

    async def fetch_page(
        self,
        currency_type: int,
        change_type: int = 0,
        limit: int = DEFAULT_LIMIT,
        seq_id: int | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "limit": limit,
            "currencyType": currency_type,
            "changeType": change_type,
        }
        if seq_id is not None:
            body["seqId"] = seq_id

        async with httpx.AsyncClient(
            base_url=API_BASE,
            timeout=REQUEST_TIMEOUT_S,
            headers=self.tokens.to_headers(),
        ) as client:
            resp = await client.post(CURRENCY_LOG_PATH, json=body)
            resp.raise_for_status()
            payload = resp.json()

        if payload.get("code") != 0:
            raise RuntimeError(payload.get("msg") or f"API error: {payload}")
        return payload.get("data") or {}

    async def iter_logs(
        self,
        currency_type: int,
        change_type: int = 0,
        limit: int = DEFAULT_LIMIT,
        start_ts: int | None = None,
        end_ts: int | None = None,
    ) -> AsyncIterator[CurrencyLogItem]:
        seq_id: int | None = None
        interval = REQUEST_INTERVAL_MS / 1000

        while True:
            data = await self.fetch_page(
                currency_type=currency_type,
                change_type=change_type,
                limit=limit,
                seq_id=seq_id,
            )
            items = data.get("list") or []
            if not items:
                break

            stop_early = False
            for raw in items:
                item = CurrencyLogItem.from_api(raw)
                if end_ts is not None and item.change_time > end_ts:
                    continue
                if start_ts is not None and item.change_time < start_ts:
                    stop_early = True
                    break
                yield item

            if stop_early or not data.get("hasNext"):
                break

            seq_id = int(items[-1]["seqId"])
            await asyncio.sleep(interval)

    async def fetch_range(
        self,
        currency_type: int,
        start_ts: int,
        end_ts: int,
        change_type: int = 0,
        limit: int = DEFAULT_LIMIT,
    ) -> list[CurrencyLogItem]:
        rows: list[CurrencyLogItem] = []
        async for item in self.iter_logs(
            currency_type=currency_type,
            change_type=change_type,
            limit=limit,
            start_ts=start_ts,
            end_ts=end_ts,
        ):
            rows.append(item)
        return rows