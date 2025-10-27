"""Locate usernames and actionable buttons within the Instagram Following popup.

Assumptions:
    - Popup is aligned as captured in config (1920x1080 screen, browser fullscreen).
    - Username text appears within a predictable region in each row.
    - The "Following" button sits a fixed offset from the username box center.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re
from typing import Dict, Iterable, Optional, Tuple

import numpy as np
from PIL import Image

from . import ocr_reader


@dataclass(frozen=True)
class PopupGeometry:
    top_margin: int
    left_margin: int
    width: int
    row_height: int
    ocr_offset_x: int
    ocr_offset_y: int
    ocr_width: int
    ocr_height: int
    button_offset_x: int
    button_offset_y: int

    @property
    def popup_bottom(self) -> int:
        return self.top_margin + self.width


def build_geometry(config: Dict[str, Dict[str, int]]) -> PopupGeometry:
    vision_cfg = config.get("vision", {})
    ocr_region = vision_cfg.get("ocr_region", {})
    return PopupGeometry(
        top_margin=vision_cfg.get("popup_top_margin", 220),
        left_margin=vision_cfg.get("popup_left_margin", 540),
        width=vision_cfg.get("popup_width", 840),
        row_height=vision_cfg.get("row_height", 72),
        ocr_offset_x=ocr_region.get("offset_x", 80),
        ocr_offset_y=ocr_region.get("offset_y", 12),
        ocr_width=ocr_region.get("width", 320),
        ocr_height=ocr_region.get("height", 32),
        button_offset_x=vision_cfg.get("following_button_offset_x", 520),
        button_offset_y=vision_cfg.get("following_button_offset_y", 0),
    )

def _focus_username_band(region: Image.Image) -> Image.Image:
    """Return a crop tightly focused on the bright username line."""
    gray = region.convert("L")
    arr = np.array(gray)
    if arr.size == 0:
        return region

    mask = arr >= 225
    if not mask.any():
        mask = arr >= 180

    row_has_text = mask.any(axis=1)
    indices = np.where(row_has_text)[0]
    if indices.size == 0:
        return region

    top = int(indices[0])
    gap_after = np.where(~row_has_text[top:])[0]
    if gap_after.size > 0:
        bottom = top + int(gap_after[0]) - 1
    else:
        bottom = int(indices[-1])

    max_band = 20
    bottom = min(bottom, top + max_band - 1, arr.shape[0] - 1)

    margin_top = 2
    margin_bottom = 4
    top = max(0, top - margin_top)
    bottom = min(arr.shape[0] - 1, bottom + margin_bottom)

    if bottom <= top:
        return region
    return region.crop((0, top, region.width, bottom + 1))


def _iter_rows(geometry: PopupGeometry, screenshot: Image.Image) -> Iterable[Tuple[int, Image.Image]]:
    popup_top = geometry.top_margin
    popup_left = geometry.left_margin
    popup_bottom = min(popup_top + screenshot.height - popup_top, screenshot.height)

    row_index = 0
    while True:
        row_top = popup_top + row_index * geometry.row_height
        if row_top + geometry.row_height > popup_bottom:
            break
        crop_box = (
            popup_left,
            row_top,
            popup_left + geometry.width,
            row_top + geometry.row_height,
        )
        row_image = screenshot.crop(crop_box)
        yield row_top, row_image
        row_index += 1


def _sanitize_label(text: Optional[str]) -> str:
    if not text:
        return "blank"
    return "".join(c for c in text if c.isalnum() or c in ("_", "-")) or "blank"


def _extract_username(
    geometry: PopupGeometry,
    row_image: Image.Image,
    *,
    debug_dir: Optional[Path] = None,
    row_top: Optional[int] = None,
) -> Optional[str]:
    ocr_box = (
        geometry.ocr_offset_x,
        geometry.ocr_offset_y,
        geometry.ocr_offset_x + geometry.ocr_width,
        geometry.ocr_offset_y + geometry.ocr_height,
    )
    username_region = row_image.crop(ocr_box)
    focused_region = _focus_username_band(username_region)
    detected = ocr_reader.read_username(focused_region)

    if debug_dir:
        label = _sanitize_label(detected)
        prefix = f"{row_top:04d}" if row_top is not None else "row"
        path = debug_dir / f"ocr_{prefix}_{label}.png"
        try:
            focused_region.save(path)
        except OSError:
            pass

    return detected


def locate_following_button(
    screenshot: Image.Image,
    target_username: str,
    config: Dict[str, Dict[str, int]],
) -> Optional[Tuple[int, int]]:
    """Return screen coordinates for the target user's button or None."""
    geometry = build_geometry(config)
    vision_cfg = config.get("vision", {})
    threshold = float(vision_cfg.get("ocr_match_threshold", 0.75))
    normalized_target = target_username.strip().lower()

    sanitize = lambda text: re.sub(r"[^a-z0-9]", "", text.lower())
    sanitized_target = sanitize(target_username)
    logging_cfg = config.get("logging", {})
    debug_enabled = bool(logging_cfg.get("debug_capture_rows", False))
    debug_dir: Optional[Path] = None

    if debug_enabled:
        logs_root = Path(config.get("paths", {}).get("logs_dir", "logs"))
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        safe_target = "".join(c for c in target_username if c.isalnum() or c in ("_", "-")) or "unknown"
        debug_dir = logs_root / "debug" / f"{timestamp}_{safe_target}"
        debug_dir.mkdir(parents=True, exist_ok=True)

    try:
        from difflib import SequenceMatcher
    except ImportError:
        SequenceMatcher = None

    def _is_match(candidate: str) -> bool:
        if candidate == normalized_target:
            return True
        if SequenceMatcher is None:
            return False
        ratio = SequenceMatcher(None, candidate, normalized_target).ratio()
        return ratio >= threshold

    for row_top, row_image in _iter_rows(geometry, screenshot):
        detected_username = _extract_username(
            geometry,
            row_image,
            debug_dir=debug_dir,
            row_top=row_top,
        )
        if debug_dir:
            label = detected_username or "unmatched"
            row_path = debug_dir / f"row_{row_top:04d}_{label}.png"
            try:
                row_image.save(row_path)
            except OSError:
                # Ignore saving errors to avoid breaking the workflow.
                pass
        if not detected_username:
            continue
        normalized_candidate = detected_username.strip().lower()
        if sanitize(normalized_candidate) == sanitized_target:
            match_ok = True
        else:
            match_ok = _is_match(normalized_candidate)
        if not match_ok:
            continue

        button_x = geometry.left_margin + geometry.button_offset_x
        button_y = row_top + geometry.button_offset_y + geometry.row_height // 2
        return button_x, button_y

    return None
