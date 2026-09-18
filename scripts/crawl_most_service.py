"""国家科技管理信息系统采集兼容入口；核心流程位于 policy_source_crawler。"""

from pathlib import Path
from typing import Callable

from most_service_parser import parse_detail, parse_list
from policy_source_crawler import SourceConfig, crawl_source, run_source_cli

SOURCE_ID = "most-service-notices"
LIST_URL = "https://service.most.gov.cn/kjjh_tztg/"
DEFAULT_OUTPUT = Path("local-artifacts/most-service-notices/first-10-pages")


def list_page_url(page: int) -> str:
    if page < 1:
        raise ValueError("页码必须大于等于 1")
    return LIST_URL if page == 1 else f"https://service.most.gov.cn/kjjh_tztg/index_{page}.html"


CONFIG = SourceConfig("most-service", SOURCE_ID, "国家科技管理信息系统公共服务平台", list_page_url, parse_list, parse_detail, DEFAULT_OUTPUT)


def crawl(*, pages: int = 10, output_dir: Path = DEFAULT_OUTPUT, fetch_text: Callable[[str], str] | None = None, delay_seconds: float = 0.2, timeout_seconds: float = 30.0, resume: bool = True) -> dict:
    return crawl_source(CONFIG, pages=pages, output_dir=output_dir, fetch_text=fetch_text, delay_seconds=delay_seconds, timeout_seconds=timeout_seconds, resume=resume)


if __name__ == "__main__":
    run_source_cli(CONFIG, "采集国家科技管理信息系统公开通知详情纯文本")
