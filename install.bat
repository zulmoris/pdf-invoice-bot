@echo off
chcp 65001 >nul
title Ustanovka PDF-bota Aganim v3.0
color 0A

echo.
echo  +==============================================+
echo  I                                              I
echo  I    PDF-bot Aganim v3.0  (Win11)              I
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
set "DESKTOP=%USERPROFILE%\Desktop"

:: ==========================================
:: SHAG 2: Udalyaem staryj VBS-avtozapusks esli bil
:: ==========================================
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
if exist "%STARTUP%\start_pdf_bot.vbs" (
    del "%STARTUP%\start_pdf_bot.vbs" >nul 2>&1
    echo  [++] Udaleno staroe avtozapusk-VBS.
)

:: ==========================================
:: SHAG 3: Sozdaem papku programmy
:: ==========================================
echo  [1/5] Sozdayu papku dlya programmy...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: ==========================================
:: SHAG 4: Kopiruem fayly programmy
:: ==========================================
echo  [2/5] Kopiruyu fayly...
copy /y "pdf_bot.exe" "%INSTALL_DIR%\" >nul 2>&1
if exist "key.json" copy /y "key.json" "%INSTALL_DIR%\" >nul 2>&1
if exist "dashboard_v30.py" copy /y "dashboard_v30.py" "%INSTALL_DIR%\" >nul 2>&1
if exist "dashboard.exe" copy /y "dashboard.exe" "%INSTALL_DIR%\" >nul 2>&1

:: ==========================================
:: SHAG 5: Yarlyk na Rabochem stole - BOT
:: ==========================================
echo  [3/5] Sozdayu yarlyk PDF-bot na Rabochem stole...
set "SHORTCUT_BOT=%DESKTOP%\PDF-bot Aganim.lnk"
set "VBS_SCRIPT=%TEMP%\create_shortcut.vbs"

echo Set WshShell = CreateObject("WScript.Shell") > "%VBS_SCRIPT%"
echo Set shortcut = WshShell.CreateShortcut("%SHORTCUT_BOT%") >> "%VBS_SCRIPT%"
echo shortcut.TargetPath = "%INSTALL_DIR%\pdf_bot.exe" >> "%VBS_SCRIPT%"
echo shortcut.WorkingDirectory = "%INSTALL_DIR%" >> "%VBS_SCRIPT%"
echo shortcut.Description = "PDF-bot Aganim v3.0" >> "%VBS_SCRIPT%"
echo shortcut.Save >> "%VBS_SCRIPT%"

cscript //nologo "%VBS_SCRIPT%" >nul 2>&1
del "%VBS_SCRIPT%" >nul 2>&1

:: ==========================================
:: SHAG 6: Yarlyk na Rabochem stole - DASHBOARD
:: ==========================================
echo  [4/5] Sozdayu yarlyk Dashboard na Rabochem stole...
if exist "%INSTALL_DIR%\dashboard.exe" (
    set "SHORTCUT_DASH=%DESKTOP%\Dashboard Aganim.lnk"
    set "VBS_SCRIPT2=%TEMP%\create_dash.vbs"

    echo Set WshShell = CreateObject("WScript.Shell") > "%VBS_SCRIPT2%"
    echo Set shortcut = WshShell.CreateShortcut("%SHORTCUT_DASH%") >> "%VBS_SCRIPT2%"
    echo shortcut.TargetPath = "%INSTALL_DIR%\dashboard.exe" >> "%VBS_SCRIPT2%"
    echo shortcut.WorkingDirectory = "%INSTALL_DIR%" >> "%VBS_SCRIPT2%"
    echo shortcut.Description = "Dashboard Aganim v3.0" >> "%VBS_SCRIPT2%"
    echo shortcut.Save >> "%VBS_SCRIPT2%"

    cscript //nologo "%VBS_SCRIPT2%" >nul 2>&1
    del "%VBS_SCRIPT2%" >nul 2>&1
    echo  [++] Yarlyk Dashboard sozdan.
) else (
    echo  [--] dashboard.exe ne nayden - yarlyk ne sozdan.
)

:: ==========================================
:: SHAG 7: ZAPUSK BOTA
:: ==========================================
echo  [5/5] Zapuskayu bota...
start "" "%INSTALL_DIR%\pdf_bot.exe"

:: ==========================================
:: ZAVERSHEMIE
:: ==========================================
echo.
echo  +==============================================+
echo  I                                              I
echo  I    [OK] USTANOVKA ZAVERSHENA!               I
echo  I                                              I
echo  I    Na rabochem stole 2 yarlyka:              I
echo  I    - PDF-bot Aganim (bot, slushaet papku)    I
echo  I    - Dashboard Aganim (prosmotr schetov)     I
echo  I                                              I
echo  I    Avtozapusks bota nastroitsya              I
echo  I    avtomaticheski.                           I
echo  I                                              I
echo  +==============================================+
echo.
echo  Nazhmite lyubuyu klavishu dlya zakrytiya okna...
pause >nul
