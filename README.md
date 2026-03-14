# Easy古典OCR(ver.1)

古典籍をテキスト化するためのOCRアプリケーションです。 
本プログラムは、国立国会図書館の[NDLラボ](https://lab.ndl.go.jp)が公開している[NDL古典籍OCR_cli ver.3](https://github.com/ndl-lab/ndlkotenocr_cli)を基に、DockerやLinuxに関する知識がないユーザーでも利用できるように改変を加えたものです。


本プログラムに適用するライセンスは、CC BY 4.0です。ライセンス詳細は[LICENSE](./LICENSE)をご覧ください。
## インストール
[EasyKotenOcr-installer.zip](https://github.com/koshoji-project/EasyKotenOcr/raw/main/EasyKoten/EasyKotenOcr-installer.zip) をダウンロードし展開してください。展開されたBATファイルをマウス右クリックから「管理者として実行」してください。

## 改変の内容
1. Dockerを用いた仮想化技術を使用せずに、Windows Native 環境上で動作するようにしました。WSLやHyper-Vも不要です。
2. GPUを用いずにCPUのみを使用してOCR処理を行うようにしました。処理速度は落ちますが、NVIDIA製のGPUを搭載していないPCでも動作可能になりました。
3. 本アプリ動作の前提条件ソフトのインストール、環境構築、学習済モデルのダウンロードまでを全て実行する All In One なインストーラを用意しました。
4. コマンドラインの入力が苦手な方向けに、OCRを実行するためのバッチファイルを用意しました。
5. OCR実行時のオプションとして文字列認識結果を画像ファイルとして出力する機能を追加しました。
6. 入出力フォルダーの構成を判りやすくシンプルにしました。

## BATファイルが実行する処理の内容
1. 下記のソフトウェアが未インストールならインストールします。未インストールのソフトが多い場合は時間を要します。特にVisual Studioは長時間となります。<br>
   - git<br>
   - Python version 3.10<br>
   - Microsoft Visual Studio C++ Build Tools<br>
2. インストール先のフォルダーを何処にするかユーザーに指示を仰ぎます。既定ではc:\easykotenocrです。
3. 上記で指示されたフォルダーに本リポジトリのクローンを生成します。
4. pip + venvを用いてPython 3.10の仮想環境を構築し、必要なパッケージを仮想環境にインストールします。
5. 学習済のモデルを国立国会図書館のNDLラボからダウンロードします。   　

## OCRの実行

## 環境構築後のディレクトリ構成（参考）
```
EasyKotenOCR
├── main.py : メインとなるPythonスクリプト
├── cli : CLIコマンド的に利用するPythonスクリプトの格納されたディレクトリ
├── src : 各推論処理のソースコード用ディレクトリ
│   ├── ndl_kotenseki_layout : レイアウト抽出処理のソースコードの格納されたディレクトリ
|   ├── reading_order：読み順整序処理のソースコードの格納されたディレクトリ
│   └── text_kotenseki_recognition : 文字認識処理のソースコードの格納されたディレクトリ
├── config.yml : サンプルの推論設定ファイル
├── README.md : このファイル
└── requirements-windows.txt : 必要なPythonパッケージリスト
```



### 推論処理の実行
input_rootディレクトリの直下にimgディレクトリがあり、その下に資料毎の画像ディレクトリ(bookid1,bookid2,...)がある場合、
```
input_root/
  └── img
      ├── page01.jpg
      ├── page02.jpg
      ・・・
      └── page10.jpg
```
以下のコマンドで実行することができます。
```
python main.py infer input_root output_dir
```

実行後の出力例は次の通りです。

```
output_dir/
  ├── input_root
  │   ├── txt
  │   │     ├── page01.txt
  │   │     ├── page02.txt
  │   │    ・・・
  │   │    
  │   └── json
  │         ├── page01.json
  │         ├── page02.json
  │        ・・・
  └── opt.json
```


重みファイルのパス等、各モジュールで利用する設定値は`config.yml`の内容を修正することで変更することができます。

### オプションについて

#### 入力形式オプション
実行時に
-s b を指定することで、次の入力形式のフォルダ構造を処理できます。

例：
```
python main.py infer input_root output_dir -s b
```

入力形式
```
input_root/
  └── img
      ├── bookid1
      │   ├── page01.jpg
      │   ├── page02.jpg
      │   ・・・
      │   └── page10.jpg
      ├── bookid2
          ├── page01.jpg
          ├── page02.jpg
          ・・・
          └── page10.jpg
```
出力形式
```
output_dir/
  ├── input_root
  |     ├──bookid1
  │     |     ├── txt
  │     |     │     ├── page01.txt
  │     |     │     ├── page02.txt
  │     |     │         ・・・
  │     |     │    
  │     |     └── json
  │     |           ├── page01.json
  │     |           ├── page02.json
  │     |               ・・・
  |     ├──bookid2
  │     |     ├── txt
  │     |     │     ├── page01.txt
  │     |     │     ├── page02.txt
  │     |     │         ・・・
  │     |     │    
  │     |     └── json
  │     |           ├── page01.json
  │     |           ├── page02.json
  │                    ・・・
  └── opt.json
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
    "img_path":（元画像のディレクトリパス）,
    "img_name":（元画像名）
  }
}
```



#### オプション情報の保存
出力ディレクトリでは、実行時に指定したオプション情報が`opt.json`に保存されています。


























