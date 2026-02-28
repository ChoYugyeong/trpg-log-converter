@echo off
REM TRPG Log Converter Pro - Windows Build Script
REM Run this on Windows PC

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
python -m venv build_venv
call build_venv\Scripts\activate.bat

echo [2/4] Installing dependencies...
pip install --upgrade pip
pip install PySide6 PySide6-Fluent-Widgets ebooklib python-docx beautifulsoup4 lxml pyyaml pillow reportlab pyinstaller playwright

echo [3/4] Building application...
pyinstaller --name TRPG_Converter_Pro ^
    --windowed ^
    --onedir ^
    --clean ^
    --noconfirm ^
    --add-data "core;core" ^
    --add-data "gui;gui" ^
    --add-data "utils;utils" ^
    --add-data "config.yaml;." ^
    --hidden-import PySide6 ^
    --hidden-import PySide6.QtWidgets ^
    --hidden-import PySide6.QtCore ^
    --hidden-import PySide6.QtGui ^
    --hidden-import qfluentwidgets ^
    --hidden-import qfluentwidgets.components ^
    --hidden-import qfluentwidgets.common ^
    --hidden-import qfluentwidgets.window ^
    --hidden-import ebooklib ^
    --hidden-import bs4 ^
    --hidden-import lxml ^
    --hidden-import docx ^
    --hidden-import yaml ^
    --hidden-import PIL ^
    --hidden-import reportlab ^
    --hidden-import playwright ^
    --hidden-import playwright.sync_api ^
    main.py

if errorlevel 1 (
    echo [ERROR] Build failed
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
