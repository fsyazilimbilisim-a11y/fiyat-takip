@echo off
chcp 65001 > nul
title F&S Yazılım - Akakçe Fiyat Takipçisi Canlı İnternet Paylaşımı
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [BILGI] Once baslat.bat calistirilmalidir.
    pause
    exit /b
)

.venv\Scripts\python.exe share_tunnel.py
pause
