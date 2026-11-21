# EasyKotenOCR マルチリリース配置案

作成: 2026-11-19 / 更新: 2026-11-19（torch 2.15系 統一・flavor 2 = cu134 を反映）
対象: `C:\easykotenocr`（windows11+amd64+python3.15.2 作業フォルダー）
この文書は**方針の記録**。当初は設計のみだったが、§11（amd64 の 2 flavor）と §12（ARM の受け皿）は
**実施済み**なので、実測値と結果が書いてある。

> **決定（2026-11-19）**: torch は **2.15.0 に統一**、GPU amd64 の CUDA variant は **cu134** を採用。
> これにより flavor 2 の id は `win11-amd64-cu130` → **`win11-amd64-cu134`** に変わる（§10 決定記録）。

---

## 0. リリース4種の定義（flavor id）

全ツール・全スクリプト・全パスの鍵になる識別子を **flavor id** と呼ぶ。命名規約は
`<os>-<arch>[-<cudavariant>]`、CPU は末尾 `-cpu`。

| # | flavor id | OS / arch | Python | torch | torchvision | index | mmcv wheel tag | device |
|---|---|---|---|---|---|---|---|---|
| 1 | `win11-amd64-cpu` | Win11 / AMD64 | 3.15.2 (cp315) | `2.15.0+cpu` | `0.29.2+cpu` | `https://download.pytorch.org/whl/cpu` | `cp315-cp315-win_amd64` | cpu |
| 2 | **`win11-amd64-cu134`** | Win11 / AMD64 | 3.15.2 (cp315) | `2.15.0+cu134` | `0.29.2+cu134` | `https://download.pytorch.org/whl/cu134` | `cp315-cp315-win_amd64` | cuda:0 |
| 3 | `win11-arm64-cpu` | Win11 on ARM / ARM64 | 3.15.2 (cp315) | `2.15.0+cu134`（**`+cpu` の win_arm64 は供給無し** → §8-③） | `0.29.2+cu134` | `https://pypi.nvidia.com/nvtorch_oot/` | `cp315-cp315-win_arm64` | cpu |
| 4 | `win11-arm64-cu135` | Win11 on ARM / ARM64 | 3.15.2 (cp315) | `2.15.0+cu135`（N1X でビルド・検証済み） | `0.29.2+cu135` | `https://pypi.nvidia.com/nvtorch_oot/` | `cp315-cp315-win_arm64` | cuda:0 |

**torch は 2.15.0 で統一、CUDA minor は flavor 変数**（amd64 = 13.4 / arm64 GPU = 13.5）。
torchvision は §0.1 の理由から **0.29.2 で統一**する。

確認済みの供給事実（2026-11-19 実測、simple index を直接走査）:

- `download.pytorch.org/whl/cu134/torch/` に **`torch-2.15.0+cu134-cp315-cp315-win_amd64.whl`**（`cp315t` も有り）。cu132 にも 2.15.0 有り。
- `download.pytorch.org/whl/cpu/torch/` に **`torch-2.15.0+cpu-cp315-cp315-win_amd64.whl`**。
- `pypi.nvidia.com/nvtorch_oot/torch/` に **`torch-2.15.0+cu135-cp315-cp315-win_arm64.whl`** と **`+cu134` 版**。同 index に `torchvision` `torchaudio` `tensordict` `torch-tensorrt-rtx`。
- **torchvision は 0.29.2 が唯一の選択肢**（Python 3.15 に対して）:
  - `torchvision-0.29.2+cu134-py3-none-win_amd64.whl`（cu134 index）
  - `torchvision-0.29.2+cpu-py3-none-win_amd64.whl`（cpu index）
  - `torchvision-0.29.2+cu134 / +cu135 -py3-none-win_arm64.whl`（nvtorch_oot）
  - `0.29.0` / `0.29.1` は **cp310〜cp314 のみで cp315 の wheel が存在しない**（現行 `pyproject.toml` の `torchvision==0.29.1+cu130` は flavor 移行時に必ず変わる）。
  - `py3-none-win_amd64` / `py3-none-win_arm64` という Python 非依存タグなので、**cp315 でも選択される**（mmcv の ABI 依存は torch 側なので、torchvision のタグ非依存は運用上むしろ有利）。
- **`+cpu` の win_arm64 torch は 2.15.0 に存在しない**（download.pytorch.org の win_arm64 は cp313 まで・cu130/cu132/cu134 に win_arm64 は無し、nvtorch_oot に `+cpu` は無し、PyPI の torch 2.15.0 にも win_arm64 ファイルは無し）→ flavor 3 は §8-③ の判断に従う。
- 本マシン（AMD64 側ビルド環境）の CUDA Toolkit は **v11.7 / v12.8 / v13.0 / v13.1 のみ**で **v13.4 は未導入**。ドライバ 621.14 / RTX 5090（sm_120）。→ flavor 2 の mmcv 再ビルドには **CUDA Toolkit 13.4 の導入が必須**（§9-2）。
- `torchvision` の供給元を統一したため、`wheels/common/` に置く pure wheel（mmengine / mmpretrain）とは別に、**torch / torchvision はリポジトリに置かず index から取得**する方針を維持する（1本 3〜4GB あるため）。

