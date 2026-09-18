"""比较同一来源两次标准化详情输出，生成新增、重复、更新、失效和失败结果。"""

from __future__ import annotations

import hashlib
import json


def record_key(record: dict) -> str | None:
    return record.get("external_id") or record.get("url") or record.get("detail_url")


def record_status(record: dict) -> str:
    metadata = record.get("metadata")
    return metadata.get("status", "ok") if isinstance(metadata, dict) else record.get("status", "ok")


def fingerprint(record: dict) -> str:
    """仅比较用户可见政策内容，忽略采集时间、HTTP 状态等运行字段。"""
    metadata = record.get("metadata") if isinstance(record.get("metadata"), dict) else {}
    value = {
        "title": record.get("title"),
        "url": record.get("url"),
        "published_at": record.get("published_at"),
        "content": record.get("content"),
        "publisher": metadata.get("publisher"),
        "document_number": metadata.get("document_number"),
        "information_type": metadata.get("information_type"),
        "deadline": metadata.get("deadline"),
        "attachments": metadata.get("attachments"),
    }
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def comparison_item(record: dict, *, before: dict | None = None) -> dict:
    result = {
        "id": record_key(record),
        "title": record.get("title"),
        "url": record.get("url") or record.get("detail_url"),
    }
    if before is not None:
        result["before_fingerprint"] = fingerprint(before)
        result["after_fingerprint"] = fingerprint(record)
    return result


def compare_runs(previous: list[dict], current: list[dict]) -> dict:
    old = {key: record for record in previous if isinstance(record, dict) if (key := record_key(record))}
    new = {key: record for record in current if isinstance(record, dict) if (key := record_key(record))}
    result = {"new": [], "repeated": [], "updated": [], "invalid": [], "failed": []}

    for key, record in new.items():
        if record_status(record) != "ok":
            result["failed"].append(comparison_item(record))
            continue
        previous_record = old.get(key)
        if previous_record is None:
            result["new"].append(comparison_item(record))
        elif record_status(previous_record) != "ok" or fingerprint(previous_record) != fingerprint(record):
            result["updated"].append(comparison_item(record, before=previous_record))
        else:
            result["repeated"].append(comparison_item(record))

    for key, record in old.items():
        if key not in new and record_status(record) == "ok":
            result["invalid"].append(comparison_item(record))

    for items in result.values():
        items.sort(key=lambda item: item["id"] or "")
    result["counts"] = {name: len(items) for name, items in result.items() if name != "counts"}
    return result
