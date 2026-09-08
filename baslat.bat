@echo off
chcp 65001 > nul
title Akakçe Fiyat Takip & Alarm Sistemi

echo ========================================================
echo   Akakçe Samsung 990 EVO Plus Fiyat Takip ve Alarmı
echo ========================================================
echo.

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [BILGI] Ilk kurulum tespit edildi. Sanal ortam hazirlaniyor...
    if exist "%USERPROFILE%\.local\bin\uv.exe" (
        "%USERPROFILE%\.local\bin\uv.exe" venv .venv
        "%USERPROFILE%\.local\bin\uv.exe" pip install -r requirements.txt
    ) else (
        python -m venv .venv
        .venv\Scripts\pip install -r requirements.txt
    )
)

echo [BASLATILIYOR] Sunucu baslatiliyor ve tarayici aciliyor...
.venv\Scripts\python.exe run.py

pause
