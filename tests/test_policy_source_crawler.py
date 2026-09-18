import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from crawl_most_service import CONFIG as MOST_CONFIG  # noqa: E402
from crawl_sc_jxt import CONFIG as JXT_CONFIG  # noqa: E402
from crawl_sc_kjt import CONFIG as KJT_CONFIG  # noqa: E402
from policy_source_crawler import normalize_detail_record  # noqa: E402


class PolicySourceCrawlerSchemaTests(unittest.TestCase):
    def test_three_sources_share_the_same_detail_schema(self):
        source_values = (
            (JXT_CONFIG, {"info_source": "技术创新处"}),
            (KJT_CONFIG, {"document_number": "川科政〔2026〕6号", "parser_template": "notice"}),
            (MOST_CONFIG, {"publishing_unit": "科学技术部", "guideline_login_required": True}),
        )
        records = []
        for config, source_specific in source_values:
            parsed = {
                "title": "关于召开测试培训会的通知",
                "published_at": "2026-09-18",
                "body": "测试正文",
                "attachments": [],
                "application_links": [],
                **source_specific,
            }
            records.append(
                normalize_detail_record(
                    config,
                    detail_url=f"https://example.test/{config.key}/1.html",
                    list_item={"title": "关于召开测试培训会的通知", "published_at": "2026-09-18", "list_page": 1},
                    parsed=parsed,
                    collected_at="2026-09-18T10:00:00+08:00",
                    http_status=200,
                )
            )

        expected_top_level = {"external_id", "title", "url", "published_at", "content", "metadata"}
        expected_metadata = set(records[0]["metadata"])
        for record in records:
            self.assertEqual(expected_top_level, set(record))
            self.assertEqual(expected_metadata, set(record["metadata"]))
            self.assertEqual("2026-09-18T00:00:00+08:00", record["published_at"])
            self.assertEqual("事务通知", record["metadata"]["information_type"])
            self.assertEqual("title_administrative_notice", record["metadata"]["information_type_rule"])

    def test_missing_source_fields_remain_explicitly_empty(self):
        record = normalize_detail_record(
            JXT_CONFIG,
            detail_url="https://example.test/empty.html",
            list_item={"title": "字段缺失样本", "published_at": None, "list_page": 1},
            parsed={"body": "正文"},
        )

        self.assertIsNone(record["published_at"])
        self.assertIsNone(record["metadata"]["issuer"])
        self.assertIsNone(record["metadata"]["document_number"])
        self.assertEqual("not_provided", record["metadata"]["document_number_status"])
        self.assertIsNone(record["metadata"]["publisher"])
        self.assertEqual("not_provided", record["metadata"]["publisher_status"])
        self.assertEqual([], record["metadata"]["attachments"])
        self.assertEqual([], record["metadata"]["application_links"])
        self.assertIsNone(record["metadata"]["deadline"])
        self.assertEqual("not_provided", record["metadata"]["deadline_status"])

    def test_deadline_fields_are_added_to_unified_metadata(self):
        record = normalize_detail_record(
            KJT_CONFIG,
            detail_url="https://example.test/deadline.html",
            list_item={"title": "项目申报通知", "published_at": "2026-09-18", "list_page": 1},
            parsed={"body": "申报截止时间为2026年10月14日18:00。"},
        )

        self.assertEqual("2026-10-14T18:00:00+08:00", record["metadata"]["deadline"])
        self.assertEqual("provided", record["metadata"]["deadline_status"])
        self.assertEqual(1, len(record["metadata"]["deadlines"]))


if __name__ == "__main__":
    unittest.main()
