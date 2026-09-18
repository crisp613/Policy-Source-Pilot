import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_comparison import compare_runs  # noqa: E402


def record(item_id: str, content: str = "正文", status: str = "ok") -> dict:
    return {
        "external_id": item_id,
        "title": item_id,
        "url": f"https://example.test/{item_id}",
        "published_at": "2026-09-18T00:00:00+08:00",
        "content": content,
        "metadata": {"status": status, "attachments": []},
    }


class RunComparisonTests(unittest.TestCase):
    def test_distinguishes_new_repeated_updated_invalid_and_failed(self):
        comparison = compare_runs(
            [record("repeated"), record("updated", "旧正文"), record("invalid")],
            [record("repeated"), record("updated", "新正文"), record("new"), record("failed", status="error")],
        )
        self.assertEqual(
            {"new": 1, "repeated": 1, "updated": 1, "invalid": 1, "failed": 1},
            comparison["counts"],
        )
        self.assertEqual("updated", comparison["updated"][0]["id"])
