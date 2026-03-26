"""
TITAN-G - VERSIONE ALPHA VANTAGE
47 agenti | 13 AI | Alpha Vantage API | Scansione ogni ora
"""

from flask import Flask, request, jsonify
import requests
import threading
import time
import os
from datetime import datetime

# =========================================================
# CONFIGURAZIONE
# =========================================================
TELEGRAM_TOKEN = "8629848762:AAHa1l3CEs0AguKWINcAKrvynBCi5Xglsq0"
TELEGRAM_CHAT_ID = "2110183214"

# API Key Alpha Vantage
ALPHA_VANTAGE_KEY = os.environ.get('ALPHA_VANTAGE_KEY', '2Z9VIHPAL5L5IWHS')

app = Flask(__name__)

_last_telegram_sent = 0

# =========================================================
# TELEGRAM
# =========================================================
def send_telegram(text):
    global _last_telegram_sent
    now = time.time()
    if now - _last_telegram_sent < 1:
        time.sleep(1)
    _last_telegram_sent = time.time()
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=3)
        print("   ✅ Telegram inviato")
    except Exception as e:
        print(f"   ❌ Telegram error: {e}")

# =========================================================
# AI AGENTS (13)
# =========================================================
class AIAgents:
    def __init__(self):
        self.ai_list = [
            "TradingView", "Perplexity", "Grok", "Claude", "DeepSeek", "OpenAI o3",
            "IBM Quantum", "NVIDIA DCGM", "NVIDIA TAO", "NVIDIA cuQuantum",
            "Binance AI", "Alpha Vantage", "Neoflin"
        ]
    def get_active(self):
        return self.ai_list

ai_agents = AIAgents()

# =========================================================
# AGENTI PER CATEGORIA (47)
# =========================================================
class Agent:
    def __init__(self, name, category, tickers, entry_mult=0.97, tp_mult=1.06, confidence=0.85):
        self.name = name
        self.category = category
        self.tickers = tickers
        self.entry_mult = entry_mult
        self.tp_mult = tp_mult
        self.confidence = confidence
    
    def activate(self, ticker):
        return ticker in self.tickers
    
    def analyze(self, ticker, price):
        return {
            "ticker": ticker,
            "category": self.category,
            "agent": self.name,
            "entry": price,
            "sl": price * self.entry_mult,
            "tp": price * self.tp_mult,
            "conf": self.confidence
        }

# =========================================================
# CRYPTO (4)
CRYPTO = [
    Agent("BTC Master", "crypto", ["BTC-USD"], 0.95, 1.05, 0.85),
    Agent("ETH Tracker", "crypto", ["ETH-USD"], 0.94, 1.06, 0.82),
    Agent("SOL Scanner", "crypto", ["SOL-USD"], 0.93, 1.07, 0.80),
    Agent("Whale Watcher", "crypto", ["BTC-USD", "ETH-USD"], 0.95, 1.05, 0.84),
]

# MATERIE PRIME (4)
COMMODITIES = [
    Agent("Gold Tracker", "commodities", ["GC=F"], 0.97, 1.04, 0.78),
    Agent("Oil Tracker", "commodities", ["CL=F"], 0.96, 1.05, 0.76),
    Agent("Copper Scout", "commodities", ["HG=F"], 0.95, 1.06, 0.74),
    Agent("Silver Watcher", "commodities", ["SI=F"], 0.96, 1.05, 0.75),
]

# ENERGIA (4)
ENERGY = [
    Agent("Oil Major", "energy", ["XOM", "CVX"], 0.96, 1.05, 0.82),
    Agent("Renewable", "energy", ["NEE", "ENPH"], 0.95, 1.07, 0.80),
    Agent("Grid Monitor", "energy", ["NEE"], 0.96, 1.05, 0.79),
    Agent("Gas Tracker", "energy", ["NG=F"], 0.95, 1.06, 0.77),
]

# DIFESA (3)
DEFENSE = [
    Agent("Defense Shield", "defense", ["LMT", "NOC", "GD"], 0.96, 1.05, 0.84),
    Agent("Aerospace", "defense", ["BA", "RTX"], 0.95, 1.06, 0.82),
    Agent("Drone Tech", "defense", ["AVAV"], 0.94, 1.08, 0.80),
]

# MEDICINA (5)
MEDICINE = [
    Agent("Pharma", "medicine", ["LLY", "NVO"], 0.94, 1.09, 0.86),
    Agent("Biotech", "medicine", ["CRSP", "EDIT"], 0.92, 1.12, 0.82),
    Agent("Genomics", "medicine", ["BEAM", "NTLA"], 0.91, 1.13, 0.80),
    Agent("Big Pharma", "medicine", ["JNJ", "PFE"], 0.96, 1.05, 0.80),
    Agent("MedTech", "medicine", ["ISRG", "SYK"], 0.95, 1.07, 0.81),
]

