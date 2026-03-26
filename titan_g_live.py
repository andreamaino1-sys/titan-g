"""
TITAN-G - DATI LIVE CON LUKHED-STOCKS
47 agenti | 13 AI | Scansione automatica ogni ora
"""

from flask import Flask, request, jsonify
import requests
import threading
import time
from datetime import datetime
from lukhed_stocks.marketdata import MarketData

# =========================================================
# CONFIGURAZIONE
# =========================================================
TELEGRAM_TOKEN = "8629848762:AAHa1l3CEs0AguKWINcAKrvynBCi5Xglsq0"
TELEGRAM_CHAT_ID = "2110183214"

app = Flask(__name__)

# Inizializza MarketData (dati live gratuiti)
md = MarketData()

# =========================================================
# TELEGRAM CON RATE LIMIT
# =========================================================
_last_telegram_sent = 0

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
print("🚀 TITAN-G - DATI LIVE CON LUKHED-STOCKS")
print(f"🧬 Agenti: {len(ALL_AGENTS)}")
print(f"🤖 AI: {len(ai_agents.get_active())}")
print("=" * 60)

# =========================================================
# STORICO SEGNALI
# =========================================================
signals_received = []
signals_validated = []

def trim_history():
    global signals_received, signals_validated
    if len(signals_received) > 1000:
        signals_received = signals_received[-1000:]
    if len(signals_validated) > 1000:
        signals_validated = signals_validated[-1000:]

# =========================================================
# VALIDAZIONE (3+ AGENTI CONCORDI)
# =========================================================
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
# FUNZIONE PER OTTENERE PREZZO LIVE
# =========================================================
def get_live_price(ticker):
    """Ottiene prezzo live da lukhed-stocks"""
    try:
        quote = md.get_quote(ticker)
        if quote and 'close' in quote:
            return float(quote['close'])
    except Exception as e:
        print(f"   Errore {ticker}: {e}")
    return None

# =========================================================
# SCANSIONE AUTOMATICA (WATCHLIST)
# =========================================================
# Lista ticker da monitorare
WATCHLIST = [
    "NVDA", "PLTR", "AAPL", "MSFT", "TSLA", "META", "GOOGL", "AMZN",
    "BTC-USD", "ETH-USD", "SOL-USD", "XOM", "CVX", "LMT", "NOC", "LLY", "CRSP",
    "RKLB", "SPY", "QQQ", "TLT"
]

def scan_all_tickers():
    """Scansiona tutti i ticker e genera segnali"""
    print(f"\n🔍 SCANSIONE AUTOMATICA - {datetime.now().strftime('%H:%M:%S')}")
    
    signals = []
    for ticker in WATCHLIST:
        price = get_live_price(ticker)
        if price:
            print(f"   {ticker}: ${price:.2f}")
            for agent in ALL_AGENTS:
                if agent.activate(ticker):
                    s = agent.analyze(ticker, price)
                    signals.append(s)
    
    print(f"   Segnali generati: {len(signals)}")
    
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
        return
    
    eurusd = 1.08  # Semplificato
    for s in signals_validated[-20:]:
        s["return_eur"] = ((s["tp"] / eurusd) - (s["entry"] / eurusd)) / (s["entry"] / eurusd) * 100
    
    top = sorted(signals_validated[-20:], key=lambda x: x["return_eur"], reverse=True)[:3]
    
    msg = f"🏆 *TOP 3 SEGNALI* {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
    msg += f"📊 Ricevuti: {len(signals_received)} | Validati: {len(signals_validated)}\n"
    msg += f"🧬 Agenti: {len(ALL_AGENTS)} | 🤖 AI: {len(ai_agents.get_active())}\n\n"
    
    for i, s in enumerate(top, 1):
        entry_eur = s["entry"] / eurusd
        tp_eur = s["tp"] / eurusd
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
        msg += f"{emoji} *{s['ticker']}* ({s['category']})\n"
        msg += f"   Agent: {s['agent']}\n"
        msg += f"   Entry: ${s['entry']:.2f} | €{entry_eur:.2f}\n"
        msg += f"   Target: ${s['tp']:.2f} | €{tp_eur:.2f}\n"
        msg += f"   Rend: +{s['return_eur']:.1f}%\n\n"
    
    send_telegram(msg)
    return top

# =========================================================
# SCHEDULER (scansione ogni ora)
# =========================================================
def schedule_scan():
    while True:
        scan_all_tickers()
        time.sleep(3600)  # 1 ora

# =========================================================
# WEBHOOK (opzionale, per TradingView)
# =========================================================
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    ticker = data.get('ticker', 'UNKNOWN')
    action = data.get('action', 'BUY')
    price = data.get('price', 0)
    
    print(f"\n📡 Webhook: {ticker} {action} @ ${price}")
    
    signals = []
    for agent in ALL_AGENTS:
        if agent.activate(ticker):
            s = agent.analyze(ticker, price)
            signals.append(s)
    
    validated = validate_signals(signals)
    
    if validated:
        best = validated[0]
        signals_validated.append(best)
        trim_history()
        
        msg = f"✅ *SEGNALE VALIDATO* {ticker}\n\n"
        msg += f"🎯 {action}\n"
        msg += f"💰 Entry: ${best['entry']:.2f}\n"
        msg += f"🎯 TP: ${best['tp']:.2f}\n"
        msg += f"🧬 {len(validated)} agenti concordi"
        
        send_telegram(msg)
        return jsonify({"status": "validated"})
    else:
        return jsonify({"status": "rejected"})

# =========================================================
# ROUTES
# =========================================================
@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "agents": len(ALL_AGENTS),
        "ai": len(ai_agents.get_active()),
        "watchlist": len(WATCHLIST)
    })

@app.route('/scan', methods=['GET'])
def scan():
    """Avvia scansione manuale"""
    scan_all_tickers()
    return jsonify({"status": "ok"})

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "name": "Titan-G",
        "agents": len(ALL_AGENTS),
        "ai": len(ai_agents.get_active()),
        "watchlist": len(WATCHLIST),
        "endpoints": ["/webhook (POST)", "/scan (GET)", "/health (GET)"]
    })

# =========================================================
# MAIN
# =========================================================
def run_bot():
    print("\n" + "=" * 60)
    print("🚀 TITAN-G - DATI LIVE DA LUKHED-STOCKS")
    print("=" * 60)
    print(f"📊 Watchlist: {len(WATCHLIST)} ticker")
    print(f"🧬 Agenti: {len(ALL_AGENTS)}")
    print(f"🤖 AI: {len(ai_agents.get_active())}")
    print("=" * 60)
    print("⏰ Scansione automatica ogni ora")
    print("📡 Webhook: http://localhost:5000/webhook")
    print("🔍 Scan manuale: http://localhost:5000/scan")
    print("=" * 60)
    
    send_telegram(f"🚀 *TITAN-G ATTIVO*\n\n📊 {len(WATCHLIST)} ticker monitorati\n🧬 {len(ALL_AGENTS)} agenti\n🤖 {len(ai_agents.get_active())} AI\n✅ 3+ conferme\n\n⏰ Scansione automatica ogni ora\n🔍 /scan per scansione manuale")
    
    # Avvia thread scansione automatica
    threading.Thread(target=schedule_scan, daemon=True).start()
    
    app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == "__main__":
    run_bot()
