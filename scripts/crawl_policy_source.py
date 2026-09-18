"""三个政策网站的统一采集命令入口。"""

import argparse
import json
from pathlib import Path

from crawl_most_service import CONFIG as MOST_SERVICE_CONFIG
from crawl_sc_jxt import CONFIG as SC_JXT_CONFIG
from crawl_sc_kjt import CONFIG as SC_KJT_CONFIG
from policy_source_crawler import crawl_source

SOURCES = {config.key: config for config in (SC_JXT_CONFIG, SC_KJT_CONFIG, MOST_SERVICE_CONFIG)}


def main() -> None:
    parser = argparse.ArgumentParser(description="统一采集三个政策网站的公开通知正文")
    parser.add_argument("--source", required=True, choices=sorted(SOURCES), help="选择政策来源")
    parser.add_argument("--pages", type=int, default=10, help="从第一页开始采集的页数，默认 10")
    parser.add_argument("--delay", type=float, default=0.2, help="远程请求最小间隔秒数，默认 0.2")
    parser.add_argument("--timeout", type=float, default=30.0, help="单个请求超时秒数，默认 30")
    parser.add_argument("--output", type=Path, help="自定义输出目录；默认使用来源专属目录")
    parser.add_argument("--no-resume", action="store_true", help="忽略已保存 HTML 并重新请求")
    args = parser.parse_args()
    config = SOURCES[args.source]
    summary = crawl_source(config, pages=args.pages, output_dir=args.output, delay_seconds=args.delay, timeout_seconds=args.timeout, resume=not args.no_resume)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
