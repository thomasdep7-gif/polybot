import os
import time
import requests
import json
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
SCAN_INTERVAL = int(os.environ.get("SCAN_INTERVAL", "600"))
def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logger.info("Telegram no configurado")
        return
    try:
url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }, timeout=10)
    except Exception as e:
        logger.error(f"Telegram error: {e}")

def get_markets():
    try:
url = "https://gamma-api.polymarket.com/markets"
        params = {
            "limit": 30,
            "active": "true",
            "closed": "false",
            "order": "volume24hr",
            "ascending": "false"
        }
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.error(f"Error obteniendo mercados: {e}")
        return []

def analyze_market(market):
    try:
        prices = market.get("outcomePrices", "[]")
        if isinstance(prices, str):
            prices = json.loads(prices)
        if len(prices) != 2:
            return None
        yes_price = float(prices[0])
        volume = float(market.get("volume", 0))
        liquidity = float(market.get("liquidity", 0))
        if volume < 10000 or liquidity < 5000:
            return None
        if yes_price < 0.05 or yes_price > 0.95:
            return None
        edge = 0
        signal = None
        if 0.10 <= yes_price <= 0.42:
            edge = round((yes_price * 1.12) - yes_price, 3)
            if edge >= 0.08:
                signal = "YES"
        elif 0.58 <= yes_price <= 0.90:
            no_price = float(prices[1])
            edge = round((no_price * 1.12) - no_price, 3)
            if edge >= 0.08:
                signal = "NO"
        if not signal:
            return None
        return {
            "question": market.get("question", "")[:100],
            "signal": signal,
            "yes_price": yes_price,
            "edge": edge,
            "slug": market.get("slug", "")
        }
    except Exception as e:
        logger.error(f"Error analizando: {e}")
        return None

def scan():
    logger.info("Escaneando mercados...")
    markets = get_markets()
    results = []
    for m in markets:
        r = analyze_market(m)
        if r:
            results.append(r)
    results.sort(key=lambda x: x["edge"], reverse=True)
    top = results[:3]
    if not top:
        logger.info("Sin oportunidades ahora.")
