@echo off
chcp 65001
cd /D "C:\EasyKotenOcr"
uv run main.py infer c:/ocr/in c:/ocr/out -a -s b
pause