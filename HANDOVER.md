# EasyKotenOCR ポート作業 業務引継ぎ資料

作成日: 2026-11-19（JST）
作成環境: Windows 11 / AMD64（x64）、Python 3.15.2、torch 2.15.0+cu134
引き継ぎ先: **NVIDIA RTX Spark（DGX Spark）N1X（Windows on ARM, ARM64）**

---

## 0. この資料の位置づけと、読むべき関連文書

| 文書 | 内容 |
|---|---|
| **本資料（`HANDOVER.md`）** | 方針・実施済みの作業・気づいた問題点・未決事項・次の手順の**総まとめ**。まずここを読む |
| `RELEASE_LAYOUT.md` | ファイル配置計画の本体（flavor 定義、ツリー構成、wheels 規則、未決事項、決定記録、§11 の amd64 2 flavor 構築結果、§12 の ARM 受け皿） |
| `HANDOFF-N1X.md` | ARM 2 flavor の成果物を N1X から受け取るための**運用手順書**（採取コマンド付き） |
| `wheels/*/PROVENANCE.md` | 各 wheel のビルド出所記録（sha256・ツールチェーン・環境回避）。`win11-amd64-*` は記入済、`win11-arm64-*` は**記入待ちテンプレ** |
| `scripts/README.md` | ベンダー patch wheel（mmengine / mmpretrain / mmcv）を作った理由と再構築手順 |
| `wheels/SHA256SUMS.txt` | 現存 wheel 6 本の SHA256（`scripts/check_wheels.py --record` で生成） |

---

## 1. なぜ N1X に移すのか（引き継ぎの理由）

- この PC は CPU が **AMD64（x64）** なので、**ARM64 のバイナリを実行できない**。
  arm64 向けにビルドした mmcv・cv2・torch を import して動かす検証が原理的にできない。
- Release 3・4（win11 on arm / ARM64）の検証は **N1X 上でしか成立しない**。
  N1X 側ではすでにビルド・動作確認・mmcv の wheel 化まで完了している（本人確認済み）。
- したがって今後は **N1X を開発機**として進める。この PC で完了した amd64 部分の成果物と
  方針・記録だけを N1X に持ち込む。

**持ち込むもの / 持ち込まないもの**

| 持ち込む | 持ち込まない（この PC 用の残骸） |
|---|---|
| `scripts/`（7 本）、`profiles/`（5 flavor 分）、`vendor/mmcv-patches/stage_mmcv.py`、`config/config.cpu.yml`、`RELEASE_LAYOUT.md`、`HANDOFF-N1X.md`、本資料、`wheels/*.whl` と `PROVENANCE.md` と `SHA256SUMS.txt` | `build/`（**8.9 GB**：amd64 用 venv と staging）、`.venv/`（amd64 専用）、`mmcv/build/`（**3.3 GB**）、`__pycache__/`（**.pyc が git 追跡済み**）、`uv.lock.bak-py310`、`time.txt` |
| `mmcv/`（v2.1.0 の checkout、`57c4e25e` / tag `v2.1.0`） | `src/text_kotenseki_recognition/model-ver2.zip`（**450 MB、解凍済み 489 MB と重複**） |
| モデル実体: `src/ndl_kotenseki_layout/models`（970 MB）、`src/text_kotenseki_recognition/model-ver2`（489 MB） | テスト画像 `c:\ocr\in`（4 ページ）は容量が小さいので持ち込み推奨。`c:\ocr\out*` は期待値の基準として **`out-cu134` だけ**残す |

---

## 2. プロジェクト概要とリリース 4 種

古典籍 OCR「easykotenocr」（レイアウト検出 mmdet + 認識 TrOCR + 読解順）を
**Python 3.15 / PyTorch 2.15 系**へ移植し、4 種類のリリースを作る。

| flavor id | 対象 | torch | CUDA | 現状 |
|---|---|---|---|---|
| `win11-amd64-cpu` | Release 1 | 2.15.0+cpu | なし | **この PC で構築・検証完了** |
| `win11-amd64-cu134` | Release 2 | 2.15.0+cu134 | 13.4 | **この PC で構築・検証完了** |
| `win11-arm64-cpu` | Release 3 | 2.15.0+cu134（実行時 device=cpu） | なし運用 | N1X で動作確認済み。**成果物の取り込み待ち** |
| `win11-arm64-cu135` | Release 4 | 2.15.0+cu135 | 13.5 | N1X で動作確認済み。**成果物の取り込み待ち** |

---

## 3. 基本方針（変更しないこと）

### 3.1 「極力同一ソース」を守る 4 層

アプリの Python ソースは flavor で作り分けない。差分は次の 4 層で吸収する。