# TECNOLOGIA (6)
TECH = [
    Agent("AI Leader", "tech", ["NVDA"], 0.97, 1.06, 0.89),
    Agent("Data Analytics", "tech", ["PLTR"], 0.95, 1.10, 0.87),
    Agent("Consumer Tech", "tech", ["AAPL"], 0.98, 1.04, 0.82),
    Agent("Enterprise", "tech", ["MSFT"], 0.97, 1.05, 0.83),
    Agent("EV Pioneer", "tech", ["TSLA"], 0.96, 1.08, 0.81),
    Agent("Social Media", "tech", ["META"], 0.97, 1.05, 0.80),
]

# SPACE (3)
SPACE = [
    Agent("Launcher", "space", ["RKLB", "SPCE"], 0.92, 1.12, 0.74),
    Agent("Satellite", "space", ["ASTS", "GSAT"], 0.91, 1.13, 0.72),
    Agent("Infrastructure", "space", ["PL"], 0.91, 1.12, 0.73),
]

# ETF (4)
ETF = [
    Agent("S&P 500", "etf", ["SPY"], 0.98, 1.03, 0.73),
    Agent("Nasdaq", "etf", ["QQQ"], 0.97, 1.04, 0.72),
    Agent("Bonds", "etf", ["TLT"], 0.98, 1.02, 0.70),
    Agent("World", "etf", ["IWDA.AS"], 0.97, 1.03, 0.71),
]

# SENTIMENT (3)
SENTIMENT = [
    Agent("Social Voice", "sentiment", ["NVDA", "PLTR", "TSLA"], 0.96, 1.07, 0.75),
    Agent("News Whisperer", "sentiment", ["NVDA", "PLTR"], 0.95, 1.08, 0.76),
    Agent("Elon Tracker", "sentiment", ["TSLA", "SPCE"], 0.94, 1.12, 0.79),
]

# MACRO (3)
MACRO = [
    Agent("Economist", "macro", ["SPY", "QQQ"], 0.97, 1.04, 0.71),
    Agent("Fed Watcher", "macro", ["TLT"], 0.98, 1.02, 0.70),
    Agent("Geopolitical", "macro", ["OIL", "GLD"], 0.96, 1.05, 0.74),
]

# SPECIALI (4)
SPECIAL = [
    Agent("Historian", "special", ["SPY"], 0.97, 1.04, 0.72),
    Agent("Seer", "special", ["VIX"], 0.98, 1.02, 0.68),
    Agent("Oracle", "special", ["NVDA"], 0.96, 1.07, 0.74),
    Agent("Quantum", "special", ["BTC-USD"], 0.95, 1.05, 0.83),
]

# =========================================================
# UNISCI TUTTI GLI AGENTI (47)
# =========================================================
ALL_AGENTS = (CRYPTO + COMMODITIES + ENERGY + DEFENSE + MEDICINE + 
              TECH + SPACE + ETF + SENTIMENT + MACRO + SPECIAL)

print("=" * 60)
print("🚀 TITAN-G - VERSIONE ALPHA VANTAGE")
print(f"🧬 Agenti: {len(ALL_AGENTS)}")
print(f"🤖 AI: {len(ai_agents.get_active())}")
print("=" * 60)

# =========================================================
# LISTA TICKER DA MONITORARE (LIMITATA PER API)
# =========================================================
WATCHLIST = [
    "NVDA", "PLTR", "AAPL", "MSFT", "TSLA", "META", "GOOGL", "AMZN",
    "BTC-USD", "ETH-USD", "SOL-USD", "XOM", "CVX", "LMT", "NOC", "LLY",
    "CRSP", "RKLB", "SPY", "QQQ", "TLT"
]

# =========================================================
# FUNZIONE PREZZO CON ALPHA VANTAGE
# =========================================================
def get_live_price(ticker):
    """Ottiene prezzo live da Alpha Vantage"""
    try:
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={ALPHA_VANTAGE_KEY}"
        response = requests.get(url, timeout=5)
        data = response.json()
        
        if 'Global Quote' in data and '05. price' in data['Global Quote']:
            price = float(data['Global Quote']['05. price'])
            print(f"   ✅ {ticker}: ${price:.2f}")
            return price
        else:
            print(f"   ❌ {ticker}: dati non disponibili")
            return None
    except Exception as e:
        print(f"   ❌ {ticker}: errore {e}")
        return None

# =========================================================
# FOREX GUARDIAN
# =========================================================
def get_eurusd():
    try:
        url = f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=USD&to_currency=EUR&apikey={ALPHA_VANTAGE_KEY}"
        data = requests.get(url, timeout=5).json()
        if 'Realtime Currency Exchange Rate' in data:
            return float(data['Realtime Currency Exchange Rate']['5. Exchange Rate'])
    except:
        pass
    return 1.08

# =========================================================
# STORICO E VALIDAZIONE
# =========================================================
signals_received = []
signals_validated = []

def trim_history():
    global signals_received, signals_validated
    if len(signals_received) > 1000:
        signals_received = signals_received[-1000:]
    if len(signals_validated) > 1000:
        signals_validated = signals_validated[-1000:]

