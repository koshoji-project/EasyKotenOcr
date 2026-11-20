#!/usr/bin/env python
"""profiles/flavors.toml から flavor 定義を読み出すヘルパ（PowerShell からの利用前提）。

    python flavor_info.py --flavor win11-amd64-cu134              # 定義全体を JSON で
    python flavor_info.py --flavor win11-amd64-cu134 --key cuda_home
    python flavor_info.py --list

flavors.toml は今回の構成で「flavor 差分の単一ソース」なので、TOML パーサを持たない
PowerShell 側は必ずこのスクリプトを経由する（ParseError や直書きを防ぐため）。
"""
from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TOML = ROOT / "profiles" / "flavors.toml"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--flavor", help="flavor id（profiles/flavors.toml の [flavor.<id>]）")
    ap.add_argument("--key", help="指定キーの値だけを出力（無い場合は空文字）")
    ap.add_argument("--list", action="store_true", help="定義されている flavor id を1行ずつ")
    ap.add_argument("--flavors", default=str(DEFAULT_TOML), help="flavors.toml のパス")
    ns = ap.parse_args()

    # Windows のエディタが付ける UTF-8 BOM を許容する（tomllib は BOM 付きを弾く）
    raw = open(ns.flavors, "rb").read()
    data = tomllib.loads(raw.decode("utf-8-sig"))
    flavors = data.get("flavor", {})

    if ns.list:
        for name in flavors:
            print(name)
        return 0

    if not ns.flavor:
        print("--flavor または --list を指定してください", file=sys.stderr)
        return 2

    entry = flavors.get(ns.flavor)
    if entry is None:
        print(f"flavors.toml に flavor が無い: {ns.flavor}（定義: {', '.join(flavors)}）", file=sys.stderr)
        return 3

    if ns.key:
        print(entry.get(ns.key, ""))
    else:
        print(json.dumps(entry, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
