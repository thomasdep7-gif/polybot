import os
import time
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("polybot")

TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT = os.environ.get("TELEGRAM_CHAT_ID", "")
INTERVAL = int(os.environ.get("SCAN_INTERVAL", "600"))

def notify(msg):
    if not TOKEN or not CHAT:
        return
    url = "https://api.telegram.org/bot" + TOKEN + "/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT, "text": msg}, timeout=10)
    except Exception as err:
        logger.error(str(err))

def get_markets():
    try:
        url = "https://gamma-api.polymarket.com/markets"
        r = requests.get(url, params={"limit": 50, "active": "true", "closed": "false"}, timeout=15)
        return r.json()
    except Exception as err:
        logger.error(str(err))
        return []

def run():
    logger.info("Escaneando...")
    markets = get_markets()
    found = 0
    for m in markets:
        try:
            prices = m.get("outcomePrices", "[]")
            if isinstance(prices, str):
                import json
                prices = json.loads(prices)
            if len(prices) < 2:
                continue
            yes = float(prices[0])
            vol = float(m.get("volume", 0))
            if vol < 5000:
                continue
            if 0.05 <= yes <= 0.70:
                edge = round((yes * 1.12 - yes) * 100, 1)
                if edge >= 4:
                    q = m.get("question", "")[:80]
                    slug = m.get("slug", "")
                    msg = "OPORTUNIDAD YES\n" + q + "\nPrecio: " + str(round(yes*100)) + "c\nVentaja: +" + str(edge) + "%\nhttps://polymarket.com/event/" + slug
                    notify(msg)
                    found += 1
        except Exception:
            continue
    if found == 0:
        logger.info("Sin oportunidades.")

notify("PolyBot activo. Escaneando cada 10 minutos.")

while True:
    try:
        run()
    except Exception as err:
        logger.error(str(err))
    time.sleep(INTERVAL)