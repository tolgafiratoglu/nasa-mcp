"""Terminal demo entry point for NASA AI Mission Control agents.

Usage:
    python -m agents.cli "Are there any hazardous asteroids approaching Earth this week?"
"""

from __future__ import annotations

import argparse
import logging
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="NASA AI Mission Control — Strands multi-agent CLI",
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default="Give me a mission briefing for the next 7 days.",
        help="User question for the Mission Commander",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging on stderr",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        stream=sys.stderr,
        format="%(levelname)s %(name)s: %(message)s",
    )

    from agents.commander import mission_control

    try:
        with mission_control() as commander:
            result = commander(args.prompt)
    except Exception as exc:
        print(f"Mission Control error: {exc}", file=sys.stderr)
        return 1

    text = str(result)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
