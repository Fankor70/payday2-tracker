#!/bin/sh
# PAYDAY 2 achievement tracker -- launcher (macOS / Linux)
cd "$(dirname "$0")" || exit 1
PORT="${PD2_PORT:-8899}"
export PD2_PORT="$PORT"

echo "Проверяю данные..."
python3 verify.py > verify_report.txt 2>&1 || echo "  в данных есть замечания: verify_report.txt"

echo "Запускаю сервер на порту $PORT"
echo "Открой: http://127.0.0.1:$PORT"
( sleep 1; (xdg-open "http://127.0.0.1:$PORT" || open "http://127.0.0.1:$PORT") ) 2>/dev/null
exec python3 server.py