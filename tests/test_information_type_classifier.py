import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from information_type_classifier import classify_information_type  # noqa: E402


class InformationTypeClassifierTests(unittest.TestCase):
    def assert_type(self, expected: str, title: str, content: str = "") -> None:
        result = classify_information_type(title, content)
        self.assertEqual(expected, result.information_type)
        self.assertIsNotNone(result.evidence)
        self.assertNotEqual("unclassified", result.rule)

    def test_classifies_five_product_types_from_explicit_title_evidence(self):
        samples = (
            ("公示", "2026年度项目拟立项名单公示"),
            ("征集", "关于征集重点产业科技攻关需求的通知"),
            ("政策文件", "关于印发《四川省科技计划管理办法》的通知"),
            ("申报通知", "关于组织开展2026年度项目申报工作的通知"),
            ("事务通知", "关于召开科技项目管理培训会的通知"),
        )
        for expected, title in samples:
            with self.subTest(title=title):
                self.assert_type(expected, title)

    def test_solicitation_has_priority_over_application_keyword(self):
        self.assert_type("征集", "关于征集2027年度项目申报需求的通知")

    def test_policy_document_has_priority_over_application_keyword(self):
        self.assert_type("政策文件", "关于印发《项目申报管理办法》的通知")

    def test_uses_body_only_when_title_is_not_explicit(self):
        result = classify_information_type("关于开展有关工作的通知", "一、申报条件 二、申报要求")
        self.assertEqual("申报通知", result.information_type)
        self.assertEqual("body_application_notice", result.rule)

    def test_ambiguous_record_remains_unclassified(self):
        result = classify_information_type("关于做好有关工作的通知", "请有关单位认真贯彻执行。")
        self.assertIsNone(result.information_type)
        self.assertIsNone(result.evidence)
        self.assertEqual("unclassified", result.rule)


if __name__ == "__main__":
    unittest.main()
