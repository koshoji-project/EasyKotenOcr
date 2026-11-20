@echo off
setlocal EnableExtensions
chcp 65001 >nul

set "INSTALL_DIR=C:\easykotenocr"
for %%I in ("%~dp0..") do set "SCRIPT_ROOT=%%~fI"
if exist "%SCRIPT_ROOT%\pyproject.toml" (
    set "INSTALL_DIR=%SCRIPT_ROOT%"
    goto :INSTALL
)
if exist "%INSTALL_DIR%\pyproject.toml" goto :INSTALL
if exist "%INSTALL_DIR%" (
    echo ERROR: %INSTALL_DIR% exists but is not an EasyKotenOCR project.
    goto :FAIL
)

git --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Git is not installed. Run 01_install_Prerequisite.bat first.
    goto :FAIL
)
git clone https://github.com/koshoji-project/EasyKotenOcr "%INSTALL_DIR%"
if errorlevel 1 goto :FAIL

:INSTALL
pushd "%INSTALL_DIR%" || goto :FAIL
if not exist "pyproject.toml" (
    echo ERROR: pyproject.toml is missing from %INSTALL_DIR%.
    goto :FAIL_POP
)
if not exist "uv.lock" (
    echo ERROR: uv.lock is missing from %INSTALL_DIR%.
    goto :FAIL_POP
)
if not exist "wheels\mmcv-2.1.0+easykotenocr.2-cp315-cp315-win_amd64.whl" (
    echo ERROR: Bundled MMCV wheel is missing. Include the wheels directory in the distribution.
    goto :FAIL_POP
)
uv --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: uv is not installed. Run 01_install_Prerequisite.bat first.
    goto :FAIL_POP
)

echo Installing the locked Python 3.15 environment and bundled MMCV wheel...
uv sync --locked --python 3.15
if errorlevel 1 goto :FAIL_POP
if not exist ".venv\Scripts\python.exe" goto :FAIL_POP

pushd "%TEMP%" || goto :FAIL_POP
"%INSTALL_DIR%\.venv\Scripts\python.exe" -c "import sys, mmcv, torch, mmcv._ext, mmpretrain, mmengine; v=sys.version_info; assert (v.major, v.minor) == (3, 15) and v.release[0] != 'beta', sys.version; assert mmcv.__version__ == '2.1.0+easykotenocr.2', mmcv.__version__; assert torch.__version__ == '2.14.1+cu130', torch.__version__; assert torch.version.cuda == '13.0', torch.version.cuda; assert mmpretrain.__version__ == '1.2.0+easykotenocr.1', mmpretrain.__version__; assert mmengine.__version__ == '0.10.7+easykotenocr.1', mmengine.__version__; print('Verified: Python', sys.version.split()[0], '| MMCV', mmcv.__version__, '| PyTorch', torch.__version__, '| CUDA', torch.version.cuda, '| MMP', mmpretrain.__version__, '| MME', mmengine.__version__)"
set "VERIFY_RC=%ERRORLEVEL%"
popd
if not "%VERIFY_RC%"=="0" goto :FAIL_POP

uv run --no-sync EasyKoten\download_models.py

popd
echo ============================================
echo EasyKotenOCR installation completed.
echo The bundled MMCV wheel is installed; users do not compile MMCV.
echo ============================================
pause
exit /b 0

:FAIL_POP
popd
:FAIL
echo Installation failed. Check the error above.
pause
exit /b 1
