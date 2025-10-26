"""Safety utilities for pacing and block detection."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Mapping, Optional

import pytesseract
from PIL import Image, ImageOps


def _normalize(text: str) -> str:
    return text.strip().lower()


def detect_block_phrase(image: Image.Image, phrases: Iterable[str]) -> Optional[str]:
    """Return the first configured block phrase found in OCR text."""
    grayscale = ImageOps.grayscale(image)
    enhanced = ImageOps.autocontrast(grayscale)
    raw_text = pytesseract.image_to_string(enhanced, config="--psm 6")
    normalized_text = raw_text.lower()
    for phrase in phrases:
        if phrase.lower() in normalized_text:
            return phrase
    return None


def _count_actions_from_log(log_path: Path) -> int:
    if not log_path.exists():
        return 0
    try:
        with log_path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError:
        return 0
    if not isinstance(data, list):
        return 0
    return sum(1 for entry in data if entry.get("status") == "unfollowed")


@dataclass
class SafetyMonitor:
    """Track action counts and detect block screens."""

    config: Mapping[str, object]
    log_path: Path
    block_phrases: List[str]
    daily_cap: int
    actions_today: int
    session_actions: int = 0

    def __init__(self, config: Mapping[str, object], log_path: Path) -> None:
        self.config = config
        self.log_path = log_path
        safety_cfg = config.get("safety", {})
        limits = config.get("limits", {})
        self.block_phrases = list(safety_cfg.get("block_phrases", []))
        self.daily_cap = int(limits.get("daily_cap", 150))
        self.actions_today = _count_actions_from_log(log_path)
        self.session_actions = 0

    def has_daily_capacity(self) -> bool:
        if self.daily_cap <= 0:
            return True
        return self.actions_today + self.session_actions < self.daily_cap

    def register_result(self, status: str) -> None:
        if status == "unfollowed":
            self.session_actions += 1

    def remaining_daily_quota(self) -> Optional[int]:
        if self.daily_cap <= 0:
            return None
        return max(self.daily_cap - (self.actions_today + self.session_actions), 0)

    def check_block_screenshot(self, screenshot: Image.Image) -> Optional[str]:
        if not self.block_phrases:
            return None
        return detect_block_phrase(screenshot, self.block_phrases)

    def mark_daily_rollover(self) -> None:
        today = datetime.now().strftime("%Y-%m-%d")
        if self.log_path.name.endswith(f"{today}.json"):
            # Same-day file; no rollover needed.
            return
        self.actions_today = 0
        self.session_actions = 0
