# HANDOVER-TO-AMD64 — mmcv package data 残骸除去 + AMD64 2 flavor 再ビルド

作成日: 2026-11-21 | 作成元: kotengawa (Windows 11 on ARM, N1X) | 受領: AMD64 PC
対象リポジトリ: `C:\easykotenocr`（フォルダー全体コピーで引き継ぎ済み）

---

## 1. 目的（1 分）

ライセンス上除外した 5 オペ（`upfirdn2d`, `fused_bias_leakyrelu`, `bias_act`,
`filtered_lrelu`, `conv2d_gradfix`。StyleGAN2 系カーネル）について、Python ラッパ・
C++ ラッパ・pybind 登録は既に `vendor/mmcv-patches/stage_mmcv.py` で除去済みだが、
**カーネルの生ソース（.cpp/.cu）が wheel に package data として同梱されたまま**
（ユーザー方針: 「残骸が同梱されるのは好ましくない。再ビルドを要しても削除する」）。

→ `stage_mmcv.py` を拡張して生ソースをステージング段階で削除し、**全 flavor を再ビルド**する。
- **AMD64 2 flavor**（`win11-amd64-cpu` / `win11-amd64-cu134`）: **この AMD64 PC で実施**（本書の主役）
- **ARM64 2 flavor**: kotengawa (N1X) 側で同じ `stage_mmcv.py` 変更を取り込んで再ビルド
- 排除済みオペが実行時に露出していないこと（ラッパ/pybind/コンパイル済み ext の 3 層）は
  N1X 側で実測済み（0 exposed）。本作業は「ソース実体の同梱除去」が目的。

## 2. 現状（2026-11-21 時点、ローカル main）

| コミット | 内容 |
|---|---|
| `1a9f50b` | ARM64 2 flavor 統合完了（mmcv wheel ビルド・検証・PROVENANCE 記録） |
| `f3ff99a` | README.md を 4-flavor uv ワークフローへ現行化 |
| `1e18464` | `profiles/*/.python-version` を `3.15.2` に修正 + 旧インストーラー BAT 2 本削除 |
| `f864bbb` | 旧 `EasyKoten/EasyKotenOcr-installer.zip` を git rm |

- **git push は未実施・要ユーザー承認**（コミットまでは可。push はユーザーが行う）。
- 4 flavor とも OCR 実走 OK（統合時の実測: amd64-cu134 約 1 秒/画像、amd64-cpu 約 12 秒、
  arm64-cu135 3.44 秒、arm64-cpu 51.67 秒）。
- `wheels/*.whl` 実体は git 管理外（gitignore）。`wheels/SHA256SUMS.txt`（7 件）は git 管理。
- mmcv ソースは `mmcv/`（v2.1.0、commit `57c4e25e` の公式 clone）をコピーに同梱済み。再 clone 不要。

## 3. 残骸の実測スキャン結果（2026-11-21、ARM64 wheel。AMD wheel も同一構造のはず）

wheel 内 package data の 5 オペ生ソース **8 ファイル**（`scripts/scan_wheel_ops.py` で再確認可）:

```
mmcv/ops/csrc/parrots/fused_bias_leakyrelu.cpp
mmcv/ops/csrc/parrots/upfirdn2d.cpp
mmcv/ops/csrc/parrots/upfirdn2d_parrots.cpp
mmcv/ops/csrc/pytorch/cuda/bias_act_cuda.cu
mmcv/ops/csrc/pytorch/cuda/filtered_lrelu.cu
mmcv/ops/csrc/pytorch/cuda/fused_bias_leakyrelu_cuda.cu
mmcv/ops/csrc/pytorch/cuda/upfirdn2d_kernel.cu
mmcv/ops/csrc/pytorch/npu/fused_bias_leakyrelu_npu.cpp
```

（参考）wheel 内には parrots フレームワーク関連がさらに 136 エントリあるが、これらは
**5 オペ以外全オペの通常同梱物**でライセンス対象外。今回の除去対象ではない（削減は別途判断）。

## 4. 実施手順（AMD64 PC）

### Step 0: 環境
- Windows 11 AMD64 / git / uv（Python 3.15.2 は uv が自動取得。`.python-version` は `3.15.2` に修正済み）
- VS Build Tools（C++）と CUDA 13.4（`nvcc`）。`win11-amd64-cu134` のビルドに必須
- venv が無ければ: `uv sync --project profiles\win11-amd64-cpu`（`UV_PROJECT_ENVIRONMENT=build\win11-amd64-cpu\venv`）。cu134 も同様に

