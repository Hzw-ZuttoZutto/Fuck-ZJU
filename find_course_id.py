#!/usr/bin/env python3
"""Deprecated entrypoint.

Use: python -m src.main <subcommand> ...
"""

from __future__ import annotations

import sys


def main() -> int:
    print(
        "This script has been migrated. Please use: python -m src.main <subcommand> ...",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
