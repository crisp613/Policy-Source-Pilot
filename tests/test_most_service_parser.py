import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from most_service_parser import parse_detail, parse_list  # noqa: E402


FIXTURES = ROOT / "tests" / "fixtures" / "policy-sources"
LIST_URL = "https://service.most.gov.cn/kjjh_tztg/"


class MostServiceParserTests(unittest.TestCase):
    def fixture(self, name: str) -> str:
        return (FIXTURES / name).read_text(encoding="utf-8")

    def test_iframe_list_extracts_complete_title_unit_date_and_url(self):
        rows = parse_list(self.fixture("most-service-list.html"), LIST_URL)

        self.assertEqual(2, len(rows))
        self.assertEqual("重点专项申报通知", rows[0]["title"])
        self.assertEqual("科学技术部", rows[0]["publishing_unit"])
        self.assertEqual("2026-09-14", rows[0]["published_at"])
        self.assertEqual(
            "https://service.most.gov.cn/kjjh_tztg_all/20260914/1.html",
            rows[0]["detail_url"],
        )

    def test_detail_extracts_public_fields_and_login_boundary(self):
        result = parse_detail(
            self.fixture("most-service-detail.html"),
            "https://service.most.gov.cn/kjjh_tztg_all/20260828/1.html",
        )

        self.assertEqual("国家重点研发计划重点专项申报通知", result["title"])
        self.assertEqual("2026-08-28", result["published_at"])
        self.assertEqual("科学技术部", result["publishing_unit"])
        self.assertEqual("科技部业务司", result["issuer"])
        self.assertEqual("2026-08-25", result["signature_date"])
        self.assertEqual(["http://service.example.gov.cn"], result["application_links"])
        self.assertEqual(2, len(result["attachments"]))
        self.assertTrue(result["guideline_login_required"])
        self.assertNotIn("login.example.invalid", result["application_links"])
        self.assertNotIn("footer.example.invalid", result["application_links"])

    def test_missing_attachment_section_returns_empty_array(self):
        result = parse_detail(
            self.fixture("most-service-detail-no-attachments.html"),
            "https://service.most.gov.cn/kjjh_tztg_all/20260901/2.html",
        )

        self.assertEqual([], result["attachments"])
        self.assertFalse(result["guideline_login_required"])

    def test_outer_shell_is_not_mistaken_for_notice_list(self):
        with self.assertRaisesRegex(ValueError, "公开列表"):
            parse_list("<html><body><iframe src='../kjjh_tztg/'></iframe></body></html>", LIST_URL)


if __name__ == "__main__":
    unittest.main()
