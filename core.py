"""
core.py — Semua logic automation (tanpa GUI).
Dipakai oleh bot.py (Telegram command bot).
"""

import requests
import random
import time
import os
import json
import re
import base64
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse


# ─────────────────────────────────────────────────────────────────────────────
# Settings helpers
# ─────────────────────────────────────────────────────────────────────────────

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "settings.json")

DEFAULT_SETTINGS = {
    "tg_token": "",
    "tg_chat_id": "",
    "serpapi_key": "",
    "serpapi_loc": "Jakarta, Indonesia",
    "proxy_host": "",
    "proxy_type": "http",
    "proxy_user": "",
    "proxy_pass": "",
    "host": "Google",
    "max_browsers": 1,
    "direction": "",
    "auto_minutes": "60",
    "auto_active": "off",
    "admin_ids": [],
}


def load_settings() -> dict:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
            merged = {**DEFAULT_SETTINGS, **data}
            return merged
        except Exception:
            pass
    return dict(DEFAULT_SETTINGS)


def save_settings(config: dict):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(config, f, indent=2)


# ─────────────────────────────────────────────────────────────────────────────
# Proxy helpers
# ─────────────────────────────────────────────────────────────────────────────

def build_proxy_dict(proxy_host, proxy_type, proxy_user, proxy_pass):
    if not proxy_host:
        return None
    if proxy_user and proxy_pass:
        return {
            "http":  f"{proxy_type}://{proxy_user}:{proxy_pass}@{proxy_host}",
            "https": f"{proxy_type}://{proxy_user}:{proxy_pass}@{proxy_host}",
        }
    return {
        "http":  f"{proxy_type}://{proxy_host}",
        "https": f"{proxy_type}://{proxy_host}",
    }


def check_proxy(proxy_host, proxy_type, proxy_user, proxy_pass) -> str:
    """Test proxy. Returns status string."""
    if not proxy_host:
        return "❌ Tidak ada proxy host yang dikonfigurasi."
    proxy_dict = build_proxy_dict(proxy_host, proxy_type, proxy_user, proxy_pass)
    try:
        res = requests.get("http://httpbin.org/ip", proxies=proxy_dict, timeout=8)
        if res.status_code == 200:
            ip = res.json().get("origin", "?")
            return f"✅ Proxy OK! IP terdeteksi: `{ip}`"
        return f"❌ Proxy gagal. Status: {res.status_code}"
    except Exception as e:
        return f"❌ Koneksi gagal: {str(e).splitlines()[0][:80]}"


def get_ip_info(proxy_host, proxy_type, proxy_user, proxy_pass):
    """Fetch IP + location info via ip-api.com."""
    proxy_dict = build_proxy_dict(proxy_host, proxy_type, proxy_user, proxy_pass)
    try:
        res = requests.get("http://ip-api.com/json/", proxies=proxy_dict, timeout=6).json()
        ip = res.get("query", proxy_host.split(":")[0] if proxy_host else "Local")
        if res.get("status") == "success":
            loc = f"{res.get('city', '?')}, {res.get('country', '?')}"
        else:
            loc = "Lookup Blocked"
        return ip, loc
    except Exception:
        return proxy_host.split(":")[0] if proxy_host else "Local", "Lookup Failed"


# ─────────────────────────────────────────────────────────────────────────────
# AMP Detection
# ─────────────────────────────────────────────────────────────────────────────

MOBILE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 11; Pixel 5) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/112.0.0.0 Mobile Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
}

AMP_URL_PATTERNS = [
    "/amp/", "/amp?", "?amp=1", "&amp=1",
    "ampproject.org", "/amp#", ".amp.html", "-amp.html",
]


