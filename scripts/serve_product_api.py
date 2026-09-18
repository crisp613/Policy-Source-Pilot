"""以只读本地 HTTP 服务暴露产品列表、详情和信息源导航数据。"""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from product_api import route_request


def make_handler(policies_path: Path, sources_path: Path):
    class ProductApiHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            try:
                status, payload = route_request(policies_path, sources_path, self.path)
            except (ValueError, TypeError) as error:
                status, payload = 400, {"error": str(error)}
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            return

    return ProductApiHandler


def main() -> None:
    parser = argparse.ArgumentParser(description="启动只读政策产品本地接口")
    parser.add_argument("--data-dir", type=Path, default=Path("product-data"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()
    handler = make_handler(args.data_dir / "policies.json", args.data_dir / "sources.json")
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"政策产品接口已启动：http://{args.host}:{args.port}")
    print("GET /api/policies?q=人工智能&page=1&page_size=20")
    print("GET /api/policies/<记录ID>")
    print("GET /api/sources")
    server.serve_forever()


if __name__ == "__main__":
    main()
