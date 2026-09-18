"""产品页面可复用的本地 JSON 查询接口逻辑。"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from search_product_data import get_policy_detail, load_policies, search_policies


def load_sources(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError(f"找不到信息源数据文件：{path}") from error
    if not isinstance(payload, dict) or not isinstance(payload.get("sources"), list):
        raise ValueError("信息源数据缺少 sources 数组")
    return payload


def first(params: dict[str, list[str]], name: str, default: str | None = None) -> str | None:
    values = params.get(name)
    return values[0] if values else default


def integer(params: dict[str, list[str]], name: str, default: int) -> int:
    value = first(params, name)
    return int(value) if value is not None else default


def query_policies(items: list[dict], query_string: str) -> dict:
    params = parse_qs(query_string, keep_blank_values=True)
    return search_policies(
        items,
        query=first(params, "q", "") or "",
        title_only=first(params, "title_only") in {"1", "true"},
        source_levels=params.get("level"),
        departments=params.get("department"),
        information_types=params.get("type"),
        source_ids=params.get("source"),
        date_from=first(params, "date_from"),
        date_to=first(params, "date_to"),
        date_range=first(params, "date_range"),
        sort=first(params, "sort", "published_desc") or "published_desc",
        page=integer(params, "page", 1),
        page_size=integer(params, "page_size", 20),
    )


def route_request(policies_path: Path, sources_path: Path, request_target: str) -> tuple[int, dict]:
    """处理 GET 路由，供 HTTP 服务和集成测试共同使用。"""
    parsed = urlparse(request_target)
    if parsed.path == "/api/policies":
        return 200, query_policies(load_policies(policies_path), parsed.query)
    if parsed.path.startswith("/api/policies/"):
        item_id = unquote(parsed.path.removeprefix("/api/policies/"))
        return 200, get_policy_detail(load_policies(policies_path), item_id)
    if parsed.path == "/api/sources":
        return 200, load_sources(sources_path)
    return 404, {"error": "未找到接口", "path": parsed.path}
