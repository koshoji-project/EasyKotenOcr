#!/usr/bin/env python
"""wheels/ のチェックサムとファイル名タグを flavor 定義と突き合わせて検査する。

    python scripts/check_wheels.py            # 検査（N1X 側でも同じものを使う）
    python scripts/check_wheels.py --record   # wheels/SHA256SUMS.txt を（再）作成

やっていること:
  1. profiles/flavors.toml の mmcv_wheel が実在するか（ARM 系は N1X 由来の取り込み待ち）
  2. wheel ファイル名タグが flavor と一致するか（arm64 flavor に win_amd64 は入れない 等）
  3. wheels/SHA256SUMS.txt の SHA256 が実ファイルと一致するか
  4. profiles/<flavor>/ に pyproject.toml / uv.lock があるか

終了コード: 0 = 全 flavor 充足 / 1 = 不足・不一致
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WHEELS = ROOT / "wheels"
SUMS = WHEELS / "SHA256SUMS.txt"

WHEEL_RE = re.compile(
    r"^(?P<name>[A-Za-z0-9_.]+?)-(?P<ver>[^-]+)"
    r"(?:-(?P<py>[A-Za-z0-9_.]+)-(?P<abi>[A-Za-z0-9_.]+)-(?P<plat>[A-Za-z0-9_.]+))?\.whl$"
)


def load_flavors() -> dict:
    raw = (ROOT / "profiles" / "flavors.toml").read_bytes()
    return tomllib.loads(raw.decode("utf-8-sig"))["flavor"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_sums() -> dict[str, str]:
    if not SUMS.exists():
        return {}
    out = {}
    for line in SUMS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        digest, _, name = line.partition("  ")
        if digest and name:
            out[name.replace("\\", "/")] = digest
    return out


def rel(path: Path) -> str:
    return path.relative_to(WHEELS).as_posix()


def check_tags(flavor_id: str, wheel: Path) -> list[str]:
    """ファイル名タグが flavor の arch / python と合うか。"""
    problems: list[str] = []
    m = WHEEL_RE.match(wheel.name)
    if not m:
        return [f"wheel ファイル名を解釈できない: {wheel.name}"]
    plat = m.group("plat") or ""
    pytag = m.group("py") or ""
    if plat in ("any", ""):          # 純 Python wheel は arch 判定しない
        return problems
    want_arch = "win_arm64" if "arm64" in flavor_id else "win_amd64"
    if plat != want_arch:
        problems.append(f"platform tag が不一致: {plat}（この flavor の想定は {want_arch}）")
    return problems


def local_sources(flavor_id: str) -> list[str]:
    """profiles/<flavor>/pyproject.toml の [tool.uv.sources] で path 参照している wheel。"""
    p = ROOT / "profiles" / flavor_id / "pyproject.toml"
    if not p.exists():
        return []
    raw = p.read_bytes()
    data = tomllib.loads(raw.decode("utf-8-sig"))
    out = []
    for name, spec in data.get("tool", {}).get("uv", {}).get("sources", {}).items():
        if isinstance(spec, dict) and spec.get("path"):
            relp = (p.parent / spec["path"]).resolve()
            # wheel ファイルのみ検査対象。editable のディレクトリ参照
            # （例: cv2_shim/ の純 Python cv2 シム）は wheel 検査の対象外。
            if relp.suffix == ".whl":
                out.append(relp.relative_to(ROOT).as_posix())
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--record", action="store_true", help="wheels/SHA256SUMS.txt を作成・更新する")
    ns = ap.parse_args()

    flavors = load_flavors()

    found = sorted(WHEELS.rglob("*.whl"))
    if ns.record:
        lines = [f"{sha256(p)}  {rel(p)}" for p in found]
        SUMS.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"記録した本数: {len(lines)} -> {SUMS}")
        return 0

    sums = read_sums()
    print(f"wheel 実ファイル: {len(found)} 本 / SHA256SUMS.txt: {len(sums)} 件")
    if not sums:
        print("  SHA256SUMS.txt が無い。`python scripts/check_wheels.py --record` で作成すること。\n")

    problems = 0

    # 1) flavor ごとに想定 wheel（mmcv + pyproject の path 参照）の存在・タグ・ハッシュ
    flavor_dirs = {ROOT / "wheels" / fid for fid in flavors}
    for fid, f in sorted(flavors.items()):
        print(f"[{fid}]")
        expected: list[str] = []
        if f.get("mmcv_wheel"):
            expected.append(Path(f["mmcv_wheel"].replace("\\", "/")).as_posix())
        else:
            print("  mmcv_wheel が未定義")
            problems += 1
        for src in local_sources(fid):
            if src not in expected:
                expected.append(src)

        present: list[Path] = []
        for want in expected:
            path = ROOT / want
            if not path.exists():
                print(f"  不足: {want}（N1X 成果物の取り込み待ち / 未ビルド）")
                problems += 1
                continue
            present.append(path)
            digest = sha256(path)
            recorded = sums.get(rel(path))
            if recorded is None:
                hash_state = "SHA256 未記録"
                problems += 1
            elif recorded.lower() == digest.lower():
                hash_state = "SHA256 一致"
            else:
                hash_state = f"SHA256 不一致!! 記録={recorded[:16]}… 実={digest[:16]}…"
                problems += 1
            print(f"  {path.name}: {hash_state}")
            for msg in check_tags(fid, path):
                print("  タグ警告: " + msg)
                problems += 1

        fdir = ROOT / "wheels" / fid
        if fdir.is_dir():
            for p in sorted(fdir.glob("*.whl")):
                if p not in present:
                    print(f"  想定外の wheel（flavors.toml / pyproject に未登録）: {p.name}")
                    problems += 1

        for need in ("pyproject.toml", "uv.lock"):
            p = ROOT / "profiles" / fid / need
            mark = "有" if p.exists() else "無"
            print(f"  profiles/{fid}/{need}: {mark}")
            if not p.exists():
                problems += 1

    # 2) flavor ディレクトリ以外の wheel: 共通として参照されているか、遺物か
    referenced = {Path(p).name for fid in flavors for p in local_sources(fid)}
    others = [p for p in found if p.parent not in flavor_dirs]
    if others:
        print("\nflavor 専用の-dir に無い wheel（§7 で wheels\\common\\ または attic\\ へ移す）")
        for p in others:
            kind = "共通（pyproject から参照ずみ）" if p.name in referenced else "遺物（参照されていない）"
            print(f"  {p.relative_to(ROOT)}  [{kind}]")

    print(f"\n問題件数: {problems}")
    return 0 if problems == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
