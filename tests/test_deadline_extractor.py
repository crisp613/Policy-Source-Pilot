import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from deadline_extractor import extract_deadlines  # noqa: E402


class DeadlineExtractorTests(unittest.TestCase):
    def test_extracts_explicit_application_deadline(self):
        result = extract_deadlines("申报截止时间为2026年10月14日18:00，请按时提交。")

        self.assertEqual("provided", result.status)
        self.assertEqual("2026-10-14T18:00:00+08:00", result.deadline)
        self.assertEqual("申报截止时间", result.deadlines[0]["name"])
        self.assertIn("2026年10月14日18:00", result.evidence)

    def test_range_uses_end_time_and_inherits_explicit_year(self):
        result = extract_deadlines("网上填报受理时间为2026年9月3日8:00至10月8日16:00。")

        self.assertEqual("2026-10-08T16:00:00+08:00", result.deadline)
        self.assertEqual(1, len(result.deadlines))

    def test_application_deadline_precedes_recommendation_deadline(self):
        result = extract_deadlines(
            "申报截止时间为2026年9月22日18:00；推荐单位确认截止时间为2026年9月23日18:00。"
        )

        self.assertEqual(2, len(result.deadlines))
        self.assertEqual("2026-09-22T18:00:00+08:00", result.deadline)
        self.assertEqual("申报截止时间", result.deadlines[0]["name"])
        self.assertEqual("推荐确认截止时间", result.deadlines[1]["name"])

    def test_date_without_time_keeps_date_precision(self):
        result = extract_deadlines("材料报送截止日期为2026年10月8日。")

        self.assertEqual("2026-10-08", result.deadline)
        self.assertEqual("date", result.deadlines[0]["precision"])

    def test_unrelated_dates_are_not_deadlines(self):
        result = extract_deadlines("本通知于2026年9月18日发布。四川省科学技术厅 2026年9月17日")

        self.assertEqual("not_provided", result.status)
        self.assertIsNone(result.deadline)
        self.assertEqual([], result.deadlines)

    def test_explicit_but_invalid_date_is_parse_failed(self):
        result = extract_deadlines("申报截止时间为2026年13月40日。")

        self.assertEqual("parse_failed", result.status)
        self.assertIsNone(result.deadline)

    def test_non_numeric_deadline_remains_not_provided_with_evidence(self):
        result = extract_deadlines("具体申报截止时间另行通知。")

        self.assertEqual("not_provided", result.status)
        self.assertIn("另行通知", result.evidence)

    def test_tolerates_spaces_inserted_inside_year_and_time(self):
        result = extract_deadlines("网上申报截止时间为202 6 年 9 月 27 日 18 时。")

        self.assertEqual("2026-09-27T18:00:00+08:00", result.deadline)

    def test_reuses_year_explicitly_written_in_same_sentence(self):
        result = extract_deadlines("2026年为首次报送，报送截止时间为9月30日。")

        self.assertEqual("2026-09-30", result.deadline)

    def test_range_can_end_with_day_only(self):
        result = extract_deadlines("2026年材料报送受理时间为11月16日至18日。")

        self.assertEqual("2026-11-18", result.deadline)

    def test_eligibility_as_of_date_is_not_a_deadline(self):
        result = extract_deadlines("截至2026年7月31日，企业注册成立时间应在7年以内。")

        self.assertEqual("not_provided", result.status)
        self.assertIsNone(result.deadline)

    def test_application_eligibility_date_is_not_a_deadline(self):
        result = extract_deadlines("一、申报对象（一）截至2025年12月31日，企业应在四川省注册。")

        self.assertEqual("not_provided", result.status)
        self.assertIsNone(result.deadline)

    def test_data_baseline_date_is_not_a_deadline(self):
        result = extract_deadlines("本次申报书所填上年度数据均以截至2025年12月31日为准。")

        self.assertEqual("not_provided", result.status)
        self.assertIsNone(result.deadline)

    def test_range_with_implicit_deadline_does_not_use_start_date(self):
        result = extract_deadlines("项目在2023年3月18日至申报截止日期间取得备案文件。")

        self.assertEqual("not_provided", result.status)
        self.assertIsNone(result.deadline)

    def test_reversed_source_range_is_parse_failed(self):
        result = extract_deadlines("网上填报时间为2023年8月28日9:00至2022年9月26日16:00。")

        self.assertEqual("parse_failed", result.status)
        self.assertIsNone(result.deadline)


if __name__ == "__main__":
    unittest.main()
