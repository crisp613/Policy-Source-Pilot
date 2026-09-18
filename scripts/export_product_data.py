"""将三个来源的标准化结果聚合为产品列表、详情和信息源导航数据。"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from policy_source_crawler import current_time, write_json


SOURCE_IDS = ("sc-jxt-notices", "sc-kjt-notices", "most-service-notices")
DETAIL_RELATIVE_PATH = Path("first-10-pages/details.json")
STATUS_RELATIVE_PATH = Path("first-10-pages/source-status.json")
REQUIRED_DETAIL_FIELDS = {"external_id", "title", "url", "published_at", "content", "metadata"}


def read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError(f"缺少输入文件：{path}") from error
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"输入文件不是有效 UTF-8 JSON：{path}") from error


def make_excerpt(content: str | None, limit: int = 180) -> str:
    compact = re.sub(r"\s+", " ", content or "").strip()
    return compact if len(compact) <= limit else compact[:limit].rstrip() + "…"


def product_item(record: dict) -> dict:
    missing = REQUIRED_DETAIL_FIELDS - set(record)
    if missing:
        raise ValueError(f"详情记录不是统一结构，缺少字段：{', '.join(sorted(missing))}")
    metadata = record["metadata"]
    if not isinstance(metadata, dict):
        raise ValueError("详情记录 metadata 必须是对象")
    return {
        "id": record["external_id"],
        "title": record["title"],
        "url": record["url"],
        "published_at": record["published_at"],
        "publisher": metadata.get("publisher"),
        "source_level": metadata.get("source_level"),
        "department_line": metadata.get("department_line"),
        "information_type": metadata.get("information_type"),
        "excerpt": make_excerpt(record.get("content")),
        "deadline": metadata.get("deadline"),
        "document_number": metadata.get("document_number"),
        "source_id": metadata.get("source_id"),
        "source_name": metadata.get("source_name"),
        "column_name": metadata.get("column_name"),
        "collection_method": metadata.get("collection_method"),
        "collected_at": metadata.get("collected_at"),
        "attachments": metadata.get("attachments") or [],
        "application_links": metadata.get("application_links") or [],
        "images": metadata.get("images") or [],
        "image_ocr_status": metadata.get("image_ocr_status"),
        "deadlines": metadata.get("deadlines") or [],
        "content": record.get("content"),
        "field_status": {
            "publisher": metadata.get("publisher_status"),
            "deadline": metadata.get("deadline_status"),
            "document_number": metadata.get("document_number_status"),
        },
    }


def count_values(items: list[dict], field: str) -> dict[str, int]:
    counts = Counter(item[field] for item in items if item.get(field))
    return dict(sorted(counts.items()))


def export_product_data(
    artifacts_root: Path,
    output_dir: Path,
    *,
    source_ids: tuple[str, ...] = SOURCE_IDS,
    generated_at: str | None = None,
) -> dict:
    generated_at = generated_at or current_time()
    items_by_id: dict[str, dict] = {}
    skipped_failed = 0
    sources = []

    for source_id in source_ids:
        source_dir = artifacts_root / source_id
        details = read_json(source_dir / DETAIL_RELATIVE_PATH)
        if not isinstance(details, list):
            raise ValueError(f"{source_id} 的 details.json 必须是数组")
        for record in details:
            if not isinstance(record, dict):
                raise ValueError(f"{source_id} 的详情记录必须是对象")
            metadata = record.get("metadata")
            if isinstance(metadata, dict) and metadata.get("status") != "ok":
                skipped_failed += 1
                continue
            item = product_item(record)
            items_by_id[item["id"]] = item

        source_status = read_json(source_dir / STATUS_RELATIVE_PATH)
        if not isinstance(source_status, dict):
            raise ValueError(f"{source_id} 的 source-status.json 必须是对象")
        sources.append(source_status)

    items = sorted(
        items_by_id.values(),
        key=lambda item: (item.get("published_at") or "", item.get("id") or ""),
        reverse=True,
    )
    policies = {
        "schema_version": 1,
        "generated_at": generated_at,
        "total": len(items),
        "skipped_failed": skipped_failed,
        "search_fields": ["title", "content", "document_number"],
        "facets": {
            "source_level": count_values(items, "source_level"),
            "department_line": count_values(items, "department_line"),
            "information_type": count_values(items, "information_type"),
            "unclassified": sum(item.get("information_type") is None for item in items),
        },
        "items": items,
    }
    source_navigation = {
        "schema_version": 1,
        "generated_at": generated_at,
        "total": len(sources),
        "sources": sorted(sources, key=lambda item: item.get("source_id") or ""),
    }
    write_json(output_dir / "policies.json", policies)
    write_json(output_dir / "sources.json", source_navigation)
    return {
        "policies": len(items),
        "sources": len(sources),
        "skipped_failed": skipped_failed,
        "output_dir": str(output_dir),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="聚合三个政策来源的产品数据")
    parser.add_argument("--artifacts-root", type=Path, default=Path("local-artifacts"))
    parser.add_argument("--output", type=Path, default=Path("product-data"))
    args = parser.parse_args()
    result = export_product_data(args.artifacts_root, args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
