#!/usr/bin/env python
"""Rebuild the vendor-patched wheels for the Python 3.15 EasyKotenOCR stack.

Produces (into C:/easykotenocr/wheels/):
  - mmpretrain-1.2.0+easykotenocr.1-py2.py3-none-any.whl
  - mmengine-0.10.7+easykotenocr.1-py3-none-any.whl

Why patched (2026-11-18, Python 3.15.2 / transformers 4.57.6):
  1. mmpretrain 1.2.0 imports transformers symbols that were removed in
     transformers 4.57 (apply_chunking_to_forward, find_pruneable_heads_and_indices,
     prune_linear_layer moved to transformers.pytorch_utils; GenerationMixin moved
     to transformers.generation). Its bare try/except then set PreTrainedModel=None,
     crashing `class BertPreTrainedModel(PreTrainedModel)` with
     "TypeError: NoneType takes no arguments".
     No newer mmpretrain release exists (1.2.0 is latest as of 2026-11).
     No transformers downgrade is possible: versions <=4.55 require
     tokenizers<0.22, which has no cp315/abi3 wheel.
  2. mmengine 0.10.7 uses pkgutil.find_loader (removed from stdlib in
     Python 3.12) in mmcv_full_available(); 0.11.0rc3 still has the bug.
  3. Both setup.py files parse the version via exec()+locals(), which no longer
     works on Python >=3.13; both also need setuptools present for the build
     (mmengine build uses --no-build-isolation).

Usage:  python build_vendor_wheels.py
Requires: uv on PATH, an internet connection, and a venv with setuptools+wheel
          (defaults to C:/easykotenocr/.venv) for --no-build-isolation builds.
"""
import io
import json
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

PROJECT = Path(r"C:/easykotenocr")
WHEELS = PROJECT / "wheels"
SCRATCH = Path.home() / "AppData/Local/hermes/cache/scratch"
VENV_PY = PROJECT / ".venv/Scripts/python.exe"
UA = {"User-Agent": "easykotenocr-wheel-rebuild"}


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def pypi_sdist(pkg: str, version: str) -> bytes:
    meta = json.loads(fetch(f"https://pypi.org/pypi/{pkg}/{version}/json"))
    sdist = next(u for u in meta["urls"] if u["packagetype"] == "sdist")
    return fetch(sdist["url"])


def patch_file(path: Path, old: str, new: str) -> None:
    raw = path.read_text(encoding="utf-8")
    if old not in raw:
        # Already patched (idempotent rerun)
        if new in raw:
            print(f"  skip (already patched): {path.name}")
            return
        raise SystemExit(f"PATCH TARGET NOT FOUND in {path}:\n{old[:200]}")
    path.write_text(raw.replace(old, new, 1), encoding="utf-8", newline="")
    print(f"  patched: {path.name}")


