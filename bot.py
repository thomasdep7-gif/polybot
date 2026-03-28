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

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "") TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "") SCAN_INTERVAL = int(os.environ.get("SCAN_INTERVAL", "600"))

def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logger.info("Telegram no configurado")
        return
    try:
        url = f"https://eur04.safelinks.protection.outlook.com/?url=https%3A%2F%2Fapi.telegram.org%2Fbot&data=05%7C02%7Cthomas.deprez%40skintechpharmagroup.com%7Cb36b45d3e5a5487def7b08de8ce54f24%7C8f364ac47bc5471f9981bae9e2ed41f0%7C0%7C0%7C639103113660639418%7CUnknown%7CTWFpbGZsb3d8eyJFbXB0eU1hcGkiOnRydWUsIlYiOiIwLjAuMDAwMCIsIlAiOiJXaW4zMiIsIkFOIjoiTWFpbCIsIldUIjoyfQ%3D%3D%7C0%7C%7C%7C&sdata=GsQldJaYm%2B2sTgXCtuMFMPcSChmfGMBbPMX4%2F11UZ4A%3D&reserved=0{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }, timeout=10)
    except Exception as e:
        logger.error(f"Telegram error: {e}")

def get_markets():
    try:
        url = "https://eur04.safelinks.protection.outlook.com/?url=https%3A%2F%2Fgamma-api.polymarket.com%2Fmarkets&data=05%7C02%7Cthomas.deprez%40skintechpharmagroup.com%7Cb36b45d3e5a5487def7b08de8ce54f24%7C8f364ac47bc5471f9981bae9e2ed41f0%7C0%7C0%7C639103113660667970%7CUnknown%7CTWFpbGZsb3d8eyJFbXB0eU1hcGkiOnRydWUsIlYiOiIwLjAuMDAwMCIsIlAiOiJXaW4zMiIsIkFOIjoiTWFpbCIsIldUIjoyfQ%3D%3D%7C0%7C%7C%7C&sdata=pSI9Xp8wnJXGD83hsmyRnBIqyvkNgqPOhFgBf8l4U%2FY%3D&reserved=0"
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
