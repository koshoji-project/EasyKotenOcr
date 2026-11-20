# wheels/win11-amd64-cu134 — ビルド出所記録（PROVENANCE）

## mmcv-2.1.0+easykotenocr.3-cp315-cp315-win_amd64.whl

| 項目 | 値 |
|---|---|
| sha256 | `78C1B3A5E08A02D8CC2CCFFD0383F5BC740E63EEA9B1DAF34BAD597E903419F9` |
| size | 21.9 MB |
| ビルド日 | 2026-11-19 |
| ビルドマシン | Windows 11 / AMD64（RTX 5090, driver 621.14） |
| 元ソース | open-mmlab/mmcv **v2.1.0**（tag v2.1.0, commit `57c4e25e`）＝ `C:\easykotenocr\mmcv` の checkout |
| ステージング | `vendor/mmcv-patches/stage_mmcv.py --suffix easykotenocr.3`（5 オペ除外 + version local tag） |
| setup.py | `scripts/mmcv_setup_py315.py` で差し替え（C++20 / `/Zc:preprocessor` / `USE_CUDA=1`） |
| Python | CPython **3.15.2**（`C:\Users\gesho\AppData\Local\Programs\Python\Python3152`） |
| torch（ABI 依存） | **2.15.0+cu134**（`profiles/win11-amd64-cu134` の venv） |
| CUDA | nvcc **release 13.4, V13.4.92**（`CUDA/v13.4`） |
| MSVC | 14.44.35207（VS Build Tools 2022） |
| TORCH_CUDA_ARCH_LIST | `7.5;8.0;8.6;9.0;10.0;12.0` → gencode sm_75/80/86/90/100/120 |
| ninja | `-j 4`（USE_NINJA=1） |
| ビルドログ | `build/win11-amd64-cu134/logs/mmcv_build_20261119-194706.log` |
| コマンド | `scripts/build_wheels.ps1 -Flavor win11-amd64-cu134 -Suffix easykotenocr.3` |

除外オペ（ライセンス上の理由。レビューなしに復活させないこと）:
`upfirdn2d`, `fused_bias_leakyrelu`, `bias_act`, `filtered_lrelu`, `conv2d_gradfix`

## この flavor で必要になった 2 つの環境回避（2026-11-19 に確定）

1. **`TORCH_DONT_CHECK_COMPILER_ABI=1`**
   現行の VS Build Tools（14.4x）は `cl` の usage バナーを **UTF-8 の日本語**で出力する。
   torch 2.15 の `cpp_extension._check_abi()` は `subprocess.check_output(compiler)` の結果を
   Python 3.15 の `oem` コーデック（このマシンでは cp932）で復号するため、
   `UnicodeDecodeError: 'cp1' codec can't decode bytes` でビルドが死ぬ。
   `VSLANG=1033` では変わることはなかった。ABI チェックは警告を出すだけなので無効化した
   （torch 公式 wheel + VS2022 の組み合わせは ABI 互換）。
2. **`/Zc:preprocessor`（cl）と `-Xcompiler /Zc:preprocessor`（nvcc）**
   CUDA 13.x の CCCL ヘッダ `cuda/std/__cccl/preprocessor.h` が MSVC の新プリプロセッサを
   要求し、でないと `fatal error C1189` になる（`active_rotated_filter_cuda.cu` で発生）。
   `scripts/mmcv_setup_py315.py` 側に追加済み。

## 検証結果（2026-11-19, `scripts/verify_env.py --flavor win11-amd64-cu134` → exit 0）

- `torch 2.15.0+cu134`（cuda 13.4）/ `torchvision 0.29.2+cu134` / `cuda.is_available() = True`（RTX 5090, sm_120）
- `mmcv 2.1.0+easykotenocr.3` を site-packages から import、`mmcv._ext` 読み込み可
- `mmcv.ops.box_iou_rotated` を CUDA 上で実行 → IoU 0.3333（妥当な値）
- `mmdet 3.3.0` / `mmpretrain 1.2.0+easykotenocr.1` / `mmengine 0.10.7+easykotenocr.1` import 可
- OCR 全体: `main.py infer c:/ocr/in c:/ocr/out-cu134 -a -s b` → 4 ページ完走、exit 0、平均 1.15 秒/画像
  - **生成された `.txt` は torch 2.14.1+cu130 での旧実行（`c:/ocr/out/2026-11-18_080641`）とバイト一致**

## 注意点

- この wheel は torch **2.15.0+cu134** でビルドしている。torch が変われば（例: flavor 1 の `+cpu`、
  ARM 側の `+cu135`）必ず再ビルドすること。`+easykotenocr.2`（torch 2.14.1+cu130 Against）は
  本 flavor では使わない。
- `wheels/` 直下の `.1`（cp310）/ `.2`（cp315 win_amd64, torch 2.14.1+cu130）は参照用遺物。