def extract(data: bytes, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    tf = tarfile.open(fileobj=io.BytesIO(data), mode="r:gz")
    tf.extractall(dest)
    inner = next(p for p in dest.iterdir() if p.is_dir())
    # move contents up one level so setup.py is at dest root
    for child in inner.iterdir():
        shutil.move(str(child), dest / child.name)
    inner.rmdir()


def build_wheel(stage: Path) -> Path:
    out = subprocess.run(
        ["uv", "build", "--wheel", "--no-build-isolation", "--python", str(VENV_PY)],
        cwd=stage, capture_output=True, text=True,
    )
    if out.returncode != 0:
        print(out.stdout[-2000:])
        print(out.stderr[-2000:])
        raise SystemExit("wheel build failed")
    wheels = list((stage / "dist").glob("*.whl"))
    assert len(wheels) == 1, f"expected 1 wheel, got {wheels}"
    return wheels[0]


def build_mmpretrain() -> None:
    print("== mmpretrain 1.2.0 ==")
    stage = SCRATCH / "mmpretrain_stage"
    extract(pypi_sdist("mmpretrain", "1.2.0"), stage)
    base = stage / "mmpretrain/models/multimodal"

    patch_file(base / "blip/language_model.py",
"""try:
    from transformers.activations import ACT2FN
    from transformers.modeling_outputs import (
        BaseModelOutputWithPastAndCrossAttentions,
        BaseModelOutputWithPoolingAndCrossAttentions,
        CausalLMOutputWithCrossAttentions)
    from transformers.modeling_utils import (PreTrainedModel,
                                             apply_chunking_to_forward,
                                             find_pruneable_heads_and_indices,
                                             prune_linear_layer)
    from transformers.models.bert.configuration_bert import BertConfig
except:
    ACT2FN = None
    BaseModelOutputWithPastAndCrossAttentions = None
    BaseModelOutputWithPoolingAndCrossAttentions = None
    CausalLMOutputWithCrossAttentions = None
    PreTrainedModel = None
    apply_chunking_to_forward = None
    find_pruneable_heads_and_indices = None
    prune_linear_layer = None
    BertConfig = None
""",
"""from transformers.activations import ACT2FN
from transformers.modeling_outputs import (
    BaseModelOutputWithPastAndCrossAttentions,
    BaseModelOutputWithPoolingAndCrossAttentions,
    CausalLMOutputWithCrossAttentions)
from transformers.modeling_utils import PreTrainedModel
from transformers.models.bert.configuration_bert import BertConfig
try:
    # apply_chunking_to_forward / find_pruneable_heads_and_indices /
    # prune_linear_layer moved out of transformers.modeling_utils in
    # recent transformers releases (4.56+/4.57): import from pytorch_utils
    from transformers.pytorch_utils import (
        apply_chunking_to_forward,
        find_pruneable_heads_and_indices,
        prune_linear_layer)
except ImportError:
    apply_chunking_to_forward = None
    find_pruneable_heads_and_indices = None
    prune_linear_layer = None
""")
    patch_file(base / "blip2/Qformer.py",
               "from transformers.modeling_utils import apply_chunking_to_forward",
               "from transformers.pytorch_utils import apply_chunking_to_forward  # moved out of modeling_utils in transformers 4.57")
    patch_file(base / "ram/bert.py",
"from transformers.modeling_utils import (PreTrainedModel,\n                                         apply_chunking_to_forward,\n                                         find_pruneable_heads_and_indices,\n                                         prune_linear_layer)",
"from transformers.modeling_utils import PreTrainedModel\nfrom transformers.pytorch_utils import (  # moved out of modeling_utils in transformers 4.57\n    apply_chunking_to_forward,\n    find_pruneable_heads_and_indices,\n    prune_linear_layer)")
    patch_file(base / "ofa/ofa_modules.py",
"from transformers.modeling_utils import (GenerationConfig, GenerationMixin,\n                                         PretrainedConfig)",
"from transformers.generation import GenerationMixin  # moved out of modeling_utils in transformers 4.57\nfrom transformers.modeling_utils import (GenerationConfig,\n                                         PretrainedConfig)")
    patch_file(stage / "mmpretrain/version.py",
               "__version__ = '1.2.0'", "__version__ = '1.2.0+easykotenocr.1'")
    patch_file(stage / "setup.py",
"""def get_version():
    version_file = 'mmpretrain/version.py'
    with open(version_file, 'r', encoding='utf-8') as f:
        exec(compile(f.read(), version_file, 'exec'))
    return locals()['__version__']""",
"""def get_version():
    version_file = 'mmpretrain/version.py'
    with open(version_file, 'r', encoding='utf-8') as f:
        ns = {}
        exec(compile(f.read(), version_file, 'exec'), ns)
    return ns['__version__']""")
    whl = build_wheel(stage)
    shutil.copy2(whl, WHEELS / whl.name)
    print(f"  -> {WHEELS / whl.name}")


def build_mmengine() -> None:
    print("== mmengine 0.10.7 ==")
    stage = SCRATCH / "mmengine_stage"
    extract(pypi_sdist("mmengine", "0.10.7"), stage)

    patch_file(stage / "mmengine/utils/dl_utils/misc.py",
"import pkgutil\nfrom typing import Optional, Tuple, Union",
"import importlib.util\nfrom typing import Optional, Tuple, Union")
    patch_file(stage / "mmengine/utils/dl_utils/misc.py",
"    ext_loader = pkgutil.find_loader('mmcv._ext')\n    return ext_loader is not None",
"    # pkgutil.find_loader was removed from the stdlib in Python 3.12;\n    # importlib.util.find_spec is the supported replacement\n    ext_loader = importlib.util.find_spec('mmcv._ext')\n    return ext_loader is not None")
    patch_file(stage / "mmengine/version.py",
               "__version__ = '0.10.7'", "__version__ = '0.10.7+easykotenocr.1'")
    patch_file(stage / "setup.py",
"""def get_version():
    with open(version_file) as f:
        exec(compile(f.read(), version_file, 'exec'))
    return locals()['__version__']""",
"""def get_version():
    with open(version_file) as f:
        ns = {}
        exec(compile(f.read(), version_file, 'exec'), ns)
    return ns['__version__']""")
    whl = build_wheel(stage)
    shutil.copy2(whl, WHEELS / whl.name)
    print(f"  -> {WHEELS / whl.name}")


if __name__ == "__main__":
    WHEELS.mkdir(exist_ok=True)
    build_mmpretrain()
    build_mmengine()
    print("done.")
