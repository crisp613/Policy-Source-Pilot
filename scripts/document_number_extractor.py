"""提取政策文件自身的文号，避免将正文引用文件文号误认为当前文号。"""

from __future__ import annotations

import re
from dataclasses import dataclass


DOCUMENT_NUMBER_RE = re.compile(
    r"(?<![\u4e00-\u9fff])[\u4e00-\u9fff]{1,20}\s*[〔［【（(]\s*20\d{2}\s*[〕］】）)]\s*\d{1,6}\s*号"
)
BRACKET_TRANSLATION = str.maketrans({"［": "〔", "【": "〔", "（": "〔", "(": "〔", "］": "〕", "】": "〕", "）": "〕", ")": "〕"})


@dataclass(frozen=True)
class DocumentNumberResult:
    document_number: str | None
    evidence: str | None
    source: str | None
    status: str


def normalize_number(value: str) -> str:
    return re.sub(r"\s+", "", value).translate(BRACKET_TRANSLATION).strip("：:，,。 ")


def clean_explicit_value(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    match = DOCUMENT_NUMBER_RE.search(value)
    return normalize_number(match.group(0) if match else value)


def extract_document_number(
    *,
    title: str | None,
    content: str | None,
    explicit_number: object = None,
    explicit_evidence: object = None,
    explicit_source: object = None,
) -> DocumentNumberResult:
    """优先使用页面字段，其次标题，最后只检查正文最开头。"""
    explicit = clean_explicit_value(explicit_number)
    if explicit:
        evidence = explicit_evidence if isinstance(explicit_evidence, str) and explicit_evidence else f"页面文号字段：{explicit}"
        source = explicit_source if isinstance(explicit_source, str) and explicit_source else "page_field"
        return DocumentNumberResult(explicit, evidence, source, "provided")

    title_match = DOCUMENT_NUMBER_RE.search(title or "")
    if title_match:
        original = title_match.group(0)
        return DocumentNumberResult(
            normalize_number(original),
            f"标题包含文号：{original}",
            "title",
            "provided",
        )

    opening = (content or "").lstrip()[:300]
    opening_match = DOCUMENT_NUMBER_RE.search(opening)
    if opening_match and opening_match.start() == 0:
        original = opening_match.group(0)
        return DocumentNumberResult(
            normalize_number(original),
            f"正文开头文号：{original}",
            "body_opening",
            "provided",
        )

    return DocumentNumberResult(None, None, None, "not_provided")