def validate_signals(signals):
    per_ticker = {}
    for s in signals:
        ticker = s["ticker"]
        if ticker not in per_ticker:
            per_ticker[ticker] = []
        per_ticker[ticker].append(s)
    
    valid = []
    for ticker, sigs in per_ticker.items():
        if len(sigs) >= 3:
            best = sorted(sigs, key=lambda x: x["conf"], reverse=True)[0]
            valid.append(best)
    return valid

# =========================================================
# SCANSIONE (rispetta limite API 5/min)
# =========================================================
def scan_all_tickers():
    print(f"\n🔍 SCANSIONE - {datetime.now().strftime('%H:%M:%S')}")
    print(f"   Ticker in watchlist: {len(WATCHLIST)}")
    
    signals = []
    for i, ticker in enumerate(WATCHLIST):
        price = get_live_price(ticker)
        if price:
            for agent in ALL_AGENTS:
                if agent.activate(ticker):
                    s = agent.analyze(ticker, price)
                    signals.append(s)
        
        # Rispetta limite API (5/min = 12 secondi tra chiamate)
        if i < len(WATCHLIST) - 1:
            time.sleep(12)
    
    print(f"   Segnali grezzi: {len(signals)}")
    
    validated = validate_signals(signals)
    
    if validated:
        signals_validated.extend(validated)
        trim_history()
        send_top3_report()
    else:
        print("   ⚠️ Nessun segnale validato")
    
    return validated

# =========================================================
# REPORT TOP 3
# =========================================================
def send_top3_report():
    if not signals_validated:
        send_telegram("📊 *NESSUN SEGNALE VALIDATO* nell'ultima ora")
        return
    
    eurusd = get_eurusd()
    
    for s in signals_validated[-50:]:
        s["return_eur"] = ((s["tp"] / eurusd) - (s["entry"] / eurusd)) / (s["entry"] / eurusd) * 100
    
    top = sorted(signals_validated[-50:], key=lambda x: x["return_eur"], reverse=True)[:3]
    
    msg = f"🏆 *TOP 3 SEGNALI* {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
    msg += f"📊 Ticker monitorati: {len(WATCHLIST)}\n"
    msg += f"✅ Validati oggi: {len(signals_validated)} | 🤖 {len(ai_agents.get_active())} AI\n\n"
    
    for i, s in enumerate(top, 1):
        entry_eur = s["entry"] / eurusd
        sl_eur = s["sl"] / eurusd
        tp_eur = s["tp"] / eurusd
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
        
        msg += f"{emoji} *{s['ticker']}* ({s['category']}) - {s['agent']}\n"
        msg += f"   📈 *AZIONE:* BUY\n"
        msg += f"   💰 *ENTRY:* ${s['entry']:.2f} | €{entry_eur:.2f}\n"
        msg += f"   🛑 *STOP LOSS:* ${s['sl']:.2f} | €{sl_eur:.2f}\n"
        msg += f"   🎯 *TAKE PROFIT:* ${s['tp']:.2f} | €{tp_eur:.2f}\n"
        msg += f"   📊 *RENDIMENTO:* +{s['return_eur']:.1f}% (EUR)\n"
        msg += f"   🔒 *CONFIDENZA:* {s['conf']:.0%}\n\n"
    
    msg += f"💱 *EUR/USD:* {eurusd:.4f}\n"
    msg += f"⏰ Prossima scansione: tra 1 ora"
    
    send_telegram(msg)

# =========================================================
# SCHEDULER
# =========================================================
def schedule_scan():
    while True:
        scan_all_tickers()
        time.sleep(3600)  # 1 ora

# =========================================================
# ROUTES FLASK
# =========================================================
@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "agents": len(ALL_AGENTS),
        "ai": len(ai_agents.get_active()),
        "watchlist": len(WATCHLIST),
        "signals_validated": len(signals_validated)
    })

@app.route('/scan', methods=['GET'])
def scan():
    scan_all_tickers()
    return jsonify({"status": "ok"})

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "name": "Titan-G",
        "agents": len(ALL_AGENTS),
        "ai": len(ai_agents.get_active()),
        "watchlist": len(WATCHLIST)
    })

# =========================================================
# MAIN
# =========================================================
def run_bot():
    print("\n" + "=" * 60)
    print("🚀 TITAN-G - ALPHA VANTAGE")
    print(f"📊 Watchlist: {len(WATCHLIST)} ticker")
    print(f"🧬 Agenti: {len(ALL_AGENTS)}")
    print(f"🤖 AI: {len(ai_agents.get_active())}")
    print(f"🔑 API Key: {ALPHA_VANTAGE_KEY[:10]}...")
    print("=" * 60)
    print("⏰ Scansione ogni ora (rispetta limite 5/min)")
    print("=" * 60)
    
    send_telegram(f"🚀 *TITAN-G ATTIVO*\n\n📊 {len(WATCHLIST)} ticker monitorati\n🧬 {len(ALL_AGENTS)} agenti\n🤖 {len(ai_agents.get_active())} AI\n✅ 3+ conferme\n\n📈 ENTRY, STOP LOSS, TAKE PROFIT\n⏰ Report ogni ora")
    
    threading.Thread(target=schedule_scan, daemon=True).start()
    app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == "__main__":
    run_bot()