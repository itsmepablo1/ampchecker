#!/bin/bash
# ============================================================
# run_vps.sh — Script untuk menjalankan bot di VPS Linux
# ============================================================

BOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$BOT_DIR/bot.log"
PID_FILE="$BOT_DIR/bot.pid"

case "$1" in
  start)
    if [ -f "$PID_FILE" ] && kill -0 "$(cat $PID_FILE)" 2>/dev/null; then
      echo "✅ Bot sudah berjalan (PID: $(cat $PID_FILE))"
      exit 0
    fi
    echo "🚀 Memulai bot..."
    cd "$BOT_DIR"
    nohup python3 bot.py >> "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    echo "✅ Bot berjalan (PID: $!)"
    echo "📄 Log: tail -f $LOG_FILE"
    ;;
  stop)
    if [ -f "$PID_FILE" ]; then
      PID=$(cat "$PID_FILE")
      kill "$PID" 2>/dev/null && echo "🛑 Bot dihentikan (PID: $PID)" || echo "⚠️ Proses tidak ditemukan"
      rm -f "$PID_FILE"
    else
      echo "ℹ️ Bot tidak sedang berjalan"
    fi
    ;;
  restart)
    $0 stop
    sleep 2
    $0 start
    ;;
  status)
    if [ -f "$PID_FILE" ] && kill -0 "$(cat $PID_FILE)" 2>/dev/null; then
      echo "🟢 Bot RUNNING (PID: $(cat $PID_FILE))"
    else
      echo "🔴 Bot STOPPED"
    fi
    ;;
  log)
    tail -f "$LOG_FILE"
    ;;
  install)
    echo "📦 Menginstall dependencies..."
    pip3 install -r requirements.txt
    echo "🎭 Menginstall Playwright browser..."
    playwright install chromium
    playwright install-deps chromium
    echo "✅ Instalasi selesai! Edit settings.json lalu jalankan: ./run_vps.sh start"
    ;;
  *)
    echo "Cara pakai: $0 {start|stop|restart|status|log|install}"
    echo ""
    echo "  install  — Install semua dependency (jalankan pertama kali)"
    echo "  start    — Jalankan bot di background"
    echo "  stop     — Hentikan bot"
    echo "  restart  — Restart bot"
    echo "  status   — Cek status bot"
    echo "  log      — Lihat log realtime"
    exit 1
    ;;
esac
