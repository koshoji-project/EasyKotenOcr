# HANDOFF-N1X — ARM64 2 flavor（Release 3・4）の受け渡し手順

> **状態（2026-11-20 更新）**: 本手順書の手順は **N1X 側で進行中**（§0.1 参照）。
> 方針変更 2 点: (1) cv2 は N1X 自前ビルド wheel ではなく **純 Python の cv2 シム
> （`cv2_shim/`、リポジトリ内蔵）** を採用（旧 N1X 実証ランタイムと等価）。(2) mmcv は
> N1X 持ち込みではなく **本 PC（=N1X 相当の ARM64 環境）で 5 オペ除去・local tag .3 で
> 再ビルド**（AMD 側のライセンス方針に整合）。§3 / §4 の cv2 自前ビルド手順は不採用。

N1X（RTX Spark / DGX Spark, Windows on ARM）でビルド・動作確認済みの成果物を、
この PC の `win11-arm64-cpu` / `win11-arm64-cu135` flavor に取り込むための手順書。

## 0.1 再開記録（2026-11-20・メモリ増配後）

**メモリ増配後の再開結果**: Total 46.5 GB（+16 GB）確認。`MAX_JOBS` 導入済みで再実行。

- **win11-arm64-cpu: 完了**
  - wheel: `wheels\win11-arm64-cpu\mmcv-2.1.0+easykotenocr.3-cp315-cp315-win_arm64.whl`
    （9.3 MB / sha256 `91ADB7CC84AFF43A88CC5B2B7602A50FC0A623EC59569C3E73B4C4A2C9B220DA`）
  - Stage 2: profile で mmcv 有効化 → sync で addict 2.4.0 / yapf 0.43.0 / platformdirs 自動導入
  - `tools\apply_venv_patches.py` 適用済み（weights_only×3 ほか）
  - `scripts\verify_env.py --flavor win11-arm64-cpu` → **VERIFY OK**
  - OCR 実走: `main.py infer <in> <out> -s s -a -c config/config.cpu.yml` → 51.7 秒/画像、
    page01.json / page01.txt（漢文テキスト）生成確認
  - 入力構造の注意: `-s s` = 入力ディレクトリ直下に画像、`-s b` = 1書籍=サブフォルダ
    （`*/*ext`）、`-s f` = 入力自体が画像1ファイル
- **win11-arm64-cu135: 完了**（`-SkipStage -MaxJobs 6` の 3 回目で完走。OOM ゼロ）
  - wheel: `wheels\win11-arm64-cu135\mmcv-2.1.0+easykotenocr.3-cp315-cp315-win_arm64.whl`
    （5.5 MB / sha256 `7CCDBAB983122A865CE36B6EF715B3A159D40827718B5D7D07F13DAA0A0F1F47`）
  - Stage 2 同期 OK（addict 2.4.0 / yapf 0.43.0 / platformdirs 自動導入は CPU と同じ）
  - `tools\apply_venv_patches.py` 適用済み
  - `scripts\verify_env.py --flavor win11-arm64-cu135` → **VERIFY OK**
    （torch 2.15.0+cu135 / CUDA 13.5 / box_iou_rotated on CUDA → IoU 0.3333）
  - OCR 実走: `main.py infer <in> <out> -s s -a`（既定 config → cuda:0）→ **3.44 秒/画像**、
    `.txt` は CPU flavor と**行単位一致**

### 0.1c 記録・整合も完了（2026-11-20 締切）

