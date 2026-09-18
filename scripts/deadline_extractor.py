"""从政策正文中提取有明确原文证据的截止日期。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


LOCAL_TIMEZONE = timezone(timedelta(hours=8))
DEADLINE_CONTEXT_RE = re.compile(
    r"截止|受理时间|申报时间|填报时间|报送时间|推荐时间|确认时间|"
    r"征求意见时间|征求意见.{0,8}前|公示期|(?:申报|报送|推荐|确认).{0,12}前|"
    r"截至.{0,20}(?:申报|报送|推荐|提交)|(?:申报|报送|推荐|提交).{0,12}截至|"
    r"于.{0,20}前.{0,30}(?:报送|提交)"
)
DATE_LIKE_RE = re.compile(r"20\d{2}.{0,3}\d{1,2}.{0,3}\d{1,2}|\d{1,2}月\d{1,2}日")
DATE_RE = re.compile(
    r"(?:(?P<year>20\d{2})年)?"
    r"(?P<month>\d{1,2})月(?P<day>\d{1,2})日"
    r"(?:\s*(?P<meridiem>上午|下午)?\s*(?P<hour>\d{1,2})"
    r"(?:[:：时](?P<minute>\d{1,2}))?分?)?"
    r"|(?P<iso_year>20\d{2})[-/.](?P<iso_month>\d{1,2})[-/.](?P<iso_day>\d{1,2})"
    r"(?:[ T](?P<iso_hour>\d{1,2})[:：](?P<iso_minute>\d{1,2}))?"
    r"|(?P<only_day>\d{1,2})日"
    r"(?:\s*(?P<only_day_meridiem>上午|下午)?\s*(?P<only_day_hour>\d{1,2})"
    r"(?:[:：时](?P<only_day_minute>\d{1,2}))?分?)?"
)
NO_EXACT_DATE_RE = re.compile(r"另行通知|长期有效|常态化|以系统时间为准|以平台时间为准")
NON_DEADLINE_CONTEXT_RE = re.compile(
    r"(?:申报对象|申报条件|基本条件).{0,20}截至|"
    r"(?:数据|指标).{0,30}(?:截至|截止).{0,30}为准"
)


@dataclass(frozen=True)
class DeadlineExtraction:
    deadline: str | None
    evidence: str | None
    status: str
    deadlines: list[dict]


def split_sentences(content: str) -> list[str]:
    return [part.strip() for part in re.split(r"[。！？；;\n\r]+", content) if part.strip()]


def split_clauses(sentence: str) -> list[str]:
    return [part.strip() for part in re.split(r"[，,]+", sentence) if part.strip()]


def parse_dates(text: str, default_year: int | None = None) -> tuple[list[tuple[str, bool]], bool]:
    """返回按原文顺序出现的日期以及是否存在无法解析的日期文本。"""
    parse_text = re.sub(r"(?<=\d)\s+(?=\d)", "", text)
    parse_text = re.sub(r"\s*([年月日时分:：])\s*", r"\1", parse_text)
    values: list[tuple[str, bool]] = []
    current_year = default_year
    current_month: int | None = None
    invalid_date_found = False
    for match in DATE_RE.finditer(parse_text):
        try:
            if match.group("iso_year"):
                year = int(match.group("iso_year"))
                month = int(match.group("iso_month"))
                day = int(match.group("iso_day"))
                hour_text = match.group("iso_hour")
                minute_text = match.group("iso_minute")
                meridiem = None
                current_year = year
                current_month = month
            elif match.group("only_day"):
                if current_year is None or current_month is None:
                    continue
                year = current_year
                month = current_month
                day = int(match.group("only_day"))
                hour_text = match.group("only_day_hour")
                minute_text = match.group("only_day_minute")
                meridiem = match.group("only_day_meridiem")
            else:
                if match.group("year"):
                    current_year = int(match.group("year"))
                elif current_year is None:
                    explicit_years = re.findall(r"(20\d{2})年", parse_text[: match.start()])
                    current_year = int(explicit_years[-1]) if explicit_years else None
                if current_year is None:
                    continue
                year = current_year
                month = int(match.group("month"))
                current_month = month
                day = int(match.group("day"))
                hour_text = match.group("hour")
                minute_text = match.group("minute")
                meridiem = match.group("meridiem")

            has_time = hour_text is not None
            hour = int(hour_text or 0)
            minute = int(minute_text or 0)
            if meridiem == "下午" and hour < 12:
                hour += 12
            parsed = datetime(year, month, day, hour, minute, tzinfo=LOCAL_TIMEZONE)
            value = parsed.isoformat(timespec="seconds") if has_time else parsed.date().isoformat()
            values.append((value, has_time))
        except ValueError:
            invalid_date_found = True
    if DATE_LIKE_RE.search(parse_text) and not values:
        invalid_date_found = True
    return values, invalid_date_found


def deadline_name(sentence: str) -> str:
    if "推荐" in sentence or "确认" in sentence:
        return "推荐确认截止时间"
    if "征求意见" in sentence:
        return "征求意见截止时间"
    if "公示" in sentence:
        return "公示截止时间"
    if "报送" in sentence:
        return "材料报送截止时间"
    if "填报" in sentence or "受理" in sentence or "申报" in sentence:
        return "申报截止时间"
    return "截止时间"


def primary_priority(item: dict) -> tuple[int, str]:
    name = item["name"]
    if "申报" in name:
        priority = 0
    elif "报送" in name or "征求意见" in name:
        priority = 1
    elif "推荐" in name or "确认" in name:
        priority = 2
    elif "公示" in name:
        priority = 3
    else:
        priority = 4
    return priority, item["value"]


def extract_deadlines(content: str | None) -> DeadlineExtraction:
    if not content:
        return DeadlineExtraction(None, None, "not_provided", [])

    deadlines: list[dict] = []
    parse_failure = False
    explicit_no_date_evidence: str | None = None
    seen: set[tuple[str, str]] = set()

    for sentence in split_sentences(content):
        context_year: int | None = None
        for clause in split_clauses(sentence):
            normalized_clause = re.sub(r"(?<=\d)\s+(?=\d)", "", clause)
            explicit_years = re.findall(r"(20\d{2})\s*年", normalized_clause)
            if explicit_years:
                context_year = int(explicit_years[-1])
            if not DEADLINE_CONTEXT_RE.search(clause):
                continue
            if NON_DEADLINE_CONTEXT_RE.search(clause):
                continue
            values, invalid_date = parse_dates(clause, context_year)
            parse_failure = parse_failure or invalid_date
            if not values:
                if NO_EXACT_DATE_RE.search(clause):
                    explicit_no_date_evidence = clause
                continue

            # 时间区间的最后一个时间是截止点；非区间中的多个明确时间分别保留。
            is_range = len(values) > 1 and bool(re.search(r"至|到|—|－|~|～", clause))
            if len(values) == 1 and re.search(r"至申报截止|至报送截止|至推荐截止", clause):
                # 只写了区间起点，终点仅以“申报截止日期”指代，不能把起点当成截止日。
                continue
            if is_range and values[-1][0] < values[0][0]:
                # 源文时间区间前后倒置，保留为解析失败，避免向产品输出明显错误日期。
                parse_failure = True
                continue
            selected_values = [values[-1]] if is_range else values
            name = deadline_name(clause)
            for value, has_time in selected_values:
                key = (name, value)
                if key in seen:
                    continue
                seen.add(key)
                deadlines.append(
                    {
                        "name": name,
                        "value": value,
                        "precision": "datetime" if has_time else "date",
                        "evidence": clause,
                    }
                )

    if deadlines:
        primary = min(deadlines, key=primary_priority)
        return DeadlineExtraction(primary["value"], primary["evidence"], "provided", deadlines)
    if parse_failure:
        return DeadlineExtraction(None, None, "parse_failed", [])
    return DeadlineExtraction(None, explicit_no_date_evidence, "not_provided", [])
