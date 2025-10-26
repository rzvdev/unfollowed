"""Screen capture helpers for Unfollowed.

Assumptions:
    - Primary display resolution is 1920x1080 at 100% scaling.
    - The bot captures from the main display only.

This module wraps ``pyautogui.screenshot`` to provide full-screen and region
captures, returning PIL Image objects for downstream processing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import pyautogui
from PIL import Image


def capture_fullscreen(save_path: Optional[Path] = None) -> Image.Image:
    """Capture the entire primary display."""
    screenshot = pyautogui.screenshot()
    if save_path:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        screenshot.save(str(save_path))
    return screenshot


def capture_region(region: Tuple[int, int, int, int], save_path: Optional[Path] = None) -> Image.Image:
    """Capture a rectangular region given (left, top, width, height)."""
    left, top, width, height = region
    screenshot = pyautogui.screenshot(region=(left, top, width, height))
    if save_path:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        screenshot.save(str(save_path))
    return screenshot
