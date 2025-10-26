from PIL import Image

from core import unfollow_worker
from vision import locator, screen_capture


def _dummy_config():
    return {
        "paths": {"templates_dir": "data/templates"},
        "vision": {"following_button_offset_x": 500},
        "timing": {"min_action_delay": 0.0, "max_action_delay": 0.0},
    }


def test_run_unfollow_dry_run_returns_coords(monkeypatch):
    dummy_image = Image.new("RGB", (1920, 1080))
    monkeypatch.setattr(screen_capture, "capture_fullscreen", lambda: dummy_image)
    monkeypatch.setattr(locator, "locate_following_button", lambda *args, **kwargs: (100, 200))

    result = unfollow_worker.run_unfollow("example", _dummy_config(), dry_run=True)

    assert result.status == "dry_run"
    assert result.details["button_coords"] == (100, 200)


def test_run_unfollow_block_detected_short_circuits(monkeypatch):
    dummy_image = Image.new("RGB", (1920, 1080))
    monkeypatch.setattr(screen_capture, "capture_fullscreen", lambda: dummy_image)

    called = {"locator": False}

    def fake_locator(*args, **kwargs):
        called["locator"] = True
        return (100, 200)

    monkeypatch.setattr(locator, "locate_following_button", fake_locator)

    class FakeSafety:
        def check_block_screenshot(self, screenshot):
            return "Action blocked"

    result = unfollow_worker.run_unfollow(
        "example",
        _dummy_config(),
        safety_monitor=FakeSafety(),
    )

    assert result.status == "blocked"
    assert result.details["block_phrase"] == "Action blocked"
    assert called["locator"] is False
