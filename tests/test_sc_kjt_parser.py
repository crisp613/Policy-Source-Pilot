import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from sc_kjt_parser import parse_detail, parse_list  # noqa: E402


FIXTURES = ROOT / "tests" / "fixtures" / "policy-sources"
LIST_URL = "https://kjt.sc.gov.cn/kjt/gstz/newschild.shtml"


class ScKjtParserTests(unittest.TestCase):
    def fixture(self, name: str) -> str:
        return (FIXTURES / name).read_text(encoding="utf-8")

    def test_list_extracts_title_date_and_absolute_url(self):
        records = parse_list(self.fixture("sc-kjt-list.html"), LIST_URL)

        self.assertEqual(2, len(records))
        self.assertEqual("科技项目申报通知", records[0]["title"])
        self.assertEqual("2026-09-15", records[0]["published_at"])
        self.assertEqual(
            "https://kjt.sc.gov.cn/kjt/gstz/2026/9/15/a.shtml",
            records[0]["detail_url"],
        )

    def test_detail_separates_body_attachment_and_navigation(self):
        url = "https://kjt.sc.gov.cn/kjt/gstz/2026/9/15/a.shtml"
        result = parse_detail(self.fixture("sc-kjt-detail-with-attachment.html"), url)

        self.assertEqual("科技项目申报通知", result["title"])
        self.assertEqual("2026-09-15 15:36:53", result["published_at"])
        self.assertEqual("人工智能处", result["info_source"])
        self.assertEqual("四川省科学技术厅", result["issuer"])
        self.assertEqual("2026年9月15日", result["signature_date"])
        self.assertEqual(["http://apply.example.gov.cn/"], result["application_links"])
        self.assertNotIn("附件：申报书", result["body"])
        self.assertNotIn("相关链接", result["body"])
        self.assertNotIn("办事大厅", result["body"])
        self.assertNotIn("邮箱", result["body"])
        self.assertEqual(
            "https://kjt.sc.gov.cn/kjt/gstz/2026/9/15/a/files/form.docx",
            result["attachments"][0]["url"],
        )

    def test_empty_source_and_attachment_remain_empty(self):
        result = parse_detail(
            self.fixture("sc-kjt-detail-empty-fields.html"),
            "https://kjt.sc.gov.cn/kjt/gstz/2026/9/8/c.shtml",
        )

        self.assertIsNone(result["info_source"])
        self.assertIsNone(result["document_number"])
        self.assertEqual([], result["attachments"])
        self.assertEqual([], result["application_links"])

    def test_policy_document_template(self):
        result = parse_detail(
            self.fixture("sc-kjt-detail-policy-template.html"),
            "https://kjt.sc.gov.cn/kjt/xzgfxwj/2026/6/9/a.shtml",
        )

        self.assertEqual("policy-document", result["parser_template"])
        self.assertEqual("政策文件模板样本", result["title"])
        self.assertEqual("2026-06-09", result["published_at"])
        self.assertEqual("四川省科学技术厅", result["info_source"])
        self.assertEqual("川科政〔2026〕6号", result["document_number"])
        self.assertIn("认真贯彻执行", result["body"])
        self.assertEqual(1, len(result["attachments"]))

    def test_unknown_template_uses_generic_fallback(self):
        result = parse_detail(
            self.fixture("sc-kjt-detail-generic-template.html"),
            "https://kjt.sc.gov.cn/kjt/unknown/2026/6/10/a.shtml",
        )

        self.assertEqual("generic-fallback", result["parser_template"])
        self.assertEqual("未知模板通知样本", result["title"])
        self.assertIn("通用正文提取规则", result["body"])
        self.assertNotIn("网站地图", result["body"])

    def test_missing_required_detail_structure_is_an_error(self):
        with self.assertRaisesRegex(ValueError, "未找到"):
            parse_detail("<html><body>访问验证页面</body></html>", LIST_URL)


if __name__ == "__main__":
    unittest.main()
