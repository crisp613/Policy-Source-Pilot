"""四川省经信厅采集兼容入口；核心流程位于 policy_source_crawler。"""

from pathlib import Path
from typing import Callable

from policy_source_crawler import HttpFetcher, SourceConfig, crawl_source, detail_file_name, load_or_fetch, run_source_cli, write_json
from sc_jxt_parser import parse_detail, parse_list

SOURCE_ID = "sc-jxt-notices"
LIST_URL = "https://jxt.sc.gov.cn/scjxt/wjfb/common_list.shtml"
DEFAULT_OUTPUT = Path("local-artifacts/sc-jxt-notices/first-10-pages")


def list_page_url(page: int) -> str:
    if page < 1:
        raise ValueError("页码必须大于等于 1")
    return LIST_URL if page == 1 else f"https://jxt.sc.gov.cn/scjxt/wjfb/common_list_{page}.shtml"


CONFIG = SourceConfig(
    "sc-jxt", SOURCE_ID, "四川省经济和信息化厅", "四川省", "经信", "文件发布",
    list_page_url, parse_list, parse_detail, DEFAULT_OUTPUT,
)


def crawl(*, pages: int = 10, output_dir: Path = DEFAULT_OUTPUT, fetch_text: Callable[[str], str] | None = None, delay_seconds: float = 0.2, timeout_seconds: float = 30.0, resume: bool = True) -> dict:
    return crawl_source(CONFIG, pages=pages, output_dir=output_dir, fetch_text=fetch_text, delay_seconds=delay_seconds, timeout_seconds=timeout_seconds, resume=resume)


if __name__ == "__main__":
    run_source_cli(CONFIG, "采集四川省经信厅通知详情纯文本")
