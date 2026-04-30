# Bot Maker Pro — VPS Edition 🤖

Bot Telegram command-based yang menggantikan GUI desktop.
Semua fitur GUI dikonversi menjadi command Telegram — bisa jalan 24/7 di VPS tanpa layar.

---

## 📁 Struktur File

```
bot_vps/
├── bot.py          ← Bot utama Telegram (asyncio, polling)
├── core.py         ← Logic automation (AMP detect, SearchAPI, Playwright)
├── settings.json   ← Konfigurasi (token, proxy, dll)
├── requirements.txt← Dependencies Python
└── run_vps.sh      ← Script manage bot di VPS Linux
```

---

## 🚀 Cara Deploy ke VPS

### 1. Upload file ke VPS
```bash
scp -r bot_vps/ user@your-vps-ip:/home/user/botcheck/
```

### 2. Install dependencies (jalankan sekali)
```bash
cd /home/user/botcheck/bot_vps
chmod +x run_vps.sh
./run_vps.sh install
```

### 3. Edit settings.json
```bash
nano settings.json
```
Isi minimal:
- `tg_token` — Token bot Telegram kamu
- `tg_chat_id` — Chat ID tujuan laporan
- `serpapi_key` — Key dari searchapi.io

### 4. Jalankan bot
```bash
./run_vps.sh start
```

### 5. Cek status
```bash
./run_vps.sh status
./run_vps.sh log      # Lihat log realtime
```

---

## 📋 Daftar Command Bot

| Command | Fungsi |
|---------|--------|
| `/start` | Sambutan + daftar perintah |
| `/help` | Tampilkan semua perintah |
| `/run kw1, kw2` | Jalankan AMP check |
| `/stop` | Hentikan task berjalan |
| `/status` | Status bot saat ini |
| `/config` | Lihat semua setting |
| `/set host Google` | Ganti search engine |
| `/set location Jakarta` | Ganti lokasi target |
| `/set serpapi_key XXX` | Set API key |
| `/set proxy host:port` | Set proxy |
| `/set proxy_user nama` | Set username proxy |
| `/set proxy_pass pass` | Set password proxy |
| `/setauto 60` | Auto repeat tiap N menit |
| `/stopauto` | Matikan auto repeat |
| `/checkproxy` | Test koneksi proxy |

---

## 🔒 Batasi Akses (Opsional)

Agar hanya user tertentu yang bisa pakai bot, kirim command:
```
/set admin_id 123456789
```
Ganti `123456789` dengan Telegram user ID kamu.

---

## ⚙️ Tips VPS

- Pakai `./run_vps.sh start` bukan `python3 bot.py` langsung (sudah pakai `nohup`)
- Log tersimpan di `bot.log`
- Untuk auto-start saat VPS reboot, tambahkan ke crontab:
  ```bash
  @reboot cd /home/user/botcheck/bot_vps && ./run_vps.sh start
  ```
