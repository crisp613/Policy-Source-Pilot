"""四川省科技厅采集兼容入口；核心流程位于 policy_source_crawler。"""

from pathlib import Path
from typing import Callable

from policy_source_crawler import SourceConfig, crawl_source, run_source_cli
from sc_kjt_parser import parse_detail, parse_list

SOURCE_ID = "sc-kjt-notices"
LIST_URL = "https://kjt.sc.gov.cn/kjt/gstz/newschild.shtml"
DEFAULT_OUTPUT = Path("local-artifacts/sc-kjt-notices/first-10-pages")


def list_page_url(page: int) -> str:
    if page < 1:
        raise ValueError("页码必须大于等于 1")
    return LIST_URL if page == 1 else f"https://kjt.sc.gov.cn/kjt/gstz/newschild_{page}.shtml"


CONFIG = SourceConfig(
    "sc-kjt", SOURCE_ID, "四川省科学技术厅", "四川省", "科技", "公示公告／告知栏",
    list_page_url, parse_list, parse_detail, DEFAULT_OUTPUT,
)


def crawl(*, pages: int = 10, output_dir: Path = DEFAULT_OUTPUT, fetch_text: Callable[[str], str] | None = None, delay_seconds: float = 0.2, timeout_seconds: float = 30.0, resume: bool = True) -> dict:
    return crawl_source(CONFIG, pages=pages, output_dir=output_dir, fetch_text=fetch_text, delay_seconds=delay_seconds, timeout_seconds=timeout_seconds, resume=resume)


if __name__ == "__main__":
    run_source_cli(CONFIG, "采集四川省科技厅通知详情纯文本")
