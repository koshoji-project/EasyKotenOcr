@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo EasyKotenOCR インストール準備スクリプト
echo ==========================================

:: 管理者権限の確認（全ユーザー向けインストールに必要）
net session >nul 2>&1
if !ERRORLEVEL! neq 0 (
    echo [エラー] このスクリプトは管理者権限で実行してください。
    echo バッチファイルを右クリックし、「管理者として実行」を選択してください。
    pause
    exit /b 1
)


:: 1. Gitのインストール確認とインストール
echo [Gitのインストール確認]
git --version >nul 2>&1
if !ERRORLEVEL! neq 0 (
    echo Gitが未インストール、またはパスが通っていません。wingetでインストールします...
    winget install --id Git.Git -e --source winget --silent --accept-package-agreements --accept-source-agreements
    if !ERRORLEVEL! neq 0 (
        echo [エラー] Gitのインストールに失敗しました。
        pause
        exit /b 1
    )
    echo Gitのインストールが完了しました。
    call %~0
    exit /b
    
) else (
    for /f "delims=" %%A in ('git --version') do echo %%A はインストール済です。
)
echo.



:: 2. Python 3.10のインストール確認とインストール
echo [Python 3.10のインストール確認]
set PYTHON_INSTALLED=0

:: `python` コマンドで3.10か確認
python --version 2>nul | findstr /R "^Python 3\.10\." >nul
if !ERRORLEVEL! equ 0 (
    set PYTHON_INSTALLED=1
) else (
    :: 念のため `py` ランチャーでも確認
    py -3.10 --version 2>nul >nul
    if !ERRORLEVEL! equ 0 (
        set PYTHON_INSTALLED=1
    )
)

if !PYTHON_INSTALLED! equ 0 (
    echo Python 3.10が未インストールのようです。wingetでインストールします...
    :: 全ユーザー向け (InstallAllUsers=1) かつ PATHに追加 (PrependPath=1)
    winget install --id Python.Python.3.10 -e --source winget --silent --accept-package-agreements --accept-source-agreements --scope machine --override "/quiet InstallAllUsers=1 PrependPath=1 Include_test=0"
    if !ERRORLEVEL! neq 0 (
        echo [エラー] Python 3.10のインストールに失敗しました。
        pause
        exit /b 1
    )
    echo Python 3.10のインストールが完了しました。
    call %~0
    exit /b
    
) else (
    echo Python 3.10 は既にインストールされています。
)
echo.


:: 3 Visual Studio Build Tools 2022のインストール
echo [Visual Studio Build Tools 2022のインストール]
echo 確認およびインストールしています...
winget install -e --id Microsoft.VisualStudio.2022.BuildTools --silent --override "--passive --wait --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended" --accept-package-agreements --accept-source-agreements
if !ERRORLEVEL! neq 0 (
    echo [情報] Visual Studio Build Tools 2022は既にインストールされているか、インストールがスキップされました。処理を続行します。
) else (
    echo Visual Studio Build Tools 2022のインストールが完了しました。
)


echo ==========================================
echo 前提条件の準備が完了しました。
echo 引き続きEasyKotenOcrのダウンロードと環境構築を行います。
echo ==========================================

:: 4. インストール先の選択 (GUIダイアログ表示)
set "DEFAULT_INSTALL_DIR=C:\easykotenocr"
set "INSTALL_DIR="

echo.
echo インストール先フォルダを選択するダイアログを表示します（裏に隠れる場合があります）...
for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; $fbd = New-Object System.Windows.Forms.FolderBrowserDialog; $fbd.SelectedPath = '%DEFAULT_INSTALL_DIR%'; $fbd.Description = 'インストール先フォルダを選択してください（キャンセルで規定値になります）'; $fbd.ShowNewFolderButton = $true; if ($fbd.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { $fbd.SelectedPath } else { '%DEFAULT_INSTALL_DIR%' }"`) do (
    set "INSTALL_DIR=%%I"
)

echo 選択されたインストール先: !INSTALL_DIR!
echo.



:: 5. リポジトリのクローン
echo [EasyKotenOcrのクローン]
if not exist "!INSTALL_DIR!" (
    mkdir "!INSTALL_DIR!"
)

:: フォルダが空かどうか確認
set "FOLDER_EMPTY=1"
for /f "delims=" %%f in ('dir /b /a "!INSTALL_DIR!" 2^>nul') do (
    set "FOLDER_EMPTY=0"
)