- **ninja 発生源の謎は解けた**: 実体は VS Build Tools 同梱
  `...\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja\ninja.exe`（**1.13.2**、
  ARM64 可。CMake も同梱 4.3.1-msvc1）。`vcvarsarm64.bat` が PATH に注入するため通常シェルでは
  `where ninja` に出ず、ビルドログにもパスが現れなかった。`build.ninja` は
  `build\temp.win-arm64-cpython-315\Release\` に生成（cu135 完走ログに ninja 文字列 0 件だったのも
  このため）。torch 同梱/venv 内 ninja は**存在しない**（`_get_ninja_path()` は vcvars 環境外では None）。
- `wheels\win11-arm64-{cpu,cu135}\PROVENANCE.md` を実測値で記入済み（環境・ninja 発生源・
  失敗履歴（pkg_resources / nvcc OOM）・除外オペ検証・OCR 実走数値込み）
- `python scripts\check_wheels.py --record`（7 件記録）→ `check_wheels.py` **問題件数 0**
- `flavors.toml` の ARM 2 本 = `easykotenocr.3` 実名で整合済み
- 注記: 除外 5 オペはラッパー/pybind 登録/コンパイルとも不在（AMD と同一構造）だが、
  `mmcv\ops\csrc\` 配下に生ソース (.cpp/.cu) が package data として残骸同梱される（AMD も同様。
  完全除去は stage_mmcv.py 拡張 + 全 flavor 再ビルドが必要 → ユーザー判断待ち）
- ⏭ **残は git commit のみ**（push はユーザー運用）

以下は元の再開手順（歴史記録。cu135 分も完了済み）:

## 0.1 再起動再開ポイント（2026-11-20 記録・作業中断）

VRAM/DRAM 割り当て変更のため PC 再起動。再開は次の手順（すべて `C:\easykotenocr` から）:

1. **mmcv wheel 2 本のビルド再開**（staging と ninja の中間生成物 `.obj` は
   `build\win11-arm64-{cpu,cu135}\staging\mmcv\build\` に残っているので、
   `-SkipStage` で中継ぎ。再ビルドは未完了オブジェクトのみ）。
   DRAM 増配後は `MaxJobs` を 6〜8 に上げてもよい（30GB 統一メモリ時代は
   デフォルト 20 並列で nvcc が OOM「Catastrophic error: out of memory」→ 既定 4 にした）。

   ```powershell
   # CPU flavor（中断時 [40/132]・CPU-only _ext）
   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_wheels.ps1 -Flavor win11-arm64-cpu  -Suffix easykotenocr.3 -SkipStage
   # GPU flavor（中断時 [~60/132]・CUDA 13.5 / sm_121。前回 OOM で失敗。MAX_JOBS 付きで中継ぎ）
   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_wheels.ps1 -Flavor win11-arm64-cu135 -Suffix easykotenocr.3 -SkipStage
   ```

   2 本は **同時に走らせない**（統一メモリでの RAM 競合が OOM の一因）。
   完了の目印: `wheels\win11-arm64-{cpu,cu135}\mmcv-2.1.0+easykotenocr.3-cp315-cp315-win_arm64.whl`
   と SHA256 の表示（ログ `build\win11-arm64-\*\logs\`）。
2. **Stage 2: flavor へ mmcv を組み込む**（両 profile の pyproject.toml で
   `# "mmcv",` と `# mmcv = { path = ... }` のコメントを解除）→
   `UV_PROJECT_ENVIRONMENT=build\<flavor>\venv uv sync --project profiles\<flavor>` ×2。
   このとき mmcv wheel の依存（addict / yapf / packaging / pillow / regex / pyyaml）が venv に入る
   （mmengine vendor wheel の METADATA に依存が無いため、yapf 等はこの経路で入るのが AMD と同じ仕組み）。
3. **検証**: `build\<flavor>\venv\Scripts\python.exe scripts\verify_env.py --flavor <flavor>` ×2
   → OCR 実走 `... python.exe main.py infer c:/ocr/in c:/ocr/out-arm-cu135 -a -s b`（cpu flavor は
   `out-arm-cpu`、`-c config/config.cpu.yml`）×2。
4. **記録**: `wheels\win11-arm64-{cpu,cu135}\PROVENANCE.md` 記入（sha256・工具・検証結果）、
   `python scripts\check_wheels.py --record`（→ 問題件数 0 になる想定）、
   `flavors.toml` の ARM 系 `mmcv_wheel` が実ファイル名と一致することを確認。
5. **git**: 変更一括コミット（wheel 実体は gitignore で除外される）。

中断時時点の已完成事項（再起動しても失われない・ディスク上）:
- 両 flavor venv sync 完了（torch 2.15.0+cu134/+cu135 / sm (12,1) / cuda_available=True）
- `import cv2` → `cv2_shim/src/cv2`（4.12.0・シム単独。albumentations/headless 除外済み）
- `mmpretrain` import OK（mmengine は mmcv 投入前の Stage 1 では yapf 不在で import 失敗＝想定内）
- `setuptools<81`（80.10.2）pin 済み（pkg_resources 必需）
- `build_wheels.ps1` に `MAX_JOBS`（既定 4）追加済み・UTF-8 BOM 維持
- ステージング確認: 5 オペ除去済み（upfirdn2d 等 0 件）・version 2.1.0+easykotenocr.3