1. **config**（`config.yml` と `config/config.cpu.yml`）: device 等の実行時差
2. **wheel**（`wheels/<flavor>/`）: ABI が違うもの（mmcv・cv2）は flavor 専用の binary
3. **profiles**（`profiles/<flavor>/pyproject.toml` + `uv.lock`）: 依存解決と pin の差
4. **patch**（`vendor/mmcv-patches/`、`scripts/mmcv_setup_py315.py`）: ベンダーソースへの介入

### 3.2 uv プロジェクトは flavor ごとに薄く分ける

`uv.lock` は同一パッケージの local version（`+cpu` / `+cu134` / `+cu135`）を**併存させられない**。
そのため flavor ごとに薄い uv プロジェクトを作り、それぞれ別 lock を持つ。
アプリ本体（`main.py` 等）は path 参照しない（依存定義だけのプロジェクト）。

### 3.3 差分の単一ソースは `profiles/flavors.toml`

flavor の arch / python / torch pin / index / device / CUDA_HOME / TORCH_CUDA_ARCH_LIST /
vcvars / mmcv wheel パスを一箇所に置く。スクリプトはここを読む
（`scripts/flavor_info.py` が PowerShell 向けの受け口）。**flavor 用にスクリプトを増やさない**。

---

## 4. ファイル配置計画（目標）と現状

```
easykotenocr/
  main.py, cli/, src/                     ... アプリ本体（flavor 差なし。改修は config.yml と bat のみ）
  config.yml                              ... デフォルト（device: cuda:0）
  config/config.cpu.yml                   ... CPU flavor 用 override（device: cpu の 2 箇所だけ）
  profiles/flavors.toml                   ... 4 flavor の差分定義（単一ソース）
  profiles/<flavor>/pyproject.toml+uv.lock ... flavor 専用の依存解決
  wheels/                                 ... 共通純 Python wheel + flavor 専用の binary wheel
    SHA256SUMS.txt                        ... check_wheels.py --record が生成
    <flavor>/*.whl + PROVENANCE.md         ... flavor 専用 binary と出所記録
  vendor/mmcv-patches/stage_mmcv.py       ... mmcv ステージング（5 オペ除外 + local tag）
  scripts/                                ... flavor_info / build_wheels.ps1 / verify_env / check_wheels /
                                             mmcv_setup_py315.py / build_vendor_wheels.py
  build/<flavor>/{venv,staging,logs}      ... ローカル作業用（git 管理しない・持ち込まない）
  mmcv/                                   ... mmcv v2.1.0 checkout（ビルド元）
```

### 4.1 掃除の実施状況（2026-11-19 に実施）

