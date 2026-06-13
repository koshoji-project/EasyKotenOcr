@echo off
echo off
setlocal
chcp 65001
cd /d %~dp0

:CLONE
c:
cd \
mkdir easykotenocr
cd easykotenocr
git clone https://github.com/koshoji-project/EasyKotenOcr .
uv init --python 3.10
uv python pin 3.10
uv add -r .\requirements-windows.txt
uv add torch==2.1.1 torchvision==0.16.1 torchaudio==2.1.1 torchtext==0.16.1 --index https://download.pytorch.org/whl/cpu
uv pip install mmcv==2.1.0 -f https://download.openmmlab.com/mmcv/dist/cpu/torch2.1/index.html
uv run EasyKoten\download_models.py
copy /Y /V .\EasyKoten\fix_packages\fcn_mask_head.py .\.venv\lib\site-packages\mmdet\models\roi_heads\mask_heads\
copy /Y /V .\EasyKoten\fix_packages\utils.py .\.venv\lib\site-packages\transformers\generation\
echo ============================================
echo  EasyKotenOCRのインストールが完了しました
echo ============================================
pause
endlocal
:END
