@echo off
setlocal

set "ROOT=%~dp0"
set "VENV=%ROOT%.venv"

if not exist "%VENV%\Scripts\python.exe" (
    echo Creating virtual environment...
    uv venv "%VENV%" --python 3.13 2>nul
    if errorlevel 1 (
        python -m venv "%VENV%"
    )
    if not exist "%VENV%\Scripts\python.exe" (
        echo.
        echo Failed to create virtual environment.
        echo Make sure Python is installed and added to PATH.
        echo Download from: https://www.python.org/downloads/
        pause
        exit /b 1
    )
)

echo Installing dependencies...
uv pip install -r "%ROOT%requirements.txt" --python "%VENV%\Scripts\python.exe" --quiet
if errorlevel 1 (
    echo Failed to install dependencies.
    pause
    exit /b 1
)

echo Starting Icarus...
"%VENV%\Scripts\python" "%ROOT%main.py"
pause
