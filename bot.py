import os
import time
import requests
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s') logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "") TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "") MIN_EDGE = float(os.environ.get("MIN_EDGE", "0.08")) MAX_BET_FRACTION = float(os.environ.get("MAX_BET_FRACTION", "0.05")) SCAN_INTERVAL = int(os.environ.get("SCAN_INTERVAL", "600"))

def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logger.info(f"[TELEGRAM DISABLED] {message}")
        return
    try:
        url = f"https://eur04.safelinks.protection.outlook.com/?url=https%3A%2F%2Fapi.telegram.org%2Fbot&data=05%7C02%7Cthomas.deprez%40skintechpharmagroup.com%7C90df6a0ebbda4e14664908de8cdd924e%7C8f364ac47bc5471f9981bae9e2ed41f0%7C0%7C0%7C639103080434433937%7CUnknown%7CTWFpbGZsb3d8eyJFbXB0eU1hcGkiOnRydWUsIlYiOiIwLjAuMDAwMCIsIlAiOiJXaW4zMiIsIkFOIjoiTWFpbCIsIldUIjoyfQ%3D%3D%7C0%7C%7C%7C&sdata=V0F2V7Am5iL7gQVvx922ANgAJFD5awdpIQoxqZq2b4o%3D&reserved=0{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}, timeout=10)
    except Exception as e:
        logger.error(f"Telegram error: {e}")

def get_markets():
    try:
        url = "https://eur04.safelinks.protection.outlook.com/?url=https%3A%2F%2Fgamma-api.polymarket.com%2Fmarkets&data=05%7C02%7Cthomas.deprez%40skintechpharmagroup.com%7C90df6a0ebbda4e14664908de8cdd924e%7C8f364ac47bc5471f9981bae9e2ed41f0%7C0%7C0%7C639103080434458541%7CUnknown%7CTWFpbGZsb3d8eyJFbXB0eU1hcGkiOnRydWUsIlYiOiIwLjAuMDAwMCIsIlAiOiJXaW4zMiIsIkFOIjoiTWFpbCIsIldUIjoyfQ%3D%3D%7C0%7C%7C%7C&sdata=rNGfWKjyHqeKzkWnlNdY1IgqM9962BTN1aZgKzJPBWo%3D&reserved=0"
        params = {"limit": 50, "active": "true", "closed": "false", "order": "volume24hr", "ascending": "false"}
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching markets: {e}")
        return []

def analyze_market(market):
    try:
        outcomes = market.get("outcomes", "[]")
        if isinstance(outcomes, str):
            outcomes = json.loads(outcomes)
        prices = market.get("outcomePrices", "[]")
        if isinstance(prices, str):
            prices = json.loads(prices)
        if len(outcomes) != 2 or len(prices) != 2:
            return None
        yes_price = float(prices[0])
        no_price = float(prices[1])
        volume = float(market.get("volume", 0))
        liquidity = float(market.get("liquidity", 0))
        if volume < 10000:
            return None
        if liquidity < 5000:
            return None
        if yes_price < 0.05 or yes_price > 0.95:
            return None
        edge = 0
        signal = "NEUTRAL"
        if 0.10 <= yes_price <= 0.42:
            fair_value = yes_price * 1.12
            edge = min(fair_value - yes_price, 0.15)
            if edge >= MIN_EDGE:
                signal = "YES"
        elif 0.58 <= yes_price <= 0.90:
            fair_value = no_price * 1.12
            edge = min(fair_value - no_price, 0.15)
            if edge >= MIN_EDGE:
                signal = "NO"
        if signal == "NEUTRAL":
            return None
        return {"question": market.get("question", ""), "signal": signal, "yes_price": yes_price, "no_price": no_price, "edge": edge, "volume": volume, "liquidity": liquidity, "end_date": market.get("endDate", ""), "market_slug": market.get("slug", "")}
    except Exception as e:
        logger.error(f"Error analyzing market: {e}")
        return None

def kelly_bet(edge, price, capital):
    if edge <= 0:
        return 0
    b = (1 / price) - 1
    p = price + edge
    q = 1 - p
    kelly = (b * p - q) / b
    safe_kelly = kelly * 0.25
    bet = capital * safe_kelly
    max_bet = capital * MAX_BET_FRACTION
    return round(min(max(bet, 0), max_bet), 2)

def scan_and_notify(capital=221.0):
    logger.info("Escaneando mercados de Polymarket...")
    markets = get_markets()
    if not markets:
        logger.warning("No se pudieron obtener mercados")
        return
    opportunities = []
    for market in markets:
        result = analyze_market(market)
        if result:
            result["bet_amount"] = kelly_bet(result["edge"], result["yes_price"] if result["signal"] == "YES" else result["no_price"], capital)
            opportunities.append(result)
    opportunities.sort(key=lambda x: x["edge"], reverse=True)
    top = opportunities[:3]
    logger.info(f"Encontradas {len(opportunities)} oportunidades.")
    if not top:
        logger.info("No hay oportunidades ahora mismo.")
        return
    for opp in top:
        signal_emoji = "🟢" if opp["signal"] == "YES" else "🔴"
        message = f"{signal_emoji} *OPORTUNIDAD DETECTADA*\n\n📋 *Mercado:* {opp['question'][:100]}\n📊 *Señal:* COMPRAR {opp['signal']}\n💰 *Precio:* {opp['yes_price']*100:.0f}¢ YES / {opp['no_price']*100:.0f}¢ NO\n📈 *Ventaja:* +{opp['edge']*100:.1f}%\n💵 *Apuesta Kelly 25%:* ${opp['bet_amount']:.2f}\n🔗 https://eur04.safelinks.protection.outlook.com/?url=https%3A%2F%2Fpolymarket.com%2Fevent%2F&data=05%7C02%7Cthomas.deprez%40skintechpharmagroup.com%7C90df6a0ebbda4e14664908de8cdd924e%7C8f364ac47bc5471f9981bae9e2ed41f0%7C0%7C0%7C639103080434476653%7CUnknown%7CTWFpbGZsb3d8eyJFbXB0eU1hcGkiOnRydWUsIlYiOiIwLjAuMDAwMCIsIlAiOiJXaW4zMiIsIkFOIjoiTWFpbCIsIldUIjoyfQ%3D%3D%7C0%7C%7C%7C&sdata=yiNcAKbpDTzGZG8Oj0F6PuGVBs5omNBs1UYYT16Fa3I%3D&reserved=0{opp['market_slug']}\n\n⚠️ Verifica antes de apostar."
        send_telegram(message)
        time.sleep(1)

def main():
    logger.info("PolyBot iniciado")
    send_telegram("🤖 *PolyBot arrancado*\n\nEscaneando Polymarket cada 10 minutos.")
    while True:
        try:
            scan_and_notify()
        except Exception as e:
            logger.error(f"Error: {e}")
        logger.info(f"Próximo escaneo en 10 minutos...")
        time.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    main()

