"""四川省经济和信息化厅公开通知页的最小验证解析器。

仅用于本地证据验证。模块不发起网络请求，也不写入业务系统。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin


DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
URL_RE = re.compile(r"https?://[^\s<>\"'，。；）]+")


@dataclass
class Element:
    tag: str
    attrs: dict[str, str]
    parent: "Element | None" = None
    children: list["Element | str"] = field(default_factory=list)

    def classes(self) -> set[str]:
        return set(self.attrs.get("class", "").split())

    def text(self, excluded_ids: set[str] | None = None) -> str:
        excluded_ids = excluded_ids or set()
        if self.attrs.get("id") in excluded_ids:
            return ""
        parts: list[str] = []
        for child in self.children:
            parts.append(child if isinstance(child, str) else child.text(excluded_ids))
        return clean_text(" ".join(parts))

    def descendants(self) -> Iterable["Element"]:
        for child in self.children:
            if isinstance(child, Element):
                yield child
                yield from child.descendants()

    def find_all(
        self,
        *,
        tag: str | None = None,
        element_id: str | None = None,
        class_name: str | None = None,
    ) -> list["Element"]:
        matches = []
        for node in self.descendants():
            if tag is not None and node.tag != tag:
                continue
            if element_id is not None and node.attrs.get("id") != element_id:
                continue
            if class_name is not None and class_name not in node.classes():
                continue
            matches.append(node)
        return matches

    def find_one(self, **criteria: str) -> "Element | None":
        matches = self.find_all(**criteria)
        return matches[0] if matches else None


class MiniDOMParser(HTMLParser):
    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Element("document", {})
        self.stack = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = Element(tag, {key: value or "" for key, value in attrs}, self.stack[-1])
        self.stack[-1].children.append(node)
        if tag not in self.VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_data(self, data: str) -> None:
        self.stack[-1].children.append(data)


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def parse_html(html: str) -> Element:
    parser = MiniDOMParser()
    parser.feed(html)
    parser.close()
    return parser.root


def parse_list(html: str, base_url: str, limit: int | None = None) -> list[dict]:
    root = parse_html(html)
    container = root.find_one(tag="ul", class_name="list-li")
    if container is None:
        raise ValueError("未找到列表容器 .list-li")

    records: list[dict] = []
    for item in container.find_all(tag="li"):
        title_box = item.find_one(tag="div", class_name="List-T")
        date_box = item.find_one(tag="span", class_name="list-time")
        link = title_box.find_one(tag="a") if title_box else None
        date_match = DATE_RE.search(date_box.text()) if date_box else None
        if link is None or not link.text() or date_match is None:
            continue
        records.append(
            {
                "title": link.text(),
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
    title_node = root.find_one(element_id="zoomtitl")
    date_node = root.find_one(tag="div", class_name="date")
    source_node = root.find_one(tag="div", class_name="source")
    body_node = root.find_one(element_id="zoomcon")
    if title_node is None or body_node is None:
        raise ValueError("详情页缺少 #zoomtitl 或 #zoomcon")

    date_match = DATE_RE.search(date_node.text()) if date_node else None
    source_text = source_node.text() if source_node else ""
    source_text = re.sub(r"^信息来源[:：]\s*", "", source_text)
    body = body_node.text(excluded_ids={"tblAppendixContainer"})

    appendix = root.find_one(element_id="tblAppendix")
    attachments = []
    if appendix:
        for link in appendix.find_all(tag="a"):
            name = link.text() or link.attrs.get("title", "")
            href = link.attrs.get("href", "")
            if name and href:
                attachments.append({"name": name, "url": urljoin(page_url, href)})

    metadata_date = None
    for meta in root.find_all(tag="meta"):
        if meta.attrs.get("name") == "PubDate":
            metadata_date = meta.attrs.get("content") or None
            break

    paragraphs = [node.text(excluded_ids={"tblAppendixContainer"}) for node in body_node.find_all(tag="p")]
    issuer = next(
        (text for text in reversed(paragraphs) if re.fullmatch(r"四川省经济和信息化厅(?:办公室)?", text)),
        None,
    )
    signature_date = next(
        (text for text in reversed(paragraphs) if re.fullmatch(r"\d{4}年\d{1,2}月\d{1,2}日", text)),
        None,
    )

    return {
        "title": title_node.text(),
        "published_at": date_match.group(0) if date_match else None,
        "metadata_published_at": metadata_date,
        "info_source": source_text or None,
        "issuer": issuer,
        "signature_date": signature_date,
        "body": body,
        "attachments": attachments,
        "application_links": URL_RE.findall(body),
    }


def _main() -> None:
    import argparse
    import json

    parser = argparse.ArgumentParser(description="解析已保存的四川省经信厅 HTML")
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
