"""Template matching helpers for detecting Instagram UI elements.

Assumptions:
    - Input images are standard RGB PIL images.
    - Templates are PNG files stored in the configured templates directory.

The functions here wrap OpenCV (cv2) template matching, returning coordinates
and confidence scores so downstream code can act on detections.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np
from PIL import Image


def _to_gray(image: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)


def _load_template(path: Path) -> np.ndarray:
    template = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if template is None:
        raise FileNotFoundError(f"Template not found or unreadable: {path}")
    return template


def find_best_match(
    haystack: Image.Image,
    template_path: Path,
    confidence_threshold: float = 0.8,
) -> Optional[Tuple[int, int, float]]:
    """Return best match (x, y, confidence) or None if below threshold."""
    gray_haystack = _to_gray(haystack)
    template = _load_template(template_path)

    result = cv2.matchTemplate(gray_haystack, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    if max_val < confidence_threshold:
        return None

    match_x, match_y = max_loc
    return match_x, match_y, float(max_val)
