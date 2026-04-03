from __future__ import annotations

import sys


def main() -> int:
    from .__main__ import main as unified_main

    argv = sys.argv[:]
    sys.argv = [argv[0], "kb", *argv[1:]]
    try:
        return unified_main()
    finally:
        sys.argv = argv


if __name__ == "__main__":
    raise SystemExit(main())
