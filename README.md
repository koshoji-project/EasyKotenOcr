# Easy古典OCR(ver.2)

古典籍をテキスト化するためのOCRアプリケーションです。 
本プログラムは、国立国会図書館の[NDLラボ](https://lab.ndl.go.jp)が公開している[NDL古典籍OCR_cli ver.3](https://github.com/ndl-lab/ndlkotenocr_cli)を基に、DockerやLinuxに関する知識がないユーザーでも利用できるように改変を加えたものです。


本プログラムに適用するライセンスは、CC BY 4.0です。ライセンス詳細は[LICENSE](./LICENSE)をご覧ください。

## リリース情報

**Easy古典OCR ver.2.1**（2026年11月22日 リリース）

| 項目 | 内容 |
|---|---|
| 対応環境 | **Windows 11 のみ**（AMD64 / ARM64 × CPU / NVIDIA GPU）の4フレーバー |
| インストール | 「セットアップ.bat」をダブルクリックするだけ（git・uv・Python の導入はセットアップが自動で行います） |
| 実行基盤 | Python 3.15.2 / PyTorch 2.15 |
| 同梱 mmcv ホイール | `2.1.0+easykotenocr.3`（フレーバー別ビルド。セットアップが自動で入手します） |

### 変更履歴

**ver.2.1（2026-11-22）**
- ワンクリックインストーラーを追加。配布zip内の「**セットアップ.bat**」をダブルクリックするだけで、git・uv・Python 3.15.2・実行環境・ビルド済みホイール・学習済みモデルのすべてが自動で入るようにした（**コマンドプロンプトは一切不要**）
- インストーラーは日本語GUI（PowerShell + WinForms、OS標準のみで動作・追加ダウンロードなし）で、PCの構成を見てフレーバーを自動判定。途中で失敗しても「セットアップ.bat」を再実行すれば続きから再開できる（冪等）
- ビルド済みホイール（mmcv / mmengine / mmpretrain）を GitHub Releases の **`v2.1.0`** アセット（単一 zip `wheels-built-v2.1.0.zip`）からオンラインダウンロードする方式に変更。**インストールにはインターネット接続が必要です**
- 環境変数の恒久的な変更を一切行わない方式に変更（PCの他のPython環境に影響しません）
- OS判定をWMI基準に修正（ARM64マシンでの誤判定を解消）
- Windows 11 のみ対応（Windows 10 は対象外）

**ver.2（2026-11-21）**
- Windows on ARM64（Snapdragon Xシリーズ等）に対応。`win11-arm64-cpu` と、RTX Spark / DGX Spark クラスの NVIDIA GPU を使う `win11-arm64-cu135` を追加し、AMD64 の CPU/GPU と合わせて **4フレーバー構成**とした
- ビルド済みホイール（`wheels\`）をフレーバー別に同梱する配布形態に変更し、**Visual Studio Build Tools や CUDA Toolkit を自分でインストールせずに**インストールできるようにした
- インストールを **uv ベース**に変更（Python 3.15.2 / PyTorch 2.15 統一）。旧 `EasyKotenOcr-installer.zip`（Python 3.10系）は廃止
- `start_ocr.bat` が起動時にフレーバーを自動判定し、仮想環境の自己修正（`tools\apply_venv_patches.py`）と環境検証（`scripts\verify_env.py`）を自動実行するようにした
- ビルド時にライセンス上除外した演算子（upfirdn2d、fused_bias_leakyrelu、bias_act、filtered_lrelu、conv2d_gradfix）を、Pythonラッパー・コンパイル対象・ホイール内同梱ソースのすべてから完全に除去した

**ver.1**
- Docker ベースの NDL古典籍OCR_cli を Windows Native 環境で動作するように改変（WSL / Hyper-V 不要）
- CPU のみでの OCR 処理に対応
- OCR 実行用バッチファイル、文字列認識結果の画像出力オプション、シンプルな入出力フォルダー構成を追加

## インストール

> **この手順どおりに進めれば完了します。コマンドの入力は一切不要です。**
> 前提: Windows 11 のPC、インターネット接続、ディスク空き容量 **15GB以上**（GPUフレーバーは約12GBの実行環境が入ります）。

### ステップ1: 配布zipをダウンロードして解凍する

配布ページの [**`EasyKotenSetup-v2.1.0.zip`**](https://github.com/koshoji-project/EasyKotenOcr/releases/download/v2.1.0/EasyKotenSetup-v2.1.0.zip) をダウンロードし、任意の場所（ダブルクリックでもOK）で解凍してください。中身は「**セットアップ.bat**」1つと説明書だけです。

### ステップ2: 「セットアップ.bat」をダブルクリックする

「セットアップ」の画面が開きます。

- 「**Windows の PC が保護しました**」という青い画面が出ることがあります。その場合は「**その他のオプション**」をクリック →「**実行します**」を選択してください（プログラムは安全ですが、ダウンロードしたファイルだとWindowsが確認を出します）。

### ステップ3: 画面の案内にしたがう

1. **使うPCの種類**（CPUのみ / NVIDIA GPUあり）をたずねられます。迷ったら「**CPUのみ**」で構いません（GPUがあってもあとで自動的に切り替えられます）。
2. **インストール先フォルダー**をたずねられます。特別な理由がなければ **`C:\easykotenocr`** のまま「インストールを実行」を押してください。
3. もらうディスク容量の確認を押すと、インストールが始まります。

**所要時間の目安: 30〜90分**（インターネットの速度や、ダウンロードする大きさによります。GPUフレーバーは数GBをダウンロードします）。画面が止まっているように見えても、ログファイル（インストールフォルダー内の `install.log`）で進んでいます。**ウィンドウを閉じずにそのまま置いてください。**

### インストールが終わったら

1. デスクトップに「**Easy古典OCR**」というアイコンができます
2. 読み取りたい画像をフォルダー **`c:\ocr\in`** に入れます
3. 「Easy古典OCR」アイコンをダブルクリックすると、OCRが実行され、`c:\ocr\out-<お使いのPCの種類>` フォルダー（例: `c:\ocr\out-win11-amd64-cpu`）にテキストが出力されます

### うまくいかないとき

- **もう一度「セットアップ.bat」をダブルクリックしてください。** できた部分は再利用され、続きからやり直します（何度も実行して問題ありません）。
- それでも失敗する場合は、画面に出るエラー表示と、インストールフォルダー内の **`install.log`**（セットアップ画面の「ログを開く」ボタンから開けます）をご用意して問い合わせてください。
- セキュリティソフトや会社のPC管理ソフトがダウンロードをブロックすることがあります。その場合は `install.log` に記録されます。

### アップデート（新しいバージョンが出たとき）

新しい配布zipをダウンロードして「セットアップ.bat」を実行し、前回と同じインストール先フォルダーを指定すると、プログラムの本体がそのバージョンに更新されます。`c:\ocr\in` の入力データや出力は影響を受けませんが、**インストールフォルダー内の `config.yml` など設定ファイルを手動で編集したことがある場合は、アップデートで初期状態に戻ることがあります。** その場合は事前に設定ファイルをコピーしてバックアップしてから実行してください。

### アンインストール（削除）方法

本プログラムはレジストリに何も書き込まないため、次の手順で完全に削除できます。

1. デスクトップの「**Easy古典OCR**」アイコンを削除します
2. インストールフォルダー（既定では **`C:\easykotenocr`**）を削除します
3. OCRの入出力フォルダー（**`C:\ocr`**）も削除しても構いません（中のデータも消えます）
4. このPCでEasy古典OCR以外にuvを使っていない場合は、次のフォルダーも削除すると約3〜10GBのディスク容量が空きます（uvが管理するPythonとダウンロードキャッシュです）
   - `C:\Users\<ユーザー名>\.local\bin`（uv本体）
   - `C:\Users\<ユーザー名>\AppData\Roaming\uv`（uv管理のPythonとキャッシュ）

## OCRの実行

`start_ocr.bat`（またはデスクトップの「Easy古典OCR」アイコン）をダブルクリックして実行してください。PCの構成（CPUアーキテクチャとNVIDIA GPUの有無）を見て、使うフレーバーを自動的に選びます。

- 入力フォルダー: `c:\ocr\in`、出力フォルダー: `c:\ocr\out-<フレーバーID>`、実行時オプションは `-s b -a` が指定されています。必要に応じて書き換えてください。
- フレーバーを明示することもできます: `start_ocr.bat win11-amd64-cu134`
- CPUフレーバーでは `config\config.cpu.yml`（device: cpu）が自動で使われます。GPUフレーバーは `config.yml` を使います。

実行の目安（テスト画像4ページ、1ページあたり。PC構成により変動します）:

| フレーバー | 1ページあたり |
|---|---|
| win11-amd64-cu134（RTX GPU） | 約1秒 |
| win11-amd64-cpu | 約12秒 |
| win11-arm64-cu135（RTX Spark） | 約3秒 |
| win11-arm64-cpu | 約50秒 |

**注意**: GPUとCPUでは浮動小数点演算の差分により、認識結果が一部異なることがあります。

## BATファイルが実行する処理の内容

`start_ocr.bat` は次の処理を行います。

1. `PROCESSOR_ARCHITECTURE` と `nvidia-smi` の成否から、使うフレーバーを自動判定する（明示指定も可）。
2. `build\<フレーバーID>\venv` の仮想環境を確認する（無ければ作成手順を表示して終了）。
3. `tools\apply_venv_patches.py` を実行して、仮想環境内のパッケージに必要な修正を適用する。
4. `scripts\verify_env.py` で環境を検証する。
5. `main.py infer` を起動する（引数なしの場合は `c:\ocr\in` → `c:\ocr\out-<フレーバーID>` を標準処理）。

## 改変の内容
1. Dockerを用いた仮想化技術を使用せずに、Windows Native 環境上で動作するようにしました。WSLやHyper-Vも不要です。
2. GPUを用いずにCPUのみを使用してOCR処理を行うようにしました。処理速度は落ちますが、NVIDIA製のGPUを搭載していないPCでも動作可能になりました。
3. AMD64 と Windows on ARM の両対応とし、さらに GPU 有無を含む4通りのフレーバー構成としました。mmcv などの必須パッケージは各フレーバー用にビルド済みホイールとして配布し、Visual Studio Build Tools 不要でインストールできるようにしました。
4. uv を使うことで、Python のバージョン違いによる環境の破壊を防いでいます。
5. コマンドラインの入力が苦手な方向けに、OCRを実行するためのバッチファイルを用意しました。
6. OCR実行時のオプションとして文字列認識結果を画像ファイルとして出力する機能を追加しました。
7. 入出力フォルダーの構成を判りやすくシンプルにしました。
8. ver.2.1 で、コマンド操作不要のワンクリックインストーラー（「セットアップ.bat」＋日本語GUI）を追加しました。

## 環境構築後のフォルダー構成（参考）
```
EasyKotenOCR
├── build : フレーバー別のPython仮想環境が入るフォルダー（uvが作成）
│   └── win11-amd64-cu134\venv : 各フレーバーの仮想環境
├── cli : CLIコマンド的に利用するPythonスクリプトの格納されたフォルダー
├── cv2_shim : 仮想環境用に同梱した opencv パッケージの差し替え用フォルダー
├── easykoten_installer : インストーラー開発一式（セットアップ.bat・setup スクリプト群・配布zip / ホイールzip の生成スクリプト）が格納されたフォルダー
├── profiles : フレーバー別の依存パッケージ定義（uv用プロファイル）
│   ├── win11-amd64-cpu
│   ├── win11-amd64-cu134
│   ├── win11-arm64-cpu
│   └── win11-arm64-cu135
├── scripts : 環境検証（verify_env.py）等が格納されたフォルダー
├── src : 各推論処理のソースコード用フォルダー
│   ├── ndl_kotenseki_layout : レイアウト抽出処理のソースコードの格納されたフォルダー
│   ├── reading_order：読み順整序処理のソースコードの格納されたフォルダー
│   └── text_kotenseki_recognition : 文字認識処理のソースコードの格納されたフォルダー
├── tools : 仮想環境への修正適用スクリプト（apply_venv_patches.py）が格納されたフォルダー
├── vendor : mmcv のビルド用パッチ等が格納されたフォルダー
├── wheels : ビルド済みホイール（セットアップが GitHub Releases から入手する）
├── config : CPUフレーバー用の推論設定ファイルのフォルダー
│   └── config.cpu.yml : device: cpu 用設定
├── config.yml : サンプルの推論設定ファイル（GPU用）
├── LICENSE : CC 4.0のライセンスファイル
├── main.py : メインとなるPythonスクリプト
├── README.md : このファイル
└── start_ocr.bat : main.pyを起動するためのバッチファイル（フレーバー自動判定）
```


### 推論処理の実行
input_rootフォルダーの直下に画像ファイルがある場合、
```
input_root/  (ユーザー指定)
 ├── 岩舩山真名縁起_page01.jpg
 ├── 岩舩山真名縁起_page02.jpg
 ・・・
 └── 岩舩山真名縁起_page07.jpg
```
以下のコマンドで実行することができます（`<フレーバーID>` は自分のものに読み替えてください）。
```
build\<フレーバーID>\venv\Scripts\python.exe main.py infer input_root output_dir -a
```

実行後の出力例は次の通りです。

```
output_dir/  (ユーザー指定)
 └── YYYY-MM-DD_HHMMSS (タイムスタンプ)
      ├── opt.json
      ├── 岩舩山真名縁起_page01.txt
      ├── 岩舩山真名縁起_page01.jpg
      ├── 岩舩山真名縁起_page01.json
       ...
      ├── 岩舩山真名縁起_page07.txt
      ├── 岩舩山真名縁起_page07.jpg
      └── 岩舩山真名縁起_page07.json
 
```


重みファイルのパス等、各モジュールで利用する設定値は`config.yml`の内容を修正することで変更することができます。

### オプションについて

#### 入力形式オプション
実行時に
-s b を指定することで、次の入力形式のフォルダ構造を処理できます。

例：
```
python main.py infer input_root output_dir -s b -a
```

入力形式
```
input_root/  (ユーザー指定)
 ├── 01_岩舩山縁起絵巻_第一巻 (文書毎のサブフォルダ名)
 │   ├── 詞書_page01.jpg
 │   ├── 詞書_page02.jpg
 	・・・
 │   └── 詞書_page10.jpg
 └── 02_開帳差免帳_第一冊 (文書毎のサブフォルダ名)
     ├── 01_延享元年_下野國_岩舩山高勝寺.jpg
     ├── 02_寛保三年_下野國_醫王寺.jpg
     ・・・
     └── 10_延享元年_勢州_白子山観音寺.jpg
```
出力形式
```
output_root/ (ユーザー指定)
 └── YYYY-MM-DD_HHMMSS (タイムスタンプ)
      ├── opt.json
      ├── 01_岩舩山縁起絵巻_第一巻 (文書毎のサブフォルダ名)
      │   ├── 詞書_page01.txt
      │   ├── 詞書_page01.jpg
      │   ├── 詞書_page01.json
      │   ├── 詞書_page02.txt
      │   ├── 詞書_page02.jpg
      │   ├── 詞書_page02.json
      │    ...
      │   ├── 詞書_page10.txt
      │   ├── 詞書_page10.jpg
      │   └── 詞書_page10.json
      └── 02_開帳差免帳_第一冊 (文書毎のサブフォルダ名)
          ├──  01_延享元年_下野國_岩舩山高勝寺.txt
          └── ...

```

#### 画像サイズ出力オプション
実行時に
-a を指定することで、出力jsonに画像サイズ情報を追加します。

例：
```
python main.py infer input_root output_dir -a
```

**注意**
このオプションを有効化すると出力jsonの形式が以下の構造になります。
```
{
  "contents":[
    (各文字列矩形の座標、認識文字列等)
  ],
  "imginfo": {
    "img_width": (元画像の幅),
    "img_height": (元画像の高さ),
    "img_path":（元画像のフォルダーパス）,
    "img_name":（元画像名）
  }
}
```

#### オプション情報の保存
出力フォルダーでは、実行時に指定したオプション情報が`opt.json`に保存されています。

---

## 【上級者向け】手動でのインストール手順

> 通常のユーザーは上の「インストール」（セットアップ.bat）を使ってください。この節は、コマンド操作ができる方向けの手動手順です（セットアップ.batが失敗したときの原因切り分けにも使えます）。

2026年11月の統合作業により、本リポジトリは **4つの環境（フレーバー）** に対応しました。古い `EasyKotenOcr-installer.zip`（Python 3.10 系の旧インストーラー）は**現在の構成では動作しないため使用しないでください**。

### ステップ1: ご自分のPCに合うフレーバーを選ぶ

| フレーバーID | 該当するPC | GPU加速 |
|---|---|---|
| `win11-amd64-cpu` | Windows 11（64ビット / Intel・AMD製CPU）、NVIDIA GPUなし | なし |
| `win11-amd64-cu134` | Windows 11（64ビット）＋ NVIDIA GPU（CUDA 13.4 対応ドライバ入り） | あり |
| `win11-arm64-cpu` | Windows 11 on ARM（Snapdragon等）、NVIDIA GPUなし | なし |
| `win11-arm64-cu135` | Windows 11 on ARM ＋ NVIDIA GPU（RTX Spark / DGX Spark クラス、CUDA 13.5） | あり |

- GPUを使うフレーバーでは、NVIDIA公式の**最新版のグラフィックドライバ**を先にインストールしてください（CUDA 13.4 / 13.5 対応版）。CUDA Toolkit や Visual Studio Build Tools を自分で入れる必要はありません。
- 迷ったら一般的なPCは `win11-amd64-cpu`、ARM PCは `win11-arm64-cpu` を選んでください。NVIDIA GPUが載っている場合は対応する cu 付きフレーバーが大幅に高速です。

### ステップ2: 前提ソフトを入れる

| ソフト | 導入方法 |
|---|---|
| git | [git-scm.com](https://git-scm.com/downloads/win) からダウンロードしてインストール |
| uv | コマンドプロンプトで `winget install --id astral-sh.uv` |

**uv は必ず最新版を使ってください。** 同梱するロックファイルは新しい形式（revision 5）で書かれており、古い uv では読み込めずインストールに失敗します。すでに uv が入っている場合は `uv self update` で更新してから進めてください（uv が古いというエラーが出た場合も、まず `uv self update` を試してください）。

Python 3.15.2 は uv が自動的にダウンロードして使うため、Python を手動でインストールする必要はありません。

### ステップ3: プログラム本体を入手する

Gitリポジトリには、専用の mmcv 等のビルド済みホイール（`wheels\`）と学習済みモデルの実体は含まれていません。

1. リポジトリをクローン（または Releases の `v2.1.0` ソースをダウンロード）し、任意のフォルダー（例: `C:\easykotenocr`）に展開してください。
2. GitHub Releases の `v2.1.0` アセットから **`wheels-built-v2.1.0.zip`** をダウンロードし、**クローン先フォルダーの直下（リポジトリルート）に展開**して `wheels\` を作成してください。
3. `wheels\SHA256SUMS.txt` にしたがって全ホイールの SHA256 を検証してください（Windows なら `Get-FileHash` を使うとよいでしょう。1つでも不一致・欠損があれば、そのzipをダウンロードし直してください）。

`wheels\` にはフレーバー専用の mmcv ホイール（`wheels\win11-<フレーバー>\`）と mmengine / mmpretrain のホイールが入っています。PyTorch などのその他のパッケージは、次のステップの `uv sync` がインターネット上の公式リポジトリ（PyTorch 公式 / NVIDIA / PyPI）から取得します。

### ステップ4: 実行環境を作る

コマンドプロンプトを開き、インストール先に移動してから、フレーバー用の仮想環境を作成します。以下は `win11-amd64-cu134` の例です。自分のフレーバーIDに読み替えてください。

```
cd /d C:\easykotenocr
set UV_PROJECT_ENVIRONMENT=build\win11-amd64-cu134\venv
uv sync --project profiles\win11-amd64-cu134
```

- インターネット経由でパッケージをダウンロードするため時間がかかります（GPUフレーバーは数GB）。ディスク空きは GPU フレーバーで約 12GB、CPU フレーバーで約 7GB を目安にしてください。

### ステップ5: 学習済みモデルをダウンロードする

NDLラボから学習済みモデルをダウンロードし、次の場所に配置します（ブラウザで直接ダウンロードしてください）。

| モデル | ダウンロードURL | 配置先 |
|---|---|---|
| 文字認識モデル | <https://lab.ndl.go.jp/dataset/ndlkotensekiocr/trocr/model-ver2.zip> | zipを解凍して `src\text_kotenseki_recognition\model-ver2\` ができるように展開 |
| レイアウト抽出モデル | <https://lab.ndl.go.jp/dataset/ndlkotensekiocr/layoutmodel/ndl_kotenseki_layout_ver3.pth> | `src\ndl_kotenseki_layout\models\ndl_kotenseki_layout_ver3.pth` |

### ステップ6: 環境を確認する

インストール先で次の2つを実行し、両方が成功すればインストール完了です（フレーバーIDは自分のものに読み替えてください）。

```
build\win11-amd64-cu134\venv\Scripts\python.exe tools\apply_venv_patches.py
build\win11-amd64-cu134\venv\Scripts\python.exe scripts\verify_env.py --flavor win11-amd64-cu134
```

`verify_env.py` が `VERIFY OK` と表示すればOKです（`tools\apply_venv_patches.py` は `start_ocr.bat` が毎回自動実行しますが、手動で実行しても安全です）。