| 項目 | 状態 |
|---|---|
| `.gitignore` の作成 | **実施**（appendix A の内容で適用。`__pycache__/`、`*.pyc`、`.venv/`、`build/`、モデル実体 `*.pth/*.pt/*.bin/*.safetensors/*.joblib`、`wheels/**/*.whl`、`attic/`） |
| `__pycache__/*.pyc` の git 追跡 | **解除**（19 本を `git rm --cached`。ステージ状態。ファイル自体はディスク上に残っている） |
| `build/`（8.9 GB）と `mmcv\build\`（3.3 GB）の git 除外 | `build/` は ignore、**`mmcv\build\` は実削除済み**（cp310・cp314 の中間生成物の残骸で、wheel は `wheels/` に保存ずみ） |
| 旧 wheel の `attic\` 行き | `.1`（cp310）は `attic\wheels\` へ移動。**`.2` は `wheels\` に残置**（ルート pyproject と対比用 `.venv` が今も参照しているため。§10-⑥ の flavor 化で移動できる） |
| `uv.lock.bak-py310` / `time.txt` | `attic\` へ移動 |
| `wheels\SHA256SUMS.txt` | 再記録（**5 本**。`.1` が抜けた） |
| `src/text_kotenseki_recognition/model-ver2.zip`（450 MB）の二重保持 | **未実施**（削除は判断待ち。git には入らない） |
| CUDA `v13.1` フォルダー（nvcc の無い残骸） | **未実施**（システムのフォルダーなのでこの PC で手動削除） |
| 大きな binary を git に載せるか Git LFS か | **未決**（§9-④。当面は全部除外し、モデル config 類だけが git に入る状態） |
| `mmcv/`（入れ子 git）の扱い | **決定・適用済み**: git に入れない（`.gitignore` に `mmcv/`）。N1X で tag `v2.1.0` を再 clone（§8.1） |

---

## 5. これまでに実施した作業

### 5.1 ベンダー patch wheel の作成（2026-11-18、この PC）

| wheel | 元 | なぜ local が必要か |
|---|---|---|
| `mmpretrain-1.2.0+easykotenocr.1` | PyPI sdist 1.2.0 | transformers 4.57 で消えたシンボル（`apply_chunking_to_forward` 等）を import して `PreTrainedModel=None` 落ち。新しい mmpretrain が出ていない。transformers を下げようにも 4.55 以下は tokenizers<0.22 で cp315 wheel が無い |
| `mmengine-0.10.7+easykotenocr.1` | PyPI sdist 0.10.7 | `mmcv_full_available()` が `pkgutil.find_loader`（Python 3.12 で削除）を使う。0.11.0rc3 でも未修正 |
| 両者の setup.py | 同上 | `exec()` + `locals()` での版解析が Python 3.13 以降で動かない。ビルドに setuptools が必要（`--no-build-isolation`） |

再現: `python scripts/build_vendor_wheels.py`（冪等）。詳細は `scripts/README.md`。

### 5.2 mmcv のソース patch 化と wheel 化

元ソースは `mmcv/` の **v2.1.0（commit `57c4e25e`）** checkout。そこから

1. `vendor/mmcv-patches/stage_mmcv.py`（`--suffix easykotenocr.N`）で staging にコピーし、
   **5 オペを除外**（Python wrapper・csrc ソース・pybind 登録・import のすべてを除去）:
   `upfirdn2d`, `fused_bias_leakyrelu`, `bias_act`, `filtered_lrelu`, `conv2d_gradfix`
   （StyleGAN2 系で kernel ソースに別ライセンスが付くため。**レビューなしに復活させない**）
2. `scripts/mmcv_setup_py315.py` で setup.py を差し替え
   （`get_version()` の exec globals 修正、torch>=2.9 向けの `USE_CUDA=1` マクロ、
   torch>=2.14 ヘッダが `std::strong_ordering` を使うため **C++20**、
   CUDA 13.x の CCCL 向けに **`/Zc:preprocessor`**）
3. vcvars64 + CUDA を効かせた cmd バッチで `setup.py bdist_wheel`
   （必須 env: `DISTUTILS_USE_SDK=1`, `MMCV_WITH_OPS=1`, `CUDA_HOME`, `TORCH_CUDA_ARCH_LIST`,
   `USE_NINJA=1`, `VSLANG=1033`, **`TORCH_DONT_CHECK_COMPILER_ABI=1`**）

local tag と ABI の対応（**torch が違えば必ず再ビルド**）:

| local tag | Python | Against torch | platform | 場所 | 状態 |
|---|---|---|---|---|---|
| `.1` | cp310 | （旧 Python 3.10 構成） | win_amd64 | `wheels/` | 遺物。`attic\` 行き |
| `.2` | cp315 | **2.14.1+cu130** | win_amd64 | `wheels/` | 対比用 `.venv` で使用中。`.3` へ置換後 `attic\` |
| `.3` | cp315 | **2.15.0+cu134** | win_amd64 | `wheels/win11-amd64-cu134/` | 検証済み |
| `.3` | cp315 | **2.15.0+cpu** | win_amd64 | `wheels/win11-amd64-cpu/` | 検証済み |
| 未定 | cp315 | arm64 側（cu134 / cu135） | **win_arm64** | `wheels/win11-arm64-*/` | **N1X の実ファイル名を正として取り込み** |

### 5.3 flavor 2（`win11-amd64-cu134`）構築と検証（2026-11-19）

- CUDA Toolkit **13.4** を導入（nvcc release 13.4 V13.4.92）。cu130 では torch 2.15.0 が供給されないため、
  **torch 2.15 統一のために cu134 へ切り替え**た（flavor id も `win11-amd64-cu130` → `cu134`）
- `profiles/win11-amd64-cu134/{pyproject.toml, uv.lock, .python-version}` を作成し、
  `UV_PROJECT_ENVIRONMENT=build/win11-amd64-cu134/venv` で `uv sync`
- mmcv `.3` をビルド（21.9 MB、sha256 `78c1b3a5…`、ログ `build/win11-amd64-cu134/logs/`）
- `scripts/verify_env.py --flavor win11-amd64-cu134` → **exit 0**
  （torch 2.15.0+cu134 / cuda 13.4 / RTX 5090 sm_120、mmcv 2.1.0+easykotenocr.3、
  `mmcv._ext` import、CUDA 上 `box_iou_rotated` = 0.3333、mmdet/mmpretrain/mmengine import）
- OCR 実走: `main.py infer c:/ocr/in c:/ocr/out-cu134 -a -s b` → 4 ページ完走、exit 0、**1.15 秒/画像**
- **生成テキストは旧環境（torch 2.14.1+cu130）の実行結果とバイト一致**

### 5.4 flavor 1（`win11-amd64-cpu`）構築と検証（同日）

- `profiles/win11-amd64-cpu/…` を作成、`uv sync` → torch **2.15.0+cpu** / torchvision **0.29.2+cpu**
- mmcv `.3` を CPU 版としてビルド（1.0 MB、`Compiling mmcv._ext only with CPU`、sha256 `e4159d32…`）
  ※ 小さいのは fatbin が無いだけで欠損ではない（オブジェクト 73 個・LTCG でリンク）
- CPU ops 実効確認: `nms`（order [0,1,2]）、`box_iou_rotated`（GPU と同値 0.3333）、`deform_conv2d`（(1,8,6,6)）
- device はソースを変えず `config/config.cpu.yml`（`device: cpu` の 2 箇所だけ）で吸収して実行
  → 4 ページ完走、exit 0、**12.14 秒/画像**（GPU の約 10.6 倍）

### 5.5 CPU 版と GPU 版の出力差（重要・定量済み）

`c:\ocr\out-cpu`（torch 2.15.0+cpu）対 `c:\ocr\out-cu134`（torch 2.15.0+cu134）:

| ページ | 行数（CPU/GPU） | bbox 完全一致 | bbox 最大差 | テキスト差異行 |
|---|---|---|---|---|
| 01_leric1-1 | 21 / 21 | 19 | 1px | 0 |
| 02_leric1-2 | 19 / 19 | 18 | 1px | 1 |
| 03_leric1-3 | 19 / 19 | 18 | 1px | 1 |
| 04_leric1-4a | 18 / 18 | 18 | 0px | 0 |
| **合計** | **77 / 77** | **73/77** | **1px** | **2 行**（1 文字単位の差） |

→ **CPU 版と GPU 版の出力は完全一致しない**。回帰テストの期待値は flavor ごとに取る
（または許容差を設ける）こと。レイアウト分割（行数）は一致。

### 5.6 ARM 2 flavor の受け皿設置（同日）

- `profiles/win11-arm64-cpu/` と `profiles/win11-arm64-cu135/` の pyproject 雛形
  （**`uv.lock` はあえて生成していない**：この PC では win_arm64 の供給を実解決できないため、N1X で生成して持ち込む）
- `wheels/win11-arm64-{cpu,cu135}/PROVENANCE.md`（記入待ちテンプレ。mmcv と **cv2** の記録欄）
- `scripts/check_wheels.py`（flavor 定義と `wheels/` の突き合わせ検査。`--record` で `SHA256SUMS.txt` 生成）
- `HANDOFF-N1X.md`（受け渡し手順と採取コマンド）
- `wheels/SHA256SUMS.txt` を生成（6 本）

現在の検査結果は **問題件数 4 / exit 1**（ARM の mmcv wheel 2 本 + `uv.lock` 2 個の不足）。
成果物が揃えば 0 になる。

---

## 6. 環境回避として確立したもの（N1X でも効く可能性が高い）

1. **`TORCH_DONT_CHECK_COMPILER_ABI=1`**
   現行の VS Build Tools（14.4x）は `cl` の usage バナーを **UTF-8 の日本語**で出力する。
   torch 2.15 の `cpp_extension._check_abi()` は `subprocess.check_output(compiler)` の結果を
   Python 3.15 の `oem` コーデック（この PC では OEM CP=932）で復号しようとし、
   `UnicodeDecodeError: 'cp1' codec can't decode bytes` で死ぬ（`VSLANG=1033` は効かなかった）。
   ABI チェックは警告を出すだけなので無効化した（torch 公式 wheel + VS2022 は ABI 互換）。
