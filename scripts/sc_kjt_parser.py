"""四川省科学技术厅公开通知页的最小验证解析器。

只读取本地 HTML，不发起网络请求，不进入申报系统。
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urljoin

from sc_jxt_parser import Element, clean_text, parse_html


DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
DATETIME_RE = re.compile(r"\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}:\d{2})?")
URL_RE = re.compile(r"https?://[^\s<>\"'，。；）]+")


def compact_text(value: str) -> str:
    value = clean_text(value)
    value = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", value)
    value = re.sub(r"(?<=[\u4e00-\u9fff”’）》】])\s+(?=[\u4e00-\u9fff“‘《（【])", "", value)
    value = re.sub(r"(?<=\d)\s+(?=[\u4e00-\u9fff])", "", value)
    value = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=\d)", "", value)
    value = re.sub(r"\s+([，。；：、（）])", r"\1", value)
    return value


def text_without(
    node: Element,
    *,
    excluded_ids: set[str] | None = None,
    excluded_classes: set[str] | None = None,
) -> str:
    excluded_ids = excluded_ids or set()
    excluded_classes = excluded_classes or set()
    if node.attrs.get("id") in excluded_ids or node.classes() & excluded_classes:
        return ""
    parts: list[str] = []
    for child in node.children:
        if isinstance(child, str):
            parts.append(child)
        else:
            parts.append(
                text_without(
                    child,
                    excluded_ids=excluded_ids,
                    excluded_classes=excluded_classes,
                )
            )
    return compact_text(" ".join(parts))


def parse_list(html: str, base_url: str, limit: int | None = None) -> list[dict]:
    root = parse_html(html)
    container = root.find_one(tag="div", class_name="column-list")
    if container is None:
        raise ValueError("未找到列表容器 .column-list")

    records: list[dict] = []
    for item in container.find_all(tag="li"):
        link = item.find_one(tag="a")
        date_node = item.find_one(tag="span")
        date_match = DATE_RE.search(date_node.text()) if date_node else None
        if link is None or not link.text() or date_match is None:
            continue
        records.append(
            {
                "title": compact_text(link.text()),
                "detail_url": urljoin(base_url, link.attrs.get("href", "")),
                "published_at": date_match.group(0),
            }
        )
        if limit is not None and len(records) >= limit:
            break

    if not records:
        raise ValueError("列表容器存在，但没有解析出有效记录")
    return records


def parse_detail(html: str, page_url: str) -> dict:
    root = parse_html(html)
    news_box = root.find_one(tag="div", class_name="newsTex")
    title_node = news_box.find_one(tag="h1") if news_box else None
    abstract = root.find_one(tag="div", class_name="abstract")
    body_node = root.find_one(tag="div", class_name="newsCon")
    if title_node is None or body_node is None:
        raise ValueError("详情页缺少 .newsTex h1 或 .newsCon")

    published_at = None
    info_source = None
    document_number = None
    if abstract:
        for item in abstract.find_all(tag="li"):
            text = compact_text(item.text())
            if text.startswith("发布日期："):
                match = DATETIME_RE.search(text)
                published_at = match.group(0) if match else None
            elif text.startswith("发布机构："):
                info_source = text.removeprefix("发布机构：").strip() or None
            elif text.startswith("文号：") or text.startswith("文 号："):
                document_number = text.split("：", 1)[1].strip() or None

    body = text_without(
        body_node,
        excluded_ids={"div_div", "tblArticleLink"},
        excluded_classes={"attachment", "relatedlinks"},
    )

    attachments: list[dict] = []
    attachment_box = root.find_one(tag="ul", class_name="attachment")
    if attachment_box:
        for link in attachment_box.find_all(tag="a"):
            name = compact_text(link.text()) or link.attrs.get("title", "")
            href = link.attrs.get("href", "")
            if name and href:
                attachments.append({"name": name, "url": urljoin(page_url, href)})

    issuer = "四川省科学技术厅" if "四川省科学技术厅" in body else None
    signature_dates = re.findall(r"\d{4}年\d{1,2}月\d{1,2}日", body)

    return {
        "title": compact_text(title_node.text()),
        "published_at": published_at,
        "info_source": info_source,
        "document_number": document_number,
        "issuer": issuer,
        "signature_date": signature_dates[-1] if signature_dates else None,
        "body": body,
        "attachments": attachments,
        "application_links": URL_RE.findall(body),
    }


def _main() -> None:
    import argparse
    import json

    parser = argparse.ArgumentParser(description="解析已保存的四川省科技厅 HTML")
    parser.add_argument("kind", choices=["list", "detail"])
    parser.add_argument("html", type=Path)
    parser.add_argument("--url", required=True, help="列表或详情页原始 URL")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    html = args.html.read_text(encoding="utf-8")
    result = parse_list(html, args.url, args.limit) if args.kind == "list" else parse_detail(html, args.url)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    _main()
