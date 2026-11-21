# wheels/win11-amd64-cpu — ビルド出所記録（PROVENANCE）

## mmcv-2.1.0+easykotenocr.3-cp315-cp315-win_amd64.whl（CPU 版）

| 項目 | 値 |
|---|---|
| sha256 | `36C52A50305CD7A32253BBA0766E3574625F8FB2600D220CF73828CA6ED3EED8` |
| size | 1.0 MB（`mmcv/_ext.cp315-win_amd64.pyd` は 0.99 MB / エントリ 510 件） |
| ビルド日 | 2026-11-21（package data 残骸除去リビルド。旧 2026-11-19 版は sha `E4159D32…` で差し替え） |
| 元ソース | open-mmlab/mmcv **v2.1.0**（tag v2.1.0, commit `57c4e25e`）＝ `C:\easykotenocr\mmcv` |
| ステージング | `vendor/mmcv-patches/stage_mmcv.py --suffix easykotenocr.3`（5 オペ除外 + **残骸生ソース削除 `EXCLUDED_CSRC_EXTRA` 9 件 + cudabind ブロック除去 + 残骸自己チェック** + version local tag） |
| setup.py | `scripts/mmcv_setup_py315.py`（C++20 / `/Zc:preprocessor` / `USE_CUDA=1`） |
| Python | CPython 3.15.2 |
| torch（ABI 依存） | **2.15.0+cpu**（`profiles/win11-amd64-cpu` の venv） |
| CUDA | 不使用（ビルドログ: `Compiling mmcv._ext only with CPU`） |
| MSVC | 14.44.35207（VS Build Tools 2022） |
| ninja | `-j 12`（USE_NINJA=1、MAX_JOBS=12）。オブジェクト 73 個 |
| ビルドログ | `build/win11-amd64-cpu/logs/mmcv_build_20261121-163207.log` |
| コマンド | `scripts/build_wheels.ps1 -Flavor win11-amd64-cpu -MaxJobs 12` |

CUDA 版（`wheels/win11-amd64-cu134/`）と同じ local tag `.3` だが、**torch のビルド違いで ABI が違うため混用不可**。
CPU 版には cuDNN/CUDA ランタイムの依存が無いので wheel が小さい（cu134 版は fatbin 込みで 9.5MB）。

## 再ビルド検証（2026-11-21、残骸除去リビルド後）

- `scripts/scan_wheel_ops.py <wheel>` → **0 hit(s) / RESULT: CLEAN**（wheel 内 package data に 5 オペ名 0 件）
- venv 入れ直し（`uv pip install --reinstall`）+ `tools/apply_venv_patches.py` →
  `scripts/verify_env.py --flavor win11-amd64-cpu` → **VERIFY OK**（mmcv は site-packages から import）
- OCR 実走: `main.py infer c:/ocr/in c:/ocr/out-cpu-rebuild -a -s b -c config/config.cpu.yml`
  → 4 ページ完走・exit 0・平均 11.96 秒/画像、`.txt` は 2026-11-19 出力（`out-cpu/2026-11-19_202502`）と**バイト一致**
- CPU ビルドは元々除外 4 .cu をコンパイルしていなかった（73 objects 不変）ため、pyd は実質同一。
  変わったのは wheel 同梱の残骸ソース削除と RECORD のみ

## 環境回避（CPU でも同じ）

- `TORCH_DONT_CHECK_COMPILER_ABI=1` は CPU ビルドでも必要（ABI チェックは cl の version 出力を
  読むだけで、CUDA とは無関係。VS Build Tools 14.4x の UTF-8 日本語バナー問題を参照）。
- `/Zc:preprocessor` は CPU ビルドでは実質無害（CCCL ヘッダを通らない）。flavor で共通の
  setup.py パッチを維持するために入れてある。

## 検証結果（2026-11-19, `scripts/verify_env.py --flavor win11-amd64-cpu` → exit 0）

- `torch 2.15.0+cpu`（`torch.version.cuda = None`）/ `torchvision 0.29.2+cpu`
- `mmcv 2.1.0+easykotenocr.3` import 可、`mmcv._ext` 読み込み可
- CPU ops の実行確認: `nms`（3 box / order [0,1,2]）、`box_iou_rotated`（0.3333 = GPU と同値）、
  `deform_conv2d`（出力形状 (1,8,6,6)）
- OCR 全体: `main.py infer c:/ocr/in c:/ocr/out-cpu -a -s b -c config/config.cpu.yml`
  → 4 ページ完走・exit 0・**平均 12.14 秒/画像**（cu134 GPU 版の 1.15 秒/画像の約 10.6 倍）

## CPU 版と GPU 版の出力差（リリース時の注意）

`c:/ocr/out-cpu`（torch 2.15.0+cpu）と `c:/ocr/out-cu134`（torch 2.15.0+cu134）の比較:

| ページ | 行数（CPU/GPU） | bbox 完全一致 | bbox 最大差 | テキスト差異行 |
|---|---|---|---|---|
| 01_leric1-1 | 21 / 21 | 19 | 1px | 0 |
| 02_leric1-2 | 19 / 19 | 18 | 1px | 1 |
| 03_leric1-3 | 19 / 19 | 18 | 1px | 1 |
| 04_leric1-4a | 18 / 18 | 18 | 0px | 0 |
| **合計** | **77 / 77** | **73/77** | **1px** | **2 行** |

- 行分割（レイアウト検出）は同じ。bbox は 1px 以内の揺れ。
- 認識テキストは 77 行中 2 行だけが 1 文字単位で異なる（trocr の CUDA/CPU カーネル差による
  浮動小数の揺れ。例: 「蜂ニ/蜂二」「改金/攻置」）。
- **同一リリース系列内で CPU 版と GPU 版の結果が完全一致する前提の運用（差分比較・回帰テスト）は
  避けること**。テストの期待値は flavor ごとに取るか、許容差を設ける。