2. **`/Zc:preprocessor`（cl）／`-Xcompiler /Zc:preprocessor`（nvcc）**
   CUDA 13.x の CCCL ヘッダ `cuda/std/__cccl/preprocessor.h` が MSVC の新プリプロセッサを要求し、
   でないと `fatal error C1189`（実測: `active_rotated_filter_cuda.cu` で発生）。
   `scripts/mmcv_setup_py315.py` に追加済み。CUDA 13.5 の N1X でも同じ手当が必要か確認すること。
3. **CUDA minor は flavor 変数**（amd64 = 13.4、arm64 GPU = 13.5）。`CUDA_HOME` は
   flavors.toml に書き、セッションの PATH を信じない（インストール後のセッション PATH は古い版を指していた）。

---

## 7. PyPI / 供給まわりで判明した制約（2026-11-19 に PyPI を直接照会して確定）

| 対象 | 事実 | 対応 |
|---|---|---|
| `torch` 2.15.0 | 公式 index に `2.15.0+cu134`（cp315, win_amd64）と `+cpu` あり。**cu130 の win_amd64 は 2.14.1 まで**。win_arm64 は cp313 まで・CPU のみ。`+cpu` の win_arm64（2.15 系）は**供給無し**（PyPI の torch 2.15.0 にも win_arm64 ファイル無し） | amd64: `download.pytorch.org/whl/{cpu,cu134}`。arm64: **NVIDIA `pypi.nvidia.com/nvtorch_oot/`** |
| `torchvision` | **0.29.0 / 0.29.1 に cp315 wheel が無い**。0.29.2 は `py3-none-win_amd64 / win_arm64` タグ（`+cpu`, `+cu134`, nvtorch の `+cu134`/`+cu135`） | **0.29.2 で統一** |
| `opencv-python` 4.14.0.94 | Windows wheel は **win32 と win_amd64 のみ**。contrib / headless / contrib-headless も同様。**win_arm64 は PyPI に一切無い** | **N1X で自前ビルド済み**。wheel 本体 + `cv2.getBuildInformation()` を配布物に含め、pyproject では path 参照（`HANDOFF-N1X.md` §3） |
| `scikit-image` | **0.27.0rc1 に cp315 win_arm64 あり**（0.26.0 には cp315 が無い） | pin は `0.27.0rc1` のまま。rc 依存である点は供給リスクとして §9-⑤ |
| `mmcv` | cp315 + torch 2.14/2.15 向けの公式 wheel 無し | 全 flavor で自前ビルド（local tag 付き） |
| mmengine / mmpretrain | cp315 で動く公式版が無い（§5.1） | local patch wheel `.1` |

