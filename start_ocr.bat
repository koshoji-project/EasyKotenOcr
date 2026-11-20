@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"
rem ============================================================
rem  EasyKotenOCR launcher (flavor-aware)
rem  Usage:
rem    start_ocr.bat [flavor-id] [main.py args...]
rem  flavor-id: win11-amd64-cpu / win11-amd64-cu134 /
rem             win11-arm64-cpu / win11-arm64-cu135
rem  If omitted, auto-detected from PROCESSOR_ARCHITECTURE + nvidia-smi.
rem  If no main.py args are given, runs the standard test:
rem    main.py infer c:/ocr/in c:/ocr/out-<flavor> -a -s b
rem ============================================================
set "FLAVOR=%~1"
if defined FLAVOR shift
if defined FLAVOR goto :CHECK

rem --- auto-detect flavor ---
set "ARCH=amd64"
if /I "%PROCESSOR_ARCHITECTURE%"=="ARM64" set "ARCH=arm64"
set "GPU=0"
nvidia-smi >nul 2>&1 && set "GPU=1"
if "%ARCH%"=="arm64" (
    if "%GPU%"=="1" (set "FLAVOR=win11-arm64-cu135") else (set "FLAVOR=win11-arm64-cpu")
) else (
    if "%GPU%"=="1" (set "FLAVOR=win11-amd64-cu134") else (set "FLAVOR=win11-amd64-cpu")
)
echo Auto-detected flavor: %FLAVOR%

:CHECK
set "VENV=build\%FLAVOR%\venv\Scripts\python.exe"
if not exist "%VENV%" (
    echo [FAIL] flavor venv not found: %VENV%
    echo        Create it first with:
    echo          set UV_PROJECT_ENVIRONMENT=build\%FLAVOR%\venv
    echo          uv sync --project profiles\%FLAVOR%
    pause
    exit /b 1
)

rem cpu flavors run with the device: cpu override config
set "CFGARG="
if "%FLAVOR%"=="win11-amd64-cpu" set "CFGARG=-c config\config.cpu.yml"
if "%FLAVOR%"=="win11-arm64-cpu" set "CFGARG=-c config\config.cpu.yml"

"%VENV%" tools\apply_venv_patches.py
if errorlevel 1 (pause & exit /b 1)

"%VENV%" scripts\verify_env.py --flavor "%FLAVOR%"
if errorlevel 1 (pause & exit /b 1)

set "TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1"
if "%~1"=="" (
    echo Running: main.py infer c:/ocr/in c:/ocr/out-%FLAVOR% -a -s b
    "%VENV%" main.py infer c:/ocr/in c:/ocr/out-%FLAVOR% -a -s b %CFGARG%
) else (
    "%VENV%" main.py %* %CFGARG%
)
set "OCR_EXIT=%ERRORLEVEL%"
if not "%OCR_EXIT%"=="0" (
    echo OCR failed with exit code %OCR_EXIT%.
    pause
    exit /b %OCR_EXIT%
)
exit /b 0
