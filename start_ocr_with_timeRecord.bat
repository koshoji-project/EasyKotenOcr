@echo off
setlocal
chcp 65001 >nul
cd /D "%~dp0"

set "TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1"
echo Loading_start: %date% %time% > time.txt

uv run --no-sync python -c "import mmcv, torch, mmcv._ext; from pathlib import Path; p=Path(mmcv.__file__).resolve(); assert mmcv.__version__ == '2.1.0+easykotenocr.1', mmcv.__version__; assert 'site-packages' in str(p).lower(), str(p); assert torch.__version__ == '2.9.0+cu130', torch.__version__; assert torch.version.cuda == '13.0', torch.version.cuda; print('MMCV wheel:', mmcv.__version__, p)"
if errorlevel 1 (
    echo ERROR: MMCV wheel is missing or incompatible. Run the installer.
    pause
    exit /b 1
)
echo Loading_end: %date% %time% >> time.txt
uv run --no-sync main.py infer c:/ocr/in c:/ocr/out -a -s b
set "OCR_EXIT=%ERRORLEVEL%"
echo OCR_end: %date% %time% >> time.txt

if not "%OCR_EXIT%"=="0" echo OCR failed with exit code %OCR_EXIT%.
pause
exit /b %OCR_EXIT%