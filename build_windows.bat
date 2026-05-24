@echo off
REM TRPG Log Converter Pro - Windows Build Script
REM
REM This batch only handles venv setup + dependency install.
REM The actual PyInstaller invocation is delegated to scripts\build.py so that
REM the bat never goes out of sync with requirements.txt.
REM
REM Past bug: the bat had a hardcoded pip-install package list that did not
REM include pydantic (added later), so PyInstaller's --collect-all pydantic
REM silently produced builds missing the package. Single source of truth now:
REM   - runtime deps  : requirements.txt
REM   - build options : scripts\build.py

chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

echo ================================================
echo   TRPG Log Converter Pro - Windows Build
echo ================================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed.
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/4] Creating virtual environment...
if not exist build_venv (
    python -m venv build_venv
    if errorlevel 1 (
        echo [ERROR] Failed to create venv
        pause
        exit /b 1
    )
)
call build_venv\Scripts\activate.bat

echo [2/4] Installing dependencies from requirements.txt...
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install runtime dependencies
    pause
    exit /b 1
)

REM Build-only dev tool. Not in requirements.txt because it does not ship.
python -m pip install pyinstaller
if errorlevel 1 (
    echo [ERROR] Failed to install PyInstaller
    pause
    exit /b 1
)

echo [3/4] Running build script (scripts\build.py)...
REM PyInstaller options, trim_bundle(), and smoke tests all live in build.py.
python scripts\build.py
if errorlevel 1 (
    echo [ERROR] Build script failed
    pause
    exit /b 1
)

echo [4/4] Creating ZIP archive...
powershell -Command "Compress-Archive -Path 'dist\TRPG_Converter_Pro' -DestinationPath 'dist\TRPG_Converter_Pro_Windows.zip' -Force"

echo.
echo ================================================
echo   Build Complete!
echo ================================================
echo.
echo Distribution file: dist\TRPG_Converter_Pro_Windows.zip
echo.
pause
