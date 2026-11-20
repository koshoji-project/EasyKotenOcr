# Easy古典OCR(ver.1)

古典籍をテキスト化するためのOCRアプリケーションです。 
本プログラムは、国立国会図書館の[NDLラボ](https://lab.ndl.go.jp)が公開している[NDL古典籍OCR_cli ver.3](https://github.com/ndl-lab/ndlkotenocr_cli)を基に、DockerやLinuxに関する知識がないユーザーでも利用できるように改変を加えたものです。


本プログラムに適用するライセンスは、CC BY 4.0です。ライセンス詳細は[LICENSE](./LICENSE)をご覧ください。
## インストール

2026年11月の統合作業により、本リポジトリは **4つの環境（フレーバー）** に対応しました。インストール手順も変更されています。古い `EasyKotenOcr-installer.zip`（Python 3.10 系の旧インストーラー）は**現在の構成では動作しないため使用しないでください**。

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

Python 3.15.2 は uv が自動的にダウンロードして使うため、Python を手動でインストールする必要はありません。

### ステップ3: プログラム本体を入手する

**Gitリポジトリには、専用の mmcv ビルド済みホイール（`wheels\`）と学習済みモデルの実体は含まれていません。** これらは配布パッケージ（zip）に同梱して配布しています。配布パッケージをダウンロードし、任意のフォルダー（例: `C:\easykotenocr`）に展開してください。

展開したフォルダーに `wheels\win11-<自分のフレーバー>\` が存在することを確認してください（ここにフレーバー専用の mmcv ホイールが入っています）。

### ステップ4: 実行環境を作る

コマンドプロンプトを開き、インストール先に移動してから、フレーバー用の仮想環境を作成します。以下は `win11-amd64-cu134` の例です。自分のフレーバーIDに読み替えてください。

```
cd /d C:\easykotenocr
set UV_PROJECT_ENVIRONMENT=build\win11-amd64-cu134\venv
uv sync --project profiles\win11-amd64-cu134
```

- インターネット経由でパッケージをダウンロードするため時間がかかります（GPUフレーバーは数GB）。ディスク空きは GPU フレーバーで約 12GB、CPU フレーバーで約 7GB を目安にしてください。
- `uv sync` で Python が見つからないというエラーになる場合は、`profiles\win11-amd64-cu134\.python-version` の中身を `3.15.2` に書き換えて再実行してください（ビルドマシンの絶対パスが書かれている場合があります）。

### ステップ5: 学習済みモデルをダウンロードする

NDLラボから学習済みモデルをダウンロードし、次の場所に配置します。ブラウザで直接ダウンロードしても、同梱の `EasyKoten\download_models.py` を venv の Python で実行しても構いません。

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

## OCRの実行

`start_ocr.bat` をダブルクリックして実行してください。PCの構成（CPUアーキテクチャとNVIDIA GPUの有無）を見て、使うフレーバーを自動的に選びます。

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
3. AMD64 と Windows on ARM の両対応とし、さらに GPU 有無を含む4通りのフレーバー構成としました。mmcv などの必須パッケージは各フレーバー用にビルド済みホイールとして同梱し、Visual Studio Build Tools 不要でインストールできるようにしました。
4. uv を使うことで、Python のバージョン違いによる環境の破壊を防いでいます。
5. コマンドラインの入力が苦手な方向けに、OCRを実行するためのバッチファイルを用意しました。
6. OCR実行時のオプションとして文字列認識結果を画像ファイルとして出力する機能を追加しました。
7. 入出力フォルダーの構成を判りやすくシンプルにしました。

## 環境構築後のフォルダー構成（参考）
```
EasyKotenOCR
├── build : フレーバー別のPython仮想環境が入るフォルダー（uvが作成）
│   └── win11-amd64-cu134\venv : 各フレーバーの仮想環境
├── cli : CLIコマンド的に利用するPythonスクリプトの格納されたフォルダー
├── cv2_shim : 仮想環境用に同梱した opencv パッケージの差し替え用フォルダー
├── EasyKoten : 学習済みモデルのダウンロードスクリプト等が格納されたフォルダー
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
├── wheels : フレーバー別の mmcv ビルド済みホイール（配布パッケージにのみ同梱）
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
 │   ・・・
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