### Step 1: `vendor/mmcv-patches/stage_mmcv.py` の拡張
`drop_excluded_ops()` に **生ソース削除**を追加する。
1. `EXCLUDED_CSRC_CPP` とは別に、`mmcv/ops/csrc/` からの相対パスリストを新設して削除:
   ```python
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
   ```
   ※ `mmcv/ops/csrc/pytorch/npu/` と `mmcv/ops/csrc/parrots/` を実 `ls` して、他に
   5 オペ名を含むファイルがあれば同様に追加すること（NPU の upfirdn2d/bias_act は
   2.1.0 に存在しないことを N1X 側で確認済み）。
2. **重要（リンク切れ防止）**: `mmcv/ops/csrc/pytorch/cuda/cudabind.cpp` は CUDA ビルドで
   **コンパイルされる**（`scripts/mmcv_setup_py315.py` の CUDA 分岐が
   `glob('.../pytorch/cuda/*.cpp')` を含める）ため、中の 5 オペブロックを patch で除去しないと
   `*_op_impl` の未定義参照でリンクに落ちる。除去対象ブロック（N1X 実測の該当行付近）:
   - `fused_bias_leakyrelu_op` / `fused_bias_leakyrelu_op_impl` + `REGISTER_DEVICE_IMPL(...CUDA...)`（約 515 行〜）
   - `bias_act_op` / `bias_act_op_impl` + `REGISTER_DEVICE_IMPL`（約 527 行〜）
   - `filtered_lrelu_act_op` / `filtered_lrelu_act_op_impl` + `REGISTER_DEVICE_IMPL`（約 541 行〜）
   - `upfirdn2d_op` / `upfirdn2d_op_impl` + `REGISTER_DEVICE_IMPL`（`grep -n upfirdn2d` で位置確認）
   関数宣言・定義・REGISTER の 3 点セットをブロック丸ごと削除する `patch_cuda_cudabind()` を
   stage_mmcv.py に追加し、`main()` の `drop_excluded_ops()` の後で呼ぶこと。
3. （ライセンス hygiene）`mmcv/ops/csrc/parrots/cudabind.cpp` 内の同名ブロック
   （`fused_bias_leakyrelu` 約 484 行〜、`upfirdn2d` 約 1314 行〜）も除去対象。
   parrots 分岐は Windows ビルドでは使われないので**ビルドは壊れない**が、参照残りを消す目的で削除する。
4. ステージング後の自己チェックを stage_mmcv.py の最後に追加推奨:
   `mmcv/ops/csrc` 配下に 5 オペ名（`upfirdn2d|bias_act|fused_bias_leakyrelu|filtered_lrelu|conv2d_gradfix`）を
   含む**ファイル名**が残っていたら fail。

### Step 2: ステージング単体テスト
```
python vendor\mmcv-patches\stage_mmcv.py --src mmcv --dst build\staging-test --suffix easykotenocr.3
```
成功後、`build\staging-test` に上記 9 ファイルが無いこと・`grep -rn "upfirdn\|bias_act\|filtered_lrelu"` が
`cudabind.cpp` からヒットしないことを確認。

