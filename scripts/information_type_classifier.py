"""基于原文明确关键词的信息类型规则分类器。"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Classification:
    information_type: str | None
    evidence: str | None
    rule: str


TITLE_RULES = (
    (
        "公示",
        "title_public_notice",
        re.compile(r"公示|拟认定|拟立项|拟支持|评审结果|评选结果|认定结果|立项结果|结果公告"),
    ),
    (
        "征集",
        "title_solicitation",
        re.compile(r"公开征求.{0,12}意见|征求.{0,12}意见|征集"),
    ),
    (
        "政策文件",
        "title_policy_document",
        re.compile(
            r"(?:印发|发布).{0,30}(?:办法|规定|细则|实施方案|指导意见|规划|措施|目录)"
            r"|《[^》]*(?:办法|规定|细则|实施方案|指导意见|规划|措施)[^》]*》"
        ),
    ),
    (
        "申报通知",
        "title_application_notice",
        re.compile(r"申报|申领|组织推荐|推荐申报|项目申请|发布.{0,20}申报指南"),
    ),
    (
        "事务通知",
        "title_administrative_notice",
        re.compile(r"召开.{0,20}(?:会议|培训)|参加.{0,20}(?:会议|培训)|报送.{0,20}材料|系统维护|网站工作.{0,10}报表|值班安排"),
    ),
)

BODY_RULES = (
    (
        "公示",
        "body_public_notice",
        re.compile(r"现将.{0,80}(?:名单|结果).{0,20}公示|公示期为"),
    ),
    (
        "征集",
        "body_solicitation",
        re.compile(r"现面向.{0,80}征集|征集范围|征集要求|征求意见截止"),
    ),
    (
        "政策文件",
        "body_policy_document",
        re.compile(r"现将《[^》]+》印发|本办法自.{0,30}(?:施行|实施)"),
    ),
    (
        "申报通知",
        "body_application_notice",
        re.compile(r"申报条件|申报要求|申报时间|申报截止|组织开展.{0,80}申报"),
    ),
    (
        "事务通知",
        "body_administrative_notice",
        re.compile(r"会议时间|培训时间|请于.{0,30}报送.{0,20}材料|系统维护期间"),
    ),
)


def classify_information_type(title: str | None, content: str | None) -> Classification:
    """返回分类、原文命中片段和规则名；没有明确证据时不强行分类。"""
    title = title or ""
    for information_type, rule, pattern in TITLE_RULES:
        match = pattern.search(title)
        if match:
            return Classification(information_type, f"标题包含“{match.group(0)}”", rule)

    # 正文只看开头部分，并且只使用高确定性短语，避免偶然提及造成误分类。
    content_excerpt = (content or "")[:2000]
    for information_type, rule, pattern in BODY_RULES:
        match = pattern.search(content_excerpt)
        if match:
            return Classification(information_type, f"正文包含“{match.group(0)}”", rule)

    return Classification(None, None, "unclassified")
