import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from export_product_data import export_product_data  # noqa: E402


class ExportProductDataTests(unittest.TestCase):
    def write_source(self, root: Path, source_id: str, records: list[dict], status: dict) -> None:
        output = root / source_id / "first-10-pages"
        output.mkdir(parents=True)
        (output / "details.json").write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
        (output / "source-status.json").write_text(json.dumps(status, ensure_ascii=False), encoding="utf-8")

    def record(self, source_id: str, record_id: str, published_at: str, *, status: str = "ok") -> dict:
        return {
            "external_id": record_id,
            "title": f"{source_id}政策",
            "url": f"https://example.test/{record_id}",
            "published_at": published_at,
            "content": "这是一段包含   多余空格的政策正文。" * 20,
            "metadata": {
                "status": status,
                "source_id": source_id,
                "source_name": source_id,
                "source_level": "四川省",
                "department_line": "科技",
                "information_type": "申报通知",
                "publisher": "测试单位",
                "publisher_status": "provided",
                "deadline": "2026-10-01",
                "deadline_status": "provided",
                "document_number": None,
                "document_number_status": "not_provided",
                "column_name": "通知公告",
                "attachments": [],
                "application_links": [],
            },
        }

    def test_exports_sorted_policies_facets_and_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "artifacts"
            output = Path(directory) / "product"
            self.write_source(
                root,
                "source-a",
                [self.record("source-a", "a", "2026-09-17T00:00:00+08:00")],
                {"source_id": "source-a", "status": "normal"},
            )
            self.write_source(
                root,
                "source-b",
                [
                    self.record("source-b", "b", "2026-09-18T00:00:00+08:00"),
                    self.record("source-b", "failed", "2026-09-19T00:00:00+08:00", status="error"),
                ],
                {"source_id": "source-b", "status": "partial"},
            )

            result = export_product_data(
                root,
                output,
                source_ids=("source-a", "source-b"),
                generated_at="2026-09-18T12:00:00+08:00",
            )
            policies = json.loads((output / "policies.json").read_text(encoding="utf-8"))
            sources = json.loads((output / "sources.json").read_text(encoding="utf-8"))

            self.assertEqual({"policies": 2, "sources": 2, "skipped_failed": 1, "output_dir": str(output)}, result)
            self.assertEqual(["b", "a"], [item["id"] for item in policies["items"]])
            self.assertEqual({"四川省": 2}, policies["facets"]["source_level"])
            self.assertEqual({"申报通知": 2}, policies["facets"]["information_type"])
            self.assertEqual(2, sources["total"])
            self.assertLessEqual(len(policies["items"][0]["excerpt"]), 181)
            self.assertNotIn("   ", policies["items"][0]["excerpt"])

    def test_rejects_legacy_detail_structure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "artifacts"
            output = Path(directory) / "product"
            self.write_source(
                root,
                "source-a",
                [{"title": "旧结构", "detail_url": "https://example.test/old"}],
                {"source_id": "source-a", "status": "normal"},
            )

            with self.assertRaisesRegex(ValueError, "统一结构"):
                export_product_data(root, output, source_ids=("source-a",))


if __name__ == "__main__":
    unittest.main()
