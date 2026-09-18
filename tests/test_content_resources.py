import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from content_resources import normalize_attachments  # noqa: E402
from image_ocr import OcrResult, ocr_image_bytes, process_images  # noqa: E402


class ContentResourceTests(unittest.TestCase):
    def test_attachments_remain_links_and_are_not_indexed(self):
        attachments = normalize_attachments(
            [
                {"name": "申报指南.pdf", "url": "https://example.test/guide.pdf"},
                {"name": "登录后获取", "url": None, "access": "login_required"},
            ]
        )
        self.assertEqual("pdf", attachments[0]["file_type"])
        self.assertFalse(attachments[0]["downloaded"])
        self.assertFalse(attachments[0]["content_indexed"])
        self.assertEqual("login_required", attachments[1]["access"])

    def test_ocr_uses_memory_bytes_and_keeps_source_status(self):
        class Completed:
            stdout = "图片中的申报文字".encode("utf-8")

        result = ocr_image_bytes(b"image", runner=lambda *args, **kwargs: Completed())
        images, text, status = process_images(
            [{"url": "https://example.test/body.png", "alt": "通知图"}],
            lambda _: b"image",
            enabled=True,
            ocr_reader=lambda _: OcrResult("processed", "图片中的申报文字"),
        )
        self.assertEqual("processed", result.status)
        self.assertEqual("processed", status)
        self.assertEqual("图片中的申报文字", text)
        self.assertEqual("https://example.test/body.png", images[0]["url"])

    def test_ocr_is_skipped_unless_explicitly_enabled(self):
        images, text, status = process_images(
            [{"url": "https://example.test/body.png"}], lambda _: self.fail("不应读取图片"), enabled=False
        )
        self.assertEqual("not_requested", status)
        self.assertIsNone(text)
        self.assertEqual("not_requested", images[0]["ocr_status"])
