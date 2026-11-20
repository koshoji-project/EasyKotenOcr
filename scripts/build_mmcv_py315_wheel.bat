@echo off
rem Build reduced-feature MMCV 2.1.0 wheel for Python 3.15 / PyTorch 2.14.1+cu130 / CUDA 13.0
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
set "DISTUTILS_USE_SDK=1"
set "TORCH_CUDA_ARCH_LIST=7.5;8.0;8.6;9.0;10.0;12.0"
set "CUDA_HOME=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.0"
set "PATH=%CUDA_HOME%\bin;%PATH%"
set "MMCV_WITH_OPS=1"
cd /d C:\Users\gesho\AppData\Local\hermes\cache\scratch\mmcv_py315_build
C:\easykotenocr\.venv\Scripts\python.exe setup.py bdist_wheel > C:\Users\gesho\AppData\Local\hermes\cache\scratch\mmcv_py315_build.log 2>&1
echo EXIT=%ERRORLEVEL% >> C:\Users\gesho\AppData\Local\hermes\cache\scratch\mmcv_py315_build.log
endlocal
