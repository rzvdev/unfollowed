"""Command-line entry point for the Unfollowed bot."""

from __future__ import annotations

import argparse
from pathlib import Path

from core import batch_runner, config_loader


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Instagram unfollow automation via screen control.")
    parser.add_argument("--input", required=True, help="Path to CSV with a 'username' column.")
    parser.add_argument("--config", help="Optional alternate config YAML path.")
    parser.add_argument("--dry-run", action="store_true", help="Locate targets without performing clicks.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = config_loader.load_config(args.config)
    csv_path = Path(args.input).expanduser().resolve()

    for result in batch_runner.run_batch(csv_path, config, dry_run=args.dry_run):
        print(f"[{result.timestamp}] {result.username}: {result.status}")


if __name__ == "__main__":
    main()
