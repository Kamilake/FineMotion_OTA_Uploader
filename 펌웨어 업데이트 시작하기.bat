@echo off
chcp 65001 > nul
python\python.exe -E ./update.py
echo 창을 닫으려면 아무 키나 누르세요...
pause > nul