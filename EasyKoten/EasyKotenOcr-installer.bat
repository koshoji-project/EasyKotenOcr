@echo off
setlocal

:: =============================================================
::  Build Tools for Visual Studio 2022 インストール確認
:: =============================================================
echo ============================================================
echo   Build Tools for Visual Studio 2022 インストール確認
echo ============================================================
echo.

:: レジストリでインストール済みか確認
:: VS2022 Build Tools は以下のキーに登録される
reg query "HKLM\SOFTWARE\Microsoft\VisualStudio\2022" /v "15.0" >nul 2>&1
if %ERRORLEVEL%==0 goto BUILDTOOLS_FOUND

reg query "HKLM\SOFTWARE\WOW6432Node\Microsoft\VisualStudio\2022" >nul 2>&1
if %ERRORLEVEL%==0 goto BUILDTOOLS_FOUND

:: Visual Studio Installer 経由のエントリを確認
reg query "HKLM\SOFTWARE\Microsoft\VisualStudio\Setup" >nul 2>&1
if %ERRORLEVEL%==0 (
    reg query "HKLM\SOFTWARE\Microsoft\VisualStudio\Setup" /s /f "BuildTools" >nul 2>&1
    if %ERRORLEVEL%==0 goto BUILDTOOLS_FOUND
)

reg query "HKLM\SOFTWARE\WOW6432Node\Microsoft\VisualStudio\Setup" >nul 2>&1
if %ERRORLEVEL%==0 (
    reg query "HKLM\SOFTWARE\WOW6432Node\Microsoft\VisualStudio\Setup" /s /f "BuildTools" >nul 2>&1
    if %ERRORLEVEL%==0 goto BUILDTOOLS_FOUND
)

:: インストールされていない場合 → サイレントインストール
echo Build Tools for Visual Studio 2022 がインストールされていません。
echo インストーラをダウンロードしています...
echo.

set BT_INSTALLER=vs_buildtools.exe
powershell -Command "$Env:BT_INSTALLER; Invoke-WebRequest -Uri https://aka.ms/vs/17/release/vs_buildtools.exe -OutFile vs_buildtools.exe"

if not exist %BT_INSTALLER% (
    echo インストーラのダウンロードに失敗しました。
    echo 処理を中断します。
    goto END
)

echo Build Tools for Visual Studio 2022 をサイレントインストール中...
echo （完了まで数分かかる場合があります）
%BT_INSTALLER% --quiet --wait --norestart ^
    --add Microsoft.VisualStudio.Workload.VCTools ^
    --add Microsoft.VisualStudio.Component.VC.Tools.x86.x64 ^
    --add Microsoft.VisualStudio.Component.Windows11SDK.22621

if %ERRORLEVEL%==0 (
    echo Build Tools for Visual Studio 2022 のインストールが完了しました。
) else (
    echo Build Tools for Visual Studio 2022 のインストールに失敗しました。（終了コード: %ERRORLEVEL%）
    echo 処理を中断します。
    goto END
)
goto BUILDTOOLS_DONE

:BUILDTOOLS_FOUND
echo Build Tools for Visual Studio 2022 は既にインストールされています。

:BUILDTOOLS_DONE
echo.


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

:: Git for Windows のインストーラをダウンロード
set GIT_INSTALLER=Git-latest-64-bit.exe
powershell -Command "Invoke-WebRequest -Uri https://github.com/git-for-windows/git/releases/latest/download/Git-2.45.2-64-bit.exe -OutFile Git-latest-64-bit.exe"

if not exist %GIT_INSTALLER% (
    echo インストーラのダウンロードに失敗しました。
    goto END
)

:: サイレントインストール
echo Git をサイレントインストール中...
%GIT_INSTALLER% /VERYSILENT /NORESTART

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
powershell -Command "Invoke-WebRequest -Uri https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe -OutFile python-3.10.11-amd64.exe"

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

