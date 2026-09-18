"""对公开正文图片执行临时 OCR，不向磁盘保存图片。"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Callable


BinaryFetcher = Callable[[str], bytes]


@dataclass(frozen=True)
class OcrResult:
    status: str
    text: str | None
    error: str | None = None


def ocr_image_bytes(image_bytes: bytes, *, runner: Callable[..., object] = subprocess.run) -> OcrResult:
    """通过 tesseract 标准输入识别，避免创建或保留本地图片文件。"""
    if not image_bytes:
        return OcrResult("failed", None, "图片响应为空")
    try:
        completed = runner(
            ["tesseract", "stdin", "stdout", "-l", "chi_sim+eng"],
            input=image_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
    except FileNotFoundError:
        return OcrResult("unavailable", None, "未安装 tesseract，未执行图片识别")
    except subprocess.CalledProcessError as error:
        message = error.stderr.decode("utf-8", errors="replace").strip() if error.stderr else str(error)
        return OcrResult("failed", None, message)
    except OSError as error:
        return OcrResult("failed", None, str(error))
    output = getattr(completed, "stdout", b"")
    text = output.decode("utf-8", errors="replace").strip() if isinstance(output, bytes) else str(output).strip()
    return OcrResult("processed", text or None, None if text else "未识别出文字")


def process_images(
    images: list[dict] | None,
    fetch_bytes: BinaryFetcher | None,
    *,
    enabled: bool,
    ocr_reader: Callable[[bytes], OcrResult] = ocr_image_bytes,
) -> tuple[list[dict], str | None, str]:
    """返回图片状态、OCR 文本和汇总状态；图片只在内存中处理。"""
    normalized = [dict(image) for image in images or [] if isinstance(image, dict) and image.get("url")]
    if not normalized:
        return [], None, "no_images"
    if not enabled:
        for image in normalized:
            image.update({"ocr_status": "not_requested", "ocr_text": None, "ocr_error": None})
        return normalized, None, "not_requested"
    if fetch_bytes is None:
        for image in normalized:
            image.update({"ocr_status": "unavailable", "ocr_text": None, "ocr_error": "未提供图片读取器"})
        return normalized, None, "unavailable"

    texts: list[str] = []
    statuses: list[str] = []
    for image in normalized:
        try:
            result = ocr_reader(fetch_bytes(image["url"]))
        except OSError as error:
            result = OcrResult("failed", None, str(error))
        image.update({"ocr_status": result.status, "ocr_text": result.text, "ocr_error": result.error})
        statuses.append(result.status)
        if result.text:
            texts.append(result.text)
    if all(status == "processed" for status in statuses):
        status = "processed"
    elif any(status == "processed" for status in statuses):
        status = "partial"
    elif all(status == "unavailable" for status in statuses):
        status = "unavailable"
    else:
        status = "failed"
    return normalized, "\n".join(texts) or None, status
