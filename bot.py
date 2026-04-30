"""
bot.py — Telegram Command Bot (VPS Ready, Headless)
Menggantikan semua fungsi GUI menjadi perintah Telegram.

Jalankan:
    python bot.py

Commands:
    /start        - Sambutan + daftar perintah
    /help         - Daftar lengkap perintah
    /run kw1, kw2 - Jalankan task
    /status       - Status task saat ini
    /stop         - Hentikan task
    /config       - Lihat semua setting
    /set key val  - Ubah satu setting
    /setauto 60   - Auto repeat tiap N menit
    /stopauto     - Matikan auto repeat
    /checkproxy   - Test proxy
"""

import asyncio
import logging
import threading
from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

import core

# ─────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Global state
# ─────────────────────────────────────────────────────────────────────────────
_task_running   = False          # apakah task sedang berjalan
_task_stop_flag = False          # sinyal berhenti ke task
_auto_job       = None           # referensi auto-repeat job
_task_thread    = None           # thread yang menjalankan task

# ─────────────────────────────────────────────────────────────────────────────
# Auth helper
# ─────────────────────────────────────────────────────────────────────────────

def is_authorized(update: Update) -> bool:
    """Cek apakah user diizinkan. Jika admin_ids kosong, semua diizinkan."""
    cfg = core.load_settings()
    admin_ids = cfg.get("admin_ids", [])
    if not admin_ids:
        return True
    return str(update.effective_user.id) in [str(a) for a in admin_ids]


async def deny(update: Update):
    await update.message.reply_text("⛔ Kamu tidak memiliki izin untuk menggunakan bot ini.")

# ─────────────────────────────────────────────────────────────────────────────
# /start and /help
# ─────────────────────────────────────────────────────────────────────────────

