"""政策来源通用 HTTP 采集引擎。"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ListParser = Callable[[str, str, int | None], list[dict]]
DetailParser = Callable[[str, str], dict]
PageUrlBuilder = Callable[[int], str]
TextFetcher = Callable[[str], str]
USER_AGENT = "PolicySourcePilot/0.2 (public-source-collection)"


@dataclass(frozen=True)
class SourceConfig:
    key: str
    source_id: str
    name: str
    list_page_url: PageUrlBuilder
    parse_list: ListParser
    parse_detail: DetailParser
    default_output: Path


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
        for item in config.parse_list(html, url, None):
            detail_url = item["detail_url"]
            if detail_url in seen_urls:
                continue
            seen_urls.add(detail_url)
            list_records.append({"source_id": config.source_id, "list_page": page, **item})

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
        item.get("detail_url"): item
        for item in previous_details
        if item.get("detail_url") and item.get("status") == "ok"
    }
    details: list[dict] = []

    for index, list_item in enumerate(list_records, start=1):
        detail_url = list_item["detail_url"]
        if detail_url in completed:
            details.append(completed[detail_url])
            continue
        html_path = output_dir / "details-html" / detail_file_name(detail_url)
        try:
            html = load_or_fetch(html_path, detail_url, fetch_text, resume)
            parsed = config.parse_detail(html, detail_url)
            record = {
                "source_id": config.source_id,
                "detail_url": detail_url,
                "list_page": list_item["list_page"],
                "list_published_at": list_item["published_at"],
                "status": "ok",
                **parsed,
            }
        except HTTPError as error:
            record = {
                "source_id": config.source_id,
                "detail_url": detail_url,
                "list_page": list_item["list_page"],
                "title": list_item["title"],
                "status": "http_error",
                "http_status": error.code,
                "error": str(error),
            }
        except (URLError, TimeoutError, OSError, UnicodeError, ValueError) as error:
            record = {
                "source_id": config.source_id,
                "detail_url": detail_url,
                "list_page": list_item["list_page"],
                "title": list_item["title"],
                "status": "error",
                "error": str(error),
            }
        details.append(record)
        write_json(details_path, details)
        print(f"[{index}/{len(list_records)}] {record['status']}: {detail_url}", flush=True)

    write_json(details_path, details)
    summary = {
        "source_id": config.source_id,
        "requested_pages": pages,
        "list_items": len(list_records),
        "details_ok": sum(item["status"] == "ok" for item in details),
        "details_failed": sum(item["status"] != "ok" for item in details),
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
