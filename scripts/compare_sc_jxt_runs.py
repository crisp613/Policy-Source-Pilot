"""比较四川省经信厅两次本地采集结果，不发起网络请求。"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from sc_jxt_parser import parse_detail, parse_list


LIST_URL = "https://jxt.sc.gov.cn/scjxt/wjfb/common_list.shtml"
DETAIL_URLS = [
    "https://jxt.sc.gov.cn/scjxt/wjfb/2026/9/15/c95e71e8c35a4caf8acad93a6a51e68d.shtml",
    "https://jxt.sc.gov.cn/scjxt/wjfb/2026/9/9/65d7fce92b864ee9a314533bddbaaaad.shtml",
    "https://jxt.sc.gov.cn/scjxt/wjfb/2026/8/25/c261d493cf3640bdaf55bc8babfe34b8.shtml",
]


def fingerprint(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def compare_lists(before: list[dict], after: list[dict]) -> dict:
    old = {item["detail_url"]: item for item in before}
    new = {item["detail_url"]: item for item in after}
    shared = old.keys() & new.keys()
    return {
        "new": [new[url] for url in sorted(new.keys() - old.keys())],
        "unchanged": [new[url] for url in sorted(shared) if old[url] == new[url]],
        "updated": [
            {"before": old[url], "after": new[url]}
            for url in sorted(shared)
            if old[url] != new[url]
        ],
        "absent_from_current_sample": [old[url] for url in sorted(old.keys() - new.keys())],
    }


def compare_details(before_paths: list[Path], after_paths: list[Path]) -> dict:
    unchanged = []
    updated = []
    failures = []
    for index, (before_path, after_path, url) in enumerate(
        zip(before_paths, after_paths, DETAIL_URLS, strict=True), start=1
    ):
        try:
            before = parse_detail(before_path.read_text(encoding="utf-8"), url)
            after = parse_detail(after_path.read_text(encoding="utf-8"), url)
        except (OSError, UnicodeError, ValueError) as error:
            failures.append({"sample": index, "url": url, "error": str(error)})
            continue
        before_hash = fingerprint(before)
        after_hash = fingerprint(after)
        record = {
            "sample": index,
            "url": url,
            "before_hash": before_hash,
            "after_hash": after_hash,
        }
        (unchanged if before_hash == after_hash else updated).append(record)
    return {"unchanged": unchanged, "updated": updated, "parse_failures": failures}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", type=Path, default=Path("local-artifacts/sc-jxt-notices"))
    parser.add_argument("--output", type=Path, default=Path("evidence/sc-jxt-run-comparison.json"))
    args = parser.parse_args()

    root = args.artifacts
    before_list = parse_list((root / "list-run-01.html").read_text(encoding="utf-8"), LIST_URL, 10)
    after_list = parse_list((root / "list-run-02.html").read_text(encoding="utf-8"), LIST_URL, 10)
    comparison = {
        "source_id": "sc-jxt-notices",
        "list": compare_lists(before_list, after_list),
        "details": compare_details(
            [root / f"detail-0{i}.html" for i in range(1, 4)],
            [root / f"detail-0{i}-run-02.html" for i in range(1, 4)],
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(comparison, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
