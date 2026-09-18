"""规范化通知附件资源；附件只保留官方链接，不下载或解析内容。"""

from __future__ import annotations

from pathlib import PurePosixPath
from urllib.parse import urlparse


def file_type(name: str | None, url: str | None) -> str | None:
    candidate = urlparse(url or "").path or (name or "")
    suffix = PurePosixPath(candidate).suffix.lower().lstrip(".")
    return suffix or None


def normalize_attachments(attachments: list[dict] | None) -> list[dict]:
    """保留附件名称、官方链接、文件类型和访问状态，绝不下载附件。"""
    normalized: list[dict] = []
    seen: set[tuple[str | None, str | None]] = set()
    for attachment in attachments or []:
        if not isinstance(attachment, dict):
            continue
        name = str(attachment.get("name") or "").strip() or None
        url = str(attachment.get("url") or "").strip() or None
        key = (name, url)
        if key in seen:
            continue
        seen.add(key)
        access = attachment.get("access")
        if access not in {"public_link", "login_required", "link_missing"}:
            access = "public_link" if url else "link_missing"
        normalized.append(
            {
                "name": name,
                "url": url,
                "file_type": file_type(name, url),
                "access": access,
                "downloaded": False,
                "content_indexed": False,
            }
        )
    return normalized
