@echo off
chcp 65001 >nul
title Obnovlenie PDF-bota Aganim
color 0B

echo.
echo  +==============================================+
echo  I                                              I
echo  I    Obnovlenie PDF-bota Aganim v2.0           I
echo  I                                              I
echo  +==============================================+
echo.

:: Proveryaem chto novyj .exe ryadom
if not exist "pdf_bot.exe" (
    echo  [!] OSHIBKA: Fayl pdf_bot.exe ne nayden ryadom s update.bat!
    echo.
    echo  Ubedites chto update.bat i pdf_bot.exe lezhat v odnoj papke.
    echo.
    pause
    exit /b 1
)

:: Papka kuda ustanovlena programma
set "INSTALL_DIR=%LOCALAPPDATA%\Programs\PDF-bot-Aganim"

if not exist "%INSTALL_DIR%\pdf_bot.exe" (
    echo  [!] Programma NE ustanovlena na etom kompyutere!
    echo.
    echo  Ispolzujte install.bat dlya pervoj ustanovki.
    echo.
    pause
    exit /b 1
)

echo  Najdena ustanovlennaya programma:
echo     %INSTALL_DIR%
echo.

:: ==========================================
:: Ostanavlivaem zapushchennuyu programmu
:: ==========================================
echo  [1/4] Ostanavlivayu programmu...
taskkill /f /im pdf_bot.exe >nul 2>&1
timeout /t 2 /nobreak >nul

:: ==========================================
:: Delaem rezervnuyu kopiyu staroj versii
:: ==========================================
echo  [2/4] Sozdayu rezervnuyu kopiyu...
if exist "%INSTALL_DIR%\pdf_bot.exe.bak" del "%INSTALL_DIR%\pdf_bot.exe.bak"
ren "%INSTALL_DIR%\pdf_bot.exe" "pdf_bot.exe.bak" >nul 2>&1

:: ==========================================
:: Kopiruem novuyu versiyu
:: ==========================================
echo  [3/4] Kopiruyu novuyu versiyu...
copy /y "pdf_bot.exe" "%INSTALL_DIR%\" >nul 2>&1

:: Proveryaem chto skopirovalos
if not exist "%INSTALL_DIR%\pdf_bot.exe" (
    echo  [!] Oshibka kopirovaniya! Vosstanavlivayu staruyu versiyu...
    ren "%INSTALL_DIR%\pdf_bot.exe.bak" "pdf_bot.exe" >nul 2>&1
    echo.
    echo  [!] Obnovlenie ne udalos.
    pause
    exit /b 1
)

:: Udalyaem bek-ap (vsyo proshlo uspeshno)
del "%INSTALL_DIR%\pdf_bot.exe.bak" >nul 2>&1

:: ==========================================
:: ZAPUSK
:: ==========================================
echo  [4/4] Zapuskayu obnovlennuyu programmu...
start "" "%INSTALL_DIR%\pdf_bot.exe"

echo.
echo  +==============================================+
echo  I                                              I
echo  I    [OK] OBNOVLENIE ZAVERSHENO!              I
echo  I                                              I
echo  I    Programma uspeshno obnovlena do v2.0      I
echo  I    i zapushchena.                            I
echo  I                                              I
echo  I    Nastroyki i klyuchi sohraneny.            I
echo  I                                              I
echo  +==============================================+
echo.
echo  Nazhmite lyubuyu klavishu dlya zakrytiya okna...
pause >nul
