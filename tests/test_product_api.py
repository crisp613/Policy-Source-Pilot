import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from product_api import route_request  # noqa: E402


class ProductApiTests(unittest.TestCase):
    def test_routes_list_detail_and_sources(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            policy_id = "sc-kjt-notices:abc"
            (root / "policies.json").write_text(
                json.dumps(
                    {"items": [{"id": policy_id, "title": "人工智能申报", "content": "正文", "published_at": "2026-09-18T00:00:00+08:00"}]},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (root / "sources.json").write_text(json.dumps({"sources": []}), encoding="utf-8")
            status, listing = route_request(root / "policies.json", root / "sources.json", "/api/policies?q=人工智能")
            _, detail = route_request(root / "policies.json", root / "sources.json", f"/api/policies/{policy_id}")
            _, sources = route_request(root / "policies.json", root / "sources.json", "/api/sources")
            missing_status, _ = route_request(root / "policies.json", root / "sources.json", "/nope")
        self.assertEqual(200, status)
        self.assertEqual([policy_id], [item["id"] for item in listing["items"]])
        self.assertEqual("正文", detail["content"])
        self.assertEqual([], sources["sources"])
        self.assertEqual(404, missing_status)
