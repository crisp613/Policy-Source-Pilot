import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from search_product_data import date_range_start, get_policy_detail, search_policies  # noqa: E402


class SearchProductDataTests(unittest.TestCase):
    @staticmethod
    def item(item_id: str, **overrides) -> dict:
        record = {
            "id": item_id,
            "title": "项目申报通知",
            "content": "正文包含人工智能和项目材料。",
            "document_number": None,
            "url": f"https://example.test/{item_id}",
            "published_at": "2026-09-18T00:00:00+08:00",
            "publisher": "测试单位",
            "source_level": "四川省",
            "department_line": "科技",
            "information_type": "申报通知",
            "excerpt": "正文摘要",
            "deadline": "2026-10-01",
            "source_id": "sc-kjt-notices",
            "source_name": "四川省科学技术厅",
            "column_name": "通知公告",
        }
        record.update(overrides)
        return record

    def test_searches_title_body_and_document_number(self):
        items = [
            self.item("title", title="人工智能项目申报通知"),
            self.item(
                "body",
                title="普通通知",
                content="正文包含人工智能需求。",
                published_at="2026-09-19T00:00:00+08:00",
            ),
            self.item(
                "number",
                title="普通通知",
                content="正文为一般事项说明。",
                document_number="川科政〔2026〕6号",
            ),
        ]

        by_text = search_policies(items, query="人工智能")
        by_number = search_policies(items, query="川科政")

        self.assertEqual(["body", "title"], [item["id"] for item in by_text["items"]])
        self.assertEqual(["number"], [item["id"] for item in by_number["items"]])

    def test_filters_sorting_and_pagination(self):
        items = [
            self.item("a", published_at="2026-09-01T00:00:00+08:00", deadline=None),
            self.item("b", published_at="2026-09-02T00:00:00+08:00", deadline="2026-09-20", department_line="经信"),
            self.item("c", published_at="2026-09-03T00:00:00+08:00", deadline="2026-09-10", source_level="国家"),
        ]

        result = search_policies(
            items,
            departments=["经信", "科技"],
            date_from="2026-09-01",
            date_to="2026-09-02",
            sort="deadline_asc",
            page=1,
            page_size=1,
        )

        self.assertEqual(2, result["total"])
        self.assertEqual(2, result["total_pages"])
        self.assertEqual(["b"], [item["id"] for item in result["items"]])
        self.assertNotIn("content", result["items"][0])

    def test_returns_full_detail_by_id_and_rejects_missing_id(self):
        items = [self.item("detail")]

        self.assertEqual("正文包含人工智能和项目材料。", get_policy_detail(items, "detail")["content"])
        with self.assertRaisesRegex(ValueError, "未找到"):
            get_policy_detail(items, "missing")

    def test_title_scope_relative_dates_relevance_and_highlights(self):
        items = [
            self.item("body", title="普通通知", content="人工智能 人工智能", published_at="2026-09-18T00:00:00+08:00"),
            self.item("title", title="人工智能项目通知", content="普通说明", published_at="2026-09-17T00:00:00+08:00"),
        ]

        result = search_policies(items, query="人工智能", title_only=True, sort="relevance")

        self.assertEqual(["title"], [item["id"] for item in result["items"]])
        self.assertEqual([[0, 4]], result["items"][0]["highlights"]["title"])
        self.assertEqual("2026-08-19", date_range_start("30d", today=__import__("datetime").date(2026, 9, 18)))


if __name__ == "__main__":
    unittest.main()