def check_amp_for_url(link: str):
    """
    5-layer AMP detector.
    Returns (is_amp: bool, amp_url: str | None)
    """
    # Layer 1: URL pattern
    for pat in AMP_URL_PATTERNS:
        if pat in link:
            return True, link

    parsed = urlparse(link)
    base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"
    html = ""
    try:
        resp = requests.get(link, timeout=10, allow_redirects=True, headers=MOBILE_HEADERS)
        ct = resp.headers.get("Content-Type", "")
        if "html" in ct:
            html = resp.text[:80_000]
    except Exception:
        html = ""

    if html:
        # Layer 2: <link rel="amphtml">
        amphtml_match = re.search(
            r'<link[^>]+rel=["\']amphtml["\'][^>]*href=["\']([^"\']+)["\']',
            html, re.IGNORECASE
        ) or re.search(
            r'<link[^>]+href=["\']([^"\']+)["\'][^>]*rel=["\']amphtml["\']',
            html, re.IGNORECASE
        )
        if amphtml_match:
            return True, amphtml_match.group(1).strip()

        # Layer 3: <html ⚡> or <html amp>
        if re.search(r'<html[^>]+(?:amp\b|⚡)', html[:2000], re.IGNORECASE):
            return True, link

        # Layer 4: AMP runtime markers
        for marker in [
            "cdn.ampproject.org/v0.js",
            "cdn.ampproject.org/v0/",
            "<style amp-boilerplate",
            'name="generator"[^>]*content="amp"',
            'content="amp"[^>]*name="generator"',
        ]:
            if re.search(marker, html[:30_000], re.IGNORECASE):
                return True, link

    # Layer 5: HEAD probe
    for amp_url in [f"{base_url}/amp", f"{base_url}/amp/", f"{link}?amp=1"]:
        try:
            r = requests.head(amp_url, timeout=6, allow_redirects=True, headers=MOBILE_HEADERS)
            if r.status_code == 200:
                final_url = r.url
                if final_url.rstrip("/") != parsed.scheme + "://" + parsed.netloc:
                    return True, amp_url
        except Exception:
            pass

    return False, None


# ─────────────────────────────────────────────────────────────────────────────
# Display helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_domain(url: str) -> str:
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return url


def get_amp_display(amp_url: str) -> str:
    try:
        parsed = urlparse(amp_url)
        domain = parsed.netloc or ""
        if domain.startswith("www."):
            domain = domain[4:]
        path = parsed.path.rstrip("/")
        if path.endswith("/amp"):
            path = path[:-4]
        if path and path != "/":
            return domain + path
        return domain
    except Exception:
        return amp_url


# ─────────────────────────────────────────────────────────────────────────────
# Google via SearchAPI
# ─────────────────────────────────────────────────────────────────────────────

def make_uule(location_name: str) -> str:
    loc_bytes = location_name.encode("utf-8")
    length_byte = bytes([min(len(loc_bytes), 255)])
    payload = length_byte + loc_bytes
    return "w+CAIQICI" + base64.b64encode(payload).decode("ascii")


def run_google_serpapi(keywords: list, cfg: dict, log_cb=None) -> list:
    """
    Search via SearchAPI, detect AMP, return all_results list.
    log_cb(text) dipanggil untuk tiap log line.
    Returns: [(keyword, [(href, amp_url, is_amp), ...]), ...]
    """
    def log(msg):
        if log_cb:
            log_cb(msg)

    serpapi_key = cfg.get("serpapi_key", "")
    serpapi_loc = cfg.get("serpapi_loc", "Jakarta, Indonesia")
    loc_display = serpapi_loc.split(",")[0].strip()
    all_results = []

    for kw_idx, keyword in enumerate(keywords):
        log(f"🔑 [{kw_idx+1}/{len(keywords)}] SearchAPI: *{keyword}*")

        uule = make_uule(serpapi_loc)
        params = {
            "engine":  "google_rank_tracking",
            "q":       keyword,
            "api_key": serpapi_key,
            "uule":    uule,
            "gl":      "id",
            "hl":      "id",
            "lr":      "lang_id",
            "cr":      "countryID",
            "num":     10,
            "device":  "mobile",
            "pws":     "0",
            "nfpr":    "1",
            "safe":    "off",
        }
        log(f"🌐 UULE({serpapi_loc}) | gl=id | hl=id | mobile")
        try:
            resp = requests.get(
                "https://www.searchapi.io/api/v1/search",
                params=params, timeout=30
            )
            data = resp.json()
        except Exception as e:
            log(f"❌ SearchAPI request gagal: {str(e)[:80]}")
            all_results.append((keyword, []))
            continue

        if data.get("search_metadata", {}).get("status") not in ("Success", None):
            err = data.get("error", "Unknown error")
            log(f"❌ SearchAPI error: {err}")
            all_results.append((keyword, []))
            continue

        organic = data.get("organic_results", [])
        log(f"✅ {len(organic)} hasil organik dari SearchAPI")

        result_links = []
        for idx, item in enumerate(organic):
            link = item.get("link", "")
            if not link:
                continue
            log(f"🔍 Cek AMP [{idx+1}/{len(organic)}]: {link[:65]}")
            is_amp, amp_url = check_amp_for_url(link)
            icon = "🟢" if is_amp else "🔴"
            log(f"{icon} [{idx+1}] AMP {'Aktif' if is_amp else 'tidak aktif'}: {link[:65]}")
            result_links.append((link, amp_url, is_amp))
            # Delay antar AMP check
            for sec in range(5, 0, -1):
                time.sleep(1)

        amp_active   = sum(1 for _, _, m in result_links if m)
        amp_inactive = sum(1 for _, _, m in result_links if not m)
        log(f"🟢 {len(result_links)} links | {amp_active} AMP Aktif | {amp_inactive} tidak aktif")
        all_results.append((keyword, result_links))
        time.sleep(random.uniform(0.5, 1.0))

    return all_results


