import sys
import unittest
from pathlib import Path
from urllib.error import HTTPError


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from policy_source_crawler import AccessBlockedError, HttpFetcher  # noqa: E402


class FakeHeaders:
    def get_content_charset(self):
        return "utf-8"


class FakeResponse:
    headers = FakeHeaders()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return "公开正文".encode("utf-8")


class HttpFetcherTests(unittest.TestCase):
    def test_stops_immediately_for_access_control_statuses(self):
        for status in (403, 412, 429):
            with self.subTest(status=status):
                calls = []

                def opener(request, timeout):
                    calls.append(request.full_url)
                    raise HTTPError(request.full_url, status, "blocked", None, None)

                fetcher = HttpFetcher(opener=opener, sleeper=lambda _: self.fail("不应退避重试"))
                with self.assertRaisesRegex(AccessBlockedError, f"HTTP {status}"):
                    fetcher("https://example.test/list")
                self.assertEqual(1, len(calls))

    def test_retries_5xx_with_exponential_backoff(self):
        calls, delays = [], []

        def opener(request, timeout):
            calls.append(request.full_url)
            if len(calls) < 3:
                raise HTTPError(request.full_url, 503, "unavailable", None, None)
            return FakeResponse()

        fetcher = HttpFetcher(delay_seconds=0, opener=opener, sleeper=delays.append)
        self.assertEqual("公开正文", fetcher("https://example.test/list"))
        self.assertEqual(3, len(calls))
        self.assertEqual([1.0, 2.0], delays)
