import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from sc_jxt_parser import parse_detail, parse_list  # noqa: E402
from compare_sc_jxt_runs import compare_lists  # noqa: E402


FIXTURES = ROOT / "tests" / "fixtures" / "policy-sources"
LIST_URL = "https://jxt.sc.gov.cn/scjxt/wjfb/common_list.shtml"


class ScJxtParserTests(unittest.TestCase):
    def test_detail_discovers_inline_body_images_without_downloading(self):
        html = """
        <h1 id="zoomtitl">图片通知</h1><div class="date">2026-09-18</div>
        <div id="zoomcon"><p>请查看图片中的申报要求。</p><img src="images/notice.png" alt="申报要求图"></div>
        """
        result = parse_detail(html, "https://example.test/news/detail.shtml")
        self.assertEqual(
            [{"url": "https://example.test/news/images/notice.png", "alt": "申报要求图"}],
            result["images"],
        )

    def fixture(self, name: str) -> str:
        return (FIXTURES / name).read_text(encoding="utf-8")

    def test_list_extracts_title_date_and_absolute_url(self):
        records = parse_list(self.fixture("sc-jxt-list.html"), LIST_URL)

        self.assertEqual(2, len(records))
        self.assertEqual("样本通知一", records[0]["title"])
        self.assertEqual("2026-09-15", records[0]["published_at"])
        self.assertEqual(
            "https://jxt.sc.gov.cn/scjxt/wjfb/2026/9/15/a.shtml",
            records[0]["detail_url"],
        )

    def test_detail_separates_body_attachments_and_navigation(self):
        url = "https://jxt.sc.gov.cn/scjxt/wjfb/2026/9/15/a.shtml"
        result = parse_detail(self.fixture("sc-jxt-detail-with-attachments.html"), url)

        self.assertEqual("样本申报通知", result["title"])
        self.assertEqual("2026-09-15", result["published_at"])
        self.assertEqual("技术创新处", result["info_source"])
        self.assertEqual("四川省经济和信息化厅办公室", result["issuer"])
        self.assertEqual("2026年9月15日", result["signature_date"])
        self.assertNotIn("附件：项目申报书", result["body"])
        self.assertNotIn("登录", result["body"])
        self.assertNotIn("邮箱", result["body"])
        self.assertEqual([], result["application_links"])
        self.assertEqual(
            "https://jxt.sc.gov.cn/scjxt/wjfb/2026/9/15/notice/files/application.doc",
            result["attachments"][0]["url"],
        )

    def test_detail_finds_only_urls_inside_body(self):
        url = "https://jxt.sc.gov.cn/scjxt/wjfb/2026/9/9/b.shtml"
        result = parse_detail(self.fixture("sc-jxt-detail-with-body-url.html"), url)

        self.assertEqual(["http://apply.example.gov.cn/form"], result["application_links"])
        self.assertEqual([], result["attachments"])
        self.assertIsNone(result["metadata_published_at"])

    def test_missing_required_detail_structure_is_an_error(self):
        with self.assertRaisesRegex(ValueError, "缺少"):
            parse_detail("<html><body>访问验证页面</body></html>", LIST_URL)

    def test_run_comparison_distinguishes_new_updated_and_absent(self):
        before = [
            {"detail_url": "https://example/a", "title": "A", "published_at": "2026-01-01"},
            {"detail_url": "https://example/b", "title": "B", "published_at": "2026-01-02"},
            {"detail_url": "https://example/c", "title": "C", "published_at": "2026-01-03"},
        ]
        after = [
            {"detail_url": "https://example/a", "title": "A", "published_at": "2026-01-01"},
            {"detail_url": "https://example/b", "title": "B（更新）", "published_at": "2026-01-02"},
            {"detail_url": "https://example/d", "title": "D", "published_at": "2026-01-04"},
        ]

        result = compare_lists(before, after)

        self.assertEqual(1, len(result["unchanged"]))
        self.assertEqual(1, len(result["updated"]))
        self.assertEqual(1, len(result["new"]))
        self.assertEqual(1, len(result["absent_from_current_sample"]))


if __name__ == "__main__":
    unittest.main()
