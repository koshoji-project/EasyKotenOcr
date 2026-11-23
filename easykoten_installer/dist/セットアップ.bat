@echo off
rem ============================================================
rem  Easy古典OCR セットアップ（v2.1.0）
rem  ダブルクリックするだけでインストールを開始します。
rem  仕様: C:\hermes_works\easykotenocr_installer\INSTALLER_SPEC_v2.1.md（リポジトリ外・設計仕様書）
rem ============================================================
setlocal
chcp 65001 >nul
title Easy古典OCR セットアップ

set "PS=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"

echo Easy古典OCR セットアップを開始します...
echo （画面がすぐに切り替わります。そのままお待ちください）
echo.

"%PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup\setup-gui.ps1"
set "RC=%ERRORLEVEL%"

if "%RC%"=="0" goto :ok
if "%RC%"=="99" goto :end

echo.
echo ----------------------------------------------------------
echo  セットアップを完了できませんでした（コード %RC%）。
echo  ログ: %%TEMP%%\EasyKotenSetup\install.log
echo  「セットアップ.bat」をもう一度ダブルクリックすると、
echo  続きから再試行できることがあります。
echo ----------------------------------------------------------
goto :end

:ok
echo.
echo セットアップが完了しました。

:end
echo.
pause
exit /b %RC%
