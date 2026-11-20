#!/usr/bin/env python
"""flavor venv が flavors.toml の期待値どおりかを検査する。

    python scripts/verify_env.py --flavor win11-amd64-cu134

対象 venv の python で実行すること（その interpreter 自体を検査する）。
終了コード: 0 = 合格 / 1 = 不一致・import 失敗 / 2 = 使い方の誤り

start_ocr.bat に埋め込まれていた版アサート（mmcv 2.1.0+easykotenocr.2 / torch
2.14.1+cu130 等）の置き換え。期待値は flavors.toml から読むので、flavor ごとに
スクリプトを増やさない。
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_flavor(flavor: str) -> dict:
    raw = (ROOT / "profiles" / "flavors.toml").read_bytes()
    return tomllib.loads(raw.decode("utf-8-sig"))["flavor"][flavor]


def expected_versions(f: dict) -> dict[str, str]:
    """flavors.toml の pin 文字列（"torch==2.15.0+cu134" 形式）から版を取り出す。"""
    out = {}
    for key in ("torch", "torchvision"):
        m = re.search(r"==\s*([^;]+)", f.get(key, ""))
        if m:
            out[key] = m.group(1).strip()
    wheel = f.get("mmcv_wheel", "")
    if wheel:
        name = Path(wheel).name
        m = re.match(r"mmcv-([^-.]+(?:\+[^-]+)?)-", name)
        if m:
            out["mmcv"] = m.group(1)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--flavor", required=True)
    ap.add_argument("--skip-gpu-op", action="store_true", help="CUDA 上での box_iou_rotated 実行を省略")
    ns = ap.parse_args()

    try:
        flavor = load_flavor(ns.flavor)
    except KeyError:
        print(f"flavors.toml に flavor が無い: {ns.flavor}", file=sys.stderr)
        return 2
    exp = expected_versions(flavor)

    fails: list[str] = []
    print(f"flavor        : {ns.flavor}")
    print(f"python        : {sys.version.split()[0]}  ({sys.executable})")
    print(f"CUDA_HOME(env): {os.environ.get('CUDA_HOME', '')}")

    try:
        import torch
    except Exception as exc:  # noqa: BLE001
        print(f"torch import 失敗: {exc}", file=sys.stderr)
        return 1

    print(f"torch         : {torch.__version__} (cuda {torch.version.cuda})")
    if exp.get("torch") and torch.__version__ != exp["torch"]:
        fails.append(f"torch {torch.__version__} != 期待 {exp['torch']}")

    try:
        import torchvision
        print(f"torchvision   : {torchvision.__version__}")
        if exp.get("torchvision") and torchvision.__version__ != exp["torchvision"]:
            fails.append(f"torchvision {torchvision.__version__} != 期待 {exp['torchvision']}")
    except Exception as exc:  # noqa: BLE001
        fails.append(f"torchvision import 失敗: {exc}")

    want_cuda = flavor.get("device", "").startswith("cuda")
    print(f"cuda available: {torch.cuda.is_available()}"
          + (f" / {torch.cuda.get_device_name(0)}" if torch.cuda.is_available() else ""))
    if want_cuda and not torch.cuda.is_available():
        fails.append("device=cuda:0 の flavor なのに torch.cuda.is_available() が False")

    try:
        import mmcv
        import mmcv._ext  # noqa: F401
        path = Path(mmcv.__file__).resolve()
        print(f"mmcv          : {mmcv.__version__}  {path}")
        if exp.get("mmcv") and mmcv.__version__ != exp["mmcv"]:
            fails.append(f"mmcv {mmcv.__version__} != 期待 {exp['mmcv']}（flavors.toml の mmcv_wheel）")
        if "site-packages" not in str(path).lower():
            fails.append(f"mmcv が site-packages 以外から import されている: {path}")
        if want_cuda and not ns.skip_gpu_op:
            from mmcv.ops import box_iou_rotated
            a = torch.tensor([[0.0, 0.0, 2.0, 2.0, 0.0]], device="cuda")
            b = torch.tensor([[1.0, 0.0, 2.0, 2.0, 0.0]], device="cuda")
            iou = box_iou_rotated(a, b)
            print(f"box_iou_rotated(cuda): {float(iou[0][0]):.4f}")
    except Exception as exc:  # noqa: BLE001
        fails.append(f"mmcv import / GPU op 失敗: {type(exc).__name__}: {exc}")

    try:
        import mmdet, mmpretrain, mmengine  # noqa: F401
        print(f"mmdet         : {mmdet.__version__}")
        print(f"mmpretrain    : {mmpretrain.__version__}")
        print(f"mmengine      : {mmengine.__version__}")
    except Exception as exc:  # noqa: BLE001
        fails.append(f"mmdet/mmpretrain/mmengine import 失敗: {type(exc).__name__}: {exc}")

    if fails:
        print("\nFAILED:", file=sys.stderr)
        for msg in fails:
            print("  - " + msg, file=sys.stderr)
        return 1
    print("\nVERIFY OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