### Step 3: 再ビルド（2 flavor）
```
powershell -File scripts\build_wheels.ps1 -Flavor win11-amd64-cpu
powershell -File scripts\build_wheels.ps1 -Flavor win11-amd64-cu134
```
- `build_wheels.ps1` が stage → `scripts\mmcv_setup_py315.py` 差し替え → vcvars + CUDA → bdist_wheel →
  `wheels\<flavor>\` 配置まで行う。nvcc 落ちる場合は `-MaxJobs` を下げる（N1X では既定 4、メモリ逼迫環境）。
- バージョン suffix は **`easykotenocr.3` のまま据置き**でよい（ソース中身の変更であって
  インターフェース変更ではない）。上げる場合は build_wheels.ps1 の `-Suffix` 既定値・
  profile の pin・SHA256SUMS をセットで。

### Step 4: 検証（3 点セット、両 flavor）
1. **残骸スキャン**: `python scripts\scan_wheel_ops.py wheels\<flavor>\<wheel>.whl`
   → 5 オペ名ヒット **0 件**が合格（136 件の parrots は従来どおり存在してよい）
2. **環境検証**: 再ビルド wheel を venv に入れ直し → `python tools\apply_venv_patches.py`
   → `python scripts\verify_env.py` → `VERIFY OK`
3. **OCR 実走**: 前回統合時の検証に使ったサンプル画像で `main.py infer` を回し、
   出力 .txt が**既存出力と一致**すること（GPU flavor は device=cuda も確認）

### Step 5: 記録
- `python scripts\check_wheels.py --record`（AMD 2 件の SHA256 が更新される。
  ARM 2 件の SHA は N1X 再ビルド後に上書きされるため、**ARM wheel をこの PC で再スキャンしないこと**）
- `wheels\win11-amd64-cpu\PROVENANCE.md` / `win11-amd64-cu135` 相当の形式で
  再ビルド日時・環境（nvcc / MSVC / ninja バージョン・stage_mmcv の変更内容）を記録
- 本ファイル§7 の進捗表を更新してコミット

### Step 6: kotengawa (N1X) への返し
- `stage_mmcv.py` の変更をコミットした旨を連絡 → N1X 側が同じスクリプトで
  ARM64 2 flavor を再ビルドし、`check_wheels.py --record` で ARM 分の SHA を更新 →
  4 flavor 揃ったところで**ユーザー判断で push**（Agent は push しない）

## 5. 既知の落とし穴（AMD に関連するもの）

- `scripts\mmcv_setup_py315.py` の `op_files.remove('./mmcv/ops/csrc/pytorch/cuda/bias_act_cuda.cu')`
  （約 159 行）は **parrots Extension 分岐の中**なので通常ビルドでは実行されない。
  通常ビルドの glob は存在しないファイルを要求しないので、ファイル削除自体は glob を壊さない。
  ただし parrots ビルドを将来使うことがあれば、削除した `.remove()` 対象が無く ValueError になる点だけ留意。
- CPU ビルド分岐（`pytorch/*.cpp + cpu/*.cpp`）は stage 済みのツリーでは 5 オペ分が既に無く、
  そのまま通る（ARM CPU flavor で実証済み）。
- **venv を作り直したら必ず `tools\apply_venv_patches.py`**（torch 2.15 の weights_only 問題対策）。
- PowerShell スクリプトは **UTF-8 BOM 付き**を保つ（BOM 消失で日本語コメントが文字化けして構文エラーになる）。
- `build/`・`wheels/*.whl` はコミットしない（gitignore 済み）。SHA256SUMS.txt はコミットする。
- **git push は行わないこと**（ユーザー承認事項）。

## 6. 参考ドキュメント

- `HANDOVER.md` — 元 AMD64 PC → N1X への引継ぎ（ビルド系の詳細の一次資料）
- `HANDOFF-N1X.md` — N1X での ARM64 統合の記録（§0.1c/§0.1d が直近）
- `RELEASE_LAYOUT.md` — 4-flavor 配布レイアウト設計
- `scripts/README.md` — ステージングスクリプトの適用内容説明
- skill `windows-arm64-pytorch-port` — ARM 側の再現手順（AMD には不要な話が多い）

## 7. 進捗管理表

| # | 項目 | 担当 | 状態 |
|---|---|---|---|
| 1 | stage_mmcv.py 拡張（EXCLUDED_CSRC_EXTRA + cudabind patch） | AMD64 PC | ☐ 未着手 |
| 2 | ステージング単体テスト（Step 2） | AMD64 PC | ☐ |
| 3 | win11-amd64-cpu 再ビルド + 検証 3 点 | AMD64 PC | ☐ |
| 4 | win11-amd64-cu134 再ビルド + 検証 3 点 | AMD64 PC | ☐ |
| 5 | SHA256SUMS 更新（AMD 分）+ PROVENANCE + コミット | AMD64 PC | ☐ |
| 6 | win11-arm64-cpu 再ビルド + 検証 | kotengawa (N1X) | ☐ AMD 変更待ち |
| 7 | win11-arm64-cu135 再ビルド + 検証 | kotengawa (N1X) | ☐ AMD 変更待ち |
| 8 | SHA256SUMS 更新（ARM 分）+ PROVENANCE + コミット | kotengawa (N1X) | ☐ |
| 9 | push | ユーザー | ☐ 4 flavor 揃ってから判断 |
