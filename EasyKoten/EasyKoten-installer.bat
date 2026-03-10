git clone https://github.com/ndl-lab/ndlkotenocr_cli
copy /Y "config.yml" "ndlkotenocr_cli\config.yml"
copy /Y "config_cuda.yml" "ndlkotenocr_cli\config_cuda.yml"
copy /Y "download_models.py" "ndlkotenocr_cli\download_models.py"
copy /Y "requirements-windows.txt" "ndlkotenocr_cli\requirements-windows.txt"
copy /Y "start_ocr.bat" "ndlkotenocr_cli\start_ocr.bat"
py -3.10 -m venv 
call "%~dp0ndlkotenocr_cli\Scripts\activate.bat"
cd .\ndlkotenocr_cli
python.exe -m pip install --upgrade pip
pip install torch==2.1.1 torchvision==0.16.1 torchaudio==2.1.1 torchtext==0.16.1 --index-url https://download.pytorch.org/whl/cpu
pip install -r .\requirements-windows.txt
pip install mmcv==2.1.0 -f https://download.openmmlab.com/mmcv/dist/cpu/torch2.1/index.html
python download_models.py
pause
