#!/usr/bin/env python3
"""wheel 内にライセンス除外 5 オペの生ソースが残っていないかスキャンする。

使い方の例:
    python scripts/scan_wheel_ops.py wheels/win11-amd64-cpu/mmcv-*.whl
    python scripts/scan_wheel_ops.py mmcv/mmcv/ops/csrc --tree
終了コード: ヒット 0 なら 0、1 件以上なら 1（CI/自己チェック用）。
"""
import argparse
import re
import sys
import zipfile
from pathlib import Path

# 除外 5 オペ名（ファイル名に対する case-insensitive regex）
OP_RE = re.compile(
    r"upfirdn2d|bias_act|fused_bias_leakyrelu|filtered_lrelu|conv2d_gradfix", re.I
)


def scan_wheel(path: Path):
    with zipfile.ZipFile(path) as z:
        return [n for n in z.namelist() if OP_RE.search(n)]


def scan_tree(root: Path):
    hits = []
    for p in root.rglob("*"):
        if p.is_file() and OP_RE.search(p.name):
            hits.append(str(p.relative_to(root)))
    return hits


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("targets", nargs="+", help=".whl ファイル、または --tree でディレクトリ")
    ap.add_argument("--tree", action="store_true", help="wheel ではなくソースツリーを走査")
    ns = ap.parse_args()

    total = 0
    for t in ns.targets:
        p = Path(t)
        hits = scan_tree(p) if ns.tree else scan_wheel(p)
        total += len(hits)
        print(f"{'TREE' if ns.tree else 'WHEEL'} {p}: {len(hits)} hit(s)")
        for h in hits:
            print(f"  {h}")
    print("RESULT:", "CLEAN" if total == 0 else f"{total} RESIDUE(S) FOUND")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