---

## 8. この PC のリポジトリ状態（2026-11-19 の掃除後・コミット前）

- branch: `main`。コミット履歴は GitHub アップロード由来（`Add files via upload` が多い）
- **コミットはまだ**（意図的に未実施）。`git add -A -n`（dry run）で **追加 53 ファイル / 削除登録 2**（`EasyKoten/fix_packages/{fcn_mask_head,utils}.py`）。内訳は
  `src/`（15: モデルの config・vocab 類のみ）・`profiles/`（11）・`scripts/`（8）・`wheels/`（5: PROVENANCE と SHA256SUMS）・
  `vendor/`・`config/`・`EasyKoten/`（2）・3 つの md 資料・`.gitignore`・ルート `pyproject.toml`/`uv.lock`/`.python-version`・bat 2 本
- **モデル実体と wheel は 1 つも追加対象に入らない**（dry run で 0 本を確認済み）。`build/`・`.venv/`・`mmcv/` も除外
- 追加予定の `src/` は trocr の tokenizer / preprocessor の json・vocab だけで、
  weights（.bin 415 MB / .pt 71 MB / .pth 970 MB）は除外。この線引きは §9-⑥ の決定で変わり得る
- 変更（アプリ側はごく少数）: `config.yml`（`device: cpu` → `cuda:0` の 2 行）、
  `start_ocr.bat`（版アサートを追加）、`EasyKoten/01_install_Prerequisite.bat`、
  `EasyKoten/02_install EasyKotenOCR.bat`、`EasyKoten/fix_packages/{fcn_mask_head,utils}.py` を**削除**
  （cp310 時代の当てパッチ。削除が意図どおりか要確認）
- `__pycache__/*.pyc` 19 本は **`git rm --cached` で追跡解除済み（ステージ状態）**。
  ディスク上には残っているので、コミットしても動作には影響しない
- アプリの Python コード自体は**未改修**（差分は config と bat のみ）。「同一ソース」方針の担保なので維持する

### 8.1 `mmcv/` は入れ子の git リポジトリ — **git に入れず N1X で再 clone（2026-11-19 決定・適用済み）**

`mmcv/` は **v2.1.0（commit `57c4e25e`）の checkout で、自前の `.git` を持つ**。
`git add` すると gitlink（submodule もどき）として 1 エントリだけ入り、
**クローン先では中身が空**になる。

- **決定**: git 管理対象にしない。`.gitignore` に `mmcv/` を追加済み（`git check-ignore -v` で確認、`git status` にも出ない）
- **N1X 側の復元コマンド**（同じ commit を必ず確認すること）:

```powershell
git clone --depth 1 --branch v2.1.0 https://github.com/open-mmlab/mmcv.git mmcv
git -C mmcv rev-parse --short HEAD      # 57c4e25e と一致すれば同じソース
```

- この PC の `mmcv\` はそのまま残してある（再 clone 不要）。**パッチは `mmcv/` に直接入れず、
  `stage_mmcv.py` で staging にコピーしてから適用する**運用なので、checkout は無傷のまま保つこと
- 別解（不採用）: proper submodule 化 / zip で物理移送

### 8.2 N1X へ運ぶ手順（推奨）

```powershell
# 1) この PC でコミット（.gitignore は適用済み）
git add -A
git commit -m "Add flavor-based build profiles, wheel provenance, and migration docs"

# 2) コードは bundle かリモートで運ぶ
git bundle create ..\easykotenocr-handover.bundle --all

