@echo off
chcp 65001 >nul
title Sborka TESTOVoj versii PDF-bota Aganim
color 0E

echo.
echo  +==============================================+
echo  I   SBORKA TESTOVOJ VERSII (tablitsa vladeltsa) I
echo  +==============================================+
echo.

:: Testovaya sborka: vstroennaya tablitsa vladeltsa + key.json iz kornya
set "PDFBOT_FLAVOR=dev"

echo  [1/3] Sobirayu pdf_bot.exe (TEST)...
.venv\Scripts\pyinstaller.exe bot_v30.spec --noconfirm --distpath dist-test >nul 2>&1
if not exist "dist-test\pdf_bot.exe" (
    echo  [!] Oshibka: pdf_bot.exe ne sobran
    pause
    exit /b 1
)
echo        OK

echo  [2/3] Sobirayu dashboard.exe (TEST)...
.venv\Scripts\pyinstaller.exe dashboard_v30.spec --noconfirm --distpath dist-test >nul 2>&1
if not exist "dist-test\dashboard.exe" (
    echo  [!] Oshibka: dashboard.exe ne sobran
    pause
    exit /b 1
)
echo        OK

echo  [3/3] key.json...
if exist "key.json" (
    copy /y "key.json" "dist-test\" >nul
    echo        vshit v sborku i skopirovan ryadom s exe
) else (
    echo        key.json net v korne proekta - pri zapuske polozhite
    echo        ego ryadom s exe ili v %%APPDATA%%\PDF-bot-Aganim
)

echo.
echo  +==============================================+
echo  I   [OK] TESTOVAYA SBORKA GOTOVA: dist-test\   I
echo  I                                              I
echo  I   Zapusk:  dist-test\pdf_bot.exe              I
echo  I   Vo vsem vidno pripechku "(test)"            I
echo  +==============================================+
echo.
pause
