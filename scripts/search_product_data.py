"""查询产品聚合数据，覆盖原型的搜索、筛选、排序、分页和详情读取。"""

from __future__ import annotations

import argparse
import json
import math
import re
from datetime import date, timedelta
from pathlib import Path


DEFAULT_INPUT = Path("product-data/policies.json")
SORT_OPTIONS = ("relevance", "published_desc", "published_asc", "deadline_asc", "deadline_desc")
DATE_RANGES = ("30d", "3m", "12m", "all")


def load_policies(path: Path) -> list[dict]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError(f"找不到产品数据文件：{path}") from error
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"产品数据不是有效 UTF-8 JSON：{path}") from error
    items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        raise ValueError("产品数据缺少 items 数组")
    return items


def normalize_values(values: list[str] | None) -> set[str]:
    return {value.strip() for value in values or [] if value.strip()}


def matches_query(item: dict, query: str, *, title_only: bool = False) -> bool:
    terms = [term.casefold() for term in query.split() if term]
    if not terms:
        return True
    fields = ("title",) if title_only else ("title", "content", "document_number")
    searchable = " ".join(str(item.get(field) or "") for field in fields).casefold()
    return all(term in searchable for term in terms)


def relevance_score(item: dict, query: str) -> int:
    terms = [term.casefold() for term in query.split() if term]
    if not terms:
        return 0
    return sum(
        str(item.get("title") or "").casefold().count(term) * 3
        + str(item.get("document_number") or "").casefold().count(term) * 2
        + str(item.get("content") or "").casefold().count(term)
        for term in terms
    )


def highlight_ranges(value: str | None, query: str) -> list[list[int]]:
    """返回字符区间，交给前端安全渲染高亮，避免在数据中嵌 HTML。"""
    text = value or ""
    ranges: list[list[int]] = []
    for term in {term.casefold() for term in query.split() if term}:
        for match in re.finditer(re.escape(term), text.casefold()):
            ranges.append([match.start(), match.end()])
    return sorted(ranges)


def date_range_start(date_range: str | None, *, today: date | None = None) -> str | None:
    if not date_range or date_range == "all":
        return None
    if date_range not in DATE_RANGES:
        raise ValueError(f"不支持的快捷日期范围：{date_range}")
    today = today or date.today()
    days = {"30d": 30, "3m": 92, "12m": 365}[date_range]
    return (today - timedelta(days=days)).isoformat()


def date_part(value: object) -> str:
    return str(value or "")[:10]


def sort_items(items: list[dict], sort: str, *, query: str = "") -> list[dict]:
    if sort not in SORT_OPTIONS:
        raise ValueError(f"不支持的排序方式：{sort}")
    if sort == "relevance":
        return sorted(
            items,
            key=lambda item: (relevance_score(item, query), item.get("published_at") or "", item.get("id") or ""),
            reverse=True,
        )
    if sort.startswith("published"):
        dated = [item for item in items if item.get("published_at")]
        undated = [item for item in items if not item.get("published_at")]
        dated.sort(
            key=lambda item: item["published_at"],
            reverse=sort == "published_desc",
        )
        return dated + undated

    dated = [item for item in items if item.get("deadline")]
    undated = [item for item in items if not item.get("deadline")]
    dated.sort(key=lambda item: item["deadline"], reverse=sort == "deadline_desc")
    return dated + undated


def list_projection(item: dict, *, query: str = "") -> dict:
    """搜索列表不重复返回大段正文；详情通过 detail 查询读取。"""
    fields = (
        "id",
        "title",
        "url",
        "published_at",
        "publisher",
        "source_level",
        "department_line",
        "information_type",
        "excerpt",
        "deadline",
        "document_number",
        "source_id",
        "source_name",
        "column_name",
    )
    result = {field: item.get(field) for field in fields}
    result["highlights"] = {
        "title": highlight_ranges(item.get("title"), query),
        "excerpt": highlight_ranges(item.get("excerpt"), query),
    }
    return result


def search_policies(
    items: list[dict],
    *,
    query: str = "",
    title_only: bool = False,
    source_levels: list[str] | None = None,
    departments: list[str] | None = None,
    information_types: list[str] | None = None,
    source_ids: list[str] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    date_range: str | None = None,
    sort: str = "published_desc",
    page: int = 1,
    page_size: int = 20,
) -> dict:
    if page < 1:
        raise ValueError("页码必须大于等于 1")
    if page_size < 1 or page_size > 100:
        raise ValueError("每页数量必须在 1 到 100 之间")
    if date_from and date_to and date_from > date_to:
        raise ValueError("起始日期不能晚于结束日期")
    date_from = date_from or date_range_start(date_range)

    levels = normalize_values(source_levels)
    department_values = normalize_values(departments)
    type_values = normalize_values(information_types)
    source_values = normalize_values(source_ids)
    filtered = []
    for item in items:
        published = date_part(item.get("published_at"))
        if not matches_query(item, query, title_only=title_only):
            continue
        if levels and item.get("source_level") not in levels:
            continue
        if department_values and item.get("department_line") not in department_values:
            continue
        if type_values and item.get("information_type") not in type_values:
            continue
        if source_values and item.get("source_id") not in source_values:
            continue
        if date_from and (not published or published < date_from):
            continue
        if date_to and (not published or published > date_to):
            continue
        filtered.append(item)

    ordered = sort_items(filtered, sort, query=query)
    total = len(ordered)
    total_pages = math.ceil(total / page_size) if total else 0
    start = (page - 1) * page_size
    return {
        "query": query,
        "title_only": title_only,
        "filters": {
            "source_level": sorted(levels),
            "department_line": sorted(department_values),
            "information_type": sorted(type_values),
            "source_id": sorted(source_values),
            "date_from": date_from,
            "date_to": date_to,
            "date_range": date_range or "all",
        },
        "sort": sort,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "items": [list_projection(item, query=query) for item in ordered[start : start + page_size]],
    }


def get_policy_detail(items: list[dict], item_id: str) -> dict:
    for item in items:
        if item.get("id") == item_id:
            return item
    raise ValueError(f"未找到政策记录：{item_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description="查询政策产品聚合数据")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--query", default="", help="搜索标题、正文和文号")
    parser.add_argument("--title-only", action="store_true", help="关键词仅匹配标题")
    parser.add_argument("--level", action="append", help="发布层级，可重复传入")
    parser.add_argument("--department", action="append", help="部门条线，可重复传入")
    parser.add_argument("--type", action="append", dest="information_type", help="信息类型，可重复传入")
    parser.add_argument("--source", action="append", help="来源 ID，可重复传入")
    parser.add_argument("--date-from", help="发布日期起始日，YYYY-MM-DD")
    parser.add_argument("--date-to", help="发布日期结束日，YYYY-MM-DD")
    parser.add_argument("--date-range", choices=DATE_RANGES, help="快捷发布日期范围")
    parser.add_argument("--sort", default="published_desc", choices=SORT_OPTIONS)
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--page-size", type=int, default=20)
    parser.add_argument("--detail", help="按记录 ID 读取完整详情")
    args = parser.parse_args()
    items = load_policies(args.input)
    if args.detail:
        result = get_policy_detail(items, args.detail)
    else:
        result = search_policies(
            items,
            query=args.query,
            title_only=args.title_only,
            source_levels=args.level,
            departments=args.department,
            information_types=args.information_type,
            source_ids=args.source,
            date_from=args.date_from,
            date_to=args.date_to,
            date_range=args.date_range,
            sort=args.sort,
            page=args.page,
            page_size=args.page_size,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
