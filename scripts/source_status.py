"""生成产品信息源导航页使用的来源级运行状态。"""

from __future__ import annotations

from typing import Any


def build_source_status(
    config: Any,
    *,
    run_started_at: str,
    updated_at: str,
    records_discovered: int,
    records_collected: int,
    records_failed: int,
    last_error: str | None = None,
    previous: dict | None = None,
    blocked: bool = False,
) -> dict:
    previous = previous or {}
    if blocked:
        status = "blocked"
    elif records_collected == 0:
        status = "failed"
    elif records_failed > 0:
        status = "partial"
    else:
        status = "normal"

    previous_failures = previous.get("consecutive_failures", 0)
    if not isinstance(previous_failures, int) or previous_failures < 0:
        previous_failures = 0
    consecutive_failures = 0 if status == "normal" else previous_failures + 1
    last_success_at = updated_at if records_collected > 0 else previous.get("last_success_at")

    return {
        "schema_version": 1,
        "source_id": config.source_id,
        "source_name": config.name,
        "source_level": config.source_level,
        "department_line": config.department_line,
        "column_name": config.column_name,
        "official_url": config.official_url,
        "list_url": config.list_page_url(1),
        "collection_method": config.collection_method,
        "status": status,
        "last_run_at": run_started_at,
        "last_success_at": last_success_at,
        "updated_at": updated_at,
        "records_discovered": records_discovered,
        "records_collected": records_collected,
        "records_failed": records_failed,
        "consecutive_failures": consecutive_failures,
        "last_error": last_error,
    }
