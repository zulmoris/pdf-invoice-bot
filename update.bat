@echo off
chcp 65001 >nul
title Обновление PDF-бота Аганим
color 0B

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║                                              ║
echo  ║    🔄 Обновление PDF-бота Аганим v2.0        ║
echo  ║                                              ║
echo  ╚══════════════════════════════════════════════╝
echo.

:: Проверяем что новый .exe рядом
if not exist "pdf_bot.exe" (
    echo  ❌ ОШИБКА: Файл pdf_bot.exe не найден рядом с update.bat!
    echo.
    echo  Убедитесь что update.bat и pdf_bot.exe лежат в одной папке.
    echo.
    pause
    exit /b 1
)

:: Папка куда установлена программа
set "INSTALL_DIR=%LOCALAPPDATA%\Programs\PDF-bot-Aganim"

if not exist "%INSTALL_DIR%\pdf_bot.exe" (
    echo  ❌ Программа не установлена на этом компьютере!
    echo.
    echo  Используйте install.bat для первой установки.
    echo.
    pause
    exit /b 1
)

echo  🔍 Найдена установленная программа:
echo     %INSTALL_DIR%
echo.

:: ==========================================
:: Останавливаем запущенную программу
:: ==========================================
echo  🛑 Останавливаю программу...
taskkill /f /im pdf_bot.exe >nul 2>&1
timeout /t 2 /nobreak >nul

:: ==========================================
:: Делаем резервную копию старой версии
:: ==========================================
echo  💾 Создаю резервную копию...
if exist "%INSTALL_DIR%\pdf_bot.exe.bak" del "%INSTALL_DIR%\pdf_bot.exe.bak"
ren "%INSTALL_DIR%\pdf_bot.exe" "pdf_bot.exe.bak" >nul 2>&1

:: ==========================================
:: Копируем новую версию
:: ==========================================
echo  📋 Копирую новую версию...
copy /y "pdf_bot.exe" "%INSTALL_DIR%\" >nul 2>&1

:: Проверяем что скопировалось
if not exist "%INSTALL_DIR%\pdf_bot.exe" (
    echo  ⚠️  Ошибка копирования! Восстанавливаю старую версию...
    ren "%INSTALL_DIR%\pdf_bot.exe.bak" "pdf_bot.exe" >nul 2>&1
    echo.
    echo  ❌ Обновление не удалось.
    pause
    exit /b 1
)

:: Удаляем бэкап (всё прошло успешно)
del "%INSTALL_DIR%\pdf_bot.exe.bak" >nul 2>&1

:: ==========================================
:: ЗАПУСК
:: ==========================================
echo  🚀 Запускаю обновлённую программу...
start "" "%INSTALL_DIR%\pdf_bot.exe"

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║                                              ║
echo  ║    ✅ ОБНОВЛЕНИЕ ЗАВЕРШЕНО!                  ║
echo  ║                                              ║
echo  ║    Программа успешно обновлена до v2.0       ║
echo  ║    и запущена.                               ║
echo  ║                                              ║
echo  ║    Настройки и ключи сохранены.              ║
echo  ║                                              ║
echo  ╚══════════════════════════════════════════════╝
echo.
echo  Нажмите любую клавишу для закрытия окна...
pause >nul
