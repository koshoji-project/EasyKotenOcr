# Easy古典OCR(ver.1)

古典の画像ファイルに対してOCR処理を行いテキスト化するためのアプリケーションを提供するリポジトリです。 
本プログラムは、国立国会図書館の[NDLラボ](https://lab.ndl.go.jp)が公開している[NDL古典籍OCR_cli ver.3](https://github.com/ndl-lab/ndlkotenocr_cli)を基に、DockerやLinuxに関する知識がないユーザーにも利用しやすいように改変を加えたものです。


本プログラムは、高勝寺プロジェクトがCC BY 4.0ライセンスの下に公開します。詳細については
[LICENSE](./LICENSE
)をご覧ください。

## 環境構築

### インストール
1. [EasyKoten-installer.bat](https://github.com/koshoji-project/EasyKotenOcr/raw/main/EasyKoten/EasyKoten-installer.bat?ver=0)右クリックから”名前を付けてリンク先を保存”します。
このとき、リンクを開いた後に右クリックから保存すると、*.batファイルではなく＊。ｔｘｔファイルになり実行できなくなります。

2. インストール先のからフォルダーをc:\EasyKotenOcrなど浅いパスに用意して、EasyKoten-installer.batを配置して実行します。

### 2. OCRの実行

### 環境構築後のディレクトリ構成（参考）
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







