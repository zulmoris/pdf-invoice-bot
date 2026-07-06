@echo off
chcp 65001 >nul
title Установка автозапуска PDF-бота

echo ==========================================
echo   Установка автозапуска PDF-бота Аганим
echo ==========================================
echo.

:: Проверяем, что запущены из папки программы
if not exist "pdf_bot.exe" (
    echo [ОШИБКА] Файл pdf_bot.exe не найден!
    echo Запустите этот файл из папки с программой.
    pause
    exit /b 1
)

:: Путь к автозагрузке Windows
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"

:: Создаём VBS-скрипт для скрытого запуска
set "VBS_PATH=%STARTUP%\start_pdf_bot.vbs"

echo Set WshShell = CreateObject("WScript.Shell") > "%VBS_PATH%"
echo WshShell.CurrentDirectory = "%~dp0" >> "%VBS_PATH%"
echo WshShell.Run "pdf_bot.exe", 0, False >> "%VBS_PATH%"

echo.
echo ✅ Автозапуск установлен!
echo.
echo Программа будет запускаться автоматически
echo при каждом включении компьютера.
echo.
pause
