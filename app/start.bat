@echo off
chcp 65001 >nul
title PAYDAY 2 - Трекер достижений
cd /d "%~dp0"

set PORT=8899

echo.
echo   PAYDAY 2 - Трекер достижений
echo   ============================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo   Python не найден.
    echo   Поставь Python 3 с python.org, при установке включи "Add python.exe to PATH".
    echo.
    pause
    exit /b 1
)

if not exist "data\app_data.json" (
    echo   Нет файла данных data\app_data.json
    echo   Собери его командой:  python build_ui.py
    echo.
    pause
    exit /b 1
)

REM --- свободен ли порт? иначе старый сервер просто не даст запуститься ---
netstat -ano | findstr /R /C:"127.0.0.1:%PORT% .*LISTENING" >nul 2>nul
if not errorlevel 1 (
    echo   Порт %PORT% уже занят - значит трекер, возможно, уже запущен.
    echo.
    start "" "http://127.0.0.1:%PORT%"
    echo   Открыл в браузере. Если страница не отвечает, закрой старый
    echo   процесс в Диспетчере задач и запуни этот файл ещё раз.
    echo.
    pause
    exit /b 0
)

echo   Проверяю данные...
python verify.py > verify_report.txt 2>&1
if errorlevel 1 (
    echo   ВНИМАНИЕ: в данных есть замечания - смотри verify_report.txt
) else (
    echo   Данные в порядке.
)
echo.

echo   Запускаю сервер на порту %PORT%
echo   Браузер откроется сам. Закрыть - Ctrl+C здесь.
echo.

start "" "http://127.0.0.1:%PORT%"
python server.py

echo.
echo   Сервер остановлен.
pause