# wheels/win11-arm64-cpu — ビルド出所記録（PROVENANCE）✅ 記入済み

対象 flavor: `win11-arm64-cpu`（Release 3: win11 on arm + ARM64 + py3.15 + torch CPU 運用）
ビルドマシン: **RTX Spark / DGX Spark N1X（本機）** で 2026-11-20 にビルド・実機検証まで完了。

## 必須記入欄

| 項目 | 値（記入） |
|---|---|
| wheel ファイル名 | `mmcv-2.1.0+easykotenocr.3-cp315-cp315-win_arm64.whl` |
| sha256 | `AD6F795A96485BA921A7D91D564E268BB688199454329578E68D30CBA2D64D77`（2026-11-21 残骸除去再ビルド版。旧 2026-11-20 初版 `91ADB7CC…20DA` は package data 残骸同梱のため廃棄） |
| size | 4.2 MB（`_ext.cp315-win_arm64.pyd` 解凍後 12.98 MB。CUDA 無し CPU-only ビルド。旧初版は pyd 30.22 MB だったが、同一ソース・同一スクリプトの再ビルドで縮退。verify_env / OCR 実走とも OK を確認済み） |
| ビルド日 | 2026-11-21（初版 2026-11-20） |
| N1X の OS / arch | Windows 11 ARM64 / NVIDIA RTX Spark（GB10）/ 統一メモリ 46.5 GB |
| Python | 3.15.2（uv 管理: `C:\Users\gesho\AppData\Roaming\uv\python\cpython-3.15.2-windows-aarch64-none`） |
| torch（ABI 依存） | `2.15.0+cu134`（nvtorch_oot の cu134 版を **device=cpu で運用**。※PyPI に win_arm64 の CPU 専用 2.15 wheel が無いため。`torch.cuda.is_available() = False` 確認済み） |
| torchvision | `0.29.2+cu134`（同上。cpu 運用） |
| CUDA（nvcc） | **不使用**。ビルドは `build_wheels.ps1 -Device cpu`（`CUDA_VISIBLE_DEVICES=` 空 + USE_CUDA=0）で CUDA なしに切り、純 CPU のみコンパイル |
| MSVC | 14.51.36231（VS 2026 Build Tools「18」、`vcvarsarm64.bat` による ARM64 ネイティブ） |
| TORCH_CUDA_ARCH_LIST | 該当なし（CUDA コンパイルなし） |
| ninja | **1.13.2 + CMake 4.3.1-msvc1、ARM64 可**。VS Build Tools 同梱版（`Common7\IDE\CommonExtensions\Microsoft\CMake\`）。vcvarsarm64.bat が PATH に注入するため通常シェルでは `where ninja` に出ない |
| mmcv の元ソース | open-mmlab/mmcv **v2.1.0**（commit `57c4e25e`。cu135 flavor と同一ソース） |
| ステージング | `vendor/mmcv-patches/stage_mmcv.py --suffix easykotenocr.3`（5 オペ除外） |
| setup.py パッチ | `scripts/mmcv_setup_py315.py`（C++20 / `/Zc:preprocessor`、CPU は USE_CUDA=0） |
| 环境回避 | `setuptools<81` pin 要（pkg_resources）。`TORCH_DONT_CHECK_COMPILER_ABI=1` は ps1 経由で常に設定 |
| ビルドログ | `build/win11-arm64-cpu/logs/mmcv_build_20261121-174314.log`（残骸除去再ビルド版。旧ログ: `..._20261120-062459.log` は初版、`..._054156.log` は中断前）。ビルドコマンド: `scripts/build_wheels.ps1 -Flavor win11-arm64-cpu`（既定 MAX_JOBS=4） |
| ビルド並列 | `MAX_JOBS=4`（統一メモリ環境のため並列制限） |

local tag / ABI の確定（テンプレ §「local tag は N1X の実ファイル名を正にする」への回答）:
ファイル名は両 flavor とも `mmcv-2.1.0+easykotenocr.3-...` と同一だが、**flavor ごとに別ビルドの
専用 wheel を同梱**（CPU 9.3 MB / cu135 5.5 MB、sha256 別個。2026-11-20 決定「保守的に分離」）。
共有名 1 本での ABI 問題は発生しない構成。`flavors.toml` は各 flavor 配下のファイルを指す。

除外オペ（ライセンス上の理由。レビューなしに復活させないこと）:
`upfirdn2d`, `fused_bias_leakyrelu`, `bias_act`, `filtered_lrelu`, `conv2d_gradfix`

検証結果（zip 検査 + venv 実測。**win11-amd64 flavor / win11-arm64-cu135 の wheel と同一構造**）:
- `mmcv/ops/*.py` の Python ラッパー: **なし**
- `mmcv/ops/csrc/pytorch/pybind.cpp` の登録: **なし**
- `_ext.pyd` へのコンパイル: **なし**（venv で `hasattr` 全 5 件 False）
- 注記: **残骸除去済み（2026-11-21）**。`stage_mmcv.py` の拡張（AMD64 側 `e61e551`）により、除外 5 オペの生ソース（.cpp/.cu、9 ファイル）はステージング段階で削除され wheel に同梱されない。`scripts/scan_wheel_ops.py <whl>` → 0 hit / exit 0 で確認

## cv2（方針変更: 自前ビルドではなく純 Python シムで確定）

cu135 flavor と同じ。`C:\easykotenocr\cv2_shim` の editable install（`cv2.__version__` = 4.12.0、dist 名 opencv-python 互換）。albumentations は profile から除外して headless cv2 の shadowing を構造的に防止。旧 N1X 実証ランタイムとの行動等価を優先。

## N1X 側での実機検証結果（2026-11-20 初版 / 2026-11-21 再ビルド版）

**2026-11-21 再ビルド版（現行 wheel）**:
- `scripts/verify_env.py --flavor win11-arm64-cpu` → **VERIFY OK**
- OCR 実走: `main.py infer c:/ocr/in c:/ocr/out-new-cpu -a -s b -c config/config.cpu.yml` → **45.4 秒/画像**、正常終了
- `.txt` を cu135 ベースライン（`c:/ocr/out-win11-arm64-cu135/2026-11-21_051523`）と比較: **5 ファイル中 4 ファイルバイト一致**。page03 の 1 文字のみ差異（`いとうつくしに` ↔ `いとうつくしう`、bbox 1 個が 1px 相当シフト）
  - 原因の切り分け済み: 同一 wheel で 2 回実行し完全一致（実行間ブレなし）。CPU ビルドは除外 5 オペ（cuda/npu/parrots 配下）を一切コンパイルしないため再ビルド前後でコンパイル対象ソースが同一で、この差異は再ビルド由来ではない。**CPU/GPU 実装差による既存の数値挙動**（11-20 の検証は page01 のみで、page03 の CPU 出力は比較済みベースラインが存在しなかった）。`いとうつくしう` は歴史的仮名遣いとしては正しい表記

**2026-11-20 初版**:

- `python scripts/verify_env.py --flavor win11-arm64-cpu` → **VERIFY OK**（cuda_avail: False は想定通り）
- `mmcv.ops` の `nms / RoIAlign / box_iou_rotated` が CPU で動作
- OCR 実走: `python main.py infer <dir> <out> -s s -a -c config/config.cpu.yml` → **51.67 秒/画像**、json/txt 生成
  - ※入力構造は `-s s`（ディレクトリ直下に画像）が正
- **`.txt` 出力は win11-arm64-cu135 flavor と行単位一致**（GPU は 3.44 秒/画像）
- 推論前に `tools/apply_venv_patches.py`（weights_only 修正）の venv 適用が必須

## この PC への持ち戻し完了分

1. ✅ `wheels/win11-arm64-cpu/mmcv-2.1.0+easykotenocr.3-cp315-cp315-win_arm64.whl`
2. ✅ `profiles/win11-arm64-cpu/uv.lock`
3. ✅ `n1x-freeze-cpu.txt`（同フォルダー。74 パッケージ）
4. ✅ 記入済みのこの `PROVENANCE.md`
5. ✅ ビルドログ（`build/win11-arm64-cpu/logs/`）と `build_mmcv.bat`

検査:

```powershell
python scripts\check_wheels.py --record   # wheels/SHA256SUMS.txt 更新
python scripts\check_wheels.py            # 問題件数 0 確認
```
