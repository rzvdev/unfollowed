"""Utilities for loading Unfollowed runtime configuration.

This module assumes the application runs on a 1920x1080 primary display and the
default configuration file lives in ``config/config.yaml`` relative to the
project root. Callers can pass an alternate path when they want to override the
defaults (e.g., for testing or per-user setups).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, MutableMapping, Optional

import yaml


def _resolve_paths(config_file: Path, raw_config: MutableMapping[str, Any]) -> MutableMapping[str, Path]:
    root = Path.cwd()
    logging_cfg = raw_config.get("logging", {})
    templates_dir = raw_config.get("vision", {}).get("templates_dir", "data/templates")

    logs_dir = (root / logging_cfg.get("directory", "logs")).resolve()
    templates_path = (root / templates_dir).resolve()

    return {
        "root": root,
        "config_file": config_file,
        "logs_dir": logs_dir,
        "templates_dir": templates_path,
    }


def _ensure_directories(paths: MutableMapping[str, Path], raw_config: MutableMapping[str, Any]) -> None:
    logging_cfg = raw_config.setdefault("logging", {})
    if logging_cfg.get("ensure_exists", True):
        paths["logs_dir"].mkdir(parents=True, exist_ok=True)

    vision_cfg = raw_config.setdefault("vision", {})
    if "templates_dir" not in vision_cfg:
        vision_cfg["templates_dir"] = str(paths["templates_dir"])


def load_config(path: Optional[str] = None) -> MutableMapping[str, Any]:
    """Load configuration data from disk.

    Parameters
    ----------
    path:
        Optional override relative or absolute path to a YAML config file.

    Returns
    -------
    MutableMapping[str, Any]
        Dict-like object with configuration values.
    """

    config_file = (Path(path).expanduser() if path else Path.cwd() / "config" / "config.yaml").resolve()
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_file}")

    with config_file.open("r", encoding="utf-8") as fh:
        raw_config: MutableMapping[str, Any] = yaml.safe_load(fh) or {}

    paths = _resolve_paths(config_file, raw_config)
    _ensure_directories(paths, raw_config)
    raw_config.setdefault("paths", {})
    raw_config["paths"].update(
        {
            "root": str(paths["root"]),
            "config_file": str(paths["config_file"]),
            "logs_dir": str(paths["logs_dir"]),
            "templates_dir": str(paths["templates_dir"]),
        }
    )

    return raw_config
