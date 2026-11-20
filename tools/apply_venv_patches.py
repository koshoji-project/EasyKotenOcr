# -*- coding: utf-8 -*-
"""Re-apply venv-local patches required for the EasyKotenOCR port.

uv sync / uv run may reinstall packages (wiping local edits), so this script
re-applies every venv-local patch idempotently. Run it before OCR inference
(start_ocr.bat does this automatically).

The target site-packages is derived from the RUNNING interpreter
(sys.executable), so this single script serves every flavor venv
(build/<flavor>/venv) on any machine.

Patches (best-effort: skipped when the installed package version already
contains the fix, e.g. the vendor-patched mmengine/mmpretrain wheels):
  1. torch.utils.cpp_extension.PLAT_TO_VCVARS: add 'win-arm64' -> 'arm64'
     (needed only when the torch wheel does not ship the mapping natively;
     no-op when already present).
  2. transformers dependency_versions_table: relax the tokenizers pin
     (only when the installed transformers hard-pins tokenizers<0.22, i.e.
     the 4.55.x series; 4.56+/4.57.x have no such pin -> skipped).
  3. mmpretrain models __init__: tolerate broken optional subpackages
     (multimodal/peft). Skipped when the vendor-patched wheel already
     handles the removed transformers symbols.
  4. mmengine checkpoint loading: torch>=2.6 defaults weights_only=True,
     which rejects mmengine checkpoint objects (HistoryBuffer, ...). The
     checkpoints used here are trusted (NDL / openmmlab), so allow loads.
  5. mmengine mmcv_full_available: pkgutil.find_loader was removed from the
     stdlib in Python 3.12. Skipped when the vendor-patched mmengine wheel
     (0.10.7+easykotenocr.1) already fixed it at the source level.
  6. site-packages/mmcv-root.pth: make the mmcv SOURCE package resolvable
     even when CWD == project root (the mmcv/ repo dir would otherwise
     shadow the installed package as a namespace package).
"""
import os
import sys
from pathlib import Path


def site_packages() -> Path:
    exe = Path(sys.executable).resolve()
    candidates = (
        exe.parent.parent / "Lib" / "site-packages",  # Windows venv
        exe.parent.parent / "lib"
        / f"python{sys.version_info.major}.{sys.version_info.minor}"
        / "site-packages",  # posix venv
    )
    for p in candidates:
        if p.is_dir():
            return p
    raise SystemExit(f"[FAIL] site-packages not found for {exe}")


def patch_file(path: Path, old: str, new: str, label: str, required: bool = False) -> None:
    if not path.is_file():
        print(f"[skip] {label}: {path.name} not found")
        if required:
            sys.exit(1)
        return
    text = path.read_text(encoding="utf-8")
    # Normalize to the file's dominant line ending for pattern matching.
    nl = "\r\n" if "\r\n" in text else "\n"
    old_n = old.replace("\n", nl)
    new_n = new.replace("\n", nl)
    if new_n in text:
        print(f"[ok]   {label}: already patched")
        return
    if old_n not in text:
        if required:
            print(f"[FAIL] {label}: pattern not found in {path}")
            sys.exit(1)
        print(f"[skip] {label}: pattern not found "
              "(version already different, e.g. vendor-patched wheel)")
        return
    path.write_text(text.replace(old_n, new_n), encoding="utf-8")
    print(f"[done] {label}: patched {path.name}")


def main() -> None:
    site = site_packages()

    # 1) torch cpp_extension: win-arm64 -> arm64 vcvars mapping
    patch_file(
        site / "torch" / "utils" / "cpp_extension.py",
        "    'win-amd64' : 'x86_amd64',\n}",
        "    'win-amd64' : 'x86_amd64',\n    'win-arm64' : 'arm64',\n}",
        "torch PLAT_TO_VCVARS win-arm64",
    )

    # 2) transformers: relax tokenizers runtime pin (4.55.x series only;
    #    tokenizers 0.21.x has no win_arm64 wheel, 0.22.2 does)
    patch_file(
        site / "transformers" / "dependency_versions_table.py",
        '"tokenizers": "tokenizers>=0.21,<0.22"',
        '"tokenizers": "tokenizers>=0.21"',
        "transformers tokenizers pin",
    )

    # 3) mmpretrain models __init__: tolerate broken optional subpackages
    patch_file(
        site / "mmpretrain" / "models" / "__init__.py",
        "from .multimodal import *  # noqa: F401,F403\n"
        "from .necks import *  # noqa: F401,F403\n"
        "from .peft import *  # noqa: F401,F403",
        "try:\n"
        "    from .multimodal import *  # noqa: F401,F403\n"
        "except ImportError:\n"
        "    # EasyKotenOCR port: multimodal (BLIP/OFA) needs transformers APIs\n"
        "    # removed in newer releases; not used by this project.\n"
        "    pass\n"
        "from .necks import *  # noqa: F401,F403\n"
        "try:\n"
        "    from .peft import *  # noqa: F401,F403\n"
        "except ImportError:\n"
        "    pass",
        "mmpretrain models optional imports",
    )

    # 4) mmengine checkpoint loading: weights_only=False at all sites
    ckpt = site / "mmengine" / "runner" / "checkpoint.py"
    for old_load, new_load in [
        ("torch.load(filename, map_location=map_location)",
         "torch.load(filename, map_location=map_location, weights_only=False)"),
        ("torch.load(downloaded_file, map_location=map_location)",
         "torch.load(downloaded_file, map_location=map_location, weights_only=False)"),
        ("torch.load(buffer, map_location=map_location)",
         "torch.load(buffer, map_location=map_location, weights_only=False)"),
    ]:
        if not ckpt.is_file():
            print("[skip] mmengine checkpoint weights_only: file not found")
            break
        text = ckpt.read_text(encoding="utf-8")
        nl = "\r\n" if "\r\n" in text else "\n"
        if new_load in text:
            print("[ok]   mmengine checkpoint weights_only: already patched")
            continue
        if old_load not in text:
            print(f"[warn] mmengine checkpoint: form not found: {old_load[:40]}...")
            continue
        ckpt.write_text(text.replace(old_load, new_load), encoding="utf-8")
        print(f"[done] mmengine checkpoint weights_only: patched ({old_load[:20]}...)")

    # 5) mmengine mmcv_full_available: pkgutil.find_loader (py>=3.12)
    patch_file(
        site / "mmengine" / "utils" / "dl_utils" / "misc.py",
        "    ext_loader = pkgutil.find_loader('mmcv._ext')\n"
        "    return ext_loader is not None",
        "    # pkgutil.find_loader was removed in Python 3.12; import directly.\n"
        "    try:\n"
        "        import mmcv._ext  # noqa: F401\n"
        "        return True\n"
        "    except (ImportError, AttributeError):\n"
        "        return False",
        "mmengine pkgutil.find_loader (py3.12+)",
    )

    # 6) mmcv root pth (plain path line, no backslash-escape pitfalls)
    pth = site / "mmcv-root.pth"
    repo_root = Path(__file__).resolve().parents[1] / "mmcv"
    expected = repo_root.as_posix().replace("/", os.sep)
    if pth.is_file() and expected in pth.read_text(encoding="utf-8"):
        print("[ok]   mmcv-root.pth: already present")
    else:
        pth.write_text(expected + "\n", encoding="utf-8")
        print(f"[done] mmcv-root.pth: wrote {expected}")

    print("venv patches applied.")


if __name__ == "__main__":
    main()