# 3) 大きな実体は git と別に運ぶ
#    wheels\*.whl（47 MB: flavor 専用の .3 を 2 本 + 共通 2 本 + 対比用の .2）
#    src\ndl_kotenseki_layout\models（970 MB）と src\text_kotenseki_recognition\model-ver2（489 MB）
#    運ばない: build\（8.9 GB）、.venv\（3.8 GB）、.venv-py310.bak\（3.4 GB）、attic\、__pycache__\、model-ver2.zip
```

### 8.3 フォルダーごとコピーする場合（17.7 GB → 約 2.1 GB に縮める）

`C:\easykotenocr` 直下をそのままコピーすると 17.7 GB になる。うち **16 GB はこの PC 専用の残骸**なので除外する。

| 除外するもの | サイズ | 理由 |
|---|---|---|
| `build\` | 8.9 GB | amd64 用の venv・staging・ログ。ARM64 では使えないので N1X で作り直す |
| `.venv\` | 3.8 GB | amd64 専用の対比用環境 |
| `.venv-py310.bak\` | 3.4 GB | Python 3.10 時代の venv のバックアップ。参照しているものはない（削除の最終判断は実施側） |
| `__pycache__\` | 2888 ディレクトリ | 実行で再生成される。アーキテクチャもバージョンも違う環境に持っていく意味がない |
| `src\text_kotenseki_recognition\model-ver2.zip` | 450 MB | 解凍済みの `model-ver2\`（489 MB）がある。二重 |

```powershell
# 例: 除外つきコピー（宛先は既存ディレクトリに合わせること）
robocopy C:\easykotenocr D:\easykotenocr /MIR /XD .venv .venv-py310.bak build __pycache__ /XF model-ver2.zip /MT:16
```

コピーで届くが git には入らない実体: `mmcv\`（83 MB。物理コピーで届くので **N1X での再 clone は不要**。`git -C mmcv rev-parse --short HEAD` が `57c4e25e` であることを確認）、`wheels\*.whl`、モデル実体。

**コピー後に N1X 側で書き換えが必要になる絶対パス**（この PC の値が焼き込まれている）:

| ファイル | 箇所 |
|---|---|
| `profiles/flavors.toml` | `cuda_home`（v13.4 → N1X の 13.5 の実パス）、`vcvars`（ARM64 ビルドに合うもの。VS の版でファイル名が違うので N1X で確認） |
| `profiles/win11-amd64-cpu/.python-version` | `C:\Users\gesho\AppData\Local\Programs\Python\Python3152\python.exe` |
| `profiles/win11-amd64-cu134/.python-version` | 同上（ARM 2 flavor は `3.15` のままなので変更不要） |

venv はコピーせず、N1X 側で `uv sync --project profiles\<flavor>` で作り直す（`UV_PROJECT_ENVIRONMENT=build\<flavor>\venv`）。
`c:\ocr\` はリポジトリ外なので**別に運ぶ**（`in\` の 4 ページと、期待値の基準 `out-cu134\`）。

---

## 9. 未決事項（誰かが判断する必要があるもの）

1. **device の吸収方法**（CPU flavor）
   - 案A（現行運用）: `config/config.cpu.yml` のような override を渡す。アプリ無改修。**動作確認済み**
   - 案B: `device: auto` を解釈する小改修を入れて config を 1 本に寄せる。配布は単純化するがアプリ改修が必要
2. **ARM の CPU flavor の torch**（`+cpu` win_arm64 が存在しない）— **N1X 側で決定済み（2026-11-20）**:
   `torch==2.15.0+cu134`（nvtorch_oot）＋実行時 device=cpu を採用（旧 CPU プロジェクト Python 3.11 系は
   統合レイアウトと不一致のため作り直し）。mmcv は **flavor ごとに専用 wheel**（共用しない＝保守的に分離）
3. **mmcv の local tag 名前** — **N1X の実ファイル名を正**とする決定済み。`flavors.toml` の ARM 系は仮置き
4. **wheel とモデルの git 方針**（Git LFS / 配布 zip / 別リポジート）
   - `wheels/` 56 MB（うち遺物 30 MB）、モデル 1.46 GB、モデル zip 450 MB
5. **`scikit-image==0.27.0rc1` の rc 依存**を許容するか（供給が止まれば ARM で入手不能になる）
6. **モデル配布方式**（リポジトリ同梱 / インストーラー内のダウンロード）
7. **CPU 版と GPU 版で結果が一致しない前提のテスト設計**（§5.5）
8. **N1X で amd64 版を再ビルドできるか**（ARM64 ホストからの x64 ビルド。vcvars のクロス構成に依存）。
   現状 amd64 wheel はこの PC でビルド済みなので、当面は持ち込みで回避可能

---

## 10. 未実施タスク（優先度つき）

| 優先 | タスク | 手掛かり |
|---|---|---|
| ① | **N1X へ環境を移す**（§8 の持ち込み手順、§1 の表） | git 未追跡のコミット、`build/` 等は除外 |
| ② | **ARM 成果物の取り込み**（mmcv wheel 2 本・cv2 wheel・`uv.lock` 2 個・freeze・PROVENANCE 記入） | `HANDOFF-N1X.md`。取込後に `check_wheels.py --record` → `check_wheels.py` が問題件数 0 |
| ③ | **ARM flavor の実機検証**（`verify_env.py` と OCR 実走を N1X で実行し、結果と速度を記録） | `verify_env.py --flavor win11-arm64-cu135` / `--flavor win11-arm64-cpu` |
| ④ | **§7 の掃除** — **概ね実施済み**（`.gitignore` 作成、`__pycache__` 19 本を untrack、`mmcv\build\` 削除、`.1` と作業残骸を `attic\` へ、SHA256 再記録）。**残り**: `.2` wheel の `attic\` 行き（⑥ まで待機）、`model-ver2.zip` の二重保持、CUDA `v13.1` 残骸の削除 | `HANDOVER.md` §4.1 |
| ⑤ | **`make_release.ps1`**（flavor 指定で `dist/<flavor>/` の zip を作る）と **`installer\02_install.bat`** の flavor 自動判定（`PROCESSOR_ARCHITECTURE` と CUDA 可否） | `RELEASE_LAYOUT.md` §9 |
| ⑥ | **ルート `pyproject.toml` / `start_ocr.bat` の flavor 化** | bat は現在 `mmcv 2.1.0+easykotenocr.2` / `torch 2.14.1+cu130` を**ハードコードでアサート**している。`scripts/verify_env.py` 呼び出しに置換すべき |
| ⑦ | 判断が必要なもの（§9）の決定と `RELEASE_LAYOUT.md` §10 への記録 | 決定記録表が各項目の日付つきで継続中 |

---

## 11. 再現コマンド集（リファレンス）

```powershell
# --- flavor venv の作成（flavor 専用の uv プロジェクト）---
$env:UV_PROJECT_ENVIRONMENT = 'C:\easykotenocr\build\win11-amd64-cu134\venv'
uv sync --project C:\easykotenocr\profiles\win11-amd64-cu134     # mmcv はビルド後に有効化するので2段階