# ─────────────────────────────────────────────────────────────────────────────
# Playwright path (Bing / Yahoo / DuckDuckGo) — headless for VPS
# ─────────────────────────────────────────────────────────────────────────────

def run_browser_search(keywords: list, cfg: dict, log_cb=None) -> list:
    """
    Jalankan pencarian via Playwright (headless). Untuk Bing/Yahoo/DuckDuckGo.
    Returns: [(keyword, [(href, amp_url, is_amp), ...]), ...]
    """
    from playwright.sync_api import sync_playwright

    def log(msg):
        if log_cb:
            log_cb(msg)

    host       = cfg.get("host", "Bing")
    proxy_host = cfg.get("proxy_host", "")
    proxy_type = cfg.get("proxy_type", "http")
    proxy_user = cfg.get("proxy_user", "")
    proxy_pass = cfg.get("proxy_pass", "")

    if proxy_type.lower() == "socks5" and proxy_user:
        log("❌ Chromium tidak support SOCKS5 dengan password! Ganti ke mode 'http'.")
        return []

    log("🚀 Meluncurkan browser (headless)...")

    proxy_settings = None
    if proxy_host:
        server_url = f"{proxy_type}://{proxy_host}"
        proxy_settings = {"server": server_url}
        if proxy_user and proxy_pass:
            proxy_settings["username"] = proxy_user
            proxy_settings["password"] = proxy_pass

    launch_args = [
        '--disable-blink-features=AutomationControlled',
        '--disable-infobars',
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
    ]

    all_results = []

    with sync_playwright() as p:
        pixel5 = p.devices["Pixel 5"]
        mobile_ctx_args = {**pixel5, "locale": "id-ID"}

        if proxy_settings:
            browser = p.chromium.launch(
                headless=True, args=launch_args,
                proxy={"server": "http://per-context"}
            )
            context = browser.new_context(proxy=proxy_settings, **mobile_ctx_args)
        else:
            browser = p.chromium.launch(headless=True, args=launch_args)
            context = browser.new_context(**mobile_ctx_args)

        context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        page = context.new_page()

        try:
            ip_used, ip_location = get_ip_info(proxy_host, proxy_type, proxy_user, proxy_pass)
            log(f"📍 IP: {ip_used} | Lokasi: {ip_location}")

            for kw_idx, keyword in enumerate(keywords):
                log(f"🔑 [{kw_idx+1}/{len(keywords)}] Searching: *{keyword}*")

                if host == "Bing":
                    page.goto("https://www.bing.com")
                    time.sleep(random.uniform(1.5, 3.0))
                    page.wait_for_selector("input[name='q']")
                    page.click("input[name='q']")
                    time.sleep(random.uniform(0.5, 1.5))
                    page.type("input[name='q']", keyword, delay=random.randint(100, 250))
                    page.press("input[name='q']", "Enter")
                elif host == "DuckDuckGo":
                    page.goto("https://duckduckgo.com")
                    time.sleep(random.uniform(1.5, 3.0))
                    page.wait_for_selector("input[name='q']")
                    page.click("input[name='q']")
                    time.sleep(random.uniform(0.5, 1.5))
                    page.type("input[name='q']", keyword, delay=random.randint(100, 250))
                    page.press("input[name='q']", "Enter")
                elif host == "Yahoo":
                    page.goto("https://search.yahoo.com")
                    time.sleep(random.uniform(1.5, 3.0))
                    page.wait_for_selector("input[name='p']")
                    page.click("input[name='p']")
                    time.sleep(random.uniform(0.5, 1.5))
                    page.type("input[name='p']", keyword, delay=random.randint(100, 250))
                    page.press("input[name='p']", "Enter")

                log("⏳ Menunggu hasil...")
                time.sleep(3)

                # Extract links
                raw_data = []
                try:
                    raw_data = page.evaluate("""
                        () => {
                            const seen = new Set();
                            const results = [];
                            const skip = [
                                'google.com','googleapis.com','gstatic.com',
                                'accounts.google','support.google','maps.google',
                                'webcache.google','translate.google',
                                'javascript:','/search?','/intl/',
                                '/preferences','/settings','/webhp'
                            ];
                            document.querySelectorAll('a[href]').forEach(a => {
                                const href = a.href;
                                if (!href || !href.startsWith('http')) return;
                                if (seen.has(href)) return;
                                if (skip.some(s => href.includes(s))) return;
                                seen.add(href);
                                results.push({ url: href });
                            });
                            return results;
                        }
                    """)
                    log(f"🔗 {len(raw_data)} link ditemukan di halaman 1")
                except Exception as e:
                    log(f"❌ Link extract error: {str(e)[:60]}")

                result_links = []
                for idx, item in enumerate(raw_data):
                    url_href = item.get("url", "")
                    log(f"🔍 Cek AMP [{idx+1}/{len(raw_data)}]: {url_href[:65]}")
                    is_amp, amp_url = check_amp_for_url(url_href)
                    icon = "🟢" if is_amp else "🔴"
                    log(f"{icon} [{idx+1}] AMP {'Aktif' if is_amp else 'tidak aktif'}: {url_href[:65]}")
                    result_links.append((url_href, amp_url, is_amp))

                amp_active   = sum(1 for _, _, m in result_links if m)
                amp_inactive = sum(1 for _, _, m in result_links if not m)
                log(f"🟢 {len(result_links)} links | {amp_active} Aktif | {amp_inactive} tidak aktif")
                all_results.append((keyword, result_links))
                time.sleep(random.uniform(1.5, 3.0))

        except Exception as e:
            log(f"❌ Browser error: {str(e).splitlines()[0][:80]}")
        finally:
            browser.close()

    return all_results


