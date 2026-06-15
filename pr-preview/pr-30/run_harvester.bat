@echo off
title AURA FARMER HARVESTER
color 0a
echo ==================================================
echo    AURA FARMER - GESTALT INTELLIGENCE UPLINK
echo ==================================================
echo.
echo [!] CHECKING FOR VIRTUAL ENVIRONMENT...
if exist .venv\Scripts\activate.bat (
    echo [!] ACTIVATING .VENV...
    call .venv\Scripts\activate.bat
)

echo [!] INITIALIZING PYTHON ENVIRONMENT...
pip install -r requirements.txt
python harvester.py
echo.
echo [!] SEQUENCE COMPLETE.
pause