if !FOLDER_EMPTY! equ 0 (
    if exist "!INSTALL_DIR!\.git" (
        echo [情報] 既にクローン済みのようです。最新をpullします...
        pushd "!INSTALL_DIR!"
        git pull
        popd
    ) else (
        echo [エラー] 選択されたフォルダ "!INSTALL_DIR!" は空ではありません。
        echo インストール先には空のフォルダ、または新しいフォルダを指定してください。
        pause
        exit /b 1
    )
) else (
    echo https://github.com/koshoji-project/EasyKotenOcr から取得しています...
    git clone https://github.com/koshoji-project/EasyKotenOcr "!INSTALL_DIR!"
    if !ERRORLEVEL! neq 0 (
        echo [エラー] リポジトリのクローンに失敗しました。ネットワーク接続等を確認してください。
        pause
        exit /b 1
    )
    echo クローンが完了しました。
)
echo.

:: 6. Python仮想環境の構築
echo [Python仮想環境の構築]
set "VENV_DIR=!INSTALL_DIR!\venv"
echo "!VENV_DIR!" に仮想環境を作成しています...

:: ※wingetでインストールした直後は現在のコンソールにPATHが反映されていない場合があるため、
:: システム共通のpyランチャー（py.exe）を優先して使用します。
py -3.10 -m venv "!VENV_DIR!" 2>nul
if !ERRORLEVEL! neq 0 (
    python -m venv "!VENV_DIR!"
    if !ERRORLEVEL! neq 0 (
        echo [エラー] 仮想環境の作成に失敗しました。Pythonが正しくインストールされているか確認してください。
        pause
        exit /b 1
    )
)
echo 仮想環境の作成が完了しました。
echo.

:: 7. 仮想環境の有効化とpipのアップデート
echo [仮想環境の有効化とpipのアップデート]
call "!VENV_DIR!\Scripts\activate.bat"
if !ERRORLEVEL! neq 0 (
    echo [エラー] 仮想環境の有効化に失敗しました。
    pause
    exit /b 1
)
echo 仮想環境を有効化しました。

echo pipを最新版にアップデートしています...
python.exe -m pip install --upgrade pip
if !ERRORLEVEL! neq 0 (
    echo [エラー] pipのアップデートに失敗しました。
    pause
    exit /b 1
)
echo pipのアップデートが完了しました。
echo.

:: 8. 必要なPythonパッケージのインストール
echo [パッケージのインストール]

echo 1/3: PyTorch関連パッケージをインストールしています...
python.exe -m pip install torch==2.1.1 torchvision==0.16.1 torchaudio==2.1.1 torchtext==0.16.1 --index-url https://download.pytorch.org/whl/cpu
if !ERRORLEVEL! neq 0 (
    echo [エラー] PyTorch関連パッケージのインストールに失敗しました。
    pause
    exit /b 1
)

echo 2/3: requirements-windows.txt からパッケージをインストールしています...
:: requirements-windows.txt はクローンしたフォルダ内にあります。
pushd "!INSTALL_DIR!"
python.exe -m pip install -r requirements-windows.txt
if !ERRORLEVEL! neq 0 (
    echo [エラー] requirements-windows.txt のパッケージインストールに失敗しました。
    popd
    pause
    exit /b 1
)
popd

echo 3/3: mmcvパッケージをインストールしています...
python.exe -m pip install mmcv==2.1.0 -f https://download.openmmlab.com/mmcv/dist/cpu/torch2.1/index.html
if !ERRORLEVEL! neq 0 (
    echo [エラー] mmcv パッケージのインストールに失敗しました。
    pause
    exit /b 1
)

echo すべてのパッケージのインストールが完了しました。
echo.

:: 9. 学習済みモデルのダウンロード
echo [学習済みモデルのダウンロード]
echo モデルをダウンロードしています...
pushd "!INSTALL_DIR!"
python.exe EasyKoten\download_models.py
if !ERRORLEVEL! neq 0 (
    echo [エラー] モデルのダウンロードに失敗しました。
    popd
    pause
    exit /b 1
)
popd
echo モデルのダウンロードが完了しました。
echo.

echo ==========================================
echo EasyKotenOCR のインストールと初期設定がすべて完了しました！
echo （起動の準備が整いました）
echo ==========================================
pause