参考: [CUDA Toolkit 13.5 Windows arm64](https://developer.nvidia.com/cuda-downloads?target_os=Windows&target_arch=arm64&target_version=11)（CUDA 側は ARM64 対応）／[PyTorch for Windows on Arm](https://learn.arm.com/install-guides/pytorch-woa/)

Release 3・4（RTX Spark N1X 上でのビルド・mmcv 2.1.0 wheel 化・動作確認済み）について、**本マシン側にはその成果物がまだ無い**。したがって §4 の `wheels/<flavor>/` と §6 の記録欄が空欄の状態でスタートする。

---

## 0.1 flavor 別ピン（この表を `profiles/flavors.toml` に写す）

| key | win11-amd64-cpu | win11-amd64-cu134 | win11-arm64-cpu | win11-arm64-cu135 |
|---|---|---|---|---|
| `python` | 3.15.2 (cp315) | 3.15.2 (cp315) | 3.15.2 (cp315) | 3.15.2 (cp315) |
| `torch` | `2.15.0+cpu` | `2.15.0+cu134` | `2.15.0+cu134`（§8-③ 未決） | `2.15.0+cu135` |
| `torchvision` | `0.29.2+cpu` | `0.29.2+cu134` | `0.29.2+cu134` | `0.29.2+cu135` |
| `index` | `/whl/cpu` | `/whl/cu134` | nvtorch_oot | nvtorch_oot |
| `cuda_home` | 不要 | CUDA v13.4（**未導入**） | 不要 | N1X 側（v13.5） |
| `device`（config） | cpu | cuda:0 | cpu | cuda:0 |
| mmcv local tag | `+easykotenocr.3`（新規ビルド） | `+easykotenocr.3`（新規ビルド） | N1X 由来（`.3` 相当、要記録） | N1X 由来（要記録） |

mmcv は **torch の ABI で張り替わる**ため、torch 2.14.1 → 2.15.0 の統一によって
**現行の `mmcv-2.1.0+easykotenocr.2-cp315-cp315-win_amd64.whl` は flavor 2 では使えない**（§7 参照）。

---

## 1. 設計原則

1. **ソースは 1 本だけ**。arch / GPU / CUDA の違いで `.py` を分岐させない。
2. 差分は次の 4 層のどれかで吸収する（ソース変更は最後の手段）。

   | 層 | 吸収するもの | 置く場所 |
   |---|---|---|
   | 設定 | `device`（cpu / cuda:0）、batch_size、score_thr | `config/` |
   | 需給（wheel） | torch・torchvision・mmcv の arch/CUDA ビルド | `wheels/<flavor>/`（mmcv）、index 側（torch/torchvision） |
   | 解像度（lock） | torch / torchvision の local version（`+cpu`/`+cu134`/`+cu135`）、index URL、Python タグ | `profiles/<flavor>/` |
   | パッチ | mmcv のオペ除外・C++20・py315 修正、mmengine/mmpretrain の修正 | `vendor/<pkg>-patches/` |

3. **生成物とモデルはツリーに置かない**（`.gitignore` + `build/` `dist/` `models/`）。モデルは arch 非依存なので **4 リリースで 1 份**を共有する（970MB + 870MB を 4 回複製しない）。
4. 各 flavor のビルドは「同じコマンド、引数は flavor id だけ」にする。スクリプト内に絶対パス・CUDA バージョン・arch を直書きしない。

---

## 2. 目標ディレクトリ構成

```
C:\easykotenocr\
├─ main.py
├─ cli\                                # 完全共通（flavor 別のソースを作らない）
├─ src\                                # 完全共通（モデル学習コード含む）
│
├─ config\
│   ├─ config.yml                      # 共通本体（device は auto にする → §5 案A）
│   ├─ device.cpu.yml                  # 案B を採る場合のみ：cpu 上書きスニペット
│   └─ device.cuda.yml                 # 案B を採る場合のみ：cuda:0 上書きスニペット
│
├─ pyproject.toml                      # アプリ本体の依存定義（torch/mmcv のピンは flavor 側）
├─ profiles\
│   ├─ flavors.toml                    # ★ flavor 定義の単一ソース（下表 §3）
│   ├─ win11-amd64-cpu\uv.lock + pyproject.toml
│   ├─ win11-amd64-cu134\uv.lock + pyproject.toml
│   ├─ win11-arm64-cpu\uv.lock + pyproject.toml
│   └─ win11-arm64-cu135\uv.lock + pyproject.toml
│
├─ wheels\
│   ├─ common\                         # arch 非依存: mmengine, mmpretrain（1 份で 4 flavor 共通）
│   ├─ win11-amd64-cpu\mmcv-2.1.0+easykotenocr.3-cp315-cp315-win_amd64.whl
│   ├─ win11-amd64-cu134\mmcv-2.1.0+easykotenocr.3-cp315-cp315-win_amd64.whl
│   ├─ win11-arm64-cpu\mmcv-2.1.0+easykotenocr.3-cp315-cp315-win_arm64.whl   # N1X 側の成果物を取り込む
│   └─ win11-arm64-cu135\mmcv-2.1.0+easykotenocr.3-cp315-cp315-win_arm64.whl # N1X 側の成果物を取り込む
│
├─ vendor\
│   ├─ mmcv\                           # open-mmlab v2.1.0 の素の checkout（build/・egg-info・.pyd は無い状態）
│   ├─ mmcv-patches\
│   │   ├─ stage_mmcv.py               # ★ 現 scratch の stage_mmcv_py315.py を git 化（オペ除外＋version local tag）
│   │   ├─ mmcv_setup_py315.py         # 現状 scripts\ にあるもの（C++20 / USE_CUDA マクロ）を here へ
│   │   └─ README.md                   # 除外オペ 5 種とライセンス上の根拠（現 scripts\README.md の該当節）
│   └─ wheel-patches\                  # mmengine / mmpretrain の .patch（build_vendor_wheels.py 内の文字列一致を移設）
│
├─ scripts\
│   ├─ build_wheels.ps1                # -Flavor <id>：vendor→staging→patch→bdist_wheel→wheels/<id>\
│   ├─ build_vendor_wheels.py          # common（arch 非依存）wheel の再生成。現状維持で可
│   ├─ verify.ps1                      # -Flavor <id>：import/版アサート（start_ocr.bat から移設）
│   ├─ download_models.py              # models/manifest.json に従い sha256 検証付きで取得
│   ├─ manifest.json                   # モデルの URL + sha256 + 展開後パス
│   └─ make_release.ps1                # -Flavor <id>：dist\<id>\*.zip 生成
│
├─ models\                             # git 管理外（LFS or 配布 zip or インストール時取得）
│   ├─ ndl_kotenseki_layout\models\ndl_kotenseki_layout_ver3.pth
│   └─ text_kotenseki_recognition\model-ver2\...
│
├─ build\                              # git 除外
│   └─ <flavor>\{venv\, staging\, logs\}
├─ dist\                               # git 除外
│   └─ <flavor>\easykotenocr-0.1.0+<flavor>.zip
│
├─ installer\
│   ├─ 01_install_Prerequisite.bat     # VS Build Tools / Git / uv（arch 共通）
│   └─ 02_install.bat                  # arch・GPU 自動判定 → flavor id 決定 → uv sync --project profiles\<id>
│
└─ docs\
    └─ WHEELS.md                       # 現 scripts\README.md（出典・除外オペ・検証記録）を flavor 表付きで here へ
```

`wheels/` は**リリース zip に含める唯一のバイナリ供給元**という位置づけを明確にしておく（`02_install.bat` が「wheels が無いとインストールできない」と明示チェックしている現状の設計は正しい）。

---

## 3. `profiles/flavors.toml`（差分の単一ソース）に持たせる項目

| キー | 意味 | flavor での違い |
|---|---|---|
| `python` | インタプリタ tag | 4 flavor とも cp315（3.15.2） |
| `index` | uv の index URL | `/whl/cpu` ・ `/whl/cu134` ・ `pypi.nvidia.com/nvtorch_oot/` |
| `torch_pin`, `torchvision_pin` | local version 込みピン | torch は **2.15.0 統一**、CUDA variant が flavor 変数（§0.1） |
| `wheel_platform` | `win_amd64` / `win_arm64` | mmcv ビルド・検証の判定に使用 |
| `cuda_home`, `vs_toolset` | ビルド環境の絶対パス | flavor 別（machine 単位でもある） |
| `torch_cuda_arch_list` | mmcv ビルド用 | amd64 cu134（RTX 5090/sm_120）: `7.5;8.0;8.6;9.0;10.0;12.0` ／ N1X 系は sm_12x 系に変更（**N1X 側の設定値を記入待ち**）／ CPU: 未使用 |
| `config_file` | 使用 config | `config/config.yml`（device auto） |
| `models` | モデル集合と sha256 | 4 flavor 共通 |

スクリプトはこの 1 ファイルだけを読み、`flavors.toml` に無い flavor id は即エラーにする。

---

## 4. `wheels/` の配置規則

1. **flavor 非依存の wheel（`py3-none-any`, `py2.py3-none-any`）は `wheels/common/` に 1 份だけ**。mmengine / mmpretrain が該当。flavor ごとにコピーしない。
2. **flavor 依存の wheel は `wheels/<flavor>/` のみ**。mmcv が該当（python tag × platform tag × ビルド時 torch 版の三重依存）。
3. ローカル ビルドは local version tag `+easykotenocr.N` を使い、**内容を変えたら N を上げる**。
   - 既存: `.1` = cp310（参照用）、`.2` = cp315 win_amd64（**torch 2.14.1+cu130  Against**）。
   - **torch 2.15 統一後は `.3` に上げる**（AMD64 の CPU/GPU 各ビルド、ARM64 の N1X 由来分を含む）。`.2` と `.3` は mmcv の Python 側コードは同一でも `_ext` の ABI が違うので、**混在すると import 時に崩れる**。`verify.ps1` で `mmcv.__version__` と `torch.__version__` を必ず対で検査する。
4. 各 flavor ディレクトリには `PROVENANCE.md` を 1 行ずつ置き、**どのソース（commit + patch 版）＋どの torch/CUDA/MSVC でビルドしたか**を記録する。N1X 由来の ARM wheel は「N1X 上でビルド、torch 2.15.0+cu13x、SHA256」を必ず記録する（本マシンでは再現不能な成果物なので特に重要）。
5. 互換性の実運用メモ: `[tool.uv.sources]` の mmcv は marker（`platform_machine`, `sys_platform`, `python_version`）で flavor を選べるが、**CPU/GPU は marker では自動判定できない**ため、flavor を明示する（= `profiles/` の方針）ほうが事故らない。

---

## 5. `config` の扱い（ソース差分を 0 にする決め手）

現状 `config.yml` の `ndl_kotenseki_layout.device` / `text_kotenseki_recognition.device` の 2 箇所だけが CPU/GPU で違う。選択肢:

- **案A（推奨）**: 共通 `config/config.yml` に `device: auto` を許し、`torch.cuda.is_available()` で解決する小改修（数行）。これで **4 flavor すべて config 1 本**。移植上の差分も 1 箇所に集約されレビューしやすい。
- **案B**: `config.yml` は 1 本のまま、`device.cpu.yml` / `device.cuda.yml` をインストール時に overlay（または `main.py infer -c` で flavor 別の設定ファイルを渡す）。ソース変更はゼロ。

どちらを採るかはこの文書の §8 未決事項に置いてある。

同時に片付けるべき既存の不整合: `config.yml` の `kotenseki_reading_order.checkpoint_path` は**存在しないパス**で、`src/reading_order/tools/process.py:InferencerWithCLI` は `conf_dict` を一切参照しない（joblib モデルも lightgbm 依存も不要）。死んだ設定として削除 or 注記の対象。

---

## 6. `profiles/` の必要性（uv の制約）

- `uv.lock` は 1 パッケージにつき 1 版しか固定できない。`torch==2.15.0+cpu` と `torch==2.15.0+cu134` を**同一ロックに併存させられない**。
- `[[tool.uv.index]]` も flavor で変わる（`/whl/cpu`・`/whl/cu134`・`https://pypi.nvidia.com/nvtorch_oot/`）。
- `uv` は lock ファイルの場所を選べないので、**flavor ごとに薄い uv プロジェクトを持つ**形にする。

```
profiles\win11-amd64-cu134\pyproject.toml
  [project] name = "easykotenocr-win11-amd64-cu134"
  dependencies = ["easykotenocr", "torch==2.15.0+cu134", "torchvision==0.29.2+cu134"]
  [tool.uv.sources] easykotenocr = { path = "../..", editable = true }
                                        mmcv = { path = "../../wheels/win11-amd64-cu134/mmcv-...+easykotenocr.3-cp315-cp315-win_amd64.whl" }
  [[tool.uv.index]] url = "https://download.pytorch.org/whl/cu134"
profiles\win11-amd64-cu134\uv.lock        # ← この flavor の解像度
```

実行（アプリ本体は共通のまま）:

```
uv sync --locked --project profiles\win11-amd64-cu134
uv run --no-sync --project profiles\win11-amd64-cu134 main.py infer c:/ocr/in c:/ocr/out -a -s b
```

venv は `build\<flavor>\venv` に集約（`UV_PROJECT_ENVIRONMENT` で指定）。`.venv` をルートに 1 個だと、4 flavor を 1 台でビルドするときに踏み抜く。

---

## 7. 現状 → 目標 の引っ越し対応表

| 現在 | 目標 | 備考 |
|---|---|---|
| `wheels\mmcv-...+easykotenocr.2-cp315-win_amd64.whl` | `attic\` | **torch 2.14.1+cu130 Against のビルドなので flavor 2 では使えない**。torch 2.15.0+cu134 に対して `.3` として再ビルド |
| （新規） | `wheels\win11-amd64-cu134\mmcv-...+easykotenocr.3-...whl` | CUDA Toolkit 13.4 導入後（§9-2）に本マシンでビルド |
| （新規） | `wheels\win11-amd64-cpu\mmcv-...+easykotenocr.3-...whl` | torch 2.15.0+cpu に対してビルド（nvcc 不要） |
| （N1X から移植） | `wheels\win11-arm64-cpu\`, `wheels\win11-arm64-cu135\` | ビルド済み・動作確認済みの wheel と SHA256 を取り込む |
| `wheels\mmcv-...cp310-win_amd64.whl` | `attic\` or 削除 | cp310 系統の遺物。`README` 上も「参照用」 |
| `wheels\mmengine-*.whl`, `wheels\mmpretrain-*.whl` | `wheels\common\` | `py3-none-any` / `py2.py3-none-any` で flavor 非依存 |
| `pyproject.toml` の `[[tool.uv.index]]`(cu130) + `torch==2.14.1+cu130` + `torchvision==0.29.1+cu130` + `[tool.uv.sources]` | `profiles\<flavor>\` へ分散 | ルートの `pyproject.toml` はアプリ本体の依存定義だけ残す。torchvision は 0.29.2 に上げる（0.29.1 に cp315 wheel は無い） |
| `uv.lock` | `profiles\win11-amd64-cu134\uv.lock` | ルート lock は廃止（複数 flavor では単一 lock が使えない） |
| `uv.lock.bak-py310`, `.venv-py310.bak`（3.4GB） | `attic\` or 削除 | cp310 系統 |
| `mmcv\`（3.3GB、`build\` と `_ext.cp310/cp314.pyd` を内包） | `vendor\mmcv\`（素の v2.1.0）+ `build\<flavor>\staging\` | `build\`・`*.egg-info`・in-tree `.pyd` は削除・git 除外 |
| `scripts\mmcv_setup_py315.py` | `vendor\mmcv-patches\mmcv_setup_py315.py` | 2.15 でも `/std:c++20`（torch>=2.14 の `std::strong_ordering`）と `USE_CUDA=1`（torch>=2.9）の分岐はそのまま有効。版判定を確認 |
| `%LOCALAPPDATA%\hermes\cache\scratch\stage_mmcv_py315.py`（**git 外・唯一のコピー**） | `vendor\mmcv-patches\stage_mmcv.py` | ★ 最優先。mmcv の 5 オペ除外（upfirdn2d / fused_bias_leakyrelu / bias_act / filtered_lrelu / conv2d_gradfix）の再構成手順がここにしかない |
| `scripts\build_mmcv_py315_wheel.bat`（scratch・venv・CUDA v13.0 が絶対パス直書き） | `scripts\build_wheels.ps1 -Flavor <id>` | `CUDA_HOME`(v13.4), `TORCH_CUDA_ARCH_LIST`, staging path を `flavors.toml` から供給 |
| `scripts\README.md` | `docs\WHEELS.md` + `vendor\mmcv-patches\README.md` | flavor 表を追加 |
| `start_ocr.bat` / `start_ocr_with_timeRecord.bat` に埋め込まれた import/版アサート | `scripts\verify.ps1 -Flavor <id>` | `mmcv.__version__ == '2.1.0+easykotenocr.2'` / `torch == 2.14.1+cu130` のハードコードが flavor と torch 統一で壊れる |
| `src\...\model-ver2.zip`(450MB) と展開済み `model-ver2\`(870MB) の二重保持 | `models\` に一本化 + `manifest.json`(sha256) | zip の保持/削除方針は §8 |
| `EasyKoten\01_,02_*.bat`, `download_models.py` | `installer\`, `scripts\download_models.py` | `02_install.bat` のアーティファクトチェックを flavor 対応に |
| git 管理下の `__pycache__\*.pyc`（19 件）、`.gitignore` 不在 | `git rm --cached` + `.gitignore` 追加 | `build\`, `dist\`, `models\`, `wheels\*.whl`(要方針), `attic\` を除外 |

---

## 8. 未決事項（判断が必要なもの）

1. **CUDA Toolkit 13.4 の導入**（決定済みの cu134 採用に伴う作業）。本マシンは v13.0/v13.1 までしか入っていない。v13.0 は cp310 系統の遺物整理まで残すか、mmcv 再ビルド後に削除するか。ドライバ 621.14 は 13.4 実行要件を満たす見込み（導入後に `nvidia-smi` と `torch.cuda.is_available()` で確認）。
2. **device の吸収方法**（§5 案A か 案B か）。
3. **flavor 3（arm64 CPU）の torch**。`+cpu` の win_arm64 wheel は 2.15.0 に存在しないため、
   - (a) `torch-2.15.0+cu134-cp315-cp315-win_arm64.whl` を **device=cpu で使う**（サイズは大きいが単一供給で済む。`wheels` は増えない）＝推奨、
   - (b) N1X で CPU-only ビルドを作る、
   - (c) flavor 3 を廃止し ARM は GPU 版のみにする。
   → N1X 側で実際に何を導入したのか（`uv.lock` と `torch.__version__`）を記録して決める。
4. **`opencv-python==4.14.0.94` に win_arm64 wheel が無い**（2026-11-19 実測で 0 件）。N1X 側が何を導入したか（別 version の `opencv-python`、`opencv-contrib-python`、自前ビルド）を `profiles\win11-arm64-*\uv.lock` から確定させ、amd64 側と同じ版に統一できるか判断する。
5. **モデル配布方法**: リリース zip に同梱（+1.8GB）/ 別 zip / `download_models.py`（sha256 付き）。4 flavor 共通の 1 份で回す前提で 1 方式に統一する。
6. **mmcv の再ビルドを 4 flavor 分やるか**。torch 2.15 統一により AMD64 の 2 本は再ビルド必須。方針案: AMD64 分は本マシンでビルド、ARM64 分は **N1X 側ビルド物を `wheels/win11-arm64-*/` に取り込み、PROVENANCE.md と SHA256 で管理**（同一の patch 版を両マシンで適用したことを記録で担保する）。
7. **`wheels/*.whl` を git に載せるか LFS か**。現状 33MB。torch 2.15 用の再ビルド 2 本＋ARM 2 本で 60〜90MB。git 履歴に binaries を置かない方針なら `dist\` 配布＋CI の artifact 保存に切り替える。
8. **`cli\procs\reading_reorder.py_old`** と `src\ndl_kotenseki_layout\models\ndl_kotenseki_layout_config.py`（v2 系）をリポジトリに残すか。

---

## 9. 作業順序（実施時の推奨・この文書では実施しない）

1. `profiles/flavors.toml` に §0.1 のピンを書き下ろす（**唯一の差分定義**）。
2. **CUDA Toolkit 13.4 を導入**（flavor 2 の mmcv 再ビルドに必須）。`vcvars` と `DISTUTILS_USE_SDK=1` の手順は現行 bat と同じでよい。
3. `stage_mmcv_py315.py` を `vendor\mmcv-patches\` に取り込み git 化する（現在 git 外＝唯一のコピーが scratch cache にある状態を解消）。local tag を `.3` に上げる。
4. 掃除（`.gitignore` 追加、`__pycache__` の git 除外、`mmcv\build\` 削除、cp310 系統と `.2` wheel の `attic\` 行き、モデルの二重保持解消）。
5. **flavor 2（cu134）を先に通す**: `uv sync --project profiles\win11-amd64-cu134` → mmcv `.3` 再ビルド → `verify.ps1`（`torch 2.15.0+cu134` / `mmcv 2.1.0+easykotenocr.3` / `box_iou_rotated` on GPU）→ OCR 実行。ここで torch 2.15 への移行自体を検証する。
6. flavor 1（cpu）: mmcv を torch 2.15.0+cpu に対してビルド（nvcc 不要）→ 検証。
7. flavor 4（arm64 cu135）: N1X の wheel・lock・SHA256 を取り込み、§4-4 の PROVENANCE を記入 → 記録ベースで合否判定。
8. flavor 3（arm64 cpu）: §8-③ を決定して同じ手順で埋める。
9. `make_release.ps1` で 4 zip を作り、`installer\02_install.bat` の flavor 自動判定（`PROCESSOR_ARCHITECTURE` と CUDA 可否）を通す。

---

## 10. 決定記録

| 日付 | 決定 | 影響 |
|---|---|---|
| 2026-11-19 | ARM64 の torch は **NVIDIA 公式（`pypi.nvidia.com/nvtorch_oot/`）** を使用。Release 3・4 は RTX Spark N1X 上でビルド・mmcv 2.1.0 wheel 化・動作確認済み | ARM 系の供給不安が消え、arm64 の 2 flavor は「N1X 成果物の取り込み＋記録」で運用できる |
| 2026-11-19 | **torch 2.15.0 で統一**、GPU amd64 の CUDA variant は **cu134** | flavor 2 の id が `win11-amd64-cu130` → **`win11-amd64-cu134`**。cu130 は使わない（2.15.0 が存在しない）。CUDA Toolkit 13.4 の導入が前提条件になる |
| 同上（導出） | torchvision は **0.29.2** で統一（`py3-none-*` タグ） | 0.29.1 には cp315 wheel が無いので、pyproject の `0.29.1+cu130` は変更必須 |
| 同上（導出） | mmcv local tag を **`.3`** に上げる | 4 flavor 分の再ビルド／移植 wheel の取り込みが必要。`.2` は `attic\` へ |
| 2026-11-19 | flavor 2（cu134）を **別 venv で構築・検証**（対比用に残す） | 既存の `.venv`（torch 2.14.1+cu130）は無傷。新環境は `build\win11-amd64-cu134\venv` |
| 2026-11-19 | ARM の **cv2 は N1X で自前ビルド済み**を配布物に含める | PyPI に win_arm64 wheel が無い（4 系統すべて確認）。`wheels\win11-arm64-*\` のローカル wheel + pyproject の path 参照 + PROVENANCE 記録が必須になる |
| 2026-11-19 | ARM の mmcv **local tag は N1X の実ファイル名を正**にする | `flavors.toml` の ARM 系 `mmcv_wheel` は仮置き。実名が来たら更新（check_wheels.py が不一致を指摘する） |
| 2026-11-19/20 | **4 プロジェクト統合の開始**（本 PC = N1X 側で実施）。AMD 統合リポジトリを `C:\easykotenocr` にコピー済み。ARM 2 flavor を本リポジトリへ統合 | 詳細は §14 |
| 同上 | ARM の cv2 は **純 Python の cv2 シム（`cv2_shim/`）** を採用（N1X 自前ビルド wheel ではない） | PyPI に win_arm64 wheel が無いのは §12 と同じ。シムは arch 非依存なので 2 ARM flavor で共用（AMD flavor は本物の opencv-python を維持） |
| 同上 | ARM の mmcv wheel は **5 オペ除去して本 PC で再ビルド**（旧 N1X wheel は素の v2.1.0 由来で 5 オペを含むため、AMD 側のライセンス方針と整合させない） | local tag は `.3`。flavor ごとに専用 wheel（cu135 = CUDA、cu134 = CPU-only _ext）。「N1X の実ファイル名を正」は再ビルドにより解消 |
| 同上 | ARM flavor の wheel ビルドは **本 PC（ARM64）で実施**（AMD PC からは win_arm64 ビルド不可） | `vcvarsarm64.bat` + CUDA 13.5（nvcc V13.5.37）+ uv 管理 Python 3.15.2。`flavors.toml` の ARM 系 `cuda_home`/`vcvars`/`torch_cuda_arch_list`（12.1 = sm_121）を記入済み |
| 同上 | ARM CPU flavor（`win11-arm64-cpu`）の torch は **`2.15.0+cu134` + 実行時 device=cpu**（§8-③ の (a) 推奨をそのまま採用） | 旧 `easykotenocr_arm64_cpu` プロジェクト（Python 3.11 / torch 2.14.1+cpu）は統合レイアウト（全 flavor cp315 / torch 2.15 統一）と不一致のため **作り直し**。旧プロジェクトフォルダーは成果物の出所として温存 |
| 同上 | ARM profile は **vendor patch wheel（mmengine/mmpretrain .1）+ transformers 4.57.6** を使用（AMD profile と揃える） | patched mmpretrain で `mmpretrain.models` のフル import が成立すれば、旧 N1X 側の `config_v3.py` バックボーン限定 import と 4.55.2 ピンは不要（同一ソース方針の担保） |
| 同上 | ARM profile から **`datasets` を除外** | pyarrow に win_arm64 wheel が一切無い（2026-11-19 PyPI 実測 0 件）ため ARM では解決不能。アプリの infer 経路は不使用（学習用 `src/.../train.py` のみ） |
| 同上 | CPU flavor の mmcv wheel は **CPU-only _ext** で作る | GPU が見える CUDA-capable torch 環境では mmcv setup.py が CUDA 分岐に入るため、`build_wheels.ps1` が `device=cpu` の flavor で `CUDA_VISIBLE_DEVICES=` を空にし CPU 分岐へ落とす（AMD flavor 1 と同じ 1MB 級 wheel） |
| 2026-11-20 | **PyPI の cv2 供給が変化した**: `opencv-python-headless` 5.1.0.95 に win_arm64 wheel が出現。ただし **シム採用は維持**（旧 N1X 実証ランタイム＝シム単独・headless なし、との行動等価を優先） | シムを shadowing し得る **`albumentations` を ARM profile から除外**（infer 経路不使用・旧 N1X lock に存在せず）。`import cv2` → `cv2_shim/src/cv2`（4.12.0）を両 venv で実測確認 |
| 同上 | ARM profile に **`setuptools<81` を pin**（実解決 80.10.2） | mmcv のレガシー setup.py が `pkg_resources` を import するが setuptools>=81 で削除済み（AMD ビルド venv は 78.1.0 で回避できていた）。初回 cu135 ビルドが `ModuleNotFoundError: No module named 'pkg_resources'` で失敗し判明 |
| 同上 | `.ps1` は **UTF-8 BOM 付き**で維持（`build_wheels.ps1` を Python で書き換えた際 BOM を落とし、PS 5.1 が ANSI として読んで ParserError になった） | §14 の規約。ps1 をコードでパッチする場合は `utf-8-sig` で読み書きすること |

---

## 11. flavor 2（win11-amd64-cu134）構築結果（2026-11-19 実施）

`§9` の 1・2・3・5 にあたる部分を実際に実施した。結果は成功で、OCR 出力は旧環境と一致した。

### できたもの

| パス | 内容 |
|---|---|
| `profiles\flavors.toml` | 4 flavor の差分定義（単一ソース）。**UTF-8 BOM 付きだと tomllib が読めないので BOM なし**で作成。パーサ側も `utf-8-sig` で読むようにした |
| `profiles\win11-amd64-cu134\pyproject.toml` + `uv.lock` | flavor 専用の uv プロジェクト（torch/torchvision/mmcv のピンと index）。`.python-version` に **3.15.2 の絶対パス**を記載 |
| `build\win11-amd64-cu134\venv` | torch 2.15.0+cu134 / torchvision 0.29.2+cu134 / mmcv .3 が入った flavor venv（`UV_PROJECT_ENVIRONMENT` で指定） |
| `vendor\mmcv-patches\stage_mmcv.py` | 5 オペ除外 + local tag のステージング。**以前は scratch cache にしか無かった**ものを git 管理下に |
| `scripts\flavor_info.py` | `flavors.toml` を読むヘルパ（PowerShell に TOML パーサが無いための受け口。BOM 許容） |
| `scripts\build_wheels.ps1` | `-Flavor <id>` 駆動の wheel ビルド（staging → setup.py 差替 → vcvars/CUDA → `wheels\<flavor>\` → SHA256 表示） |
| `scripts\verify_env.py` | `-Flavor <id>` の環境検査（版アサート、`mmcv._ext`、CUDA 上 `box_iou_rotated`） |
| `wheels\win11-amd64-cu134\mmcv-2.1.0+easykotenocr.3-cp315-cp315-win_amd64.whl` | 21.9MB。sha256 とツールチェーンは同フォルダーの `PROVENANCE.md` |

### 検証結果

- `scripts\verify_env.py --flavor win11-amd64-cu134` → **exit 0**（torch 2.15.0+cu134 / cuda 13.4 / RTX 5090 sm_120、mmcv 2.1.0+easykotenocr.3、`box_iou_rotated` GPU 実行 0.3333）
- `main.py infer c:/ocr/in c:/ocr/out-cu134 -a -s b` → 4 ページ完走・exit 0・平均 1.15 秒/画像
- 生成された `.txt` は旧環境（torch 2.14.1+cu130、`c:\ocr\out\2026-11-18_080641`）と **バイト一致**

### ビルドで出た 2 つの環境依存（flavor 3・4 でも効く可能性が高い／詳細は `wheels\win11-amd64-cu134\PROVENANCE.md`）

1. `TORCH_DONT_CHECK_COMPILER_ABI=1` が必要。VS Build Tools 14.4x は cl の usage バナーを **UTF-8 の日本語**で出し、torch 2.15 の ABI チェックが Python 3.15 の `oem` コーデック（cp932）でそれを復号できず `UnicodeDecodeError` で死ぬ。`VSLANG=1033` は効かなかった。
2. CUDA 13.x の CCCL は MSVC の新プリプロセッサを要求する → cl に `/Zc:preprocessor`、nvcc に `-Xcompiler /Zc:preprocessor`（`scripts\mmcv_setup_py315.py` に追加済み）。N1X 側（CUDA 13.5）でも同じ扱いになっているか確認すること。

### flavor 1（win11-amd64-cpu）も同じ日に構築・検証完了

- `profiles\win11-amd64-cpu\{pyproject.toml, uv.lock, .python-version}` と `build\win11-amd64-cpu\venv`
  （**torch 2.15.0+cpu / torchvision 0.29.2+cpu**、Python 3.15.2）
- `wheels\win11-amd64-cpu\mmcv-2.1.0+easykotenocr.3-cp315-cp315-win_amd64.whl`（1.0MB、`_ext` は CPU ops のみ）。
  出所と sha256 は同フォルダーの `PROVENANCE.md`
- `config\config.cpu.yml`（`config.yml` との違いは `device: cpu` の 2 箇所だけ）を追加。
  実行は `main.py infer ... -c config/config.cpu.yml`（§5 の**案B**で運用してみる形）
- `verify_env.py --flavor win11-amd64-cpu` → exit 0。`nms` / `box_iou_rotated` / `deform_conv2d` を CPU で実行確認
- OCR 実走: 4 ページ完走・exit 0・**12.14 秒/画像**（cu134 GPU 版は 1.15 秒/画像 ≒ 10.6 倍差）

**重要な caveat: CPU 版と GPU 版の出力は完全一致しない**（`wheels\win11-amd64-cpu\PROVENANCE.md` に表あり）

- 行数（レイアウト分割）は 4 ページとも一致、bbox は 77 本中 73 本が一致・残りも 1px 以内
- 認識テキストは 77 行中 2 行が 1 文字単位で異なる（trocr の CPU/CUDA カーネル差＝浮動小数の揺れ）
- したがって **リリース間の回帰テストの期待値は flavor ごとに取る**（または許容差を設ける）こと。
  なお cu134 版（torch 2.15.0）と旧環境（torch 2.14.1+cu130）の GPU 出力はバイト一致だった

### まだやっていないこと

- ARM 2 flavor の N1X 成果物取り込みと `PROVENANCE.md` 記入（SHA256 含む）
- `§7` の掃除（`mmcv\build\` 削除、`.gitignore`、`__pycache__` の git 除外、モデルの二重保持、`wheels\common\` への集約）
- ルート `pyproject.toml` と `start_ocr.bat` の整理（bat は `mmcv 2.1.0+easykotenocr.2` / `torch 2.14.1+cu130` を今もアサートしている。flavor 化したら `verify_env.py` に置き換える）
- `make_release.ps1` と `installer\02_install.bat` の flavor 自動判定

---

## 12. ARM 2 flavor の受け皿（2026-11-19 設置）

N1X（RTX Spark / DGX Spark）側の成果物を受け取るための受け皿を置いた。

| 追加したもの | 用途 |
|---|---|
| `profiles\win11-arm64-cpu\pyproject.toml` + `.python-version` | 雛形。`uv.lock` は**意図的に無し**（この PC では win_arm64 の供給を実解決できないため、N1X 側で生成して持ち戻る） |
| `profiles\win11-arm64-cu135\pyproject.toml` + `.python-version` | 同上 |
| `wheels\win11-arm64-cpu\PROVENANCE.md` / `wheels\win11-arm64-cu135\PROVENANCE.md` | 記入待ちのテンプレ（必要記入欄と、N1X 側で貼るコマンド入り） |
| `scripts\check_wheels.py` | flavor 定義と `wheels/` を突き合わせる検査。`--record` で `wheels\SHA256SUMS.txt` を生成 |
| `wheels\SHA256SUMS.txt` | 現存 6 本の SHA256 を記録（amd64 の `.3` 2 本＋共通 2 本＋遺物 2 本） |

`python scripts\check_wheels.py` の現状の出口は **問題件数 4 / exit 1**。内訳は ARM 2 flavor の
mmcv wheel 不足と `uv.lock` 不足で、N1X 成果物が揃えば 0 になる想定。検査内容は
存在確認・ファイル名タグ（arm64 flavor に `win_amd64` を置かない等）・SHA256 一致・
`profiles/<flavor>/{pyproject.toml, uv.lock}` の存在・flavor 専用 dir 外の wheel（共通/遺物の区別）。

### 供給ギャップ（2026-11-19 に PyPI を直接照会して確定）

| パッケージ | win_arm64 | 対応 |
|---|---|---|
| `torch` 2.15.0 | 公式 index は cp313 まで・CPU のみ。`+cpu` の win_arm64 は無し | NVIDIA `pypi.nvidia.com/nvtorch_oot/` の `+cu134` / `+cu135` を使用 |
| `torchvision` 0.29.2 | nvtorch_oot に `+cu134` / `+cu135`（`py3-none-win_arm64`）のみ | 同上 |
| `opencv-python` 4.14.0.94 | **win_arm64 wheel 無し**（contrib も同。win32 / win_amd64 のみ） | **純 Python の cv2 シム（`cv2_shim/`）を editable 参照**で採用。2026-11-20 時点では `opencv-python-headless` 5.1.0.95 に win_arm64 wheel が出たが、未検証の 5.x 系より旧 N1X 実証のシムを優先（§10 参照）。albumentations 除外でシムの shadowing を防止 |
| `scikit-image` 0.27.0rc1 | **cp315 win_arm64 あり** | pin はそのまま |

### local tag は N1X の実ファイル名を正にする（2026-11-19 決定）

`flavors.toml` の ARM 系 `mmcv_wheel` は**仮置き**で、N1X でビルド済みの実名に合わせて更新する
（amd64 の `.3` と揃える必要はない）。`check_wheels.py` が「不足」と「未登録 wheel」の両方で
指摘するので、更新の手掛かりになる。`win11-arm64-cpu` と `win11-arm64-cu135` は torch の ABI が
違うため、**同一 wheel 1 本を両 flavor で共用している場合は検証結果を必ず残す**こと
（amd64 側では `.2`/`.3` で ABI 違いによる張替えを実測済み）。

---

## 13. §7 の掃除の実施（2026-11-19）

実施したもの:

- `.gitignore` を作成・適用（`__pycache__/`、`*.pyc`、`.venv/`、`build/`、モデル実体
  `*.pth/*.pt/*.bin/*.safetensors/*.joblib`、`wheels/**/*.whl`、`attic/`）
- 追跡されていた `__pycache__/*.pyc` 19 本を `git rm --cached` で解除（ステージ状態）
- `mmcv\build\`（3.3 GB、cp310/cp314 の中間生成物）を削除
- `wheels\mmcv-...+easykotenocr.1-cp310-...whl`、`uv.lock.bak-py310`、`time.txt` を `attic\` へ
  （`attic\README.md` に理由を記載）
- `wheels\SHA256SUMS.txt` を再記録（5 本）

据え置き:

- `wheels\mmcv-...+easykotenocr.2-...whl` はルート `pyproject.toml` と対比用 `.venv` が参照しているため
  `attic\` へ移せない（§9 の flavor 化と同時に移動）
- `src\text_kotenseki_recognition\model-ver2.zip`（450 MB）の削除は判断待ち
- CUDA `v13.1` フォルダーはシステム側なのでこの PC で手動削除

**未コミット**（コミットは実施側の判断）。`git add -A -n` の dry run では **追加 53 / 削除登録 2** で、
モデル実体・wheel は 0 本。`mmcv\` は入れ子 git のため **git 管理しない**と決定し `.gitignore` に追加済み
（N1X 側で `git clone --depth 1 --branch v2.1.0 ...` で復元）。
