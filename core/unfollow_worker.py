"""Single-username unfollow workflow.

This module glues together screen capture, vision, and controller utilities to
process one username from the Following popup. It assumes a 1920x1080 display
and that the user has already opened the popup before execution.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple

from PIL import Image

from controller import mouse_controller
from core.safety import SafetyMonitor
from vision import locator, screen_capture, template_matcher

CONFIRM_CONFIDENCE_THRESHOLD = 0.82
CONFIRM_POLL_INTERVAL = 0.5
CONFIRM_MAX_ATTEMPTS = 8


@dataclass(frozen=True)
class UnfollowResult:
    username: str
    status: str
    timestamp: str
    details: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "username": self.username,
            "status": self.status,
            "timestamp": self.timestamp,
            "details": self.details,
        }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_timing(config: Mapping[str, Any]) -> Tuple[float, float]:
    timing_cfg = config.get("timing", {})
    min_delay = float(timing_cfg.get("min_action_delay", 2.0))
    max_delay = float(timing_cfg.get("max_action_delay", 4.5))
    if max_delay < min_delay:
        max_delay = min_delay
    return min_delay, max_delay


def _sleep_random_delay(config: Mapping[str, Any]) -> None:
    min_delay, max_delay = _get_timing(config)
    time.sleep(random.uniform(min_delay, max_delay))


def _confirm_template_path(config: Mapping[str, Any]) -> Path:
    safety_cfg = config.get("safety", {})
    template_name = safety_cfg.get("confirm_template_name", "confirm_unfollow.png")
    templates_dir = Path(config.get("paths", {}).get("templates_dir", "data/templates"))
    return templates_dir / template_name


def _confirm_unfollow(
    dry_run: bool,
    config: Mapping[str, Any],
) -> Tuple[bool, Optional[float], Optional[Image.Image]]:
    template_path = _confirm_template_path(config)
    if not template_path.exists():
        return False, None, None

    last_screenshot: Optional[Image.Image] = None
    with Image.open(template_path) as template_img:
        template_size = template_img.size

    for attempt in range(CONFIRM_MAX_ATTEMPTS):
        time.sleep(CONFIRM_POLL_INTERVAL)
        screenshot = screen_capture.capture_fullscreen()
        last_screenshot = screenshot
        match = template_matcher.find_best_match(screenshot, template_path, CONFIRM_CONFIDENCE_THRESHOLD)
        if not match:
            continue

        match_x, match_y, confidence = match
        button_x = int(match_x + template_size[0] / 2)
        button_y = int(match_y + template_size[1] / 2)

        if not dry_run:
            mouse_controller.move_mouse_human_like(button_x, button_y)
            mouse_controller.click()

        return True, confidence, screenshot

    return False, None, last_screenshot


def run_unfollow(
    username: str,
    config: Mapping[str, Any],
    *,
    dry_run: bool = False,
    safety_monitor: Optional[SafetyMonitor] = None,
) -> UnfollowResult:
    """Attempt to unfollow a single username."""
    screenshot = screen_capture.capture_fullscreen()

    if safety_monitor:
        block_phrase = safety_monitor.check_block_screenshot(screenshot)
        if block_phrase:
            return UnfollowResult(
                username=username,
                status="blocked",
                timestamp=_now_iso(),
                details={"block_phrase": block_phrase},
            )

    button_coords = locator.locate_following_button(screenshot, username, config)

    if not button_coords:
        return UnfollowResult(
            username=username,
            status="not_found",
            timestamp=_now_iso(),
            details={"message": "Username not visible in current viewport"},
        )

    if dry_run:
        return UnfollowResult(
            username=username,
            status="dry_run",
            timestamp=_now_iso(),
            details={"button_coords": button_coords},
        )

    mouse_controller.move_mouse_human_like(*button_coords)
    mouse_controller.click()

    confirmed, confidence, confirm_screenshot = _confirm_unfollow(dry_run, config)
    screenshot_to_inspect = confirm_screenshot or screenshot

    if safety_monitor and screenshot_to_inspect:
        block_phrase = safety_monitor.check_block_screenshot(screenshot_to_inspect)
        if block_phrase:
            return UnfollowResult(
                username=username,
                status="blocked",
                timestamp=_now_iso(),
                details={"block_phrase": block_phrase, "button_coords": button_coords},
            )

    if not confirmed:
        return UnfollowResult(
            username=username,
            status="confirm_not_found",
            timestamp=_now_iso(),
            details={"button_coords": button_coords},
        )

    _sleep_random_delay(config)
    return UnfollowResult(
        username=username,
        status="unfollowed",
        timestamp=_now_iso(),
        details={
            "button_coords": button_coords,
            "confirm_confidence": confidence,
        },
    )
