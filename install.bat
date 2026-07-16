@echo off
chcp 65001 >nul
title Ustanovka PDF-bota Aganim v2.0
color 0A

echo.
echo  +==============================================+
echo  I                                              I
echo  I    PDF-bot Aganim v2.0                       I
echo  I                                              I
echo  I    Ustanovka programmy...                    I
echo  I                                              I
echo  +==============================================+
echo.

:: ==========================================
:: SHAG 1: Proveryaem chto zapushcheny iz papki programmy
:: ==========================================
if not exist "pdf_bot.exe" (
    echo  [!] OSHIBKA: Fayl pdf_bot.exe ne nayden!
    echo.
    echo  Zapustite etot fayl iz papki s programmoj.
    echo.
    pause
    exit /b 1
)

:: Papki dlya ustanovki
set "INSTALL_DIR=%LOCALAPPDATA%\Programs\PDF-bot-Aganim"
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "DESKTOP=%USERPROFILE%\Desktop"

:: ==========================================
:: SHAG 2: Sozdaem papku programmy
:: ==========================================
echo  [1/5] Sozdayu papku dlya programmy...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: ==========================================
:: SHAG 3: Kopiruem fayly programmy
:: ==========================================
echo  [2/5] Kopiruyu fayly...
copy /y "pdf_bot.exe" "%INSTALL_DIR%\" >nul 2>&1
if exist "key.json" copy /y "key.json" "%INSTALL_DIR%\" >nul 2>&1

:: ==========================================
:: SHAG 4: Avtozapusks
:: ==========================================
echo  [3/5] Nastrivayu avtozapusks...
set "VBS_PATH=%STARTUP%\start_pdf_bot.vbs"

echo Set WshShell = CreateObject("WScript.Shell") > "%VBS_PATH%"
echo WshShell.CurrentDirectory = "%INSTALL_DIR%" >> "%VBS_PATH%"
echo WshShell.Run "pdf_bot.exe", 0, False >> "%VBS_PATH%"

:: ==========================================
:: SHAG 5: Yarlyk na Rabochem stole
:: ==========================================
echo  [4/5] Sozdayu yarlyk na Rabochem stole...
set "SHORTCUT=%DESKTOP%\PDF-bot Aganim.lnk"
set "VBS_SCRIPT=%TEMP%\create_shortcut.vbs"

echo Set WshShell = CreateObject("WScript.Shell") > "%VBS_SCRIPT%"
echo Set shortcut = WshShell.CreateShortcut("%SHORTCUT%") >> "%VBS_SCRIPT%"
echo shortcut.TargetPath = "%INSTALL_DIR%\pdf_bot.exe" >> "%VBS_SCRIPT%"
echo shortcut.WorkingDirectory = "%INSTALL_DIR%" >> "%VBS_SCRIPT%"
echo shortcut.Description = "PDF-bot Aganim v2.0" >> "%VBS_SCRIPT%"
echo shortcut.Save >> "%VBS_SCRIPT%"

cscript //nologo "%VBS_SCRIPT%" >nul 2>&1
del "%VBS_SCRIPT%" >nul 2>&1

:: ==========================================
:: SHAG 6: ZAPUSK
:: ==========================================
echo  [5/5] Zapuskayu programmu...
start "" "%INSTALL_DIR%\pdf_bot.exe"

:: ==========================================
:: ZAVERSHEMIE
:: ==========================================
echo.
echo  +==============================================+
echo  I                                              I
echo  I    [OK] USTANOVKA ZAVERSHENA!               I
echo  I                                              I
echo  I    Programma ustanovlena i zapushchena.      I
echo  I                                              I
echo  I    - Yarlyk sozdan na Rabochem stole         I
echo  I    - Avtozapusks pri vklyuchenii PK          I
echo  I    - Nastroyki i klyuchi sohraneny           I
echo  I                                              I
echo  I    Programma budet zapuskatsya               I
echo  I    avtomaticheski pri vklyuchenii PK.        I
echo  I                                              I
echo  +==============================================+
echo.
echo  Nazhmite lyubuyu klavishu dlya zakrytiya okna...
pause >nul
