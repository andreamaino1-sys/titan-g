"""
TITAN-G - VERSIONE CORRETTA
Agenti con vera analisi | Validazione realistica
"""

from flask import Flask, request, jsonify
import requests
import threading
import time
import yfinance as yf
import numpy as np
from datetime import datetime

# =========================================================
# CONFIGURAZIONE
# =========================================================
TELEGRAM_TOKEN = "8629848762:AAHa1l3CEs0AguKWINcAKrvynBCi5Xglsq0"
TELEGRAM_CHAT_ID = "2110183214"
ALPHA_VANTAGE_KEY = "2Z9VIHPAL5L5IWHS"

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
# AGENTE CON ANALISI REALE (USANDO YFINANCE)
# =========================================================
class SmartAgent:
    def __init__(self, name, category, tickers, strategy="momentum"):
        self.name = name
        self.category = category
        self.tickers = tickers
        self.strategy = strategy
        self.last_analysis = {}
    
    def activate(self, ticker):
        return ticker in self.tickers
    
    def get_historical_data(self, ticker):
        """Ottiene dati storici con yfinance"""
        try:
            # Mappa ticker crypto per yfinance
            yf_ticker = ticker.replace("-USD", "-USD") if "-USD" in ticker else ticker
            stock = yf.Ticker(yf_ticker)
            hist = stock.history(period="1mo", interval="1d")
            
            if hist.empty:
                return None
            
            return {
                'close': hist['Close'].values,
                'high': hist['High'].values,
                'low': hist['Low'].values,
                'volume': hist['Volume'].values,
                'dates': hist.index
            }
        except Exception as e:
            print(f"   Errore dati storici {ticker}: {e}")
            return None
    
    def analyze(self, ticker, price):
        """Analisi reale con dati storici"""
        # Ottieni dati storici
        hist_data = self.get_historical_data(ticker)
        
        if hist_data is None or len(hist_data['close']) < 20:
            # Dati insufficienti, segnale debole
            return {
                "ticker": ticker,
                "category": self.category,
                "agent": self.name,
                "strategy": self.strategy,
                "entry": price,
                "sl": price * 0.97,
                "tp": price * 1.04,
                "conf": 0.50,
                "reason": "⚠️ Dati insufficienti per analisi"
            }
        
        # Analisi in base alla strategia
        close = hist_data['close']
        volume = hist_data['volume']
        
        if self.strategy == "momentum":
            return self._momentum_analysis(ticker, price, close, volume)
        elif self.strategy == "rsi":
            return self._rsi_analysis(ticker, price, close)
        elif self.strategy == "volume":
            return self._volume_analysis(ticker, price, close, volume)
        elif self.strategy == "ma_crossover":
            return self._ma_analysis(ticker, price, close)
        else:
            return self._default_analysis(ticker, price, close)
    
    def _momentum_analysis(self, ticker, price, close, volume):
        """Analisi momentum: ROC e accelerazione"""
        if len(close) < 10:
            return None
        
        # ROC a 5 e 10 giorni
        roc_5 = (close[-1] / close[-6] - 1) * 100 if len(close) >= 6 else 0
        roc_10 = (close[-1] / close[-11] - 1) * 100 if len(close) >= 11 else 0
        
        # Volume conferma
        avg_volume = np.mean(volume[-20:]) if len(volume) >= 20 else volume[-1]
        volume_surge = volume[-1] > avg_volume * 1.3
        
        # Scoring
        score = 0
        reasons = []
        
        if roc_5 > 2:
            score += 0.2
            reasons.append(f"Momentum 5gg: +{roc_5:.1f}%")
        elif roc_5 > 0:
            score += 0.1
            reasons.append(f"Leggero momentum: +{roc_5:.1f}%")
        elif roc_5 < -2:
            return None  # Momentum negativo, evita
        
        if roc_5 > roc_10:
            score += 0.15
            reasons.append("Accelerazione positiva")
        
        if volume_surge:
            score += 0.15
            reasons.append("Volume in aumento")
        
        confidence = 0.5 + score
        
        return {
            "ticker": ticker,
            "category": self.category,
            "agent": self.name,
            "strategy": self.strategy,
            "entry": price,
            "sl": price * (0.95 if confidence > 0.7 else 0.97),
            "tp": price * (1.08 if confidence > 0.7 else 1.05),
            "conf": min(confidence, 0.95),
            "reason": " | ".join(reasons)
        }
    
    def _rsi_analysis(self, ticker, price, close):
        """Analisi RSI per ipervenduto"""
        if len(close) < 15:
            return None
        
        # Calcola RSI a 14 periodi
        gains = []
        losses = []
        for i in range(1, 15):
            change = close[-i] - close[-i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        
        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        # Cerca ipervenduto
        if rsi < 30:
            confidence = 0.7 + (30 - rsi) / 100
            return {
                "ticker": ticker,
                "category": self.category,
                "agent": self.name,
                "strategy": self.strategy,
                "entry": price,
                "sl": price * 0.96,
                "tp": price * 1.07,
                "conf": min(confidence, 0.9),
                "reason": f"RSI={rsi:.1f} (ipervenduto)"
            }
        
        return None  # Non ipervenduto, niente segnale
    
    def _volume_analysis(self, ticker, price, close, volume):
        """Analisi volume: accumulazione"""
        if len(volume) < 20:
            return None
        
        avg_volume = np.mean(volume[-20:])
        volume_ratio = volume[-1] / avg_volume
        
        price_change = (close[-1] - close[-2]) / close[-2] * 100 if len(close) > 1 else 0
        
        if volume_ratio > 1.5 and price_change > 1:
            return {
                "ticker": ticker,
                "category": self.category,
                "agent": self.name,
                "strategy": self.strategy,
                "entry": price,
                "sl": price * 0.97,
                "tp": price * 1.06,
                "conf": 0.75,
                "reason": f"Volume {volume_ratio:.1f}x media, prezzo +{price_change:.1f}%"
            }
        
        return None
    
    def _ma_analysis(self, ticker, price, close):
        """Analisi medie mobili: golden cross"""
        if len(close) < 50:
            return None
        
        sma_20 = np.mean(close[-20:])
        sma_50 = np.mean(close[-50:])
        sma_20_prev = np.mean(close[-21:-1])
        sma_50_prev = np.mean(close[-51:-1])
        
        # Golden cross
        if sma_20_prev <= sma_50_prev and sma_20 > sma_50:
            return {
                "ticker": ticker,
                "category": self.category,
                "agent": self.name,
                "strategy": self.strategy,
                "entry": price,
                "sl": price * 0.96,
                "tp": price * 1.10,
                "conf": 0.85,
                "reason": "Golden Cross! SMA20 incrocia sopra SMA50"
            }
        
        # Prezzo sopra SMA20 (trend rialzista)
        if price > sma_20 and sma_20 > sma_50:
            return {
                "ticker": ticker,
                "category": self.category,
                "agent": self.name,
                "strategy": self.strategy,
                "entry": price,
                "sl": price * 0.97,
                "tp": price * 1.07,
                "conf": 0.70,
                "reason": f"Trend rialzista: prezzo sopra SMA20"
            }
        
        return None
    
    def _default_analysis(self, ticker, price, close):
        """Analisi base di default"""
        if len(close) < 5:
            return None
        
        # Trend semplice
        trend = (close[-1] - close[-5]) / close[-5] * 100 if len(close) >= 5 else 0
        
        if trend > 0:
            return {
                "ticker": ticker,
                "category": self.category,
                "agent": self.name,
                "strategy": self.strategy,
                "entry": price,
                "sl": price * 0.98,
                "tp": price * 1.04,
                "conf": 0.55 + (trend / 100),
                "reason": f"Trend 5gg: +{trend:.1f}%"
            }
        
        return None

# =========================================================
# CREA AGENTI CON STRATEGIE DIVERSE
# =========================================================
AGENTS = [
    # Momentum
    SmartAgent("Momentum Hunter", "tech", ["NVDA", "PLTR"], "momentum"),
    SmartAgent("Crypto Momentum", "crypto", ["BTC-USD", "ETH-USD"], "momentum"),
    
    # RSI (ipervenduto)
    SmartAgent("RSI Reversal", "tech", ["NVDA", "TSLA", "META"], "rsi"),
    SmartAgent("Crypto RSI", "crypto", ["BTC-USD", "ETH-USD", "SOL-USD"], "rsi"),
    
    # Volume
    SmartAgent("Volume Accumulator", "tech", ["AAPL", "MSFT"], "volume"),
    SmartAgent("Whale Watcher", "crypto", ["BTC-USD"], "volume"),
    
    # Medie mobili
    SmartAgent("Golden Cross", "etf", ["SPY", "QQQ"], "ma_crossover"),
    SmartAgent("Trend Follower", "tech", ["MSFT", "NVDA"], "ma_crossover"),
    
    # Difesa/energia (strategia base)
    SmartAgent("Defense Analyst", "defense", ["LMT", "NOC"], "default"),
    SmartAgent("Energy Analyst", "energy", ["XOM", "CVX"], "default"),
]

print(f"🧬 Agenti con analisi reale: {len(AGENTS)}")

# =========================================================
# WATCHLIST REALE (derivata dagli agenti)
# =========================================================
WATCHLIST = list(set([ticker for agent in AGENTS for ticker in agent.tickers]))
print(f"📊 Watchlist: {len(WATCHLIST)} ticker - {WATCHLIST}")

# =========================================================
# DATI LIVE
# =========================================================
def get_live_price_alpha(ticker):
    """Prezzo da Alpha Vantage"""
    try:
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={ALPHA_VANTAGE_KEY}"
        r = requests.get(url, timeout=5)
        data = r.json()
        if 'Global Quote' in data and '05. price' in data['Global Quote']:
            return float(data['Global Quote']['05. price'])
    except:
        pass
    return None

def get_crypto_price_binance(ticker):
    """Prezzo crypto da Binance"""
    symbol = ticker.replace("-USD", "USDT")
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        r = requests.get(url, timeout=3)
        return float(r.json()['price'])
    except:
        return None

def get_live_price(ticker):
    """Ottiene prezzo dalla fonte appropriata"""
    if ticker in ["BTC-USD", "ETH-USD", "SOL-USD"]:
        return get_crypto_price_binance(ticker)
    return get_live_price_alpha(ticker)

# =========================================================
# VALIDAZIONE SEGNALI (2+ CONFERME, più realistico)
# =========================================================
signals_validated = []

def validate_signals(signals):
    """Validazione: almeno 2 segnali concordi per ticker"""
    per_ticker = {}
    for s in signals:
        if s is None:
            continue
        ticker = s["ticker"]
        if ticker not in per_ticker:
            per_ticker[ticker] = []
        per_ticker[ticker].append(s)
    
    valid = []
    for ticker, sigs in per_ticker.items():
        if len(sigs) >= 2:  # 2 conferme sono sufficienti
            best = sorted(sigs, key=lambda x: x["conf"], reverse=True)[0]
            valid.append(best)
    
    return valid

# =========================================================
# SCANSIONE PRINCIPALE
# =========================================================
def scan_all_tickers():
    print(f"\n🔍 SCANSIONE - {datetime.now().strftime('%H:%M:%S')}")
    
    all_signals = []
    
    for ticker in WATCHLIST:
        price = get_live_price(ticker)
        if not price:
            print(f"   ❌ {ticker}: prezzo non disponibile")
            continue
        
        print(f"   📊 {ticker}: ${price:.2f}")
        
        for agent in AGENTS:
            if agent.activate(ticker):
                signal = agent.analyze(ticker, price)
                if signal:
                    all_signals.append(signal)
                    print(f"      ✅ {agent.name}: conf={signal['conf']:.0%} - {signal['reason']}")
        
        time.sleep(12)  # Rate limiting
    
    print(f"\n   Segnali grezzi: {len(all_signals)}")
    
    validated = validate_signals(all_signals)
    print(f"   Validati (2+ conferme): {len(validated)}")
    
    if validated:
        global signals_validated
        signals_validated = validated
        send_report(validated)
    else:
        print("   ⚠️ Nessun segnale valido")
    
    return validated

def send_report(signals):
    """Invia report Telegram"""
    if not signals:
        return
    
    # Ordina per confidenza
    top = sorted(signals, key=lambda x: x["conf"], reverse=True)[:3]
    
    msg = f"🏆 *TOP SEGNALI* {datetime.now().strftime('%H:%M')}\n\n"
    
    for i, s in enumerate(top, 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
        msg += f"{emoji} *{s['ticker']}* ({s['category']})\n"
        msg += f"   🤖 {s['agent']} - {s['strategy']}\n"
        msg += f"   💰 Entry: ${s['entry']:.2f}\n"
        msg += f"   🎯 TP: ${s['tp']:.2f} | 🛑 SL: ${s['sl']:.2f}\n"
        msg += f"   🔒 Conf: {s['conf']:.0%}\n"
        msg += f"   📝 {s['reason']}\n\n"
    
    send_telegram(msg)

# =========================================================
# WEBHOOK
# =========================================================
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    ticker = data.get('ticker')
    price = data.get('price', 0)
    
    print(f"\n📡 Webhook: {ticker} @ ${price}")
    
    signals = []
    for agent in AGENTS:
        if agent.activate(ticker):
            signal = agent.analyze(ticker, price)
            if signal:
                signals.append(signal)
    
    validated = validate_signals(signals)
    
    if validated:
        best = validated[0]
        msg = f"⚡ *SEGNALE* {ticker}\n\n"
        msg += f"🤖 {best['agent']} ({best['strategy']})\n"
        msg += f"💰 Entry: ${best['entry']:.2f}\n"
        msg += f"🎯 TP: ${best['tp']:.2f}\n"
        msg += f"📝 {best['reason']}"
        send_telegram(msg)
        return jsonify({"status": "validated", "signal": best})
    
    return jsonify({"status": "rejected"})

# =========================================================
# ROUTES
# =========================================================
@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "agents": len(AGENTS),
        "watchlist": len(WATCHLIST),
        "signals": len(signals_validated)
    })

@app.route('/scan', methods=['GET'])
def scan():
    scan_all_tickers()
    return jsonify({"status": "ok"})

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "name": "Titan-G",
        "version": "2.0",
        "agents": len(AGENTS),
        "strategies": ["momentum", "rsi", "volume", "ma_crossover", "default"]
    })

# =========================================================
# MAIN
# =========================================================
def schedule_scan():
    while True:
        scan_all_tickers()
        time.sleep(3600)

def run_bot():
    print("\n" + "=" * 60)
    print("🚀 TITAN-G 2.0 - CON ANALISI REALE")
    print(f"📊 Watchlist: {len(WATCHLIST)} ticker")
    print(f"🧬 Agenti: {len(AGENTS)} con strategie diverse")
    print(f"🎯 Strategie: momentum, rsi, volume, ma_crossover")
    print("=" * 60)
    
    send_telegram(f"🚀 *TITAN-G 2.0 ATTIVO*\n\n📊 {len(WATCHLIST)} ticker\n🧬 {len(AGENTS)} agenti con analisi reale\n🎯 Strategie: momentum, RSI, volume, MA crossover\n✅ Validazione: 2+ conferme")
    
    threading.Thread(target=schedule_scan, daemon=True).start()
    app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == "__main__":
    run_bot()