HELP_TEXT = """
╔══════════════════════════════╗
       🤖 *Bot Maker Pro*
    _Google Rank + AMP Detector_
╚══════════════════════════════╝

━━━━━━━ 🚀 *TASK* ━━━━━━━
`/run kw1, kw2, ...`
  └ Jalankan AMP check untuk keyword

`/stop`
  └ Hentikan task yang sedang berjalan

`/status`
  └ Cek status bot saat ini

━━━━━━━ ⏱ *AUTO REPEAT* ━━━━━━━
`/setauto <menit>`
  └ Otomatis ulang task tiap N menit
  └ Contoh: `/setauto 60`

`/stopauto`
  └ Matikan jadwal auto repeat

━━━━━━━ ⚙️ *KONFIGURASI* ━━━━━━━
`/config`
  └ Lihat semua setting saat ini

`/set host <nilai>`
  └ Pilih: `Google` `Bing` `Yahoo` `DuckDuckGo`

`/set location <kota, negara>`
  └ Contoh: `/set location Jakarta, Indonesia`

`/set serpapi_key <key>`
  └ API key dari searchapi.io

`/set auto_minutes <menit>`
  └ Interval auto repeat (default: 60)

━━━━━━━ 🌐 *PROXY* ━━━━━━━
`/set proxy <host:port>`
  └ Contoh: `/set proxy 95.135.1.1:5010`

`/set proxy_type <tipe>`
  └ Pilih: `http` `https` `socks5`

`/set proxy_user <username>`
  └ Username proxy (jika ada auth)

`/set proxy_pass <password>`
  └ Password proxy (jika ada auth)

`/checkproxy`
  └ Test koneksi proxy sekarang

━━━━━━━ 🔑 *TELEGRAM* ━━━━━━━
`/set tg_token <token>`
  └ Token bot Telegram

`/set tg_chat_id <id>`
  └ Chat ID tujuan laporan

`/set admin_id <user_id>`
  └ Tambah admin (batasi akses bot)

━━━━━━━ ℹ️ *INFO* ━━━━━━━
`/start` — Sambutan bot
`/help`  — Tampilkan menu ini
"""


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return await deny(update)
    await update.message.reply_text(
        f"👋 Halo *{update.effective_user.first_name}*!\n\n{HELP_TEXT}",
        parse_mode="Markdown"
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return await deny(update)
    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")

# ─────────────────────────────────────────────────────────────────────────────
# /config
# ─────────────────────────────────────────────────────────────────────────────

async def cmd_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return await deny(update)
    cfg = core.load_settings()
    proxy_pass = cfg.get("proxy_pass", "")
    masked_pass = ("*" * len(proxy_pass)) if proxy_pass else "(kosong)"

    text = (
        "⚙️ *Konfigurasi Saat Ini*\n"
        "─────────────────────────\n"
        f"🔍 Host: `{cfg.get('host', 'Google')}`\n"
        f"📍 Lokasi: `{cfg.get('serpapi_loc', '-')}`\n"
        f"🔑 SearchAPI Key: `{cfg.get('serpapi_key', '-')[:8]}...`\n"
        f"🌐 Proxy: `{cfg.get('proxy_host', '(kosong)')}`\n"
        f"   Type: `{cfg.get('proxy_type', 'http')}`\n"
        f"   User: `{cfg.get('proxy_user', '(kosong)')}`\n"
        f"   Pass: `{masked_pass}`\n"
        f"🤖 Telegram Token: `{cfg.get('tg_token', '-')[:12]}...`\n"
        f"💬 Chat ID: `{cfg.get('tg_chat_id', '-')}`\n"
        f"⏱ Auto Repeat: `{cfg.get('auto_active', 'off')}` (setiap `{cfg.get('auto_minutes', '60')} menit`)\n"
        f"👮 Admin IDs: `{cfg.get('admin_ids', [])}`\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# ─────────────────────────────────────────────────────────────────────────────
# /set key value
# ─────────────────────────────────────────────────────────────────────────────

VALID_KEYS = {
    "host":         ("host",          "Host pencarian (Google/Bing/Yahoo/DuckDuckGo)"),
    "location":     ("serpapi_loc",   "Lokasi (e.g. Jakarta, Indonesia)"),
    "serpapi_key":  ("serpapi_key",   "SearchAPI key"),
    "proxy":        ("proxy_host",    "Proxy host:port"),
    "proxy_type":   ("proxy_type",    "Tipe proxy (http/https/socks5)"),
    "proxy_user":   ("proxy_user",    "Username proxy"),
    "proxy_pass":   ("proxy_pass",    "Password proxy"),
    "auto_minutes": ("auto_minutes",  "Interval auto repeat (menit)"),
    "tg_token":     ("tg_token",      "Telegram bot token"),
    "tg_chat_id":   ("tg_chat_id",    "Telegram chat ID"),
    "admin_id":     ("admin_ids",     "Tambah admin ID (append)"),
}


async def cmd_set(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return await deny(update)
    if len(context.args) < 2:
        keys_list = "\n".join(f"  `{k}` — {v[1]}" for k, v in VALID_KEYS.items())
        await update.message.reply_text(
            f"❓ Cara pakai: `/set <key> <value>`\n\nKey yang tersedia:\n{keys_list}",
            parse_mode="Markdown"
        )
        return

    key = context.args[0].lower()
    value = " ".join(context.args[1:])

    if key not in VALID_KEYS:
        await update.message.reply_text(f"❌ Key tidak dikenal: `{key}`\nGunakan /set tanpa argumen untuk melihat daftar key.", parse_mode="Markdown")
        return

    cfg_key = VALID_KEYS[key][0]
    cfg = core.load_settings()

    if cfg_key == "admin_ids":
        # Append mode untuk admin_id
        admin_ids = cfg.get("admin_ids", [])
        if value not in [str(a) for a in admin_ids]:
            admin_ids.append(value)
        cfg["admin_ids"] = admin_ids
        await update.message.reply_text(f"✅ Admin ID `{value}` ditambahkan.", parse_mode="Markdown")
    else:
        cfg[cfg_key] = value
        await update.message.reply_text(f"✅ `{key}` diset ke: `{value}`", parse_mode="Markdown")

    core.save_settings(cfg)

# ─────────────────────────────────────────────────────────────────────────────
# /checkproxy
# ─────────────────────────────────────────────────────────────────────────────

async def cmd_checkproxy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return await deny(update)
    await update.message.reply_text("⏳ Mengecek proxy...")
    cfg = core.load_settings()
    result = await asyncio.get_event_loop().run_in_executor(
        None,
        core.check_proxy,
        cfg.get("proxy_host", ""),
        cfg.get("proxy_type", "http"),
        cfg.get("proxy_user", ""),
        cfg.get("proxy_pass", ""),
    )
    await update.message.reply_text(result, parse_mode="Markdown")

# ─────────────────────────────────────────────────────────────────────────────
# /status
# ─────────────────────────────────────────────────────────────────────────────

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return await deny(update)
    global _task_running, _auto_job
    cfg = core.load_settings()
    running_txt = "🟢 *RUNNING*" if _task_running else "⚪ *IDLE*"
    auto_txt = f"⏱ Auto: setiap `{cfg.get('auto_minutes','60')} menit`" if _auto_job else "⏱ Auto: *OFF*"
    await update.message.reply_text(
        f"📊 *Status Bot*\n"
        f"Task: {running_txt}\n"
        f"{auto_txt}\n"
        f"Host: `{cfg.get('host', 'Google')}`",
        parse_mode="Markdown"
    )

# ─────────────────────────────────────────────────────────────────────────────
# /stop
# ─────────────────────────────────────────────────────────────────────────────

async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return await deny(update)
    global _task_stop_flag, _task_running
    if not _task_running:
        await update.message.reply_text("ℹ️ Tidak ada task yang sedang berjalan.")
        return
    _task_stop_flag = True
    await update.message.reply_text("🛑 Sinyal stop dikirim. Task akan berhenti setelah langkah saat ini selesai.")

# ─────────────────────────────────────────────────────────────────────────────
# /setauto & /stopauto
# ─────────────────────────────────────────────────────────────────────────────

async def cmd_setauto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return await deny(update)
    global _auto_job

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("❓ Cara pakai: `/setauto <menit>`\nContoh: `/setauto 60`", parse_mode="Markdown")
        return

    minutes = int(context.args[0])
    if minutes <= 0:
        await update.message.reply_text("❌ Menit harus > 0.")
        return

    # Simpan ke settings
    cfg = core.load_settings()
    cfg["auto_minutes"] = str(minutes)
    cfg["auto_active"] = "on"
    core.save_settings(cfg)

    # Hapus job lama jika ada
    if _auto_job:
        _auto_job.schedule_removal()
        _auto_job = None

    # Buat job baru
    interval_seconds = minutes * 60
    _auto_job = context.job_queue.run_repeating(
        _auto_task_job,
        interval=interval_seconds,
        first=interval_seconds,
        chat_id=update.effective_chat.id,
        name="auto_task",
    )
    await update.message.reply_text(
        f"✅ Auto repeat aktif! Task akan dijalankan setiap *{minutes} menit*.\n"
        f"Gunakan /stopauto untuk membatalkan.",
        parse_mode="Markdown"
    )


async def cmd_stopauto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return await deny(update)
    global _auto_job
    if not _auto_job:
        await update.message.reply_text("ℹ️ Auto repeat tidak sedang aktif.")
        return
    _auto_job.schedule_removal()
    _auto_job = None
    cfg = core.load_settings()
    cfg["auto_active"] = "off"
    core.save_settings(cfg)
    await update.message.reply_text("✅ Auto repeat dimatikan.")


async def _auto_task_job(context: ContextTypes.DEFAULT_TYPE):
    """Dipanggil otomatis oleh job_queue untuk auto repeat."""
    chat_id = context.job.chat_id
    cfg = core.load_settings()
    keywords_raw = cfg.get("last_keywords", "")
    if not keywords_raw:
        await context.bot.send_message(chat_id, "⚠️ Auto repeat: tidak ada keyword tersimpan. Jalankan /run dulu.")
        return
    keywords = [k.strip() for k in keywords_raw.split(",") if k.strip()]
    await context.bot.send_message(chat_id, f"⏱ *Auto Repeat* dimulai! Keywords: {', '.join(keywords)}", parse_mode="Markdown")
    await _execute_task(context.bot, chat_id, keywords, cfg)

# ─────────────────────────────────────────────────────────────────────────────
# /run
# ─────────────────────────────────────────────────────────────────────────────

async def cmd_run(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return await deny(update)
    global _task_running

    if _task_running:
        await update.message.reply_text("⚠️ Task masih berjalan! Gunakan /stop terlebih dahulu.")
        return

    if not context.args:
        await update.message.reply_text(
            "❓ Cara pakai: `/run keyword1, keyword2`\nContoh: `/run jasa seo jakarta, beli domain murah`",
            parse_mode="Markdown"
        )
        return

    raw = " ".join(context.args)
    keywords = [k.strip() for k in raw.split(",") if k.strip()]
    if not keywords:
        await update.message.reply_text("❌ Keyword tidak boleh kosong.")
        return

    # Simpan keyword terakhir untuk auto repeat
    cfg = core.load_settings()
    cfg["last_keywords"] = ", ".join(keywords)
    core.save_settings(cfg)

    await update.message.reply_text(
        f"🚀 Task dimulai!\n"
        f"🔑 Keywords: *{', '.join(keywords)}*\n"
        f"🔍 Host: *{cfg.get('host', 'Google')}*\n\n"
        f"_Log akan dikirim ke sini saat proses berjalan..._",
        parse_mode="Markdown"
    )
    await _execute_task(context.bot, update.effective_chat.id, keywords, cfg)


async def _execute_task(bot, chat_id: int, keywords: list, cfg: dict):
    """Core task executor — diam selama proses, kirim 1 laporan akhir."""
    global _task_running, _task_stop_flag

    _task_running   = True
    _task_stop_flag = False

    host = cfg.get("host", "Google")
    loop = asyncio.get_event_loop()

    # Log hanya ke console/file, tidak ke Telegram
    def sync_log(msg: str):
        logger.info(msg)

    try:
        await bot.send_message(chat_id, "⏳ Task berjalan, mohon tunggu...")

        if host == "Google":
            if not cfg.get("serpapi_key"):
                await bot.send_message(
                    chat_id,
                    "❌ SearchAPI Key belum dikonfigurasi!\nGunakan: `/set serpapi_key XXXXX`",
                    parse_mode="Markdown"
                )
                return

            all_results = await loop.run_in_executor(
                None,
                core.run_google_serpapi,
                keywords, cfg, sync_log
            )
        else:
            all_results = await loop.run_in_executor(
                None,
                core.run_browser_search,
                keywords, cfg, sync_log
            )

        # ── Kirim 1 laporan akhir ─────────────────────────────────────────────
        if all_results:
            loc_display = cfg.get("serpapi_loc", "Jakarta, Indonesia").split(",")[0].strip()
            message = core.build_combined_message(all_results, loc_display)
            MAX_LEN = 4000
            chunks = [message[i:i+MAX_LEN] for i in range(0, len(message), MAX_LEN)]
            for chunk in chunks:
                # Kirim plain text — hindari Markdown error karena karakter URL
                await bot.send_message(chat_id, chunk)
        else:
            await bot.send_message(chat_id, "⚠️ Tidak ada hasil yang ditemukan.")

    except Exception as e:
        logger.exception("Task error")
        await bot.send_message(chat_id, f"❌ Error: {str(e)[:200]}")
    finally:
        _task_running   = False
        _task_stop_flag = False

# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    cfg = core.load_settings()
    token = cfg.get("tg_token", "")
    if not token:
        raise RuntimeError(
            "❌ Telegram token belum diisi!\n"
            "Edit settings.json dan isi 'tg_token', lalu jalankan lagi."
        )

    app = (
        Application.builder()
        .token(token)
        .build()
    )

    # Register handlers
    handlers = [
        ("start",       cmd_start),
        ("help",        cmd_help),
        ("config",      cmd_config),
        ("set",         cmd_set),
        ("run",         cmd_run),
        ("stop",        cmd_stop),
        ("status",      cmd_status),
        ("setauto",     cmd_setauto),
        ("stopauto",    cmd_stopauto),
        ("checkproxy",  cmd_checkproxy),
    ]
    for name, fn in handlers:
        app.add_handler(CommandHandler(name, fn))

    logger.info("Bot started. Polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