---

## 0. 受け皿の現状（この PC にあるもの）

| パス | 状態 |
|---|---|
| `profiles/flavors.toml` | ARM 2 flavor 定義済み。**`cuda_home`（CUDA v13.5）/ `vcvars`（vcvarsarm64）/ `torch_cuda_arch_list`（12.1 = sm_121）は記入済み**（2026-11-20） |
| `profiles/win11-arm64-cpu/pyproject.toml` | 完成形（torch 2.15.0+cu134 + device=cpu 運用）。`uv.lock` 生成済み（2026-11-20） |
| `profiles/win11-arm64-cu135/pyproject.toml` | 完成形（torch 2.15.0+cu135）。`uv.lock` 生成済み（2026-11-20・Stage 1 = mmcv なし） |
| `wheels/win11-arm64-cpu/PROVENANCE.md` | ✅ 記入済み（2026-11-20） |
| `wheels/win11-arm64-cu135/PROVENANCE.md` | ✅ 記入済み（2026-11-20） |
| `scripts/check_wheels.py` | 存在・タグ・SHA256・pyproject/lock の検査。`--record` で `wheels/SHA256SUMS.txt` を生成 |

検査の実行（受け入れ前に毎回）:

```powershell
python scripts\check_wheels.py            # 問題件数が 0 なら受け入れ完了
python scripts\check_wheels.py --record   # 持ち込んだ wheel の SHA256 を記録
```

## 1. N1X 側で守ってもらうこと（ソースを同一に保つため）

- mmcv のステージングは同じ `vendor/mmcv-patches/stage_mmcv.py`（5 オペ除外 + local tag）を使う。
  除外オペ: `upfirdn2d`, `fused_bias_leakyrelu`, `bias_act`, `filtered_lrelu`, `conv2d_gradfix`
- setup.py は同じ `scripts/mmcv_setup_py315.py`（C++20 / `/Zc:preprocessor` / `USE_CUDA=1`）で差し替える。
  CUDA 13.5 でも `/Zc:preprocessor` と `TORCH_DONT_CHECK_COMPILER_ABI=1` が必要かを確認し、結果を PROVENANCE に書く。
- `scripts/build_wheels.ps1` は `profiles/flavors.toml` 駆動。N1X 側で ARM flavor の
  `vcvars`（ARM64 用 vcvars の実パス）と `cuda_home` を記入すれば、同じスクリプトでビルドできる。
  別マシン用にスクリプトを複製しないこと。

## 2. mmcv の local version tag は **N1X の実ファイル名を正にする**（2026-11-19 決定）

`win11-amd64-*` の `.3` と揃える必要はない。**N1X でビルド済みのファイル名をそのまま使う**方針。
ただし ABI が違うのに両 ARM flavor のファイル名が同一だと区別がつかないので、
N1X 側で分かれていればそれを拾い、**同一だった場合だけ tag を分けて再ビルド**してもらう。

`flavors.toml` の `mmcv_wheel` と pyproject の path は**現時点の仮置き**で、実名が分かり次第こちらを更新する。
`scripts\check_wheels.py` が「不足」と「想定外の wheel（未登録）」の両方で指摘するので、
その指摘を見た人が更新手順を辿れるようになっている。

## 3. wheel 供給のギャップ（2026-11-19 に PyPI を直接確認）

| パッケージ | win_arm64 供給 | 対応 |
|---|---|---|
| `torch` 2.15.0 | 公式 index は cp313 まで・CPU のみ。`+cpu` の win_arm64 は**無し**。`+cu134` / `+cu135` の win_arm64 は NVIDIA `pypi.nvidia.com/nvtorch_oot/` に有 | ARM 2 flavor とも nvtorch_oot を使う（flavors.toml に反映ずみ） |
| `torchvision` 0.29.2 | nvtorch_oot に `0.29.2+cu134 / +cu135 -py3-none-win_arm64` | 同上 |
| `opencv-python` 4.14.0.94 | **win_arm64 wheel 無し**（contrib も同。`opencv-python-headless` 5.1.0.95 に win_arm64 wheel が 2026-11-20 に出たが未検証の 5.x 系） | **純 Python の cv2 シム（`cv2_shim/`）を editable 参照**（パッケージ名 opencv-python・モジュール cv2）。旧 N1X 実証ランタイム（シム単独）と等価。シムを shadowing し得る albumentations は ARM profile から除外 |
| `scikit-image` 0.27.0rc1 | **cp315 win_arm64 あり** | pin はそのまま使える |

