#!/usr/bin/env python
"""EasyKotenOCR 用の mmcv 2.1.0 ソースをステージングする。

素の open-mmlab mmcv v2.1.0 checkout をコピーし、EasyKotenOCR で使うために必要な
変形だけを適用した「ビルド用ツリー」を作る。ビルドそのものは
``scripts/build_wheels.ps1`` が行う（vcvars / CUDA / TORCH_CUDA_ARCH_LIST は
``profiles/flavors.toml`` から来る）。

適用内容（scripts/README.md の記述と同一。元は scratch にしか無いスクリプトだった）:

1. ライセンス上の理由で除外する 5 オペを削除する
   ``upfirdn2d``, ``fused_bias_leakyrelu``, ``bias_act``, ``filtered_lrelu``,
   ``conv2d_gradfix``（StyleGAN2 系。カーネルソースが別ライセンス）
   - Python ラッパ（mmcv/ops/*.py）
   - C++ ソース（mmcv/ops/csrc/pytorch/*.cpp）
   - kernel 生ソースの実体（``EXCLUDED_CSRC_EXTRA``: pytorch/cuda/*.cu、
     pytorch/npu/*、parrots/*。package data として wheel に同梱されていた残骸）
   - ``mmcv/ops/__init__.py`` の import と ``__all__`` の該当項目
   - ``mmcv/ops/csrc/pytorch/pybind.cpp`` の宣言と ``m.def`` 登録
   - ``pytorch/cuda/cudabind.cpp`` と ``parrots/cudabind.cpp`` の
     ``*_op`` / ``*_op_impl`` 宣言 + ``REGISTER_DEVICE_IMPL`` ブロック
     （CUDA ビルドは cuda/*.cpp を glob で拾うため、除去しないと
     ``*_op_impl`` の未定義参照でリンクに落ちる）
   - 最終自己チェック: ``mmcv/ops/csrc`` 配下に 5 オペ名を含むファイル名が
     残っていたら fail
2. ``mmcv/version.py`` に local version suffix を付け、suffix を許容するよう
   ``version_info`` を直す（PEP 440 の ``2.1.0+easykotenocr.3`` 対応）

注意: この wheel は完全な mmcv-full の代わりにはならない（``scripts/README.md`` 参照）。

使い方:
    python stage_mmcv.py --src <mmcv checkout> --dst <staging dir> [--suffix easykotenocr.3]
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

# 除外するオペ（ライセンス確認済みのものだけ復活させること）
EXCLUDED_PY_WRAPPERS = [
    "bias_act.py",
    "conv2d_gradfix.py",
    "filtered_lrelu.py",
    "fused_bias_leakyrelu.py",
    "upfirdn2d.py",
]
EXCLUDED_CSRC_CPP = [
    "bias_act.cpp",
    "filtered_lrelu.cpp",
    "fused_bias_leakyrelu.cpp",
    "upfirdn2d.cpp",
]
# wheel の package data として同梱されていた kernel 生ソースの実体
# （mmcv/ops/csrc/ からの相対パス。除外根拠は mmcv LICENSE の NVIDIA 由来ファイル表記）
EXCLUDED_CSRC_EXTRA = [
    "pytorch/cuda/bias_act_cuda.cu",
    "pytorch/cuda/filtered_lrelu.cu",
    "pytorch/cuda/fused_bias_leakyrelu_cuda.cu",
    "pytorch/cuda/upfirdn2d_kernel.cu",
    "pytorch/npu/fused_bias_leakyrelu_npu.cpp",
    "parrots/fused_bias_leakyrelu.cpp",
    "parrots/fused_bias_parrots.cpp",
    "parrots/upfirdn2d.cpp",
    "parrots/upfirdn2d_parrots.cpp",
]
# 残骸ファイル名の自己チェック用（scripts/scan_wheel_ops.py と同一パターン）
RESIDUE_NAME_RE = re.compile(
    r"upfirdn2d|bias_act|fused_bias_leakyrelu|filtered_lrelu|conv2d_gradfix", re.I
)
OPS_INIT_IMPORTS = [
    "from .bias_act import bias_act\n",
    "from .conv2d_gradfix import conv2d, conv_transpose2d\n",
    "from .filtered_lrelu import filtered_lrelu\n",
    "from .fused_bias_leakyrelu import FusedBiasLeakyReLU, fused_bias_leakyrelu\n",
    "from .upfirdn2d import filter2d, upfirdn2d, upsample2d\n",
]
COPY_EXCLUDE = {".git", "__pycache__", "build", ".eggs"}

PYBIND_DECL_BLOCKS = [
    (
        "Tensor upfirdn2d(torch::Tensor input, torch::Tensor filter, int upx, int upy,\n"
        "                 int downx, int downy, int padx0, int padx1, int pady0,\n"
        "                 int pady1, bool flip, float gain);\n"
        "\n"
        "Tensor fused_bias_leakyrelu(const Tensor &input, const Tensor &bias,\n"
        "                            const Tensor &refer, int act, int grad, float alpha,\n"
        "                            float scale);\n"
        "\n"
    ),
    (
        "Tensor bias_act(const Tensor &input, const Tensor &bias, const Tensor &xref,\n"
        "                const Tensor &yref, const Tensor &dy, int grad, int dim,\n"
        "                int act, float alpha, float gain, float clamp);\n"
        "\n"
        "std::tuple<torch::Tensor, torch::Tensor, int> filtered_lrelu(\n"
        "    torch::Tensor x, torch::Tensor fu, torch::Tensor fd, torch::Tensor b,\n"
        "    torch::Tensor si, int up, int down, int px0, int px1, int py0, int py1,\n"
        "    int sx, int sy, float gain, float slope, float clamp, bool flip_filters,\n"
        "    bool writeSigns);\n"
        "\n"
        "torch::Tensor filtered_lrelu_act_(torch::Tensor x, torch::Tensor si, int sx,\n"
        "                                  int sy, float gain, float slope, float clamp,\n"
        "                                  bool writeSigns);\n"
        "\n"
    ),
]
PYBIND_DEF_BLOCKS = [
    (
        '  m.def("upfirdn2d", &upfirdn2d, "upfirdn2d (CUDA)", py::arg("input"),\n'
        '        py::arg("filter"), py::arg("upx"), py::arg("upy"), py::arg("downx"),\n'
        '        py::arg("downy"), py::arg("padx0"), py::arg("padx1"), py::arg("pady0"),\n'
        '        py::arg("pady1"), py::arg("flip"), py::arg("gain"));\n'
        '  m.def("fused_bias_leakyrelu", &fused_bias_leakyrelu,\n'
        '        "fused_bias_leakyrelu (CUDA)", py::arg("input"), py::arg("bias"),\n'
        '        py::arg("empty"), py::arg("act"), py::arg("grad"), py::arg("alpha"),\n'
        '        py::arg("scale"));\n'
    ),
    (
        '  m.def("bias_act", &bias_act, "bias_act (CUDA)", py::arg("input"),\n'
        '        py::arg("bias"), py::arg("xref"), py::arg("yref"), py::arg("dy"),\n'
        '        py::arg("grad"), py::arg("dim"), py::arg("act"), py::arg("alpha"),\n'
        '        py::arg("gain"), py::arg("clamp"));\n'
        '  m.def("filtered_lrelu", &filtered_lrelu, "filtered_lrelu (CUDA)",\n'
        '        py::arg("x"), py::arg("fu"), py::arg("fd"), py::arg("b"), py::arg("si"),\n'
        '        py::arg("up"), py::arg("down"), py::arg("px0"), py::arg("px1"),\n'
        '        py::arg("py0"), py::arg("py1"), py::arg("sx"), py::arg("sy"),\n'
        '        py::arg("gain"), py::arg("slope"), py::arg("clamp"),\n'
        '        py::arg("flip_filters"), py::arg("writeSigns"));\n'
        '  m.def("filtered_lrelu_act_", &filtered_lrelu_act_,\n'
        '        "filtered_lrelu_act_ (CUDA)", py::arg("x"), py::arg("si"),\n'
        '        py::arg("sx"), py::arg("sy"), py::arg("gain"), py::arg("slope"),\n'
        '        py::arg("clamp"), py::arg("writeSigns"));\n'
    ),
]

# mmcv/ops/csrc/pytorch/cuda/cudabind.cpp から除去するブロック
# （関数宣言・_op_impl 宣言・REGISTER_DEVICE_IMPL の 3 点セット。
#  CUDA ビルドは scripts/mmcv_setup_py315.py が glob('.../pytorch/cuda/*.cpp')
#  でこれを含むため、削除した .cu の *_op_impl を参照したままにすると
#  未定義シンボルでリンクに落ちる。末尾の空行ごと消す）
CUDA_CUDABIND_BLOCKS = [
    (
        "torch::Tensor fused_bias_leakyrelu_op(const torch::Tensor &input,\n"
        "                                      const torch::Tensor &bias,\n"
        "                                      const torch::Tensor &refer, int act,\n"
        "                                      int grad, float alpha, float scale);\n"
        "\n"
        "torch::Tensor fused_bias_leakyrelu_op_impl(const torch::Tensor &input,\n"
        "                                           const torch::Tensor &bias,\n"
        "                                           const torch::Tensor &refer, int act,\n"
        "                                           int grad, float alpha, float scale);\n"
        "REGISTER_DEVICE_IMPL(fused_bias_leakyrelu_op_impl, CUDA,\n"
        "                     fused_bias_leakyrelu_op);\n"
        "\n"
    ),
    (
        "torch::Tensor bias_act_op_impl(const torch::Tensor &input,\n"
        "                               const torch::Tensor &bias,\n"
        "                               const torch::Tensor &xref,\n"
        "                               const torch::Tensor &yref,\n"
        "                               const torch::Tensor &dy, int grad, int dim,\n"
        "                               int act, float alpha, float gain, float clamp);\n"
        "\n"
        "torch::Tensor bias_act_op(const torch::Tensor &input, const torch::Tensor &bias,\n"
        "                          const torch::Tensor &xref, const torch::Tensor &yref,\n"
        "                          const torch::Tensor &dy, int grad, int dim, int act,\n"
        "                          float alpha, float gain, float clamp);\n"
        "\n"
        "REGISTER_DEVICE_IMPL(bias_act_op_impl, CUDA, bias_act_op);\n"
        "\n"
    ),
    (
        "torch::Tensor filtered_lrelu_act_op_impl(torch::Tensor x, torch::Tensor si,\n"
        "                                         int sx, int sy, float gain,\n"
        "                                         float slope, float clamp,\n"
        "                                         bool writeSigns);\n"
        "\n"
        "torch::Tensor filtered_lrelu_act_op(torch::Tensor x, torch::Tensor si, int sx,\n"
        "                                    int sy, float gain, float slope,\n"
        "                                    float clamp, bool writeSigns);\n"
        "\n"
        "REGISTER_DEVICE_IMPL(filtered_lrelu_act_op_impl, CUDA, filtered_lrelu_act_op);\n"
        "\n"
    ),
    (
        "torch::Tensor upfirdn2d_op(torch::Tensor input, torch::Tensor filter, int upx,\n"
        "                           int upy, int downx, int downy, int padx0, int padx1,\n"
        "                           int pady0, int pady1, bool flip, float gain);\n"
        "\n"
        "torch::Tensor upfirdn2d_op_impl(torch::Tensor input, torch::Tensor filter,\n"
        "                                int upx, int upy, int downx, int downy,\n"
        "                                int padx0, int padx1, int pady0, int pady1,\n"
        "                                bool flip, float gain);\n"
        "REGISTER_DEVICE_IMPL(upfirdn2d_op_impl, CUDA, upfirdn2d_op);\n"
        "\n"
    ),
]

# mmcv/ops/csrc/parrots/cudabind.cpp から除去する同名ブロック
# （parrots 分岐は Windows ビルドでは使われないが、参照残りを消す hygiene 目的）
PARROTS_CUDABIND_BLOCKS = [
    (
        "torch::Tensor fused_bias_leakyrelu_op(const torch::Tensor& input,\n"
        "                                      const torch::Tensor& bias,\n"
        "                                      const torch::Tensor& refer, int act,\n"
        "                                      int grad, float alpha, float scale);\n"
        "\n"
        "torch::Tensor fused_bias_leakyrelu_op_impl(const torch::Tensor& input,\n"
        "                                           const torch::Tensor& bias,\n"
        "                                           const torch::Tensor& refer, int act,\n"
        "                                           int grad, float alpha, float scale);\n"
        "REGISTER_DEVICE_IMPL(fused_bias_leakyrelu_op_impl, CUDA,\n"
        "                     fused_bias_leakyrelu_op);\n"
        "\n"
    ),
    (
        "torch::Tensor upfirdn2d_op(const torch::Tensor& input,\n"
        "                           const torch::Tensor& kernel, int up_x, int up_y,\n"
        "                           int down_x, int down_y, int pad_x0, int pad_x1,\n"
        "                           int pad_y0, int pad_y1);\n"
        "\n"
        "torch::Tensor upfirdn2d_op_impl(const torch::Tensor& input,\n"
        "                                const torch::Tensor& kernel, int up_x, int up_y,\n"
        "                                int down_x, int down_y, int pad_x0, int pad_x1,\n"
        "                                int pad_y0, int pad_y1);\n"
        "REGISTER_DEVICE_IMPL(upfirdn2d_op_impl, CUDA, upfirdn2d_op);\n"
        "\n"
    ),
]


def fail(msg: str) -> None:
    raise SystemExit(f"STAGING FAILED: {msg}")


def copy_tree(src: Path, dst: Path) -> None:
    for p in src.iterdir():
        if p.name in COPY_EXCLUDE or p.suffix == ".pyd":
            continue
        if p.name.endswith(".egg-info"):
            continue
        q = dst / p.name
        if p.is_dir():
            q.mkdir(parents=True, exist_ok=True)
            copy_tree(p, q)
        else:
            shutil.copy2(p, q)


def drop_excluded_ops(dst: Path) -> None:
    for name in EXCLUDED_PY_WRAPPERS:
        t = dst / "mmcv" / "ops" / name
        if not t.exists():
            fail(f"除外対象の Python ラッパが見つからない: {t}")
        t.unlink()
    for name in EXCLUDED_CSRC_CPP:
        t = dst / "mmcv" / "ops" / "csrc" / "pytorch" / name
        if not t.exists():
            fail(f"除外対象の C++ ソースが見つからない: {t}")
        t.unlink()
    for relp in EXCLUDED_CSRC_EXTRA:
        t = dst / "mmcv" / "ops" / "csrc" / Path(relp)
        if not t.exists():
            fail(f"除外対象の kernel 生ソースが見つからない: {t}")
        t.unlink()
    print(
        f"  removed {len(EXCLUDED_PY_WRAPPERS)} python wrappers, "
        f"{len(EXCLUDED_CSRC_CPP)} csrc sources, "
        f"{len(EXCLUDED_CSRC_EXTRA)} kernel sources"
    )


def patch_ops_init(dst: Path) -> None:
    p = dst / "mmcv" / "ops" / "__init__.py"
    s = p.read_text(encoding="utf-8")
    for line in OPS_INIT_IMPORTS:
        if line not in s:
            fail(f"ops/__init__.py に import 行が見つからない: {line!r}")
        s = s.replace(line, "")
    s = s.replace(
        "    'knn', 'ball_query', 'upfirdn2d', 'FusedBiasLeakyReLU',\n"
        "    'fused_bias_leakyrelu', 'rotated_feature_align', 'RiRoIAlignRotated',\n",
        "    'knn', 'ball_query', 'rotated_feature_align', 'RiRoIAlignRotated',\n",
    )
    s = s.replace(
        "    'PrRoIPool', 'prroi_pool', 'bias_act', 'filtered_lrelu', 'conv2d',\n",
        "    'PrRoIPool', 'prroi_pool',\n",
    )
    s = s.replace(" 'conv_transpose2d',", "")
    if "'upfirdn2d'" in s or "'FusedBiasLeakyReLU'" in s or "'fused_bias_leakyrelu'" in s:
        fail("ops/__init__.py の __all__ から除外オペが残りている")
    p.write_text(s, encoding="utf-8")
    print("  patched mmcv/ops/__init__.py")


def patch_pybind(dst: Path) -> None:
    p = dst / "mmcv" / "ops" / "csrc" / "pytorch" / "pybind.cpp"
    s = p.read_text(encoding="utf-8")
    for block in PYBIND_DECL_BLOCKS + PYBIND_DEF_BLOCKS:
        if block not in s:
            fail(f"pybind.cpp にExpected ブロックが見つからない:\n{block[:120]}...")
        s = s.replace(block, "")
    p.write_text(s, encoding="utf-8")
    print("  patched mmcv/ops/csrc/pytorch/pybind.cpp")


def _patch_cudabind_file(p: Path, blocks: list[str]) -> None:
    s = p.read_text(encoding="utf-8")
    for block in blocks:
        if block not in s:
            fail(f"{p.name} に Expected ブロックが見つからない:\n{block[:120]}...")
        s = s.replace(block, "")
    if RESIDUE_NAME_RE.search(s):
        fail(f"{p.name} に除外オペの参照が残っている")
    p.write_text(s, encoding="utf-8")
    print(f"  patched {p.relative_to(p.parents[4]).as_posix()}"
          f" ({len(blocks)} blocks removed)")


def patch_cuda_cudabind(dst: Path) -> None:
    # CUDA ビルドは mmcv_setup_py315.py が pytorch/cuda/*.cpp を glob で拾うため、
    # cudabind.cpp の 5 オペブロック（宣言 + REGISTER_DEVICE_IMPL）を除去しないと
    # 削除した *_op_impl の未定義参照でリンクに落ちる。
    _patch_cudabind_file(
        dst / "mmcv" / "ops" / "csrc" / "pytorch" / "cuda" / "cudabind.cpp",
        CUDA_CUDABIND_BLOCKS,
    )
    # parrots 分岐は Windows ビルドでは使われないが、参照残りを消す（hygiene）
    _patch_cudabind_file(
        dst / "mmcv" / "ops" / "csrc" / "parrots" / "cudabind.cpp",
        PARROTS_CUDABIND_BLOCKS,
    )


def check_no_residue(dst: Path) -> None:
    """ステージングツリーに 5 オペ名を含むファイル名が残っていたら fail。"""
    csrc = dst / "mmcv" / "ops" / "csrc"
    residue = sorted(
        str(p.relative_to(csrc).as_posix())
        for p in csrc.rglob("*")
        if p.is_file() and RESIDUE_NAME_RE.search(p.name)
    )
    if residue:
        fail("mmcv/ops/csrc に残骸ファイルが残っている:\n    " + "\n    ".join(residue))
    print("  residue check OK: mmcv/ops/csrc に 5 オペ名ファイル 0 件")


def set_version(dst: Path, base: str, suffix: str) -> None:
    p = dst / "mmcv" / "version.py"
    s = p.read_text(encoding="utf-8")
    full = f"{base}+{suffix}"
    s = s.replace(f"__version__ = '{base}'", f"__version__ = '{full}'")
    old_vi = "version_info = tuple(int(x) for x in __version__.split('.')[:3])"
    new_vi = (
        "# strip PEP 440 local version suffix (e.g. 2.1.0+easykotenocr.3 -> 2.1.0)\n"
        "version_info = tuple(int(x) for x in __version__.split('+')[0].split('.')[:3])"
    )
    if full not in s:
        fail(f"version.py に __version__ = '{base}' が見つからない（version.py を確認）")
    if old_vi not in s:
        fail("version.py の version_info 行が想定と異なる")
    s = s.replace(old_vi, new_vi)
    p.write_text(s, encoding="utf-8")
    print(f"  version -> {full}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--src", required=True, help="素の mmcv checkout（v2.1.0）")
    ap.add_argument("--dst", required=True, help="ステージング先（毎回作り直す）")
    ap.add_argument("--base-version", default="2.1.0")
    ap.add_argument("--suffix", default="easykotenocr.3", help="PEP 440 local version suffix")
    ns = ap.parse_args()

    src, dst = Path(ns.src).resolve(), Path(ns.dst).resolve()
    if not (src / "setup.py").exists():
        fail(f"src が mmcv checkout ではない: {src}")
    if not (src / "mmcv" / "ops" / "csrc" / "pytorch" / "pybind.cpp").exists():
        fail(f"src に mmcv/ops/csrc が見つからない: {src}")
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)

    copy_tree(src, dst)
    print(f"copied {src} -> {dst}")
    drop_excluded_ops(dst)
    patch_ops_init(dst)
    patch_pybind(dst)
    patch_cuda_cudabind(dst)
    set_version(dst, ns.base_version, ns.suffix)
    check_no_residue(dst)
    print("STAGING OK ->", dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
