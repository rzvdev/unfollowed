"""OCR helpers for extracting Instagram usernames from screenshot regions.

Assumptions:
    - pytesseract is installed and configured on the system PATH.
    - Input images are PIL Image objects cropped to username text regions.
"""

from __future__ import annotations

import re
from typing import Optional

import pytesseract
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

USERNAME_PATTERN = re.compile(r"[A-Za-z0-9._]+")


def _preprocess(image: Image.Image) -> Image.Image:
    """Lightweight upscale + sharpen to help Tesseract see punctuation."""
    gray = ImageOps.grayscale(image)
    boosted = ImageOps.autocontrast(gray, cutoff=1)

    width, height = boosted.size
    if width > 0 and height > 0:
        boosted = boosted.resize((width * 3, height * 3), Image.LANCZOS)

    contrasted = ImageEnhance.Contrast(boosted).enhance(1.3)
    return contrasted.filter(ImageFilter.UnsharpMask(radius=1, percent=110, threshold=2))


def read_username(image: Image.Image) -> Optional[str]:
    """Return cleaned username text or None if OCR fails."""
    processed = _preprocess(image)
    processed.save("logs/debug/last_ocr_processed.png")
    raw_text = pytesseract.image_to_string(
        processed,
        config="--oem 1 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._",
    )
    matches = USERNAME_PATTERN.findall(raw_text)
    if not matches:
        return None
    # Choose the longest token as the best candidate.
    candidate = max(matches, key=len)
    return candidate.strip()
