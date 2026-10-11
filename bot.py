"""
Phone Deal Alert Bot (Amazon.in + Flipkart) - Telegram
Run:  pip install -r requirements.txt && cp .env.example .env && python bot.py
"""
import os, re, sqlite3, logging, asyncio, random
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
SCAN_MINUTES = int(os.getenv("SCAN_MINUTES", "30"))
DB = "deals.db"
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("dealbot")

# Deployment platforms occasionally expose a stale local proxy through the
# environment.  Deal sites must be reached directly (or through ScraperAPI),
# otherwise every scan fails before it can evaluate an alert.
HTTP = requests.Session()
HTTP.trust_env = False


class HealthCheckHandler(BaseHTTPRequestHandler):
    """Minimal endpoint used by Render to verify that the service is running."""

    def do_GET(self):
        body = b"Bot is running\n"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        log.info("HTTP %s - %s", self.client_address[0], format % args)


def start_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = ThreadingHTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.daemon_threads = True
    thread = Thread(target=server.serve_forever, name="health-server", daemon=True)
    thread.start()
    log.info("HTTP server started on 0.0.0.0:%s", port)
    return server, thread

# Scan ke liye search pages - yahan aur URLs/queries add kar sakte ho
SEARCH_URLS = {
    "amazon": [
        "https://www.amazon.in/s?k=smartphone",
        "https://www.amazon.in/s?k=5g+mobile+phone",
    ],
    "flipkart": [
        "https://www.flipkart.com/search?q=mobiles",
        "https://www.flipkart.com/search?q=5g+mobile",
    ],
}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-IN,en;q=0.9",
}

