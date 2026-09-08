@echo off
chcp 65001 > nul
title Windows Görevi Kaldır

echo ========================================================
echo   Akakçe Saat 10:00 Görevi Kaldırma
echo ========================================================
echo.

schtasks /delete /tn "Akakce_Samsung990_Gunluk_10_00" /f

if %ERRORLEVEL% equ 0 (
    echo [BASARILI] Gorev Windows Gorev Zamanlayicisi'ndan kaldirildi.
) else (
    echo [BILGI] Gorev zaten mevcut degil veya yetki gerekiyor.
)

echo.
pause
