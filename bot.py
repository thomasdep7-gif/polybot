import os
import time
import requests
import json
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
    r = requests.post(url, data={"chat_id": CHAT, "text": msg}, timeout=10)
    logger.info("Telegram: " + str(r.status_code))

def get_markets():
    url = "https://gamma-api.polymarket.com/markets"
    r = requests.get(url, params={"limit": 50, "active": "true", "closed": "false"}, timeout=15)
    return r.json()

def run():
    logger.info("Escaneando...")
    markets = get_markets()
    found = 0
    for m in markets:
        try:
            prices = m.get("outcomePrices", "[]")
            if isinstance(prices, str):
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
        except Exception as e:
            logger.error(str(e))
    logger.info("Oportunidades encontradas: " + str(found))

notify("PolyBot activo.")

while True:
    try:
        run()
    except Exception as e:
        logger.error(str(e))
    time.sleep(INTERVAL)