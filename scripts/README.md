# Vendor wheel provenance — EasyKotenOCR Python 3.15 migration (2026-11-18)

`wheels/` contains four local wheels that `pyproject.toml` / `uv.lock` reference
via `[tool.uv.sources]`. All are verified on Python 3.15.2 / PyTorch 2.14.1+cu130
/ CUDA 13.0 / MSVC 14.44 (VS Build Tools 2022) / RTX 5090 (sm_120).

| Wheel | Built from | Why local |
|---|---|---|
| `mmcv-2.1.0+easykotenocr.1-cp310-...whl` | MMCV 2.1.0 source (`../mmcv` checkout), feature-reduced | legacy cp310 build; kept for reference only |
| `mmcv-2.1.0+easykotenocr.2-cp315-cp315-win_amd64.whl` | same source, cp315 build | no PyPI mmcv for cp315+torch 2.14; reduced build (5 ops excluded for third-party license reasons, see below) |
| `mmpretrain-1.2.0+easykotenocr.1-py2.py3-none-any.whl` | PyPI sdist 1.2.0 | 1.2.0 (latest, as of 2026-11) breaks on transformers 4.57 (see `build_vendor_wheels.py`) |
| `mmengine-0.10.7+easykotenocr.1-py3-none-any.whl` | PyPI sdist 0.10.7 | uses `pkgutil.find_loader` (removed from stdlib in Python 3.12) |

## Rebuilding

- **mmpretrain + mmengine**: `python scripts/build_vendor_wheels.py`
  (downloads sdist from PyPI, re-applies the patches, builds with `uv build`,
  copies to `wheels/`. Idempotent.)
- **mmcv cp315**:
  1. Re-stage from the `../mmcv` checkout into a scratch dir and re-apply the
     excluded-op removals (see below).
  2. Copy `mmcv_setup_py315.py` over the staged `setup.py`. It adds the C++20
     requirement for PyTorch >= 2.14 (`/std:c++20` for cl, `-std=c++20` for nvcc
     on Windows) — required because torch 2.14 headers use
     `std::strong_ordering`.
  3. Run `build_mmcv_py315_wheel.bat` (adjust the `cd /d ...` staging path; it
     sets `DISTUTILS_USE_SDK=1` — mandatory for torch 2.14's ABI check — and
     `TORCH_CUDA_ARCH_LIST=7.5;8.0;8.6;9.0;10.0;12.0`).
  4. Verify: install into a clean venv, import `mmcv._ext`, run
     `mmcv.ops.box_iou_rotated` on CUDA.

### Excluded MMCV ops (third-party license concerns — do not restore without review)

`upfirdn2d`, `fused_bias_leakyrelu`, `bias_act`, `filtered_lrelu`,
`conv2d_gradfix` (StyleGAN2-style ops; kernel sources carry separate licenses).
Exclusion spans kernel/source files, pybind registrations, Python wrappers and
imports. The wheel is NOT a drop-in replacement for full mmcv-full.

## Verification performed (2026-11-18)

- `mmcv._ext` imports; `box_iou_rotated` runs on GPU.
- `import mmpretrain.models` + `ConvNeXt` (the chain that failed pre-patch).
- `mmengine.utils.dl_utils.misc.mmcv_full_available()` returns True (previously
  `AttributeError: module 'pkgutil' has no attribute 'find_loader'`).
- Full OCR pipeline: `main.py infer c:/ocr/in c:/ocr/out -a -s b` → 4/4 pages,
  EXIT=0, plausible classical-Japanese text + bounding-box JSON.

## Known caveats

- `mmcv.utils.ext_loader.check_ops_exist` still calls `pkgutil.find_loader`;
  it has **no callers** in mmdet/mmpretrain/the app, so it is dead code in this
  stack. If it is ever called, patch it to `importlib.util.find_spec`.
- `mmengine.utils.dl_utils.collect_env` still imports `distutils` inside the
  diagnostic function `collect_env()`; not on the runtime path.
- scikit-image 0.26.0's sdist cannot build on Python 3.15 (pythran dead end:
  0.19.0 fails MSVC 14.44 with C2559 in its own headers; <=0.18.1 crashes on
  the 3.15 AST via gast 0.6.0). We ship the prebuilt `scikit-image 0.27.0rc1`
  cp315 wheel from PyPI instead (pinned in pyproject).
- Third-party redistribution review of the reduced mmcv wheel and CUDA runtime
  DLLs is still open (see project-level notes).