# --- mmcv wheel のビルド（flavors.toml 駆動。staging → setup.py 差替 → wheels\<flavor>\）---
& C:\easykotenocr\scripts\build_wheels.ps1 -Flavor win11-amd64-cu134 -Suffix easykotenocr.3
#   -SkipStage を付けるとステージングだけを飛ばす（setup.py のパッチだけ変えて再ビルドする運用）

# --- 環境検証（版アサート、mmcv._ext、CUDA 上 box_iou_rotated）---
& C:\easykotenocr\build\win11-amd64-cu134\venv\Scripts\python.exe C:\easykotenocr\scripts\verify_env.py --flavor win11-amd64-cu134

# --- OCR 実走 ---
$env:TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD='1'
& <venv python> C:\easykotenocr\main.py infer c:/ocr/in c:/ocr/out-cu134 -a -s b
& <venv python> C:\easykotenocr\main.py infer c:/ocr/in c:/ocr/out-cpu -a -s b -c config/config.cpu.yml

# --- wheels の整合性検査（N1X 側でも同じものを使う）---
python C:\easykotenocr\scripts\check_wheels.py --record
python C:\easykotenocr\scripts\check_wheels.py
```

ビルドに必要な環境変数（`build_wheels.ps1` が flavors.toml と併せて設定する）:
`DISTUTILS_USE_SDK=1`, `MMCV_WITH_OPS=1`, `CUDA_HOME`, `TORCH_CUDA_ARCH_LIST`（amd64: `7.5;8.0;8.6;9.0;10.0;12.0`）,
`USE_NINJA=1`, `VSLANG=1033`, `TORCH_DONT_CHECK_COMPILER_ABI=1`。

---

## 12. wheel のハッシュと実測サイズ（2026-11-19 に再記録、`wheels/SHA256SUMS.txt` = 5 本）

```
ad41840dd4cf26ddb418e3cdd4aa7274b921a2a678367f3d4a70870b6767d45c  mmcv-2.1.0+easykotenocr.2-cp315-cp315-win_amd64.whl   （対比用。attic 行きは §10-⑥ 後）
24f173b7a1470d9d2ecda956acd9978e504dc7f5d709a3e8b00df385d25bc2a7  mmengine-0.10.7+easykotenocr.1-py3-none-any.whl       （共通）
cb7f0b80c612229614ab88b44a045e36e0fafe6498a96ac51e247310ec9fc0c2  mmpretrain-1.2.0+easykotenocr.1-py2.py3-none-any.whl  （共通）
e4159d324c5cc041dd3008c32775ca4bbd16b99d18004966ea74ddcb1b52cb4a  win11-amd64-cpu/mmcv-2.1.0+easykotenocr.3-…           （1.0 MB）
78c1b3a5e08a02d8cc2ccffd0383f5bc740e63eea9b1daf34bad597e903419f9  win11-amd64-cu134/mmcv-2.1.0+easykotenocr.3-…        （21.9 MB）

