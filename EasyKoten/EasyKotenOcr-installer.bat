@echo off
setlocal

echo ================================
echo   Git インストール確認ツール
echo ================================
echo.

:: Git がインストールされているか確認
git --version >nul 2>&1
if %ERRORLEVEL%==0 (
    echo Git は既にインストールされています。
    git --version
    goto PYTHON
)

echo Git がインストールされていません。
echo Git をインストールします...
echo.

:: Git for Windows のインストール
winget install --id Git.Git -e --source winget


echo インストール完了を確認しています...
timeout /t 5 >nul

:: 再確認
git --version >nul 2>&1
if %ERRORLEVEL%==0 (
    echo Git のインストールが正常に完了しました。
    git --version
) else (
    echo Git のインストールに失敗しました。
)


:: -------------
:PYTHON

echo ==========================================
echo     Python 3.10 インストール確認ツール
echo ==========================================
echo.

:: Python 3.10 がインストールされているか確認
python --version 2>nul | findstr "3.10" >nul
if %ERRORLEVEL%==0 (
    echo Python 3.10 は既にインストールされています。
    python --version
    goto CLONE
)

echo Python 3.10 がインストールされていません。
echo Python 3.10 をインストールします...
echo.

:: インストーラのファイル名
set PY_INSTALLER=python-3.10.11-amd64.exe

:: Python 3.10.11 インストーラをダウンロード
powershell -Command "Invoke-WebRequest -Uri https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe -OutFile %PY_INSTALLER%"

if not exist %PY_INSTALLER% (
    echo インストーラのダウンロードに失敗しました。
    goto END
)

:: サイレントインストール
echo Python 3.10 をサイレントインストール中...
%PY_INSTALLER% /quiet InstallAllUsers=1 PrependPath=1 Include_test=0

echo インストール完了を確認しています...
timeout /t 5 >nul

:: 再確認
python --version 2>nul | findstr "3.10" >nul
if %ERRORLEVEL%==0 (
    echo Python 3.10 のインストールが正常に完了しました。
    python --version
) else (
    echo Python 3.10 のインストールに失敗しました。
)

:: -----------------
:CLONE

git clone https://github.com/koshoji-project/EasyKotenOcr


:: -----------------
:VENV
cd EasyKotenOcr
py -3.10 -m venv venv
call "%~dp0EasyKotenOcr\venv\Scripts\activate.bat"


:: -----------------
:INSTALL

python.exe -m pip install --upgrade pip
pip install torch==2.1.1 torchvision==0.16.1 torchaudio==2.1.1 torchtext==0.16.1 --index-url https://download.pytorch.org/whl/cpu
pip install -r .\requirements-windows.txt
pip install mmcv==2.1.0 -f https://download.openmmlab.com/mmcv/dist/cpu/torch2.1/index.html
python EasyKoten\download_models.py


:END
echo.
echo 処理が完了しました。
pause
endlocal

