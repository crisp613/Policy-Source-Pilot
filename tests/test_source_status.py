import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from crawl_sc_jxt import CONFIG  # noqa: E402
from source_status import build_source_status  # noqa: E402


class SourceStatusTests(unittest.TestCase):
    def build(self, **overrides):
        values = {
            "run_started_at": "2026-09-18T10:00:00+08:00",
            "updated_at": "2026-09-18T10:05:00+08:00",
            "records_discovered": 150,
            "records_collected": 150,
            "records_failed": 0,
        }
        values.update(overrides)
        return build_source_status(CONFIG, **values)

    def test_successful_run_is_normal(self):
        status = self.build()

        self.assertEqual("normal", status["status"])
        self.assertEqual(0, status["consecutive_failures"])
        self.assertEqual(status["updated_at"], status["last_success_at"])
        self.assertEqual("https://jxt.sc.gov.cn/", status["official_url"])

    def test_partial_run_increments_consecutive_failures(self):
        status = self.build(
            records_collected=149,
            records_failed=1,
            last_error="timeout",
            previous={"consecutive_failures": 2, "last_success_at": "2026-09-17T10:00:00+08:00"},
        )

        self.assertEqual("partial", status["status"])
        self.assertEqual(3, status["consecutive_failures"])
        self.assertEqual("timeout", status["last_error"])
        self.assertEqual(status["updated_at"], status["last_success_at"])

    def test_failed_run_preserves_previous_success_time(self):
        status = self.build(
            records_discovered=0,
            records_collected=0,
            records_failed=0,
            last_error="list request failed",
            previous={"consecutive_failures": 1, "last_success_at": "2026-09-17T10:00:00+08:00"},
        )

        self.assertEqual("failed", status["status"])
        self.assertEqual(2, status["consecutive_failures"])
        self.assertEqual("2026-09-17T10:00:00+08:00", status["last_success_at"])


if __name__ == "__main__":
    unittest.main()
