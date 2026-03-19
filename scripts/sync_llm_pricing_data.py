#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "data" / "llm_pricing.json"
TARGET = ROOT / "static" / "data" / "llm-pricing.json"


def main() -> None:
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Synced {SOURCE.relative_to(ROOT)} -> {TARGET.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
