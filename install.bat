@echo off
chcp 65001 >nul
title Установка PDF-бота Аганим v2.0
color 0A

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║                                              ║
echo  ║    🤖 PDF-бот Аганим v2.0                    ║
echo  ║                                              ║
echo  ║    Установка программы...                    ║
echo  ║                                              ║
echo  ╚══════════════════════════════════════════════╝
echo.

:: ==========================================
:: ШАГ 1: Проверяем что запущены из папки программы
:: ==========================================
if not exist "pdf_bot.exe" (
    echo  ❌ ОШИБКА: Файл pdf_bot.exe не найден!
    echo.
    echo  Запустите этот файл из папки с программой.
    echo.
    pause
    exit /b 1
)

:: Папки для установки
set "INSTALL_DIR=%LOCALAPPDATA%\Programs\PDF-bot-Aganim"
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "DESKTOP=%USERPROFILE%\Desktop"

:: ==========================================
:: ШАГ 2: Создаём папку программы
:: ==========================================
echo  📁 Создаю папку для программы...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: ==========================================
:: ШАГ 3: Копируем файлы программы
:: ==========================================
echo  📋 Копирую файлы...
copy /y "pdf_bot.exe" "%INSTALL_DIR%\" >nul 2>&1
if exist "key.json" copy /y "key.json" "%INSTALL_DIR%\" >nul 2>&1

:: ==========================================
:: ШАГ 4: Автозапуск при включении ПК
:: ==========================================
echo  ⚙️  Настраиваю автозапуск...
set "VBS_PATH=%STARTUP%\start_pdf_bot.vbs"

echo Set WshShell = CreateObject("WScript.Shell") > "%VBS_PATH%"
echo WshShell.CurrentDirectory = "%INSTALL_DIR%" >> "%VBS_PATH%"
echo WshShell.Run "pdf_bot.exe", 0, False >> "%VBS_PATH%"

:: ==========================================
:: ШАГ 5: Ярлык на Рабочем столе
:: ==========================================
echo  🔗 Создаю ярлык на Рабочем столе...
set "SHORTCUT=%DESKTOP%\PDF-бот Аганим.lnk"
set "VBS_SCRIPT=%TEMP%\create_shortcut.vbs"

echo Set WshShell = CreateObject("WScript.Shell") > "%VBS_SCRIPT%"
echo Set shortcut = WshShell.CreateShortcut("%SHORTCUT%") >> "%VBS_SCRIPT%"
echo shortcut.TargetPath = "%INSTALL_DIR%\pdf_bot.exe" >> "%VBS_SCRIPT%"
echo shortcut.WorkingDirectory = "%INSTALL_DIR%" >> "%VBS_SCRIPT%"
echo shortcut.Description = "PDF-бот Аганим v2.0" >> "%VBS_SCRIPT%"
echo shortcut.Save >> "%VBS_SCRIPT%"

cscript //nologo "%VBS_SCRIPT%" >nul 2>&1
del "%VBS_SCRIPT%" >nul 2>&1

:: ==========================================
:: ШАГ 6: ЗАПУСК
:: ==========================================
echo  🚀 Запускаю программу...
start "" "%INSTALL_DIR%\pdf_bot.exe"

:: ==========================================
:: ШАГ 7: ЗАВЕРШЕНИЕ
:: ==========================================
echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║                                              ║
echo  ║    ✅ УСТАНОВКА ЗАВЕРШЕНА!                   ║
echo  ║                                              ║
echo  ║    Программа установлена и запущена.         ║
echo  ║                                              ║
echo  ║    • Ярлык создан на Рабочем столе           ║
echo  ║    • Автозапуск при включении ПК включён     ║
echo  ║    • Настройки и ключи сохранены             ║
echo  ║                                              ║
echo  ║    Программа будет запускаться               ║
echo  ║    автоматически при включении ПК.           ║
echo  ║                                              ║
echo  ╚══════════════════════════════════════════════╝
echo.
echo  Нажмите любую клавишу для закрытия окна...
pause >nul
