"""政策来源通用 HTTP 采集引擎。"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from information_type_classifier import classify_information_type


ListParser = Callable[[str, str, int | None], list[dict]]
DetailParser = Callable[[str, str], dict]
PageUrlBuilder = Callable[[int], str]
TextFetcher = Callable[[str], str]
USER_AGENT = "PolicySourcePilot/0.2 (public-source-collection)"
LOCAL_TIMEZONE = timezone(timedelta(hours=8))


@dataclass(frozen=True)
class SourceConfig:
    key: str
    source_id: str
    name: str
    source_level: str
    department_line: str
    column_name: str
    list_page_url: PageUrlBuilder
    parse_list: ListParser
    parse_detail: DetailParser
    default_output: Path


def current_time() -> str:
    return datetime.now(LOCAL_TIMEZONE).isoformat(timespec="seconds")


def normalize_datetime(value: str | None) -> str | None:
    """将源站常见日期格式统一成带东八区时区的 ISO 8601。"""
    if not value:
        return None
    raw_value = value.strip()
    normalized = raw_value.replace(" ", "T")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        parsed = None
        for date_format in ("%Y年%m月%d日", "%Y年%m月%d日%H时%M分"):
            try:
                parsed = datetime.strptime(raw_value, date_format)
                break
            except ValueError:
                continue
        if parsed is None:
            return value
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=LOCAL_TIMEZONE)
    return parsed.isoformat(timespec="seconds")


def external_id(source_id: str, url: str) -> str:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return f"{source_id}:{digest}"


def normalize_list_record(
    config: SourceConfig,
    item: dict,
    *,
    list_page: int,
    collected_at: str,
) -> dict:
    """统一三个来源的列表输出；未知值保持为空。"""
    return {
        "source_id": config.source_id,
        "title": item.get("title"),
        "detail_url": item.get("detail_url"),
        "published_at": normalize_datetime(item.get("published_at")),
        "published_at_evidence": "列表页可见日期文本",
        "collected_at": collected_at,
        "list_page": list_page,
        "publishing_unit": item.get("publishing_unit"),
    }


def normalize_detail_record(
    config: SourceConfig,
    *,
    detail_url: str,
    list_item: dict,
    parsed: dict | None = None,
    status: str = "ok",
    collected_at: str | None = None,
    http_status: int | None = None,
    error: str | None = None,
) -> dict:
    """转换为任务书规定的 RawFeedItem 兼容结构。"""
    parsed = parsed or {}
    published_at = parsed.get("published_at") or list_item.get("published_at")
    title = parsed.get("title") or list_item.get("title")
    content = parsed.get("body")
    classification = classify_information_type(title, content)
    return {
        "external_id": external_id(config.source_id, detail_url),
        "title": title,
        "url": detail_url,
        "published_at": normalize_datetime(published_at),
        "content": content,
        "metadata": {
            "source_id": config.source_id,
            "source_name": config.name,
            "source_level": config.source_level,
            "department_line": config.department_line,
            "column_name": config.column_name,
            "issuer": parsed.get("issuer"),
            "publishing_unit": parsed.get("publishing_unit") or list_item.get("publishing_unit"),
            "info_source": parsed.get("info_source"),
            "document_number": parsed.get("document_number"),
            "information_type": parsed.get("information_type") or classification.information_type,
            "information_type_evidence": parsed.get("information_type_evidence") or classification.evidence,
            "information_type_rule": parsed.get("information_type_rule") or classification.rule,
            "signature_date": normalize_datetime(parsed.get("signature_date")),
            "metadata_published_at": normalize_datetime(parsed.get("metadata_published_at")),
            "attachments": parsed.get("attachments") or [],
            "application_links": parsed.get("application_links") or [],
            "guideline_login_required": bool(parsed.get("guideline_login_required", False)),
            "parser_template": parsed.get("parser_template"),
            "list_page": list_item.get("list_page"),
            "list_published_at": normalize_datetime(list_item.get("published_at")),
            "published_at_evidence": "详情页可见日期文本" if parsed.get("published_at") else "列表页可见日期文本",
            "collected_at": collected_at,
            "status": status,
            "http_status": http_status,
            "error": error,
        },
    }


def record_url(record: dict) -> str | None:
    return record.get("url") or record.get("detail_url")


def record_status(record: dict) -> str | None:
    metadata = record.get("metadata")
    return metadata.get("status") if isinstance(metadata, dict) else record.get("status")


def parser_values_from_record(record: dict) -> dict:
    """将新旧两种已保存记录还原为标准化函数可接受的解析值。"""
    metadata = record.get("metadata")
    if not isinstance(metadata, dict):
        return record
    return {
        "title": record.get("title"),
        "published_at": record.get("published_at"),
        "body": record.get("content"),
        "issuer": metadata.get("issuer"),
        "publishing_unit": metadata.get("publishing_unit"),
        "info_source": metadata.get("info_source"),
        "document_number": metadata.get("document_number"),
        "signature_date": metadata.get("signature_date"),
        "metadata_published_at": metadata.get("metadata_published_at"),
        "attachments": metadata.get("attachments"),
        "application_links": metadata.get("application_links"),
        "guideline_login_required": metadata.get("guideline_login_required"),
        "parser_template": metadata.get("parser_template"),
        "information_type": metadata.get("information_type"),
        "information_type_evidence": metadata.get("information_type_evidence"),
        "information_type_rule": metadata.get("information_type_rule"),
    }


def decode_response(payload: bytes, charset: str | None) -> str:
    encodings = [charset, "utf-8", "gb18030"]
    for encoding in dict.fromkeys(value for value in encodings if value):
        try:
            return payload.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    return payload.decode("utf-8", errors="replace")


class HttpFetcher:
    def __init__(self, delay_seconds: float = 0.2, timeout_seconds: float = 30.0) -> None:
        if delay_seconds < 0:
            raise ValueError("请求间隔不能小于 0")
        self.delay_seconds = delay_seconds
        self.timeout_seconds = timeout_seconds
        self._last_started_at: float | None = None

    def __call__(self, url: str) -> str:
        if self._last_started_at is not None:
            remaining = self.delay_seconds - (time.monotonic() - self._last_started_at)
            if remaining > 0:
                time.sleep(remaining)
        self._last_started_at = time.monotonic()
        request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
        with urlopen(request, timeout=self.timeout_seconds) as response:
            payload = response.read()
            charset = response.headers.get_content_charset()
        return decode_response(payload, charset)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def detail_file_name(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest() + ".html"


def load_or_fetch(path: Path, url: str, fetch_text: TextFetcher, resume: bool) -> str:
    if resume and path.exists():
        return path.read_text(encoding="utf-8")
    html = fetch_text(url)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return html


def crawl_source(
    config: SourceConfig,
    *,
    pages: int = 10,
    output_dir: Path | None = None,
    fetch_text: TextFetcher | None = None,
    delay_seconds: float = 0.2,
    timeout_seconds: float = 30.0,
    resume: bool = True,
) -> dict:
    if pages < 1:
        raise ValueError("采集页数必须大于等于 1")
    output_dir = output_dir or config.default_output
    fetch_text = fetch_text or HttpFetcher(delay_seconds, timeout_seconds)
    list_records: list[dict] = []
    seen_urls: set[str] = set()

    for page in range(1, pages + 1):
        url = config.list_page_url(page)
        html_path = output_dir / "lists" / f"page-{page:03d}.html"
        html = load_or_fetch(html_path, url, fetch_text, resume)
        collected_at = current_time()
        for item in config.parse_list(html, url, None):
            detail_url = item["detail_url"]
            if detail_url in seen_urls:
                continue
            seen_urls.add(detail_url)
            list_records.append(
                normalize_list_record(config, item, list_page=page, collected_at=collected_at)
            )

    write_json(output_dir / "lists.json", list_records)
    details_path = output_dir / "details.json"
    previous_details: list[dict] = []
    if resume and details_path.exists():
        try:
            loaded = json.loads(details_path.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                previous_details = loaded
        except (OSError, UnicodeError, json.JSONDecodeError):
            previous_details = []

    completed = {
        record_url(item): item
        for item in previous_details
        if record_url(item) and record_status(item) == "ok"
    }
    details: list[dict] = []

    for index, list_item in enumerate(list_records, start=1):
        detail_url = list_item["detail_url"]
        if detail_url in completed:
            previous = completed[detail_url]
            previous_metadata = previous.get("metadata") if isinstance(previous.get("metadata"), dict) else {}
            details.append(
                normalize_detail_record(
                    config,
                    detail_url=detail_url,
                    list_item=list_item,
                    parsed=parser_values_from_record(previous),
                    status="ok",
                    collected_at=previous_metadata.get("collected_at") or previous.get("collected_at"),
                    http_status=previous_metadata.get("http_status") or previous.get("http_status"),
                )
            )
            continue
        html_path = output_dir / "details-html" / detail_file_name(detail_url)
        try:
            html = load_or_fetch(html_path, detail_url, fetch_text, resume)
            parsed = config.parse_detail(html, detail_url)
            record = normalize_detail_record(
                config,
                detail_url=detail_url,
                list_item=list_item,
                parsed=parsed,
                status="ok",
                collected_at=current_time(),
                http_status=200,
            )
        except HTTPError as error:
            record = normalize_detail_record(
                config,
                detail_url=detail_url,
                list_item=list_item,
                status="http_error",
                collected_at=current_time(),
                http_status=error.code,
                error=str(error),
            )
        except (URLError, TimeoutError, OSError, UnicodeError, ValueError) as error:
            record = normalize_detail_record(
                config,
                detail_url=detail_url,
                list_item=list_item,
                status="error",
                collected_at=current_time(),
                error=str(error),
            )
        details.append(record)
        write_json(details_path, details)
        print(f"[{index}/{len(list_records)}] {record_status(record)}: {detail_url}", flush=True)

    write_json(details_path, details)
    summary = {
        "source_id": config.source_id,
        "requested_pages": pages,
        "list_items": len(list_records),
        "details_ok": sum(record_status(item) == "ok" for item in details),
        "details_failed": sum(record_status(item) != "ok" for item in details),
        "delay_seconds": delay_seconds,
        "attachments_downloaded": 0,
        "images_processed": 0,
        "output_dir": str(output_dir),
    }
    write_json(output_dir / "summary.json", summary)
    return summary


def run_source_cli(config: SourceConfig, description: str) -> None:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--pages", type=int, default=10, help="从第一页开始采集的页数，默认 10")
    parser.add_argument("--delay", type=float, default=0.2, help="远程请求最小间隔秒数，默认 0.2")
    parser.add_argument("--timeout", type=float, default=30.0, help="单个请求超时秒数，默认 30")
    parser.add_argument("--output", type=Path, default=config.default_output, help="输出目录")
    parser.add_argument("--no-resume", action="store_true", help="忽略已保存 HTML 并重新请求")
    args = parser.parse_args()
    summary = crawl_source(
        config,
        pages=args.pages,
        output_dir=args.output,
        delay_seconds=args.delay,
        timeout_seconds=args.timeout,
        resume=not args.no_resume,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
