import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from document_number_extractor import extract_document_number  # noqa: E402


class DocumentNumberExtractorTests(unittest.TestCase):
    def test_explicit_page_field_has_priority(self):
        result = extract_document_number(
            title="测试通知",
            content="引用文件川科政〔2025〕1号",
            explicit_number="川经信办函〔2026〕321号",
        )

        self.assertEqual("川经信办函〔2026〕321号", result.document_number)
        self.assertEqual("page_field", result.source)

    def test_extracts_document_number_from_body_opening(self):
        result = extract_document_number(
            title="关于开展有关工作的通知",
            content="川经信办函〔2026〕315号 各市（州）经济和信息化局：正文内容。",
        )

        self.assertEqual("川经信办函〔2026〕315号", result.document_number)
        self.assertEqual("body_opening", result.source)

    def test_referenced_document_number_later_in_body_is_ignored(self):
        result = extract_document_number(
            title="关于开展有关工作的通知",
            content="各有关单位：根据上级有关工作要求和《管理办法》（国科发资〔2024〕28号）组织实施。",
        )

        self.assertIsNone(result.document_number)
        self.assertEqual("not_provided", result.status)

    def test_extracts_document_number_from_title(self):
        result = extract_document_number(
            title="关于有关事项的通知（川科政〔2026〕6号）",
            content="正文",
        )

        self.assertEqual("川科政〔2026〕6号", result.document_number)
        self.assertEqual("title", result.source)

    def test_normalizes_spaces_and_brackets(self):
        result = extract_document_number(
            title="测试通知",
            content="川经信办函【 2026 】 314 号 各有关单位：",
        )

        self.assertEqual("川经信办函〔2026〕314号", result.document_number)

    def test_missing_document_number_remains_empty(self):
        result = extract_document_number(title="普通通知", content="正文没有文号。")

        self.assertIsNone(result.document_number)
        self.assertIsNone(result.evidence)
        self.assertEqual("not_provided", result.status)


if __name__ == "__main__":
    unittest.main()