attic\wheels\mmcv-2.1.0+easykotenocr.1-cp310-cp310-win_amd64.whl（cp310 遺物。2026-11-19 に移動。参考ハッシュ）
7c41a758b58b7f0ebac4ee51ab9e8c1c402349aa76824f8179b3a6a118bea1e9
```

---

## 13. この PC の環境スナップショット（比較・再現用）

| 項目 | 値 |
|---|---|
| OS / arch | Windows 11 / AMD64 |
| GPU / driver | NVIDIA GeForce RTX 5090（sm_120）/ driver 621.14 |
| CUDA | Toolkit 13.4（nvcc release 13.4, V13.4.92）。`CUDA_PATH` は v13.4。**v13.1 は nvcc の無い残骸**、v13.0 は現存 |
| MSVC | VS Build Tools 2022、14.44.35207（vcvars64） |
| Python | 3.15.2（`C:\Users\gesho\AppData\Local\Programs\Python\Python3152`）。uv 管理の 3.15.0b1 と混同注意 |
| uv | 0.11.15 |
| ninja | `C:\Python314\Scripts\ninja.exe`（PATH 依存。flavor venv には無い） |
| 対比用 venv | ルート `.venv` = torch 2.14.1+cu130 / mmcv +easykotenocr.2 / py3.15.2（**壊さず残す**） |
| flavor venv | `build\win11-amd64-cu134\venv`、`build\win11-amd64-cpu\venv` |
| テストデータ | `c:\ocr\in`（4 ページ）。期待値の基準は `c:\ocr\out-cu134`（旧 cu130 実行とバイト一致）、`c:\ocr\out-cpu`（2 行差）、`c:\ocr\out`（旧 cu130） |

---

## 14. 作業時の注意（壊しやすいもの）

- **除外した 5 オペを復活させない**（ライセンス上の判断。`stage_mmcv.py` と PROVENANCE に理由を書いてある）
- **PowerShell スクリプト（`.ps1`）は UTF-8 BOM 付き**。BOM 無しだと PS 5.1 が ANSI として読み日本語が壊れる。
  逆に **TOML / YAML / MD は BOM 無し**（`tomllib` が BOM 付き TOML を弾く。パーサ側は `utf-8-sig` で読むようにしてある）
- `mmcv_setup_py315.py` は `torch>=2.14` 条件で C++20 を足しているので、torch を上げても条件式を見直す必要がない
- `build_wheels.ps1` は `-SkipStage` でも setup.py を必ず差し替える（パッチだけ直して再ビルドする運用があるため）
- `start_ocr.bat` の版アサートは**古い値のまま**。更新しないと誤った環境検査になる（§10-⑥）
- `config.yml` の `kotenseki_reading_order.checkpoint_path` は**使われていない死んだ設定**
  （`InferencerWithCLI` は config を読まない）。device も `config.yml` の 2 箇所だけが効く
- `TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1` は現状必須（`torch.load` の `weights_only` 既定変更のため）
- venv を uv に自動で作らせると **3.15.0b1** を選ぶことがある（pyyaml のビルドが 0xc0000005 で落ちた）。
  `.python-version` に 3.15.2 の**絶対パス**を書くこと

---

## appendix A. `.gitignore`（2026-11-19 に**適用済み**。実際の除外範囲）

```gitignore
__pycache__/
*.pyc
*.egg-info/
.pytest_cache/
.venv/
build/                      # flavor 専用の build\<flavor>\{venv,staging,logs} も一緒に除外
src/**/*.pth
src/**/*.zip
*.pth                       # layout 970 MB
*.pt                        # trocr 71 MB
*.bin                       # trocr 415 MB
*.safetensors
*.joblib
*.onnx
wheels/*.whl
wheels/**/*.whl
attic/
uv.lock.bak-py310
time.txt
```

- 適用は `git check-ignore -v` で確認済み（`__pycache__/x.pyc`、`build/...`、`wheels/**/*.whl`、
  `attic/...`、`src/**/*.pth` がそれぞれ該当ルールで除外される）
- **既に追跡されているファイルは .gitignore では消えない**。`__pycache__` の 19 本は `git rm --cached` で解除した
- `EasyKoten/EasyKotenOcr-installer.zip` は過去から**追跡されたまま**（意図的か要確認）
- `mmcv/` を追加済み（§8.1 の決定により、入れ子 git は git 管理しない）

## appendix B. N1X で用意しておくもの（チェックリスト）

- [ ] VS Build Tools 2022（ARM64、できれば x64 クロスも）と CUDA 13.5 の nvcc
- [ ] `flavors.toml` の ARM 系に `vcvars`（ARM64 用）と `cuda_home` を記入
- [ ] `.python-version` を N1X の 3.15.x の実パスに差し替え
- [ ] mmcv ビルド済み wheel と cv2 自前ビルド wheel の在り処（`Get-ChildItem -Recurse -Filter '*win_arm64*.whl'`）
- [ ] `uv lock` を ARM flavor で実行して lock を生成
- [ ] `verify_env.py` と OCR 実走の実行結果（速度と出力）を PROVENANCE に記録
- [ ] `check_wheels.py --record` → `check_wheels.py` が問題件数 0
