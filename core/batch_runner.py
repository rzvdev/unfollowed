"""Batch processing for unfollowing multiple accounts."""

from __future__ import annotations

import csv
import json
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Mapping, Optional

from core.safety import SafetyMonitor
from core.unfollow_worker import UnfollowResult, run_unfollow


def _read_csv(path: Path) -> List[str]:
    if not path.exists():
        raise FileNotFoundError(f"Input CSV not found: {path}")
    usernames: List[str] = []
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if "username" not in reader.fieldnames:
            raise ValueError("CSV must contain a 'username' column")
        for row in reader:
            username = (row.get("username") or "").strip()
            if username:
                usernames.append(username)
    return usernames


def _session_log_path(config: Mapping[str, object]) -> Path:
    logs_dir = Path(config.get("paths", {}).get("logs_dir", "logs"))
    date_str = datetime.now().strftime("%Y-%m-%d")
    return logs_dir / f"session-{date_str}.json"


def _load_existing_log(path: Path) -> List[Mapping[str, object]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except json.JSONDecodeError:
            return []
    if isinstance(data, list):
        return data
    return []


def _append_log(path: Path, result: UnfollowResult) -> None:
    history = _load_existing_log(path)
    history.append(result.to_dict())
    with path.open("w", encoding="utf-8") as fh:
        json.dump(history, fh, indent=2)


def _should_pause(index: int, config: Mapping[str, object]) -> Optional[float]:
    timing = config.get("timing", {})
    cooldown_every = int(timing.get("cooldown_every", 10))
    if cooldown_every <= 0:
        return None
    if (index + 1) % cooldown_every != 0:
        return None
    min_cooldown = float(timing.get("cooldown_min_seconds", 60.0))
    max_cooldown = float(timing.get("cooldown_max_seconds", 120.0))
    if max_cooldown < min_cooldown:
        max_cooldown = min_cooldown
    return random.uniform(min_cooldown, max_cooldown)


def _session_limit(config: Mapping[str, object]) -> int:
    limits = config.get("limits", {})
    return int(limits.get("actions_per_session", 30))


def run_batch(
    csv_path: Path,
    config: Mapping[str, object],
    *,
    dry_run: bool = False,
) -> Iterable[UnfollowResult]:
    usernames = _read_csv(csv_path)
    session_cap = _session_limit(config)
    log_path = _session_log_path(config)
    safety_monitor = SafetyMonitor(config, log_path)

    for index, username in enumerate(usernames):
        if index >= session_cap:
            break
        if not safety_monitor.has_daily_capacity():
            break

        result = run_unfollow(username, config, dry_run=dry_run, safety_monitor=safety_monitor)
        yield result
        safety_monitor.register_result(result.status)
        _append_log(log_path, result)

        pause_seconds = _should_pause(index, config)
        if pause_seconds:
            time.sleep(pause_seconds)

        if result.status == "blocked":
            break