# ─────────────────────────────────────────────────────────────────────────────
# Telegram senders
# ─────────────────────────────────────────────────────────────────────────────

def build_combined_message(all_results: list, loc_display: str) -> str:
    sep = "─" * 32
    wib = timezone(timedelta(hours=7))
    now_wib = datetime.now(wib)
    tgl_wib = now_wib.strftime("%d %B %Y")
    jam_wib = now_wib.strftime("%H:%M:%S")

    sections = []
    total_active = 0
    total_inactive = 0

    for keyword, result_links in all_results:
        lines = []
        for i, (href, amp_url, is_match) in enumerate(result_links):
            domain = get_domain(href)
            if is_match:
                total_active += 1
                amp_display = get_amp_display(amp_url) if amp_url else "?"
                lines.append(f"{i+1}. {domain}")
                lines.append(f"   AMP: 🟢 {amp_display}")
            else:
                total_inactive += 1
                lines.append(f"{i+1}. {domain}")
                lines.append(f"   AMP: 🔴 tidak aktif")

        links_text = "\n".join(lines) if lines else "(Tidak ada hasil)"
        sections.append(f"🔑 Keyword: {keyword}\n{links_text}")

    combined_body = ("\n\n" + sep + "\n\n").join(sections)

    message = (
        f"{sep}\n"
        f"🏁 Google Rank Report + AMP Detect by ITSPAB\n"
        f"{sep}\n"
        f"📅 {tgl_wib}  🕐 {jam_wib} WIB\n"
        f"source: SerpAPI | loc: 📍 {loc_display}\n"
        f"📊 Total: {total_active} AMP Aktif | {total_inactive} tidak aktif\n"
        f"{sep}\n\n"
        f"{combined_body}"
    )
    return message


def send_telegram_message(token: str, chat_id: str, text: str) -> bool:
    """Send message to Telegram, splitting if > 4096 chars."""
    tg_url = f"https://api.telegram.org/bot{token}/sendMessage"
    MAX_LEN = 4096
    chunks = [text[i:i+MAX_LEN] for i in range(0, len(text), MAX_LEN)]
    for chunk in chunks:
        try:
            resp = requests.post(
                tg_url,
                data={"chat_id": chat_id, "text": chunk, "parse_mode": "Markdown"},
                timeout=15
            )
            if resp.status_code != 200:
                return False
        except Exception:
            return False
    return True
