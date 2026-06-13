@echo off
echo off
setlocal
chcp 932
:: バッチファイルの存在するディレクトリに移動
cd /d %~dp0
:: ==========================================
:: 管理者権限のチェック (net session コマンドの成功可否で判定)
:: ==========================================

net session >nul 2>&1
if %errorLevel% == 0 (
    goto :AdminTask
) else (
    echo 管理者権限がありません。管理者として再実行します...
    :: PowerShellを使用して自身を管理者として再起動
    powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)
echo 管理者権限を確認しました。インストールを開始します...
 :AdminTask
echo ================================
echo 1. Visual Studio Build Tools 2022 のインストール済み確認
echo ================================
:: vswhere.exe と vcvarsall.bat の存在を確認してインストール状態を判定
set "VS_PATH="
set "VSWHERE_EXE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
if not exist "%VSWHERE_EXE%" goto START_INSTALL

pushd "%ProgramFiles(x86)%\Microsoft Visual Studio\Installer"
for /f "usebackq tokens=*" %%i in (`vswhere.exe -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "VS_PATH=%%i"
popd

if not defined VS_PATH goto START_INSTALL
if not exist "%VS_PATH%\VC\Auxiliary\Build\vcvarsall.bat" goto START_INSTALL

echo 既に Visual Studio Build Tools 2022 がインストールされています。
echo インストールパス: %VS_PATH%
echo スキップします。
goto GIT

:START_INSTALL
echo インストールが見つかりませんでした。インストールを開始します。
:: ==========================================
:: サイレントインストールの実行
:: ==========================================
:: 一時ディレクトリの作成
set "TEMP_DIR=%~dp0\VS_BuildTools"
if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"
:: セットアップインストーラーのダウンロード先
set "INSTALLER_URL=https://aka.ms/vs/17/release/vs_BuildTools.exe"
set "INSTALLER_FILE=%TEMP_DIR%\vs_BuildTools.exe"

echo Visual Studio Build Tools 2022 インストーラーをダウンロードしています...

:: wget または curl が利用できない場合のフォールバックとして powershell を使用
powershell -Command "Invoke-WebRequest -Uri '%INSTALLER_URL%' -OutFile '%INSTALLER_FILE%'"
if %errorlevel% neq 0 (
    echo エラー: インストーラーのダウンロードに失敗しました。
    pause
    exit /b 1
)
if not exist "%INSTALLER_FILE%" (
    echo エラー: インストーラーファイル '%INSTALLER_FILE%' が存在しません。
    pause
    exit /b 1
)
echo インストールを開始します...
echo 完了まで数分かかる場合があります。
:: インストールオプション
:: --wait: インストール完了まで待機
:: --norestart: 再起動を強制しない（管理者が必要に応じて再起動）
:: --nocache: キャッシュを無効化
:: --includeRecommended: 推奨コンポーネントもインストール
:: --add: インストールするワークロード/コンポーネント
::    Microsoft.VisualStudio.Workload.VCTools: C++ ビルドツール
::    Microsoft.VisualStudio.Component.VC.Tools.x86.x64: VC++ ビルドツール
::    Microsoft.VisualStudio.Component.Windows10SDK: Windows 10 SDK
::    Microsoft.VisualStudio.Component.VC.CMake.Project: CMake サポート
::    Microsoft.VisualStudio.Component.VC.ATL: ATL サポート
::    Microsoft.VisualStudio.Component.VC.MFC: MFC サポート
"%INSTALLER_FILE%" ^
    --wait ^
    --norestart ^
    --nocache ^
    --includeRecommended ^
    --add Microsoft.VisualStudio.Workload.VCTools ^
    --add Microsoft.VisualStudio.Component.VC.Tools.x86.x64 ^
    --add Microsoft.VisualStudio.Component.Windows10SDK ^
    --add Microsoft.VisualStudio.Component.VC.CMake.Project ^
    --add Microsoft.VisualStudio.Component.VC.ATL ^
    --add Microsoft.VisualStudio.Component.VC.MFC ^
    --passive
:: ==========================================
:: 結果表示
:: ==========================================
if  %ERRORLEVEL%==0 (
    echo ==========================================
    echo Visual Studio Build Tools 2022 のインストールが完了しました。
    if exist "%TEMP_DIR%" rmdir /s /q "%TEMP_DIR%"
    goto GIT
    echo ==========================================
) 
if %ERRORLEVEL%=3010 (
    echo ==========================================
    echo インストールは完了しましたが、再起動が必要です。
    echo 再起動してください。
    echo ==========================================
    if exist "%TEMP_DIR%" rmdir /s /q "%TEMP_DIR%"
    goto END
    pause
) else (
    echo ==========================================
    echo インストール中にエラーが発生しました (エラーコード: %INSTALL_RESULT%)。
    echo 詳細はログを確認してください。
    echo ==========================================
    if exist "%TEMP_DIR%" rmdir /s /q "%TEMP_DIR%"
    pause
    goto END
)
:: --------------------
:GIT
echo ================================
echo 2.  Git インストール確認ツール
echo ================================
echo.
:: Git がインストールされているか確認
git --version >nul 2>&1
if %ERRORLEVEL%==0 (
    echo Git は既にインストールされています。
    git --version
    goto UV
)
echo Git がインストールされていません。
echo Git をインストールします...
echo 管理者権限を確認しました。インストールを開始します...
winget install --id Git.Git -e --scope machine --accept-package-agreements --accept-source-agreements --force
if %errorLevel%==0 ( 
@echo 完了。 
) else ( 
@echo エラーが発生しました。終了コード: %errorlevel%
)
:: -------------
:UV

echo ================================
echo 3.  uv インストール確認ツール
echo ================================
echo.
:: uv がインストールされているか確認
uv --version >nul 2>&1
if %ERRORLEVEL%==0 (
    echo uv は既にインストールされています。
    uv --version
    goto CLONE
)
echo uv がインストールされていません。
echo uv をインストールします...
echo 管理者権限を確認しました。インストールを開始します...
powershell -ExecutionPolicy Bypass  -c "irm https://astral.sh/uv/install.ps1 | iex"
if %errorLevel%==0 ( 
@echo 完了。 
) else ( 
@echo エラーが発生しました。終了コード: %errorlevel%
goto END
)
:CLONE
pause
endlocal
:END
