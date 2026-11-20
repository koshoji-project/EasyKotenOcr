# wheels/win11-arm64-cu135 — ビルド出所記録（PROVENANCE）✅ 記入済み

対象 flavor: `win11-arm64-cu135`（Release 4: win11 on arm + ARM64 + py3.15 + torch GPU cu135）
ビルドマシン: **RTX Spark / DGX Spark N1X（本機）** で 2026-11-20 にビルド・実機検証まで完了。

## 必須記入欄

| 項目 | 値（記入） |
|---|---|
| wheel ファイル名 | `mmcv-2.1.0+easykotenocr.3-cp315-cp315-win_arm64.whl` |
| sha256 | `7CCDBAB983122A865CE36B6EF715B3A159D40827718B5D7D07F13DAA0A0F1F47` |
| size | 5.5 MB（`_ext.cp315-win_arm64.pyd` 解凍後 26.37 MB。sm_121 単一 arch） |
| ビルド日 | 2026-11-20 |
| N1X の OS / arch | Windows 11 ARM64 / NVIDIA RTX Spark（GB10、GPU 6144-core Blackwell）/ 統一メモリ 46.5 GB（増配後。旧 30.5 GB では nvcc が OOM した） |
| Python | 3.15.2（uv 管理: `C:\Users\gesho\AppData\Roaming\uv\python\cpython-3.15.2-windows-aarch64-none`） |
| torch（ABI 依存） | `2.15.0+cu135`（`pypi.nvidia.com/nvtorch_oot/`） |
| torchvision | `0.29.2+cu135` |
| CUDA（nvcc） | release 13.5 / V13.5.37 ／ CUDA_HOME=`C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.5` |
| MSVC | 14.51.36231（VS 2026 Build Tools「18」、`vcvarsarm64.bat` による ARM64 ネイティブ） |
| TORCH_CUDA_ARCH_LIST | `12.1` → sm_121（`torch.cuda.get_device_capability() = (12, 1)` 実測） |
| ninja | **1.13.2 + CMake 4.3.1-msvc1、ARM64 可**。VS Build Tools 同梱版 `Common7\IDE\CommonExtensions\Microsoft\CMake\{Ninja,CMake}`。**vcvarsarm64.bat が PATH に注入するため通常シェルでは `where ninja` で見つからない**（torch cpp_extension は vcvars 環境内でのみ解決できる）。`build.ninja` は `build/temp.win-arm64-cpython-315/Release/` |
| mmcv の元ソース | open-mmlab/mmcv **v2.1.0**（commit `57c4e25e`、`git log -1` = "Bump version to 2.1.0 (#2959)"。ローカル変更は setup.py 差し替えのみ） |
| ステージング | `vendor/mmcv-patches/stage_mmcv.py --suffix easykotenocr.3`（5 オペ除外） |
| setup.py パッチ | `scripts/mmcv_setup_py315.py`（C++20 / `/Zc:preprocessor` / `USE_CUDA=1`） |
| 环境回避 | `TORCH_DONT_CHECK_COMPILER_ABI=1`: **要**（日本語 cl バナーの cp932 復号失敗対策）。追加で **`setuptools<81` pin 要**（mmcv レガシー setup.py の pkg_resources import。setuptools 84 で ModuleNotFoundError） |
| ビルドログ | `build/win11-arm64-cu135/logs/mmcv_build_20261120-063242.log`（sha256 `55db7e1e6fb3eb4fa8d283a97c465e64a14720dafda12fdff3395393b7f3718c`）。失敗履歴: `..._20261120-043047.log`（pkg_resources）/ `..._20261120-045924.log`（nvcc OOM @ [67/132]） |
| ビルドコマンド | `scripts/build_wheels.ps1 -Flavor win11-arm64-cu135 -Suffix easykotenocr.3 -SkipStage -MaxJobs 6`（統一メモリ環境のため MAX_JOBS で並列制限。無制限禁止） |

除外オペ（ライセンス上の理由。レビューなしに復活させないこと）:
`upfirdn2d`, `fused_bias_leakyrelu`, `bias_act`, `filtered_lrelu`, `conv2d_gradfix`

検証結果（zip 検査 + venv 実測。**win11-amd64 flavor の wheel と同一構造**）:
- `mmcv/ops/*.py` の Python ラッパー: **なし**
- `mmcv/ops/csrc/pytorch/pybind.cpp` の登録: **なし**
- `_ext.pyd` へのコンパイル: **なし**（venv で `hasattr` 全 5 件 False）
- 注記: `mmcv/ops/csrc/` 配下に該当オペの生ソース (.cpp/.cu) が package data として残骸同梱（AMD flavor wheel と同様。コンパイルも import もされない。完全除去は stage_mmcv.py 拡張 + 全 flavor 再ビルドが必要なので未実施）

## cv2（方針変更: 自前ビルドではなく純 Python シムで確定）

当初想定の「自前 OpenCV wheel 配布」は採用せず、リポジトリ同梱の純 Python シムを維持する。

| 項目 | 値 |
|---|---|
| 実装 | `C:\easykotenocr\cv2_shim`（editable install: `-e file:///C:/easykotenocr/cv2_shim`。dist 名 opencv-python 互換、`cv2.__version__` = 4.12.0） |
| 採用理由 | 旧 N1X 実証ランタイムとの行動等価を優先。PyPI に win_arm64 wheel 無しは変わらず |
| shadowing 対策 | albumentations を ARM profile から除外し、headless cv2 が入らない構造にした（除外前は headless 5.1.0.95 が混入し `import cv2` がそちらを指していた） |
| アプリ要求 API | シムが充足（両 flavor venv で import・OCR 実走 OK） |

## N1X 側での実機検証結果（2026-11-20）

- `python scripts/verify_env.py --flavor win11-arm64-cu135` → **VERIFY OK**
  - torch 2.15.0+cu135 / CUDA 13.5 / `cuda.is_available()=True`（RTX Spark N1X）
  - `mmcv.ops.box_iou_rotated` を CUDA 上で実行 → IoU 0.3333
  - 除外 5 オペの `hasattr` チェック: `[]`（空 = OK）
- OCR 実走: `python main.py infer <dir> <out> -s s -a`（既定 config → cuda:0）→ **3.44 秒/画像**、json/txt 生成
  - ※入力構造は **`-s s`（ディレクトリ直下に画像）** が正。旧テンプレ記載の `-s b` は 1書籍=サブフォルダ構造用
- **`.txt` 出力は win11-arm64-cpu flavor と行単位一致**（CPU 51.67 秒/画像）
- 推論前に `tools/apply_venv_patches.py`（weights_only 修正）の venv 適用が必須

## この PC への持ち戻し完了分

1. ✅ `wheels/win11-arm64-cu135/mmcv-2.1.0+easykotenocr.3-cp315-cp315-win_arm64.whl`
2. ✅ `profiles/win11-arm64-cu135/uv.lock`
3. ✅ `n1x-freeze-cu135.txt`（同フォルダー。74 パッケージ）
4. ✅ 記入済みのこの `PROVENANCE.md`
5. ✅ ビルドログ（`build/win11-arm64-cu135/logs/`）と `build_mmcv.bat`

検査:

```powershell
python scripts\check_wheels.py --record   # wheels/SHA256SUMS.txt 更新
python scripts\check_wheels.py            # 問題件数 0 確認
```
