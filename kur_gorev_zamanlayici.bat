@echo off
chcp 65001 > nul
title Windows Görev Zamanlayıcısı Kurulumu

echo ========================================================
echo   Akakçe Saat 10:00 Günlük Rapor Görev Zamanlayıcısı
echo ========================================================
echo.
echo Bu işlem, bilgisayarınızda her gün saat 10:00'da Akakçe
echo üzerinden Samsung 990 EVO Plus fiyatlarını otomatik tarayıp
echo düne göre fiyat farkı ve kampanya raporunu üretmesi ve
echo fiyat eşiği altına inmişse hemen alarm göndermesi için
echo Windows Görev Zamanlayıcısı'na otomatik bir görev ekler.
echo.

cd /d "%~dp0"

set PYTHON_EXE=%~dp0.venv\Scripts\python.exe
set CLI_SCRIPT=%~dp0cli.py

if not exist "%PYTHON_EXE%" (
    echo [HATA] .venv klasoru bulunamadi! Lutfen once baslat.bat'i calistirin.
    pause
    exit /b 1
)

echo Görev adı: Akakce_Samsung990_Gunluk_10_00
echo Çalışma saati: Her gün 10:00
echo Komut: "%PYTHON_EXE%" "%CLI_SCRIPT%" report
echo.

schtasks /create /tn "Akakce_Samsung990_Gunluk_10_00" /tr "\"%PYTHON_EXE%\" \"%CLI_SCRIPT%\" report" /sc daily /st 10:00 /f

if %ERRORLEVEL% equ 0 (
    echo.
    echo ========================================================
    echo [BASARILI] Windows gorevi basariyla olusturuldu!
    echo Her gun saat 10:00'da arka planda otomatik calisacak.
    echo ========================================================
) else (
    echo.
    echo [UYARI] Gorev olusturulurken izin sorunu yasandiysa, bu dosyaya
    echo sag tiklayip 'Yonetici Olarak Calistir' demeyi deneyebilirsiniz.
)

echo.
pause
