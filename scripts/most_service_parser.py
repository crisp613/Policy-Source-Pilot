"""国家科技管理信息系统公开通知的本地验证解析器。

只读取公开页面的本地 HTML，不登录系统，也不获取登录后指南。
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urljoin

from sc_jxt_parser import Element, extract_body_images, parse_html
from sc_kjt_parser import compact_text


OPEN_URL_RE = re.compile(r"openW\('([^']+)'\)")
DATE_RE = re.compile(r"(\d{4})年(\d{1,2})月(\d{1,2})日")
URL_RE = re.compile(r"https?://[^\s<>\"'，。；）]+")


def parse_list(html: str, base_url: str, limit: int | None = None) -> list[dict]:
    root = parse_html(html)
    table = root.find_one(tag="table", class_name="table_gkgs")
    if table is None:
        raise ValueError("未找到公开列表 table.table_gkgs")

    records: list[dict] = []
    for row in table.find_all(tag="tr"):
        title_cell = row.find_one(tag="td", class_name="table_gkgs_title")
        unit_cell = row.find_one(tag="td", class_name="table_gkgs_unit")
        date_cell = row.find_one(tag="td", class_name="table_gkgs_date")
        title_node = title_cell.find_one(tag="div") if title_cell else None
        if title_node is None or date_cell is None:
            continue
        path_match = OPEN_URL_RE.search(title_node.attrs.get("onclick", ""))
        title = title_node.attrs.get("title") or title_node.text()
        published_at = compact_text(date_cell.text())
        if path_match is None or not title or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", published_at):
            continue
        records.append(
            {
                "title": compact_text(title),
                "detail_url": urljoin(base_url, path_match.group(1)),
                "published_at": published_at,
                "publishing_unit": compact_text(unit_cell.attrs.get("title") or unit_cell.text()) if unit_cell else None,
            }
        )
        if limit is not None and len(records) >= limit:
            break

    if not records:
        raise ValueError("列表存在，但没有解析出有效通知")
    return records


def right_aligned(node: Element) -> bool:
    return node.attrs.get("align", "").lower() == "right" or "text-align: right" in node.attrs.get("style", "").lower()


def direct_blocks(node: Element) -> list[tuple[Element, str]]:
    blocks = []
    for child in node.children:
        if isinstance(child, Element):
            text = compact_text(child.text())
            if text:
                blocks.append((child, text))
    return blocks


def extract_attachments(body_node: Element) -> list[dict]:
    names: list[str] = []
    collecting = False
    for node, text in direct_blocks(body_node):
        if text.startswith("附件："):
            collecting = True
            suffix = text.removeprefix("附件：").strip()
            if suffix:
                names.append(re.sub(r"^\d+[.．、]\s*", "", suffix))
            continue
        if not collecting:
            continue
        if right_aligned(node) or "请登录系统" in text:
            break
        names.append(re.sub(r"^\d+[.．、]\s*", "", text))
    return [{"name": name, "url": None, "access": "login_required"} for name in names if name]


def parse_detail(html: str, page_url: str) -> dict:
    root = parse_html(html)
    title_node = root.find_one(tag="h1", class_name="article__title")
    subtitle = root.find_one(tag="p", class_name="article__subTitle")
    body_node = root.find_one(tag="div", class_name="article-body")
    if title_node is None or subtitle is None or body_node is None:
        raise ValueError("详情页缺少标题、副标题或公开正文")

    subtitle_text = compact_text(subtitle.text())
    date_match = DATE_RE.search(subtitle_text)
    source_match = re.search(r"来源：(.+)$", subtitle_text)
    published_at = None
    if date_match:
        year, month, day = map(int, date_match.groups())
        published_at = f"{year:04d}-{month:02d}-{day:02d}"

    body = compact_text(body_node.text())
    signature_lines = [text for node, text in direct_blocks(body_node) if node.tag == "p" and right_aligned(node)]
    signature_date = None
    issuer = None
    for text in signature_lines:
        match = DATE_RE.fullmatch(text)
        if match:
            year, month, day = map(int, match.groups())
            signature_date = f"{year:04d}-{month:02d}-{day:02d}"
        elif issuer is None:
            issuer = text

    return {
        "title": compact_text(title_node.text()),
        "url": page_url,
        "published_at": published_at,
        "publishing_unit": compact_text(source_match.group(1)) if source_match else None,
        "issuer": issuer,
        "signature_date": signature_date,
        "body": body,
        "attachments": extract_attachments(body_node),
        "images": extract_body_images(body_node, page_url),
        "application_links": URL_RE.findall(body),
        "guideline_login_required": "请登录系统" in body and "申报指南" in body,
    }


def _main() -> None:
    import argparse
    import json

    parser = argparse.ArgumentParser(description="解析已保存的国家科技管理信息系统公开 HTML")
    parser.add_argument("kind", choices=["list", "detail"])
    parser.add_argument("html", type=Path)
    parser.add_argument("--url", required=True)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    html = args.html.read_text(encoding="utf-8")
    result = parse_list(html, args.url, args.limit) if args.kind == "list" else parse_detail(html, args.url)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    _main()
