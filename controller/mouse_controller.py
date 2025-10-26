"""Mouse control utilities for Unfollowed.

Assumptions:
    - Primary display is 1920x1080.
    - The bot has exclusive control of the mouse while running.
    - ``pyautogui`` is installed and allowed to move the system cursor.

The helpers here wrap ``pyautogui`` with easing and jitter to better mimic
human input while keeping the API small and predictable for the rest of the
application.
"""

from __future__ import annotations

import math
import random
import time
from typing import Tuple

import pyautogui

# Fail fast if failsafe triggers due to rapid corner movement.
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.0


def _jitter(value: float, magnitude: float) -> float:
    return value + random.uniform(-magnitude, magnitude)


def _compute_travel_time(distance: float) -> float:
    # Travel speed loosely calibrated to feel natural on a 1080p display.
    base_speed = 700.0  # pixels per second
    min_time = 0.18
    time_seconds = max(distance / base_speed, min_time)
    return time_seconds * random.uniform(0.9, 1.2)


def move_mouse_human_like(x: int, y: int, *, jitter_pixels: float = 2.0) -> None:
    """Move cursor to target coordinates with slight randomness."""
    current_x, current_y = pyautogui.position()
    distance = math.dist((current_x, current_y), (x, y))
    duration = _compute_travel_time(distance)

    target_x = _jitter(float(x), jitter_pixels)
    target_y = _jitter(float(y), jitter_pixels)

    pyautogui.moveTo(target_x, target_y, duration=duration, tween=pyautogui.easeInOutQuad)


def click(button: str = "left", clicks: int = 1, interval: float = 0.15) -> None:
    """Perform a mouse click with subtle timing variation."""
    actual_interval = interval * random.uniform(0.85, 1.15)
    time.sleep(random.uniform(0.08, 0.16))
    pyautogui.click(button=button, clicks=clicks, interval=actual_interval)
    time.sleep(random.uniform(0.05, 0.12))


def scroll(amount: int) -> None:
    """Scroll the mouse wheel with a slight randomized cadence."""
    pyautogui.scroll(amount)
    time.sleep(random.uniform(0.25, 0.45))


def move_and_click(point: Tuple[int, int]) -> None:
    """Convenience helper to move and click in a single call."""
    x, y = point
    move_mouse_human_like(x, y)
    click()
