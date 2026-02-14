from __future__ import annotations

import sys

from core.config_loader import ConfigError, load_all_configs


def main() -> int:
    try:
        load_all_configs("configs")
    except ConfigError as exc:
        print(f"CONFIG ERROR: {exc}", file=sys.stderr)
        return 2

    print("CONFIG OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
