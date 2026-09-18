"""将各来源不同的发布单位字段统一为产品使用的发布主体。"""

from __future__ import annotations

import re
from dataclasses import dataclass


ORGANIZATION_SUFFIX_RE = re.compile(
    r"(?:人民政府|人民政府办公厅|管理委员会|委员会|管理办公室|办公室|"
    r"经济和信息化厅|科学技术厅|科技厅|工业和信息化部|科学技术部|"
    r"厅|部|委|局|中心|研究院|科学院|协会|集团|公司)$"
)


@dataclass(frozen=True)
class PublisherResult:
    publisher: str | None
    evidence: str | None
    source_field: str | None
    status: str


def clean_value(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = re.sub(r"\s+", "", value).strip("：:，,。 ")
    return cleaned or None


def is_full_organization(value: str) -> bool:
    """只接受具有明确机构后缀的名称，排除“人工智能处”等内部处室。"""
    return len(value) >= 4 and bool(ORGANIZATION_SUFFIX_RE.search(value))


def normalize_publisher(
    *,
    issuer: object = None,
    publishing_unit: object = None,
    info_source: object = None,
    publisher: object = None,
    publisher_evidence: object = None,
    publisher_source: object = None,
) -> PublisherResult:
    """按正文落款、页面发布单位、完整发布机构的顺序确定发布主体。"""
    explicit_publisher = clean_value(publisher)
    if explicit_publisher:
        return PublisherResult(
            explicit_publisher,
            clean_value(publisher_evidence),
            clean_value(publisher_source) or "publisher",
            "provided",
        )

    issuer_value = clean_value(issuer)
    if issuer_value:
        return PublisherResult(
            issuer_value,
            f"正文落款：{issuer_value}",
            "issuer",
            "provided",
        )

    unit_value = clean_value(publishing_unit)
    if unit_value:
        return PublisherResult(
            unit_value,
            f"页面发布单位：{unit_value}",
            "publishing_unit",
            "provided",
        )

    source_value = clean_value(info_source)
    if source_value and is_full_organization(source_value):
        return PublisherResult(
            source_value,
            f"页面发布机构：{source_value}",
            "info_source",
            "provided",
        )

    return PublisherResult(None, None, None, "not_provided")
