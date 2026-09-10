@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title Sborka novoj versii PDF-bota Aganim
color 0B

echo.
echo  +==============================================+
echo  I                                              I
echo  I    SBORKA NOVOJ VERSII PDF-bota Aganim       I
echo  I                                              I
echo  +==============================================+
echo.

:: ==========================================
:: Versiya
:: ==========================================
:: Kompilyator Inno Setup: isshem vo vsekh standartnyh mestah
set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
    echo  [!] Inno Setup 6 ne nayden - ustanovite ego i povtorite.
    pause
    exit /b 1
)

:: Reliznaya sborka (dlya klientov): bez vstroennoj tablitsy i bez key.json
set "PDFBOT_FLAVOR=release"

set "VERSION=%~1"
if "%VERSION%"=="" (
    set /p "VERSION=Vvedite versiyu (naprimer 3.2): "
)
if "%VERSION%"=="" (
    echo  [!] Versiya ne ukazana.
    pause
    exit /b 1
)

echo  Versiya: %VERSION%
echo.

:: ==========================================
:: 1. Obnovlyaem versiyu v iskhodnikakh
:: ==========================================
echo  [1/6] Obnovlyayu versiyu v iskhodnikakh...
powershell -NoProfile -ExecutionPolicy Bypass -File _update_version.ps1 %VERSION%
if errorlevel 1 (
    echo  [!] Oshibka obnovleniya versii
    pause
    exit /b 1
)

:: ==========================================
:: 2. Sobiraem pdf_bot.exe
:: ==========================================
echo  [2/6] Sobirayu pdf_bot.exe...
.venv\Scripts\pyinstaller.exe bot_v30.spec --noconfirm >nul 2>&1
if not exist "dist\pdf_bot.exe" (
    echo  [!] Oshibka: pdf_bot.exe ne sobran
    pause
    exit /b 1
)
echo       OK

:: ==========================================
:: 3. Sobiraem dashboard.exe
:: ==========================================
echo  [3/6] Sobirayu dashboard.exe...
.venv\Scripts\pyinstaller.exe dashboard_v30.spec --noconfirm >nul 2>&1
if not exist "dist\dashboard.exe" (
    echo  [!] Oshibka: dashboard.exe ne sobran
    pause
    exit /b 1
)
echo       OK

:: ==========================================
:: 4. Sobiraem setup.exe (Inno Setup)
:: ==========================================
echo  [4/6] Sobirayu setup.exe...
if not exist install_build mkdir install_build
"%ISCC%" /DMyAppVersion=%VERSION% /Q setup.iss >nul 2>&1
if not exist "install_build\PDF-bot-Aganim-setup-v%VERSION%.exe" (
    echo  [!] Oshibka: setup.exe ne sobran
    echo      Podrobnee:
    "%ISCC%" /DMyAppVersion=%VERSION% setup.iss
    pause
    exit /b 1
)
echo       OK

:: ==========================================
:: 5. Sobiraem update.exe (Inno Setup)
:: ==========================================
echo  [5/6] Sobirayu update.exe...
"%ISCC%" /DMyAppVersion=%VERSION% /Q update.iss >nul 2>&1
if not exist "install_build\PDF-bot-Aganim-update-v%VERSION%.exe" (
    echo  [!] Oshibka: update.exe ne sobran
    pause
    exit /b 1
)
echo       OK

:: ==========================================
:: 6. Sobiraem papku distributiva
:: ==========================================
echo  [6/6] Sobirayu papku distributiva...
set "DIST=PDF-Р±РѕС‚ РђРіР°РЅРёРј v%VERSION%"
if exist "%DIST%" rmdir /s /q "%DIST%"
mkdir "%DIST%"

copy /y "install_build\PDF-bot-Aganim-setup-v%VERSION%.exe" "%DIST%\" >nul
copy /y "install_build\PDF-bot-Aganim-update-v%VERSION%.exe" "%DIST%\" >nul
if exist "uninstall_old.bat" copy /y "uninstall_old.bat" "%DIST%\" >nul
copy /y "apps_script.gs" "%DIST%\" >nul

echo       OK

:: ==========================================
:: ITOG
:: ==========================================
echo.
echo  +==============================================+
echo  I                                              I
echo  I    [OK] VERSIYA %VERSION% SOBRANA!         I
echo  I                                              I
echo  I    Papka: %DIST%
echo  I                                              I
echo  I    Faily:                                    I
echo  I    ^> PDF-bot-Aganim-setup-v%VERSION%.exe   I
echo  I    ^> PDF-bot-Aganim-update-v%VERSION%.exe   I
echo  I    ^> uninstall_old.bat                      I
echo  I    ^> apps_script.gs                         I
echo  I                                              I
echo  +==============================================+
echo.
echo  Nazhmite lyubuyu klavishu dlya vyhoda...
pause >nul

