from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from client.currency import CurrencyLogItem
from config import CHANGE_TYPES, CURRENCY_TYPES, TIMEZONE, load_change_reasons


def date_bounds(start: date, end: date) -> tuple[int, int]:
    tz = ZoneInfo(TIMEZONE)
    start_dt = datetime.combine(start, time.min, tzinfo=tz)
    end_dt = datetime.combine(end, time.max.replace(microsecond=0), tzinfo=tz)
    return int(start_dt.timestamp()), int(end_dt.timestamp())


def reason_label(code: str | int, currency_type: int | None = None) -> str:
    # currency_type 保留兼容旧调用；三币种共用同一套 changeReason 码表
    _ = currency_type
    key = str(code).strip()
    label = load_change_reasons().get(key)
    if label:
        return label
    return f"未知原因({key})"


def signed_delta(item: CurrencyLogItem) -> int:
    if item.change_type == 2:
        return -abs(item.change_num)
    if item.change_type == 1:
        return abs(item.change_num)
    return item.change_num


def aggregate_logs(
    items: list[CurrencyLogItem],
    currency_type: int,
    start: date,
    end: date,
) -> dict[str, Any]:
    tz = ZoneInfo(TIMEZONE)
    ordered = sorted(items, key=lambda x: (x.change_time, x.seq_id))

    gained = 0
    consumed = 0
    by_reason: dict[str, dict[str, int | str]] = {}
    by_day: dict[str, dict[str, int]] = defaultdict(lambda: {"gain": 0, "consume": 0, "net": 0})

    for item in ordered:
        delta = signed_delta(item)
        day_key = datetime.fromtimestamp(item.change_time, tz=tz).strftime("%Y-%m-%d")

        if item.change_type == 1 or delta > 0:
            amount = abs(item.change_num)
            gained += amount
            by_day[day_key]["gain"] += amount
            by_day[day_key]["net"] += amount
            reason_key = item.change_reason
            slot = by_reason.setdefault(
                reason_key,
                {
                    "reason": reason_key,
                    "label": reason_label(reason_key, currency_type),
                    "count": 0,
                    "amount": 0,
                    "kind": "gain",
                },
            )
            if slot["kind"] == "gain" or item.change_type == 1:
                slot["count"] = int(slot["count"]) + 1
                slot["amount"] = int(slot["amount"]) + amount
        elif item.change_type == 2 or delta < 0:
            amount = abs(item.change_num)
            consumed += amount
            by_day[day_key]["consume"] += amount
            by_day[day_key]["net"] -= amount
            reason_key = item.change_reason
            slot = by_reason.setdefault(
                f"c:{reason_key}",
                {
                    "reason": reason_key,
                    "label": reason_label(reason_key, currency_type),
                    "count": 0,
                    "amount": 0,
                    "kind": "consume",
                },
            )
            slot["count"] = int(slot["count"]) + 1
            slot["amount"] = int(slot["amount"]) + amount

    opening = None
    closing = None
    if ordered:
        first = ordered[0]
        last = ordered[-1]
        opening = first.after - signed_delta(first)
        closing = last.after

    reason_rows = sorted(
        by_reason.values(),
        key=lambda r: (0 if r["kind"] == "gain" else 1, -int(r["amount"])),
    )
    day_rows = []
    cursor = start
    while cursor <= end:
        key = cursor.isoformat()
        day_rows.append(
            {
                "date": key,
                "gain": by_day[key]["gain"],
                "consume": by_day[key]["consume"],
                "net": by_day[key]["net"],
            }
        )
        cursor += timedelta(days=1)

    return {
        "currencyType": currency_type,
        "currencyName": CURRENCY_TYPES.get(currency_type, str(currency_type)),
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "timezone": TIMEZONE,
        "summary": {
            "opening": opening,
            "closing": closing,
            "net": (closing - opening) if opening is not None and closing is not None else gained - consumed,
            "gain": gained,
            "consume": consumed,
            "recordCount": len(ordered),
        },
        "byReason": reason_rows,
        "byDay": day_rows,
        "records": [
            item.to_dict()
            | {
                "changeTypeName": CHANGE_TYPES.get(item.change_type, str(item.change_type)),
                "changeReasonLabel": reason_label(item.change_reason, currency_type),
            }
            for item in reversed(ordered)
        ],
    }