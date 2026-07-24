#!/usr/bin/env python3
"""CLI production preflight. Не выводит значения переменных окружения."""

import os
import sys

from app.core.preflight import check_production_environment


def main() -> int:
    result = check_production_environment(os.environ)
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    for error in result.errors:
        print(f"ERROR: {error}")
    if not result.ok:
        print(f"Production preflight: FAILED ({len(result.errors)} ошибок)")
        return 1
    print("Production preflight: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
