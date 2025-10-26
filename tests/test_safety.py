import json

from PIL import Image

from core import safety


def test_detect_block_phrase_monkeypatched(monkeypatch):
    monkeypatch.setattr(safety.pytesseract, "image_to_string", lambda *args, **kwargs: "Try again later")
    image = Image.new("RGB", (10, 10), color="white")

    phrase = safety.detect_block_phrase(image, ["Action blocked", "Try again later"])

    assert phrase == "Try again later"


def test_safety_monitor_counts_existing_logs(tmp_path):
    log_path = tmp_path / "session-2025-10-26.json"
    entries = [
        {"status": "unfollowed"},
        {"status": "not_found"},
        {"status": "unfollowed"},
    ]
    log_path.write_text(json.dumps(entries), encoding="utf-8")

    config = {
        "limits": {"daily_cap": 3},
        "safety": {"block_phrases": ["Action blocked"]},
    }

    monitor = safety.SafetyMonitor(config, log_path)

    assert monitor.actions_today == 2
    assert monitor.has_daily_capacity() is True
    assert monitor.remaining_daily_quota() == 1

    monitor.register_result("unfollowed")

    assert monitor.has_daily_capacity() is False
    assert monitor.remaining_daily_quota() == 0