# ---------------- DB ----------------
def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            chat_id INTEGER PRIMARY KEY,
            min_discount INTEGER DEFAULT 60,   -- MRP se kam se kam itna % off
            min_drop INTEGER DEFAULT 20,       -- ya pichle price se itna % gira
            max_price INTEGER DEFAULT 0        -- 0 = koi limit nahi
        );
        CREATE TABLE IF NOT EXISTS products(
            url TEXT PRIMARY KEY, site TEXT, title TEXT,
            price INTEGER, mrp INTEGER, lowest INTEGER, updated TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS alerted(chat_id INTEGER, url TEXT, price INTEGER, PRIMARY KEY(chat_id, url, price));
        """)

# ---------------- Fetchers ----------------
def _num(txt):
    m = re.findall(r"[\d,]+", txt or "")
    return int(m[0].replace(",", "")) if m and m[0].replace(",", "") else None

def fetch_html(url):
    SCRAPER_KEY = os.getenv("SCRAPER_KEY")
    if SCRAPER_KEY:
        r = HTTP.get("https://api.scraperapi.com", params={
            "api_key": SCRAPER_KEY, "url": url, "country_code": "in"
        }, timeout=60)
    else:
        r = HTTP.get(url, headers=HEADERS, timeout=20)
    if r.status_code != 200 or "captcha" in r.text.lower()[:5000]:
        log.warning("Blocked/failed %s (%s)", url, r.status_code)
        return None
    return r.text

def parse_amazon(html):
    soup, out = BeautifulSoup(html, "html.parser"), []
    for card in soup.select('div[data-component-type="s-search-result"]'):
        a = card.select_one("a[href*='/dp/']") or card.select_one("h2 a")
        title = card.select_one("h2")
        price = card.select_one("span.a-price:not(.a-text-price) span.a-offscreen")
        mrp = card.select_one("span.a-price.a-text-price span.a-offscreen")
        if not (a and title and price):
            continue
        asin = re.search(r"/dp/([A-Z0-9]{10})", a.get("href", ""))
        if not asin:
            continue
        p = _num(price.text)
        out.append(dict(site="amazon", url=f"https://www.amazon.in/dp/{asin.group(1)}",
                        title=title.get_text(" ", strip=True)[:120], price=p,
                        mrp=_num(mrp.text) if mrp else p))
    return out

def parse_flipkart(html):
    """Flipkart ke class names random hote hain, isliye class-independent heuristic:
    product link (/p/) ke aas-paas ke text se Rupee amounts nikalte hain."""
    soup, out, seen = BeautifulSoup(html, "html.parser"), [], set()
    for a in soup.select("a[href*='/p/']"):
        href = a["href"].split("&")[0]
        if href in seen:
            continue
        card = a
        for _ in range(4):                      # upar ke parent tak jao jahan price mile
            if card.parent: card = card.parent
            if "₹" in card.get_text():
                break
        text = card.get_text(" ", strip=True)
        prices = [int(x.replace(",", "")) for x in re.findall(r"₹\s?([\d,]{4,})", text)]
        if not prices:
            continue
        seen.add(href)
        title = (a.get("title") or a.get_text(" ", strip=True) or text)[:120]
        price, mrp = prices[0], max(prices[:3])
        out.append(dict(site="flipkart", url="https://www.flipkart.com" + href,
                        title=title, price=price, mrp=mrp))
    return out

PARSERS = {"amazon": parse_amazon, "flipkart": parse_flipkart}

def scan_all():
    """Return items plus how many source pages succeeded/failed."""
    items, succeeded, failed = [], 0, 0
    for site, urls in SEARCH_URLS.items():
        for u in urls:
            try:
                html = fetch_html(u)
                if html:
                    items += PARSERS[site](html)
                    succeeded += 1
                    log.info("%s -> %d items so far", site, len(items))
                else:
                    failed += 1
            except Exception as e:
                failed += 1
                log.error("scan error %s: %s", u, e)
            import time; time.sleep(random.uniform(3, 7))   # polite delay
    return items, succeeded, failed

# ---------------- Core logic ----------------
def evaluate(items):
    """Products update karo aur ye list return karo: [(item, discount%, drop%)]"""
    results = []
    with db() as c:
        for it in items:
            if not it["price"] or it["price"] < 1000:      # accessories filter
                continue
            old = c.execute("SELECT price, lowest FROM products WHERE url=?", (it["url"],)).fetchone()
            disc = round((it["mrp"] - it["price"]) * 100 / it["mrp"]) if it["mrp"] and it["mrp"] > it["price"] else 0
            drop = round((old["price"] - it["price"]) * 100 / old["price"]) if old and old["price"] > it["price"] else 0
            lowest = min(it["price"], old["lowest"]) if old else it["price"]
            c.execute("""INSERT INTO products(url,site,title,price,mrp,lowest) VALUES(?,?,?,?,?,?)
                         ON CONFLICT(url) DO UPDATE SET price=?, mrp=?, lowest=?, title=?, updated=CURRENT_TIMESTAMP""",
                      (it["url"], it["site"], it["title"], it["price"], it["mrp"], lowest,
                       it["price"], it["mrp"], lowest, it["title"]))
            results.append((it, disc, drop, lowest))
    return results

def fmt(it, disc, drop):
    tag = "🔥 PRICE DROP" if drop else "💸 BIG DISCOUNT"
    return (f"{tag} ({it['site'].title()})\n{it['title']}\n"
            f"💰 ₹{it['price']:,}  (MRP ₹{it['mrp']:,})\n"
            f"🏷 {disc}% off MRP" + (f" | ⬇️ {drop}% sasta pichle price se" if drop else "") +
            f"\n🔗 {it['url']}")

async def scan_job(context: ContextTypes.DEFAULT_TYPE):
    items, sources_ok, sources_failed = await asyncio.to_thread(scan_all)
    results = await asyncio.to_thread(evaluate, items)
    stats = {"sources_ok": sources_ok, "sources_failed": sources_failed,
             "fetched": len(items), "tracked": len(results),
             "matched": 0, "sent": 0, "already_alerted": 0}
    with db() as c:
        users = c.execute("SELECT * FROM users").fetchall()
        for it, disc, drop, lowest in results:
            for u in users:
                if u["max_price"] and it["price"] > u["max_price"]:
                    continue
                if not (disc >= u["min_discount"] or drop >= u["min_drop"]):
                    continue
                stats["matched"] += 1
                # ek user ko ek (product, price) combo pe sirf ek baar alert
                if c.execute("SELECT 1 FROM alerted WHERE chat_id=? AND url=? AND price=?",
                             (u["chat_id"], it["url"], it["price"])).fetchone():
                    stats["already_alerted"] += 1
                    continue
                try:
                    await context.bot.send_message(u["chat_id"], fmt(it, disc, drop))
                    c.execute("INSERT INTO alerted VALUES(?,?,?)", (u["chat_id"], it["url"], it["price"]))
                    stats["sent"] += 1
                except Exception as e:
                    log.error("send fail %s", e)
    log.info("scan complete: %s sources OK, %s failed, %s items, %s alerts sent",
             sources_ok, sources_failed, len(items), stats["sent"])
    return stats

# ---------------- Commands ----------------
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    with db() as c:
        c.execute("INSERT OR IGNORE INTO users(chat_id) VALUES(?)", (update.effective_chat.id,))
    await update.message.reply_text(
        "👋 Phone Deal Bot ready!\n\n"
        "/discount 70 - MRP se itna % off pe alert\n"
        "/drop 25 - pichle price se itna % gira to alert\n"
        "/maxprice 20000 - is budget ke andar ke phones (0 = off)\n"
        "/settings - current settings\n"
        "/scan - abhi scan karo\n\n"
        f"Main har {SCAN_MINUTES} min me Amazon + Flipkart check karta hoon.")

async def _set(update, field, label):
    try:
        val = int(update.message.text.split()[1])
    except Exception:
        return await update.message.reply_text(f"Aise likho: /{label} 70")
    with db() as c:
        c.execute("INSERT OR IGNORE INTO users(chat_id) VALUES(?)", (update.effective_chat.id,))
        c.execute(f"UPDATE users SET {field}=? WHERE chat_id=?", (val, update.effective_chat.id))
    await update.message.reply_text(f"✅ {label} = {val}")

async def discount(u, c): await _set(u, "min_discount", "discount")
async def drop(u, c): await _set(u, "min_drop", "drop")
async def maxprice(u, c): await _set(u, "max_price", "maxprice")

async def settings(update: Update, ctx):
    with db() as c:
        u = c.execute("SELECT * FROM users WHERE chat_id=?", (update.effective_chat.id,)).fetchone()
    if not u:
        return await update.message.reply_text("Pehle /start karo")
    await update.message.reply_text(
        f"⚙️ Min discount: {u['min_discount']}%\nMin drop: {u['min_drop']}%\n"
        f"Max price: {'no limit' if not u['max_price'] else '₹' + str(u['max_price'])}")

async def scan_now(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Scan chalu... 1-2 min lagenge")
    stats = await scan_job(ctx)
    if not stats["sources_ok"]:
        return await update.message.reply_text(
            "⚠️ Scan fail ho gaya: Amazon/Flipkart se koi data nahi mila, isliye alerts check nahi hui. "
            "Server logs me `scan error` check karo.")
    message = (f"✅ Scan complete: {stats['fetched']} listings mili "
               f"({stats['sources_ok']} source pages). ")
    if stats["sent"]:
        message += f"{stats['sent']} naya alert bheja."
    elif stats["matched"]:
        message += "Matching deal pehle hi isi price par alert ho chuki hai."
    else:
        message += ("Current settings par koi deal match nahi hui. Yaad rahe: `/drop 25` "
                    "tabhi alert karta hai jab tracked phone ka price agle scan me 25% gire; "
                    "pehla scan sirf baseline save karta hai.")
    if stats["sources_failed"]:
        message += f" ({stats['sources_failed']} source page fail hua.)"
    await update.message.reply_text(message)

def main():
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN .env me daalo")
    init_db()
    app = Application.builder().token(BOT_TOKEN).connect_timeout(30).read_timeout(30).build()
    for name, fn in [("start", start), ("discount", discount), ("drop", drop),
                     ("maxprice", maxprice), ("settings", settings), ("scan", scan_now)]:
        app.add_handler(CommandHandler(name, fn))
    app.job_queue.run_repeating(scan_job, interval=SCAN_MINUTES * 60, first=10)
    health_server, health_thread = start_health_server()
    log.info("Bot started")
    try:
        app.run_polling()
    finally:
        health_server.shutdown()
        health_server.server_close()
        health_thread.join(timeout=5)

if __name__ == "__main__":
    # Python 3.14 no longer creates a default event loop implicitly.
    # python-telegram-bot's run_polling() expects one to be current.
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    main()
