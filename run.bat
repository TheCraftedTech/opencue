@echo off
setlocal
cd /d "%~dp0"

rem Starts OpenCue from the source folder. On the first start it creates the virtual environment (venv) and installs the
rem requirements - this needs Python 3.13 (64-bit, from python.org) and an internet connection once. ffmpeg is included in the ffmpeg folder.
if not exist "venv\Scripts\python.exe" (
    echo First start: creating the virtual environment and installing the requirements...
    py -3.13 -m venv venv 2>/dev/null || py -3 -m venv venv 2>/dev/null || python -m venv venv
    if errorlevel 1 (
        echo Python 3 was not found. Please install Python 3.13 from https://www.python.org/downloads/ and run this file again.
        pause
        exit /b 1
    )
    venv\Scripts\python.exe -m pip install --upgrade pip
    venv\Scripts\python.exe -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Installing the requirements failed. Check the internet connection and run this file again.
        rmdir /s /q venv
        pause
        exit /b 1
    )
)

venv\Scripts\python.exe main.py
pause
