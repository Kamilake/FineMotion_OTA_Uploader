@echo off
chcp 65001 > nul
python\python.exe -E ./update.py
echo Press any key to close this window...
pause > nul