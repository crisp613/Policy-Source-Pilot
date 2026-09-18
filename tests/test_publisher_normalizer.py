import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from publisher_normalizer import normalize_publisher  # noqa: E402


class PublisherNormalizerTests(unittest.TestCase):
    def test_body_issuer_has_highest_priority(self):
        result = normalize_publisher(
            issuer="四川省经济和信息化厅办公室",
            publishing_unit="四川省经济和信息化厅",
            info_source="技术创新处",
        )

        self.assertEqual("四川省经济和信息化厅办公室", result.publisher)
        self.assertEqual("issuer", result.source_field)
        self.assertEqual("正文落款：四川省经济和信息化厅办公室", result.evidence)

    def test_publishing_unit_is_used_when_issuer_is_missing(self):
        result = normalize_publisher(publishing_unit="科学技术部")

        self.assertEqual("科学技术部", result.publisher)
        self.assertEqual("publishing_unit", result.source_field)

    def test_full_organization_info_source_can_be_used(self):
        result = normalize_publisher(info_source="四川省科学技术厅")

        self.assertEqual("四川省科学技术厅", result.publisher)
        self.assertEqual("info_source", result.source_field)

    def test_internal_division_is_not_promoted_to_publisher(self):
        result = normalize_publisher(info_source="人工智能处")

        self.assertIsNone(result.publisher)
        self.assertEqual("not_provided", result.status)

    def test_existing_explicit_publisher_is_preserved(self):
        result = normalize_publisher(
            publisher="国家能源局",
            publisher_evidence="页面发布单位：国家能源局",
            publisher_source="publishing_unit",
            issuer="其他单位",
        )

        self.assertEqual("国家能源局", result.publisher)
        self.assertEqual("publishing_unit", result.source_field)


if __name__ == "__main__":
    unittest.main()