### cv2（自前ビルド）で持ち戻るもの

```powershell
# 版とビルド条件の記録（CMake のモジュール設定・GUI/FFmpeg 等有効機能が全部出る）
python -c "import cv2;print(cv2.__version__);print(cv2.__file__);print(cv2.getBuildInformation())" > n1x-cv2-buildinfo.txt

# 自前ビルドした wheel 本体を探す（ビルド残骸から出てこなければ再ビルドが必要）
Get-ChildItem -Path C:\ -Recurse -Filter 'opencv*win_arm64*.whl' -ErrorAction SilentlyContinue | Select-Object FullName, Length
# インストール元の記録
uv pip show opencv-python        # （pip の場合は python -m pip show opencv-python）

# 使っている cv2 がどの API を要求するか（ビルド差異で壊れやすい箇所）
python -c "import cv2;print([n for n in ('imdecode','imencode','resize','warpAffine','findContours','connectedComponents') if hasattr(cv2,n)])"
```

- wheel 本体（例: `opencv_python-<ver>-cp37-abi3-win_arm64.whl`）→ `wheels\win11-arm64-cu135\`（CPU flavor にも同じ ABI ならコピー、あるいは path を共通化）
- `n1x-cv2-buildinfo.txt` と、ビルドに使ったコマンド（`pip wheel` / `python setup.py bdist_wheel` と `CMAKE_ARGS`、OpenCV の版・コミット）を PROVENANCE に記入
- **cv2 の版が amd64 の 4.14.0.94 と違う場合は flavors.toml / pyproject のピンも実版に合わせる**こと


## 4. N1X 側で実行して持ち戻るコマンド

```powershell
# 環境メタデータ（画面コピーを PROVENANCE に貼る）
python -c "import sys;print(sys.version);print(sys.executable)"
python -c "import torch,torchvision,mmcv;print('torch',torch.__version__,'cuda',torch.version.cuda);print('tv',torchvision.__version__);print('mmcv',mmcv.__version__,mmcv.__file__)"
python -c "import torch;print(torch.cuda.is_available(), torch.cuda.get_device_name(0), torch.cuda.get_device_capability(0))"
nvcc --version
python -c "import mmcv.ops as o;print([n for n in ('upfirdn2d','fused_bias_leakyrelu','bias_act','filtered_lrelu','conv2d_gradfix') if hasattr(o,n)])"   # [] が空なら OK
uv pip freeze > n1x-freeze-cu135.txt        # CPU flavor 側は n1x-freeze-cpu.txt
python scripts\verify_env.py --flavor win11-arm64-cu135
python main.py infer c:/ocr/in c:/ocr/out-n1x-cu135 -a -s b
```

持ち戻るファイル:

1. `wheels/win11-arm64-cu135/mmcv-…-cp315-cp315-win_arm64.whl`（CPU flavor 分も同様に）
2. ~~cv2 の自前ビルド wheel 本体~~ **不採用**（cv2 は `cv2_shim/` シムで統合済み）
3. `profiles/win11-arm64-*/uv.lock`
4. `n1x-freeze-cu135.txt` / `n1x-freeze-cpu.txt`
5. 記入済み `wheels/win11-arm64-*/PROVENANCE.md` とビルドログ・`build_mmcv.bat`

## 5. この PC での受け入れ

```powershell
# 1) wheel を所定の dir に置く → 2) SHA256 記録 → 3) 検査
python scripts\check_wheels.py --record
python scripts\check_wheels.py            # 問題件数: 0
```

`verify_env.py` の import 検査は **N1X 側でのみ**意味がある（この PC では win_arm64 wheel を import できない）。
`check_wheels.py` はファイル名タグ（arm64 flavor に win_amd64 を置かない等）まで検査する。
