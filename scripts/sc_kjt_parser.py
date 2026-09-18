"""四川省科学技术厅公开通知页的最小验证解析器。

只读取本地 HTML，不发起网络请求，不进入申报系统。
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urljoin

from sc_jxt_parser import Element, clean_text, extract_body_images, parse_html


DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
DATETIME_RE = re.compile(r"\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}:\d{2})?")
URL_RE = re.compile(r"https?://[^\s<>\"'，。；）]+")
FILE_LINK_RE = re.compile(r"(?:/files/|\.(?:pdf|docx?|xlsx?|pptx?|zip|rar|7z)(?:$|[?#]))", re.I)
BODY_EXCLUDED_CLASSES = {
    "attachment",
    "relatedlinks",
    "share",
    "toolbar",
    "pagination",
    "breadcrumb",
}


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


def extract_metadata(container: Element | None) -> tuple[str | None, str | None, str | None]:
    published_at = None
    info_source = None
    document_number = None
    if container is None:
        return published_at, info_source, document_number

    for item in container.find_all(tag="li"):
        text = compact_text(item.text()).replace("\u00a0", "").replace("\u2003", "")
        if "发布日期：" in text:
            match = DATETIME_RE.search(text)
            published_at = match.group(0) if match else published_at
        elif "发布机构：" in text:
            info_source = text.split("发布机构：", 1)[1].strip() or info_source
        elif "文号：" in text:
            document_number = text.split("文号：", 1)[1].strip() or document_number
    return published_at, info_source, document_number


def generic_title(root: Element) -> Element | None:
    candidates = []
    for node in root.find_all(tag="h1"):
        text = compact_text(node.text())
        if 4 <= len(text) <= 500:
            candidates.append((len(text), node))
    return max(candidates, key=lambda item: item[0])[1] if candidates else None


def generic_body(root: Element) -> Element | None:
    candidates: list[tuple[float, int, Element]] = []
    for tag in ("article", "main", "section", "div"):
        for node in root.find_all(tag=tag):
            marker = f"{node.attrs.get('id', '')} {' '.join(node.classes())}".lower()
            if any(token in marker for token in ("nav", "header", "footer", "menu", "list", "sidebar")):
                continue

            text = text_without(
                node,
                excluded_ids={"div_div", "tblArticleLink"},
                excluded_classes=BODY_EXCLUDED_CLASSES,
            )
            if len(text) < 80:
                continue

            paragraph_count = len(node.find_all(tag="p"))
            link_text_length = sum(len(compact_text(link.text())) for link in node.find_all(tag="a"))
            link_ratio = link_text_length / max(len(text), 1)
            hint_bonus = 0
            if any(token in marker for token in ("article", "content", "detail", "text", "body", "cont")):
                hint_bonus += 1500
            if tag in {"article", "main"}:
                hint_bonus += 1000
            if any(token in marker for token in ("wrap", "container", "page")):
                hint_bonus -= 500

            score = min(len(text), 12000) + min(paragraph_count, 40) * 100 + hint_bonus - link_ratio * 4000
            candidates.append((score, -len(text), node))

    return max(candidates, key=lambda item: (item[0], item[1]))[2] if candidates else None


def extract_attachments(root: Element, page_url: str, template_box: Element | None) -> list[dict]:
    links: list[Element] = []
    attachment_box = root.find_one(tag="ul", class_name="attachment")
    if attachment_box:
        links.extend(attachment_box.find_all(tag="a"))
    if template_box:
        links.extend(
            link
            for link in template_box.find_all(tag="a")
            if FILE_LINK_RE.search(link.attrs.get("href", ""))
        )

    attachments = []
    seen_urls = set()
    for link in links:
        name = compact_text(link.text()) or link.attrs.get("title", "")
        href = link.attrs.get("href", "")
        url = urljoin(page_url, href)
        if name and href and url not in seen_urls:
            seen_urls.add(url)
            attachments.append({"name": name, "url": url})
    return attachments


def parse_detail(html: str, page_url: str) -> dict:
    root = parse_html(html)
    news_box = root.find_one(tag="div", class_name="newsTex")
    article_box = root.find_one(tag="div", class_name="articlebox")

    if news_box and root.find_one(tag="div", class_name="newsCon"):
        parser_template = "notice"
        title_node = news_box.find_one(tag="h1")
        body_node = root.find_one(tag="div", class_name="newsCon")
        metadata_box = root.find_one(tag="div", class_name="abstract")
        template_box = news_box
    elif article_box and article_box.find_one(tag="div", class_name="contText"):
        parser_template = "policy-document"
        title_node = article_box.find_one(tag="h1")
        body_node = article_box.find_one(tag="div", class_name="contText")
        metadata_box = root.find_one(tag="div", class_name="topbox")
        template_box = article_box
    else:
        parser_template = "generic-fallback"
        title_node = generic_title(root)
        body_node = generic_body(root)
        metadata_box = root
        template_box = body_node

    if title_node is None or body_node is None:
        raise ValueError("详情页未匹配已知模板，通用规则也未找到标题或正文")

    published_at, info_source, document_number = extract_metadata(metadata_box)

    body = text_without(
        body_node,
        excluded_ids={"div_div", "tblArticleLink"},
        excluded_classes=BODY_EXCLUDED_CLASSES,
    )
    title = compact_text(title_node.text())
    if body.startswith(title):
        body = body[len(title):].strip()
    if len(body) < 20:
        raise ValueError(f"详情页正文过短，解析模板：{parser_template}")

    attachments = extract_attachments(root, page_url, template_box)

    issuer = "四川省科学技术厅" if "四川省科学技术厅" in body else None
    signature_dates = re.findall(r"\d{4}年\d{1,2}月\d{1,2}日", body)

    return {
        "title": title,
        "published_at": published_at,
        "info_source": info_source,
        "document_number": document_number,
        "issuer": issuer,
        "signature_date": signature_dates[-1] if signature_dates else None,
        "body": body,
        "attachments": attachments,
        "images": extract_body_images(body_node, page_url),
        "application_links": URL_RE.findall(body),
        "parser_template": parser_template,
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
