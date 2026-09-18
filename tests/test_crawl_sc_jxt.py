import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from crawl_sc_jxt import LIST_URL, crawl, list_page_url  # noqa: E402


FIXTURES = ROOT / "tests" / "fixtures" / "policy-sources"


class ScJxtCrawlerTests(unittest.TestCase):
    def fixture(self, name: str) -> str:
        return (FIXTURES / name).read_text(encoding="utf-8")

    def test_list_page_urls(self):
        self.assertEqual(LIST_URL, list_page_url(1))
        self.assertEqual(
            "https://jxt.sc.gov.cn/scjxt/wjfb/common_list_10.shtml",
            list_page_url(10),
        )

    def test_crawl_saves_plain_text_details_without_network(self):
        responses = {
            LIST_URL: self.fixture("sc-jxt-list.html"),
            "https://jxt.sc.gov.cn/scjxt/wjfb/2026/9/15/a.shtml": self.fixture(
                "sc-jxt-detail-with-attachments.html"
            ),
            "https://jxt.sc.gov.cn/scjxt/wjfb/2026/9/9/b.shtml": self.fixture(
                "sc-jxt-detail-with-body-url.html"
            ),
        }

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            summary = crawl(
                pages=1,
                output_dir=output,
                fetch_text=responses.__getitem__,
                delay_seconds=0,
            )
            details = json.loads((output / "details.json").read_text(encoding="utf-8"))

            self.assertEqual(2, summary["details_ok"])
            self.assertEqual(0, summary["details_failed"])
            self.assertIn("申报", details[0]["body"])
            self.assertNotIn("附件：项目申报书", details[0]["body"])
            self.assertEqual(0, summary["attachments_downloaded"])
            self.assertTrue((output / "lists" / "page-001.html").exists())


if __name__ == "__main__":
    unittest.main()
