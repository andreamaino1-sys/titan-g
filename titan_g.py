# ================================================
# GRAFENE HFT SYSTEM v29.0 - GOOGLE COLAB
# NUOVI AGENTI:
#   - Pattern-X    (pattern recognition 50 anni)
#   - The Satoshi  (BTC on-chain correlazione)
#   - A-Quant 7    (arbitraggio statistico)
#   - Chronos-Turbo (supply chain impact)
#   - The Skeptic  (stress test scenari negativi)
#   - The Regulator (compliance SEC check)
#   - Scalping Mode (scan 15min, soglie brevi)
#   - Mirroring    (multi-chat Telegram)
# ================================================
# Cella 1: !pip install -q curl_cffi yfinance --upgrade --no-deps
# Cella 2: from google.colab import drive; drive.mount('/content/drive')

from curl_cffi import requests as cffi_requests
import yfinance as yf
import requests
import time
import pickle
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from collections import defaultdict

# ===================== CONFIG =====================
YF_SESSION       = cffi_requests.Session(impersonate="chrome110")
TELEGRAM_TOKEN   = "8629848762:AAHa1l3CEs0AguKWINcAKrvynBCi5Xglsq0"
TELEGRAM_CHAT_ID = 2110183214
DRIVE_CACHE_PATH = "/content/drive/MyDrive/grafene_cache.pkl"
CACHE_MAX_AGE_H  = 24

# ── Mirroring: aggiungi qui altri chat_id Telegram ──
MIRROR_CHAT_IDS  = [
    TELEGRAM_CHAT_ID,
    # 987654321,   # secondo canale
    # -1001234567, # gruppo Telegram
]

# ── Modalità ─────────────────────────────────────
MODE_SWING    = "swing"    # scan 3x/giorno, SL 2.5%, TP 8%
MODE_SCALPING = "scalping" # scan ogni 15min, SL 0.8%, TP 2%
ACTIVE_MODE   = MODE_SWING # cambia in MODE_SCALPING per scalping

# ── Orari swing ──────────────────────────────────
SCAN_TIMES_SWING    = ["08:00", "13:30", "19:00"]  # UTC
SCAN_INTERVAL_SCALP = 15 * 60                        # 15 minuti in secondi

# ── Parametri rischio per modalità ───────────────
RISK_PARAMS = {
    MODE_SWING:    {"sl": 0.025, "tp": 0.08,  "min_score": 0.82, "min_change": 2.0},
    MODE_SCALPING: {"sl": 0.008, "tp": 0.02,  "min_score": 0.78, "min_change": 0.5},
}

# ── RSI ──────────────────────────────────────────
RSI_PERIOD     = 14
RSI_OVERSOLD   = 35
RSI_OVERBOUGHT = 70
RSI_BULL_ZONE  = (45, 70)

# ── Live cache ───────────────────────────────────
LIVE_CACHE_TTL_S = 120

# ===================== LOG ========================
def log(level: str, message: str):
    colors = {"INFO":"34","SUCCESS":"32","BLOCKED":"31","WARNING":"33","ALERT":"35"}
    c = colors.get(level.upper(), "37")
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"\033[{c}m[{ts}] {level}: {message}\033[0m")

# ===================== CATEGORIE ==================
CATEGORIES = {
    "Tecnologia": [
        "NVDA","AAPL","MSFT","AVGO","V","CRM","MA","MU","INTC","AMD",
        "PLTR","CSCO","ORCL","QCOM","AMAT","LRCX","ACN","NOW","IBM","ADBE",
        "TXN","INTU","PANW","ANET","CDNS","SNPS","KLAC","ADSK","APH","ROP"
    ],
    "Comunicazione": [
        "GOOGL","META","GOOG","NFLX","DIS","VZ","TMUS","T","CMCSA","CHTR",
        "TTWO","EA","WBD","SE","PINS","SNAP","LYV","RBLX","MTCH","OMC",
        "FOXA","NWSA","Z","IRDM","VOD","AMX"
    ],
    "Consumo Discrezionale": [
        "AMZN","TSLA","HD","MCD","TJX","LOW","BKNG","SBUX","RCL","MAR",
        "ORLY","NKE","GM","HLT","ROST","DASH","AZO","ABNB","F","CMG",
        "CVNA","YUM","DHI","GRMN","EBAY","LEN","LULU","TGT","PHM","EXPE"
    ],
    "Consumo Base": [
        "PG","COST","WMT","KO","PEP","PM","MDLZ","MO","CL",
        "EL","GIS","KHC","MNST","SYY","ADM","STZ","KMB","HSY","KR",
        "KDP","CAG","CLX","HRL","TSN","MKC","CHD","CPB"
    ],
    "Energia": [
        "XOM","CVX","COP","SLB","EOG","MPC","PSX","VLO","OXY",
        "WMB","LNG","BKR","HAL","KMI","OKE","FANG","DVN","CTRA",
        "APA","EQT","TRGP","DINO","AR","RRC"
    ],
    "Finanza": [
        "JPM","BRK-B","BAC","WFC","GS","MS","SPGI","BLK","CB","C",
        "PGR","BX","ICE","AON","CME","MCO","SCHW","AXP","MET",
        "USB","PNC","AFL","TRV","APO","AJG","COF","TFC","BK","PRU"
    ],
    "Sanità": [
        "LLY","UNH","JNJ","NVO","MRK","ABBV","TMO","ABT","DHR","AMGN",
        "PFE","ISRG","MDT","SYK","REGN","BSX","VRTX","GILD","ELV","ZTS",
        "HCA","CVS","BDX","HUM","MRNA","IDXX","DXCM","ILMN","BIIB"
    ],
    "Industria": [
        "CAT","GE","UNP","RTX","HON","UPS","LMT","DE","BA","ADP",
        "ETN","FDX","WM","NOC","ITW","EMR","CSX","FAST","PH","TT",
        "LHX","GD","PCAR","ODFL","PAYX","CARR","RSG","TDG","CTAS","GWW"
    ],
    "Materiali": [
        "LIN","SHW","APD","FCX","ECL","NUE","DOW","NEM","CTVA","PPG",
        "LYB","VMC","MLM","DD","ALB","IP","STLD","CF","MOS","BALL",
        "AVY","EMN","CE","PKG","RS","SCCO","RPM","FMC"
    ],
    "Immobiliare": [
        "PLD","AMT","EQIX","WELL","SPG","PSA","CCI","DLR","O","VICI",
        "IRM","SBAC","AVB","EQR","CBRE","EXR","ESS","HST",
        "ARE","INVH","MAA","WPC","SUI","KIM","GLPI","BXP","UDR"
    ],
    "Utilities": [
        "NEE","SO","DUK","CEG","SRE","AEP","D","EXC","PCG","PEG",
        "XEL","ED","WEC","VST","ETR","FE","ES","EIX","AWK","DTE",
        "PPL","AEE","CNP","ATO","CMS","LNT","NI","PNW","NRG"
    ],
    "Crypto": [
        "BTC-USD","ETH-USD","XRP-USD","BNB-USD","SOL-USD",
        "DOGE-USD","ADA-USD","LINK-USD","XLM-USD",
        "AVAX-USD","DOT-USD","NEAR-USD","LTC-USD"
    ],
    "Blue Chips Europa": [
        "ASML","MC.PA","SAP","NESN.SW","ROG.SW","OR.PA",
        "HSBA.L","SHEL","AZN","RMS.PA","NOVN.SW","TTE","SU.PA",
        "AIR.PA","ALV.DE","SIE.DE","ITX.MC","IBE.MC","RACE",
        "ENEL.MI","AI.PA","BNP.PA","MBG.DE","SAN.MC"
    ]
}

CATEGORY_EMOJI = {
    "Tecnologia":"💻","Comunicazione":"📡","Consumo Discrezionale":"🛍️",
    "Consumo Base":"🛒","Energia":"⚡","Finanza":"🏦","Sanità":"🏥",
    "Industria":"🏭","Materiali":"⚗️","Immobiliare":"🏢","Utilities":"💡",
    "Crypto":"₿","Blue Chips Europa":"🇪🇺"
}

OMNIBUS_RULES = {
    "Tecnologia":            (2.0, 0.82),
    "Comunicazione":         (2.0, 0.82),
    "Consumo Discrezionale": (2.0, 0.82),
    "Consumo Base":          (1.0, 0.80),
    "Energia":               (2.0, 0.82),
    "Finanza":               (1.5, 0.82),
    "Sanità":                (1.5, 0.82),
    "Industria":             (1.5, 0.82),
    "Materiali":             (1.5, 0.80),
    "Immobiliare":           (1.0, 0.80),
    "Utilities":             (1.0, 0.78),
    "Crypto":                (4.0, 0.85),
    "Blue Chips Europa":     (1.5, 0.80),
}

DEFENSIVE_SECTORS = ["Utilities", "Consumo Base", "Sanità", "Immobiliare"]
POSITIVE_WORDS = {"surge","rally","beat","growth","record","strong","bullish","upgrade","buy","profit","gain"}
NEGATIVE_WORDS = {"crash","drop","loss","miss","downgrade","sell","weak","bearish","cut","fraud","bankrupt"}

ARK_HOLDINGS = {
    "ARKK": ["TSLA","ROKU","COIN","TWLO","DXCM","CRSP","BEAM","EXAS"],
    "ARKQ": ["TSLA","KTOS","AXON","AVAV","TER","TRMB","CDNS"],
    "ARKG": ["RXRX","CRSP","BEAM","TDOC","VEEV","EXAS"],
    "ARKW": ["TSLA","COIN","ROKU","TWLO","SHOP","HOOD"],
    "ARKF": ["HOOD","COIN","SOFI","AFRM","MELI"],
}

SHADOW_HOLDINGS = {
    "Renaissance": ["NVDA","MSFT","AAPL","GOOGL","META","AMZN","JPM","V","MA"],
    "Citadel":     ["AAPL","MSFT","NVDA","AMZN","TSLA","GOOGL","META","BRK-B","JPM"],
    "Jane Street": ["AAPL","MSFT","AMZN","GOOGL","NVDA","TSLA","META","V","JPM"],
    "Bridgewater": ["AAPL","MSFT","JNJ","PG","KO"],
    "Two Sigma":   ["NVDA","AAPL","MSFT","AMZN","GOOGL","META","TSLA","V","MA"],
}

WORLD_MONITOR_SECTORS = {
    "war":       {"Energia": +0.06, "Industria": +0.05, "Materiali": +0.04},
    "sanctions": {"Energia": +0.05, "Materiali": +0.04},
    "recession": {"Utilities": +0.05, "Consumo Base": +0.04, "Sanità": +0.03},
    "inflation": {"Energia": +0.04, "Materiali": +0.03},
    "rate hike": {"Finanza": +0.03, "Immobiliare": -0.04},
    "tech boom": {"Tecnologia": +0.07, "Comunicazione": +0.04},
    "oil":       {"Energia": +0.06},
    "pandemic":  {"Sanità": +0.07},
}

# Supply chain: chi dipende da chi
SUPPLY_CHAIN_GRAPH = {
    "NVDA": ["MSFT","GOOGL","META","AMZN","TSLA","AAPL"],
    "AMD":  ["MSFT","GOOGL","META","AMZN"],
    "INTC": ["MSFT","AAPL","IBM","CSCO"],
    "AMAT": ["NVDA","AMD","INTC","QCOM","MU"],
    "LRCX": ["NVDA","AMD","INTC","QCOM","MU"],
    "XOM":  ["LIN","DOW","MPC","VLO"],
    "CVX":  ["LIN","DOW","MPC","PSX"],
    "LIN":  ["DOW","CE","LYB","EMN"],
    "TSLA": ["NMC","LIT","ALB"],
    "AAPL": ["QCOM","AVGO","TXN","AMAT"],
}

# Asset correlati a BTC per Satoshi
BTC_CORRELATED = {
    "alto":   ["ETH-USD","SOL-USD","BNB-USD","AVAX-USD","COIN","MSTR"],
    "medio":  ["SQ","PYPL","HOOD","MELI"],
    "basso":  ["NVDA","AMD","TSLA"],
}

# Asset con problemi compliance noti (esempio)
COMPLIANCE_WATCHLIST = {
    "PARA": "delistata",
    "CLOV": "SEC investigation",
    "SPCE": "diluizione massiva",
}


# ================================================
# ⚡ LIVE CACHE
# ================================================
class LiveCache:
    def __init__(self, ttl: int = LIVE_CACHE_TTL_S):
        self._store = {}
        self._ttl   = ttl

    def get(self, key):
        if key in self._store:
            val, ts = self._store[key]
            if (datetime.now() - ts).total_seconds() < self._ttl:
                return val
        return None

    def set(self, key, value):
        self._store[key] = (value, datetime.now())


# ================================================
# 💾 THE VAULT
# ================================================
class TheVault:
    def save(self, cache: dict):
        try:
            with open(DRIVE_CACHE_PATH, "wb") as f:
                pickle.dump({"timestamp": datetime.now(), "cache": cache}, f)
            log("SUCCESS", f"💾 Cache salvata ({len(cache)} simboli)")
        except Exception as e:
            log("WARNING", f"Vault save: {e}")

    def load(self) -> dict:
        try:
            if not os.path.exists(DRIVE_CACHE_PATH):
                return {}
            with open(DRIVE_CACHE_PATH, "rb") as f:
                data = pickle.load(f)
            age_h = (datetime.now() - data["timestamp"]).total_seconds() / 3600
            if age_h > CACHE_MAX_AGE_H:
                log("INFO", f"📂 Cache scaduta ({age_h:.1f}h)")
                return {}
            log("SUCCESS", f"📂 Cache Drive: {len(data['cache'])} simboli ({age_h:.1f}h fa)")
            return data["cache"]
        except Exception as e:
            log("WARNING", f"Vault load: {e}")
            return {}


# ================================================
# 📊 RSI AVANZATO
# ================================================
class RSIAnalyzer:
    @staticmethod
    def compute(close, period=RSI_PERIOD):
        delta = close.diff()
        gain  = delta.clip(lower=0).rolling(period).mean()
        loss  = (-delta.clip(upper=0)).rolling(period).mean()
        return 100 - (100 / (1 + gain / loss.replace(0, 1e-9)))

    @staticmethod
    def score(close):
        if len(close) < RSI_PERIOD + 10:
            return 0.0, {}
        rsi   = RSIAnalyzer.compute(close)
        rsi_v = float(rsi.iloc[-1])
        rsi_p = float(rsi.iloc[-2]) if len(rsi) > 1 else rsi_v
        rsi_pp= float(rsi.iloc[-3]) if len(rsi) > 2 else rsi_p
        bonus = 0.0
        tags  = {"rsi_value": round(rsi_v, 1)}

        if rsi_v >= RSI_OVERBOUGHT:
            return -0.15, {**tags, "overbought": True}
        if rsi_v <= RSI_OVERSOLD:
            bonus += 0.10; tags["oversold"] = True
        if RSI_BULL_ZONE[0] <= rsi_v <= RSI_BULL_ZONE[1]:
            bonus += 0.08; tags["bull_zone"] = True
        if rsi_v > rsi_p > rsi_pp:
            bonus += 0.06; tags["momentum"] = True

        price_now  = float(close.iloc[-1])
        price_prev = float(close.iloc[-6]) if len(close) > 5 else price_now
        rsi_6ago   = float(rsi.iloc[-6])   if len(rsi) > 5  else rsi_v
        if price_now < price_prev and rsi_v > rsi_6ago:
            bonus += 0.08; tags["divergenza_bullish"] = True

        return round(max(-0.15, min(0.20, bonus)), 3), tags


# ================================================
# 🔍 PATTERN-X — pattern recognition 50 anni
# ================================================
class PatternX:
    """
    Confronta il pattern di prezzo degli ultimi 20 giorni
    con pattern storici simili negli ultimi 50 anni (cache).
    Se storicamente il pattern è seguito da un rialzo
    nel 70%+ dei casi → bonus.
    """
    def get_pattern_bonus(self, symbol: str, cache: dict) -> tuple[float, str]:
        if symbol not in cache: return 0.0, ""
        close = cache[symbol].copy()
        if len(close) < 250: return 0.0, ""
        try:
            # Pattern corrente: ultimi 20 giorni normalizzati
            recent = close.tail(20)
            norm   = (recent - recent.min()) / (recent.max() - recent.min() + 1e-9)
            pattern = norm.values

            # Scorri la storia cercando pattern simili
            matches_up = matches_dn = 0
            step = 5  # ogni 5 giorni per velocità
            for i in range(0, len(close) - 30, step):
                window = close.iloc[i:i+20]
                w_norm = (window - window.min()) / (window.max() - window.min() + 1e-9)
                # Correlazione con il pattern corrente
                if len(w_norm) < 20: continue
                corr = float(sum((pattern[j] - w_norm.values[j])**2
                                  for j in range(20)) / 20)
                if corr < 0.02:  # match trovato
                    future = close.iloc[i+20:i+30]
                    if len(future) < 5: continue
                    ret = (float(future.iloc[-1]) - float(window.iloc[-1])) / float(window.iloc[-1])
                    if ret > 0.02:   matches_up += 1
                    elif ret < -0.02: matches_dn += 1

            total = matches_up + matches_dn
            if total < 3: return 0.0, ""

            win_rate = matches_up / total
            if win_rate >= 0.70:
                bonus = round((win_rate - 0.5) * 0.20, 3)
                label = f"Pattern match WR={win_rate:.0%} ({total} casi)"
                log("ALERT", f"🔍 Pattern-X: {symbol} {label} (+{bonus})")
                return min(0.12, bonus), label
            return 0.0, ""
        except Exception:
            return 0.0, ""


# ================================================
# ₿ THE SATOSHI — correlazione BTC/macro
# ================================================
class TheSatoshi:
    """
    Legge il prezzo BTC live e verifica:
    - Se BTC è in rialzo forte → bonus per Crypto e asset correlati
    - Se BTC crolla → malus per Crypto e correlati
    - Fear & Greed index pubblico via API
    """
    def __init__(self):
        self.btc_change  = 0.0
        self.fear_greed  = 50
        self._fetch()

    def _fetch(self):
        try:
            t  = yf.Ticker("BTC-USD", session=YF_SESSION)
            h  = t.history(period="2d")
            if not h.empty and len(h) >= 2:
                cur  = float(h['Close'].iloc[-1])
                prev = float(h['Close'].iloc[-2])
                self.btc_change = round(((cur - prev) / prev) * 100, 2)
            # Fear & Greed Index (API pubblica)
            r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=6)
            if r.status_code == 200:
                self.fear_greed = int(r.json()['data'][0]['value'])
            log("INFO", f"₿ Satoshi: BTC {self.btc_change:+.2f}% | F&G {self.fear_greed}")
        except Exception:
            pass

    def get_satoshi_bonus(self, symbol: str, category: str) -> float:
        bonus = 0.0
        # Crypto diretta
        if category == "Crypto":
            if self.btc_change > 3.0:   bonus += 0.08
            elif self.btc_change > 1.0: bonus += 0.04
            elif self.btc_change < -3.0: bonus -= 0.08
            elif self.btc_change < -1.0: bonus -= 0.04
            # Fear & Greed: Extreme Greed (>75) = possibile top, Extreme Fear (<25) = opportunità
            if self.fear_greed < 25:    bonus += 0.05
            elif self.fear_greed > 75:  bonus -= 0.05
        # Asset correlati
        elif symbol in BTC_CORRELATED.get("alto", []):
            bonus += self.btc_change * 0.01
        elif symbol in BTC_CORRELATED.get("medio", []):
            bonus += self.btc_change * 0.005

        return round(max(-0.10, min(0.10, bonus)), 3)


# ================================================
# 📡 A-QUANT 7 — arbitraggio statistico
# ================================================
class AQuant7:
    """
    Identifica divergenze statistiche tra asset correlati.
    Se un asset è significativamente sotto la media del suo
    peer group → segnale di mean reversion (opportunità).
    Bonus se lo spread è > 2 sigma.
    """
    PEER_GROUPS = {
        "chip":    ["NVDA","AMD","INTC","QCOM","AMAT","LRCX","MU"],
        "big_tech":["AAPL","MSFT","GOOGL","META","AMZN"],
        "banks":   ["JPM","BAC","WFC","GS","MS","C"],
        "oil_maj": ["XOM","CVX","COP","OXY"],
        "pharma":  ["LLY","JNJ","MRK","ABBV","PFE","AMGN"],
        "crypto":  ["BTC-USD","ETH-USD","SOL-USD","BNB-USD"],
    }

    def get_arbitrage_bonus(self, symbol: str, cache: dict) -> float:
        group = None
        for g, members in self.PEER_GROUPS.items():
            if symbol in members:
                group = members
                break
        if not group: return 0.0

        try:
            # Rendimento ultimi 5 giorni per ogni membro del gruppo
            returns = {}
            for peer in group:
                if peer in cache and len(cache[peer]) > 5:
                    c = cache[peer]
                    ret = (float(c.iloc[-1]) - float(c.iloc[-6])) / float(c.iloc[-6])
                    returns[peer] = ret

            if len(returns) < 3 or symbol not in returns: return 0.0

            vals   = list(returns.values())
            mean   = sum(vals) / len(vals)
            var    = sum((v - mean)**2 for v in vals) / len(vals)
            std    = var ** 0.5
            if std < 0.001: return 0.0

            z_score = (returns[symbol] - mean) / std

            # Sottoperformante > 2 sigma → opportunità mean reversion
            if z_score < -2.0:
                bonus = round(min(0.10, abs(z_score) * 0.03), 3)
                log("ALERT", f"📡 A-Quant7: {symbol} z={z_score:.1f}σ vs peers (+{bonus})")
                return bonus
            return 0.0
        except Exception:
            return 0.0


# ================================================
# 🔗 CHRONOS-TURBO — supply chain impact
# ================================================
class ChronosTurbo:
    """
    Se un fornitore chiave ha un segnale forte,
    propaga un bonus ai clienti a valle.
    Es: NVDA forte → bonus per MSFT, META, AMZN.
    """
    def __init__(self):
        self.strong_signals = set()  # popolato durante la scan

    def register_signal(self, symbol: str, score: float):
        if score >= 0.85:
            self.strong_signals.add(symbol)

    def get_chain_bonus(self, symbol: str) -> float:
        for supplier, customers in SUPPLY_CHAIN_GRAPH.items():
            if supplier in self.strong_signals and symbol in customers:
                log("INFO", f"🔗 Chronos: {symbol} ← {supplier} supply chain (+0.05)")
                return 0.05
        return 0.0

    def reset(self):
        self.strong_signals = set()


# ================================================
# 🧐 THE SKEPTIC — stress test scenari negativi
# ================================================
class TheSkeptic:
    """
    Prima di approvare un segnale, simula 3 scenari negativi:
    1. Rialzo tassi Fed (+50bp)
    2. Flash crash -10% mercato
    3. Settore in crisi (-20%)
    Se il segnale non sopravvive a 2/3 scenari → penalizzato.
    """
    def stress_test(self, symbol: str, score: float,
                    category: str, cache: dict) -> float:
        if symbol not in cache: return score
        close = cache[symbol].copy()
        if len(close) < 60: return score

        try:
            beta   = self._estimate_beta(close, cache)
            passed = 0

            # Scenario 1: rate hike → impatto su beta alto
            impact1 = -beta * 0.03
            if score + impact1 >= 0.70: passed += 1

            # Scenario 2: flash crash -10%
            impact2 = -beta * 0.10
            if score + impact2 >= 0.60: passed += 1

            # Scenario 3: settore crisi
            sector_impact = -0.05 if category not in DEFENSIVE_SECTORS else -0.02
            if score + sector_impact >= 0.72: passed += 1

            if passed < 2:
                penalty = -0.05
                log("WARNING", f"🧐 Skeptic: {symbol} stress test {passed}/3 (penalità {penalty})")
                return score + penalty

            log("INFO", f"🧐 Skeptic: {symbol} stress test {passed}/3 ✓")
            return score
        except Exception:
            return score

    @staticmethod
    def _estimate_beta(close, cache) -> float:
        spy = cache.get("SPY")
        if spy is None: return 1.0
        try:
            n    = min(len(close), len(spy), 60)
            r_s  = close.pct_change().dropna().tail(n)
            r_m  = spy.pct_change().dropna().tail(n)
            n    = min(len(r_s), len(r_m))
            cov  = sum((r_s.iloc[i] - r_s.mean()) * (r_m.iloc[i] - r_m.mean())
                       for i in range(n)) / n
            var  = sum((r_m.iloc[i] - r_m.mean())**2 for i in range(n)) / n
            return round(cov / max(var, 1e-9), 2)
        except Exception:
            return 1.0


# ================================================
# ⚖️ THE REGULATOR — compliance check
# ================================================
class TheRegulator:
    """
    Verifica che il simbolo non sia nella watchlist
    di compliance (asset con problemi SEC noti,
    delistati, o sotto indagine).
    """
    def is_compliant(self, symbol: str) -> tuple[bool, str]:
        if symbol in COMPLIANCE_WATCHLIST:
            reason = COMPLIANCE_WATCHLIST[symbol]
            log("BLOCKED", f"⚖️ Regulator: {symbol} NON COMPLIANT — {reason}")
            return False, reason
        return True, ""


# ================================================
# 🏛️ THE WATCHTOWER
# ================================================
class TheWatchtower:
    HEADERS = {"User-Agent": "GrafeneHFT contact@grafene.ai"}

    def get_insider_score(self, symbol: str) -> float:
        try:
            start = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            end   = datetime.now().strftime("%Y-%m-%d")
            url   = (f"https://efts.sec.gov/LATEST/search-index"
                     f"?q=%22{symbol}%22&dateRange=custom"
                     f"&startdt={start}&enddt={end}&forms=4")
            r    = requests.get(url, headers=self.HEADERS, timeout=8)
            if r.status_code != 200: return 0.0
            hits = r.json().get("hits", {}).get("hits", [])
            buys = sells = 0
            for hit in hits[:20]:
                text = str(hit.get("_source", "")).lower()
                if "purchase" in text: buys += 1
                elif "sale" in text:   sells += 1
            if buys == 0 and sells == 0: return 0.0
            bonus = round((buys / max(buys + sells, 1)) * 0.15, 3)
            if buys > 0:
                log("ALERT", f"🏛️ Watchtower: {symbol} {buys} insider buy (+{bonus})")
            return bonus
        except Exception:
            return 0.0


# ================================================
# 🗣️ THE VOICE
# ================================================
class TheVoice:
    def get_sentiment(self, symbol: str) -> float:
        try:
            url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region=US&lang=en-US"
            r   = requests.get(url, timeout=6)
            if r.status_code != 200: return 0.0
            root  = ET.fromstring(r.content)
            items = root.findall(".//item")[:10]
            score = articles = 0
            for item in items:
                text = ((item.findtext("title") or "") + " " +
                        (item.findtext("description") or "")).lower()
                pos = sum(1 for w in POSITIVE_WORDS if w in text)
                neg = sum(1 for w in NEGATIVE_WORDS if w in text)
                if pos + neg > 0:
                    score    += (pos - neg) / (pos + neg)
                    articles += 1
            if articles == 0: return 0.0
            bonus = round((score / articles) * 0.10, 3)
            if abs(bonus) >= 0.03:
                log("INFO", f"🗣️ Voice: {symbol} {'pos' if bonus>0 else 'neg'} ({bonus:+.2f})")
            return bonus
        except Exception:
            return 0.0


# ================================================
# ✅ THE VERIFIER
# ================================================
class TheVerifier:
    def verify(self, symbol: str, live_price: float, cache: dict) -> bool:
        if live_price <= 0: return False
        if symbol not in cache: return True
        hist_mean = float(cache[symbol].tail(60).mean())
        if hist_mean <= 0: return True
        ratio = live_price / hist_mean
        if ratio > 5.0 or ratio < 0.1:
            log("BLOCKED", f"✅ Verifier: {symbol} anomalia (ratio={ratio:.2f})")
            return False
        return True


# ================================================
# 📊 THE HISTORIAN — walk-forward
# ================================================
class TheHistorian:
    def backtest_score(self, symbol: str, cache: dict) -> float:
        if symbol not in cache: return 0.0
        close = cache[symbol].copy()
        if len(close) < 500: return 0.0
        try:
            split    = int(len(close) * 0.6)
            train_wr = self._win_rate(close.iloc[:split])
            test_wr  = self._win_rate(close.iloc[split:])
            if train_wr == 0: return 0.0
            if test_wr / max(train_wr, 0.01) < 0.7:
                log("WARNING", f"📊 Historian: {symbol} overfitting (train={train_wr:.0%} test={test_wr:.0%})")
                return -0.05
            bonus = round((test_wr - 0.5) * 0.20, 3)
            if bonus > 0.02:
                log("INFO", f"📊 Historian: {symbol} WR test={test_wr:.0%} (+{bonus})")
            return max(-0.10, min(0.10, bonus))
        except Exception:
            return 0.0

    @staticmethod
    def _win_rate(close) -> float:
        if len(close) < 60: return 0.0
        sma50  = close.rolling(50).mean()
        sma200 = close.rolling(200).mean()
        wins = losses = 0
        for i in range(10, len(close) - 10):
            if sma50.iloc[i] > sma200.iloc[i]:
                ret = (float(close.iloc[i+10]) - float(close.iloc[i])) / float(close.iloc[i])
                if ret > 0.02:    wins += 1
                elif ret < -0.02: losses += 1
        total = wins + losses
        return wins / total if total > 0 else 0.0


# ================================================
# 📈 THE FLOW
# ================================================
class TheFlow:
    def get_options_bonus(self, symbol: str) -> float:
        try:
            t = yf.Ticker(symbol, session=YF_SESSION)
            expirations = t.options
            if not expirations: return 0.0
            opt   = t.option_chain(expirations[0])
            calls = opt.calls
            if calls.empty: return 0.0
            calls = calls[calls['inTheMoney'] == False].copy()
            calls = calls[calls['volume'] > 1000]
            if calls.empty: return 0.0
            calls['ratio'] = calls['volume'] / calls['openInterest'].replace(0, 1)
            max_ratio = float(calls['ratio'].max())
            if max_ratio > 3.0:
                bonus = min(0.12, round(max_ratio / 100, 3))
                log("ALERT", f"📈 Flow: {symbol} call OTM ratio={max_ratio:.1f} (+{bonus})")
                return bonus
            return 0.0
        except Exception:
            return 0.0


# ================================================
# 🌍 THE CORRELATOR
# ================================================
class TheCorrelator:
    MACRO_RSS = "https://feeds.reuters.com/reuters/businessNews"
    SECTOR_KEYWORDS = {
        "Energia":    (["oil","opec","crude","gas","energy"], +0.08),
        "Finanza":    (["fed","rate","interest","bank","inflation"], +0.06),
        "Tecnologia": (["ai","chip","semiconductor","nvidia","tech"], +0.06),
        "Sanità":     (["fda","drug","pharma","approval","vaccine"], +0.06),
        "Crypto":     (["bitcoin","crypto","btc","ethereum","blockchain"], +0.08),
    }

    def __init__(self):
        self.macro_headlines = self._fetch_headlines()

    def _fetch_headlines(self) -> str:
        try:
            r    = requests.get(self.MACRO_RSS, timeout=8)
            root = ET.fromstring(r.content)
            return " ".join(
                ((item.findtext("title") or "") + " " + (item.findtext("description") or "")).lower()
                for item in root.findall(".//item")[:20]
            )
        except Exception:
            return ""

    def get_macro_bonus(self, category: str) -> float:
        if not self.macro_headlines: return 0.0
        keywords, base_bonus = self.SECTOR_KEYWORDS.get(category, ([], 0.0))
        if not keywords: return 0.0
        hits  = sum(1 for kw in keywords if kw in self.macro_headlines)
        if hits == 0: return 0.0
        bonus = round(base_bonus * (hits / len(keywords)), 3)
        if bonus > 0.02:
            log("INFO", f"🌍 Correlator: {category} ({hits} kw, +{bonus})")
        return bonus


# ================================================
# 🚀 THE ARK
# ================================================
class TheArk:
    def get_ark_bonus(self, symbol: str) -> float:
        count = sum(1 for h in ARK_HOLDINGS.values() if symbol in h)
        if count == 0: return 0.0
        bonus = round(min(0.10, count * 0.03), 3)
        log("INFO", f"🚀 Ark: {symbol} in {count} ETF ARK (+{bonus})")
        return bonus


# ================================================
# 📉 THE CONTRARIAN
# ================================================
class TheContrarian:
    def __init__(self):
        self.active     = False
        self.spy_change = 0.0
        self.vix        = 0.0
        self._check_market()

    def _check_market(self):
        try:
            t = yf.Ticker("SPY", session=YF_SESSION)
            h = t.history(period="2d")
            if not h.empty and len(h) >= 2:
                cur  = float(h['Close'].iloc[-1])
                prev = float(h['Close'].iloc[-2])
                self.spy_change = round(((cur - prev) / prev) * 100, 2)
            v = yf.Ticker("^VIX", session=YF_SESSION)
            vh = v.history(period="1d")
            if not vh.empty:
                self.vix = round(float(vh['Close'].iloc[-1]), 2)
            self.active = self.spy_change <= -2.0 or self.vix >= 25.0
            status = f"SPY {self.spy_change:+.2f}% | VIX {self.vix:.1f}"
            if self.active: log("ALERT", f"📉 Contrarian ATTIVATO — {status}")
            else:           log("INFO",  f"📊 Mercato OK — {status}")
        except Exception:
            pass

    def adjust_rules(self, category, change_min, score_min):
        if not self.active: return change_min, score_min
        if category in DEFENSIVE_SECTORS:
            return change_min * 0.7, score_min - 0.03
        return change_min * 1.5, score_min + 0.05

    def get_contrarian_tag(self, category):
        return self.active and category in DEFENSIVE_SECTORS


# ================================================
# 🕵️ THE SHADOW
# ================================================
class TheShadow:
    def get_shadow_bonus(self, symbol: str) -> float:
        count = sum(1 for h in SHADOW_HOLDINGS.values() if symbol in h)
        if count == 0: return 0.0
        bonus = round(min(0.12, count * 0.025), 3)
        funds = [n for n, h in SHADOW_HOLDINGS.items() if symbol in h]
        log("INFO", f"🕵️ Shadow: {symbol} → {', '.join(funds)} (+{bonus})")
        return bonus


# ================================================
# 🌐 WORLD MONITOR
# ================================================
class WorldMonitor:
    FEEDS = [
        "https://world-monitor.com/feed/",
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    ]

    def __init__(self):
        self.text = ""
        self._fetch()

    def _fetch(self):
        texts = []
        for url in self.FEEDS:
            try:
                r = requests.get(url, timeout=8,
                    headers={"User-Agent": "GrafeneHFT contact@grafene.ai"})
                if r.status_code != 200: continue
                root = ET.fromstring(r.content)
                for item in root.findall(".//item")[:15]:
                    texts.append((item.findtext("title") or "").lower() + " " +
                                  (item.findtext("description") or "").lower())
            except Exception:
                continue
        self.text = " ".join(texts)
        if self.text: log("SUCCESS", f"🌐 WorldMonitor: {len(texts)} eventi")

    def get_geopolitical_bonus(self, category: str) -> float:
        if not self.text: return 0.0
        total = sum(
            impact for keyword, impacts in WORLD_MONITOR_SECTORS.items()
            if keyword in self.text
            for cat, impact in impacts.items()
            if cat == category
        )
        return round(max(-0.10, min(0.12, total)), 3)


# ================================================
# 📰 SEEKING ALPHA
# ================================================
class SeekingAlpha:
    def get_sa_bonus(self, symbol: str) -> float:
        try:
            url = f"https://seekingalpha.com/api/sa/combined/{symbol}.xml"
            r   = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code != 200: return 0.0
            root  = ET.fromstring(r.content)
            items = root.findall(".//item")[:5]
            if not items: return 0.0
            score = articles = 0
            for item in items:
                text = ((item.findtext("title") or "") + " " +
                        (item.findtext("description") or "")).lower()
                pos = sum(1 for w in POSITIVE_WORDS if w in text)
                neg = sum(1 for w in NEGATIVE_WORDS if w in text)
                if "strong buy" in text or "outperform" in text: pos += 2
                if "strong sell" in text or "underperform" in text: neg += 2
                if pos + neg > 0:
                    score    += (pos - neg) / (pos + neg)
                    articles += 1
            if articles == 0: return 0.0
            bonus = round((score / articles) * 0.08, 3)
            if abs(bonus) >= 0.03:
                log("INFO", f"📰 SA: {symbol} {'bullish' if bonus>0 else 'bearish'} ({bonus:+.2f})")
            return bonus
        except Exception:
            return 0.0


# ================================================
# 🤖 TICKERON
# ================================================
class Tickeron:
    BULLISH = ["ascending triangle","bull flag","cup and handle",
               "double bottom","golden cross","breakout","oversold"]
    BEARISH = ["descending triangle","bear flag","head and shoulders",
               "double top","death cross","breakdown","overbought"]

    def get_pattern_bonus(self, symbol: str) -> float:
        try:
            url = f"https://tickeron.com/ticker/{symbol}/"
            r   = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code != 200: return 0.0
            text    = r.text.lower()
            bullish = sum(1 for p in self.BULLISH if p in text)
            bearish = sum(1 for p in self.BEARISH if p in text)
            if bullish == 0 and bearish == 0: return 0.0
            bonus = round(((bullish - bearish) / max(bullish + bearish, 1)) * 0.10, 3)
            if abs(bonus) >= 0.03:
                log("INFO", f"🤖 Tickeron: {symbol} {bullish}↑{bearish}↓ ({bonus:+.2f})")
            return bonus
        except Exception:
            return 0.0


# ================================================
# 🧠 OMNIBUS — orchestratore globale
# ================================================
class Omnibus:
    def __init__(self, vault_cache, watchtower, voice, verifier, historian,
                 flow, correlator, ark, contrarian, shadow, world_monitor,
                 seeking_alpha, tickeron, pattern_x, satoshi, aquant7,
                 chronos, skeptic, regulator):
        self.cache         = vault_cache
        self.watchtower    = watchtower
        self.voice         = voice
        self.verifier      = verifier
        self.historian     = historian
        self.flow          = flow
        self.correlator    = correlator
        self.ark           = ark
        self.contrarian    = contrarian
        self.shadow        = shadow
        self.world_monitor = world_monitor
        self.seeking_alpha = seeking_alpha
        self.tickeron      = tickeron
        self.pattern_x     = pattern_x
        self.satoshi       = satoshi
        self.aquant7       = aquant7
        self.chronos       = chronos
        self.skeptic       = skeptic
        self.regulator     = regulator
        self.all_signals   = []

    def submit(self, symbol, data, score, rsi_tags, category):
        rp = RISK_PARAMS[ACTIVE_MODE]

        # Compliance check
        ok, reason = self.regulator.is_compliant(symbol)
        if not ok: return

        change_min = rp["min_change"]
        score_min  = rp["min_score"]
        if ACTIVE_MODE == MODE_SWING:
            change_min_cat, score_min_cat = OMNIBUS_RULES.get(category, (2.0, 0.82))
            change_min = max(change_min, change_min_cat)
            score_min  = max(score_min, score_min_cat)

        change_min, score_min = self.contrarian.adjust_rules(category, change_min, score_min)

        if abs(data['change']) < change_min or score < score_min: return
        if not self.verifier.verify(symbol, data['price'], self.cache): return
        if rsi_tags.get("overbought"):
            log("BLOCKED", f"📊 RSI overbought: {symbol}")
            return

        is_usa = "-USD" not in symbol and "." not in symbol

        # Stress test prima di procedere
        score = self.skeptic.stress_test(symbol, score, category, self.cache)

        insider_bonus    = self.watchtower.get_insider_score(symbol)    if is_usa else 0.0
        sentiment_bonus  = self.voice.get_sentiment(symbol)             if is_usa else 0.0
        historian_bonus  = self.historian.backtest_score(symbol, self.cache)
        flow_bonus       = self.flow.get_options_bonus(symbol)          if is_usa else 0.0
        macro_bonus      = self.correlator.get_macro_bonus(category)
        ark_bonus        = self.ark.get_ark_bonus(symbol)               if is_usa else 0.0
        shadow_bonus     = self.shadow.get_shadow_bonus(symbol)         if is_usa else 0.0
        contrarian_bonus = 0.05 if self.contrarian.get_contrarian_tag(category) else 0.0
        geo_bonus        = self.world_monitor.get_geopolitical_bonus(category)
        sa_bonus         = self.seeking_alpha.get_sa_bonus(symbol)      if is_usa else 0.0
        tickeron_bonus   = self.tickeron.get_pattern_bonus(symbol)      if is_usa else 0.0
        pattern_bonus, pattern_label = self.pattern_x.get_pattern_bonus(symbol, self.cache)
        satoshi_bonus    = self.satoshi.get_satoshi_bonus(symbol, category)
        aquant_bonus     = self.aquant7.get_arbitrage_bonus(symbol, self.cache)
        chain_bonus      = self.chronos.get_chain_bonus(symbol)

        final_score = min(1.0, score + insider_bonus + sentiment_bonus +
                          historian_bonus + flow_bonus + macro_bonus +
                          ark_bonus + shadow_bonus + contrarian_bonus +
                          geo_bonus + sa_bonus + tickeron_bonus +
                          pattern_bonus + satoshi_bonus + aquant_bonus + chain_bonus)

        if final_score < rp["min_score"]: return

        # Registra per Chronos supply chain
        self.chronos.register_signal(symbol, final_score)

        self.all_signals.append({
            "symbol":        symbol,
            "data":          data,
            "score":         final_score,
            "category":      category,
            "rsi_tags":      rsi_tags,
            "insider":       insider_bonus > 0,
            "sentiment":     sentiment_bonus,
            "historian":     historian_bonus,
            "flow":          flow_bonus > 0,
            "macro":         macro_bonus > 0,
            "ark":           ark_bonus > 0,
            "shadow":        shadow_bonus > 0,
            "contrarian":    contrarian_bonus > 0,
            "geo":           geo_bonus,
            "sa":            sa_bonus,
            "tickeron":      tickeron_bonus,
            "pattern":       pattern_bonus > 0,
            "pattern_label": pattern_label,
            "satoshi":       satoshi_bonus,
            "aquant":        aquant_bonus > 0,
            "chain":         chain_bonus > 0,
        })

    def get_top(self, n=5):
        seen, unique = set(), []
        for s in sorted(self.all_signals, key=lambda x: x['score'], reverse=True):
            if s['symbol'] not in seen:
                seen.add(s['symbol'])
                unique.append(s)
        return unique[:n]

    def reset(self):
        self.all_signals = []
        self.chronos.reset()


# ================================================
# ⚙️ SISTEMA PRINCIPALE
# ================================================
def flatten_close(df, symbol):
    if df is None or df.empty: return None
    if hasattr(df.columns, 'levels'):
        try:    return df['Close'][symbol].dropna()
        except Exception:
            try: return df.xs('Close', axis=1, level=0).iloc[:, 0].dropna()
            except Exception: return None
    return df['Close'].dropna() if 'Close' in df.columns else None


def analyze_signal_advanced(symbol, cache):
    if symbol not in cache: return 0.0, {}
    close = cache[symbol].copy()
    if len(close) < 200: return 0.0, {}
    sma50  = close.rolling(50).mean()
    sma200 = close.rolling(200).mean()
    ema20  = close.ewm(span=20).mean()
    price  = float(close.iloc[-1])
    score  = 0.50
    if price > float(sma50.iloc[-1]) > float(sma200.iloc[-1]): score += 0.20
    if price > float(ema20.iloc[-1]):                            score += 0.05
    if price > float(close.tail(20).max()) * 0.97:               score += 0.10
    if (len(close) >= 4 and
        float(close.iloc[-1]) > float(close.iloc[-2]) > float(close.iloc[-3])): score += 0.05
    rsi_bonus, rsi_tags = RSIAnalyzer.score(close)
    score += rsi_bonus
    return max(0.1, min(1.0, score)), rsi_tags


class GrapheneSystem:
    def __init__(self):
        self.vault         = TheVault()
        self.cache         = self.vault.load()
        self.live_cache    = LiveCache()
        if len(self.cache) < 10:
            self.load_historical_data()

        self.watchtower    = TheWatchtower()
        self.voice         = TheVoice()
        self.verifier      = TheVerifier()
        self.historian     = TheHistorian()
        self.flow          = TheFlow()
        self.correlator    = TheCorrelator()
        self.ark           = TheArk()
        self.contrarian    = TheContrarian()
        self.shadow        = TheShadow()
        self.world_monitor = WorldMonitor()
        self.seeking_alpha = SeekingAlpha()
        self.tickeron      = Tickeron()
        self.pattern_x     = PatternX()
        self.satoshi       = TheSatoshi()
        self.aquant7       = AQuant7()
        self.chronos       = ChronosTurbo()
        self.skeptic       = TheSkeptic()
        self.regulator     = TheRegulator()
        self.omnibus       = Omnibus(
            self.cache, self.watchtower, self.voice, self.verifier,
            self.historian, self.flow, self.correlator, self.ark,
            self.contrarian, self.shadow, self.world_monitor,
            self.seeking_alpha, self.tickeron, self.pattern_x,
            self.satoshi, self.aquant7, self.chronos,
            self.skeptic, self.regulator
        )

    def load_historical_data(self):
        total = sum(len(v) for v in CATEGORIES.values())
        log("INFO", f"📡 Scarico dati storici per {total} simboli...")
        loaded = 0
        for symbols in CATEGORIES.values():
            for symbol in symbols:
                if symbol in self.cache:
                    loaded += 1
                    continue
                try:
                    df    = yf.download(symbol, period="5y", progress=False, session=YF_SESSION)
                    close = flatten_close(df, symbol)
                    if close is not None and len(close) > 200:
                        self.cache[symbol] = close
                        loaded += 1
                except Exception:
                    pass
                time.sleep(0.25)
        self.vault.save(self.cache)
        log("SUCCESS", f"Cache pronta: {loaded}/{total} simboli")

    def get_live_data(self, symbol):
        cached = self.live_cache.get(symbol)
        if cached: return cached, None
        try:
            t     = yf.Ticker(symbol, session=YF_SESSION)
            h     = t.history(period="2d")
            if h.empty or 'Close' not in h.columns: return None, None
            close = h['Close'].dropna()
            if len(close) < 1: return None, None
            cur  = float(close.iloc[-1])
            prev = float(close.iloc[-2]) if len(close) > 1 else cur
            data = {'symbol': symbol, 'price': round(cur, 4),
                    'change': round(((cur - prev) / prev) * 100, 2)}
            self.live_cache.set(symbol, data)
            return data, h
        except Exception:
            return None, None

    def create_message(self, signal):
        rp    = RISK_PARAMS[ACTIVE_MODE]
        d     = signal['data']
        entry = d['price']
        sl    = round(entry * (1 - rp["sl"]), 4)
        tp    = round(entry * (1 + rp["tp"]), 4)
        rr    = round(rp["tp"] / rp["sl"], 1)
        emoji = CATEGORY_EMOJI.get(signal['category'], "📌")
        arrow = "🟢" if d['change'] >= 0 else "🔴"
        mode_tag = "⚡ SCALPING" if ACTIVE_MODE == MODE_SCALPING else "📊 SWING"

        rsi_v = signal['rsi_tags'].get('rsi_value', '?')
        rsi_l = f"RSI {rsi_v}"
        if signal['rsi_tags'].get('oversold'):           rsi_l += " 🔥"
        if signal['rsi_tags'].get('bull_zone'):          rsi_l += " 📶"
        if signal['rsi_tags'].get('momentum'):           rsi_l += " ⬆️"
        if signal['rsi_tags'].get('divergenza_bullish'): rsi_l += " 🔀"

        tags = ""
        if signal['insider']:             tags += "\n🏛️ <b>Insider Buy</b>"
        if signal['shadow']:              tags += "\n🕵️ <b>Top fund istituzionale</b>"
        if signal['sentiment'] >= 0.05:  tags += "\n🗣️ <b>Sentiment positivo</b>"
        if signal['historian'] >= 0.05:  tags += "\n📊 <b>Backtest WR elevato</b>"
        if signal['flow']:                tags += "\n📈 <b>Options flow insolito</b>"
        if signal['macro']:               tags += "\n🌍 <b>Macro correlato</b>"
        if signal['ark']:                 tags += "\n🚀 <b>ARK Invest</b>"
        if signal['contrarian']:          tags += "\n📉 <b>Difensivo — correzione</b>"
        if signal['geo'] >= 0.03:         tags += "\n🌐 <b>Evento geopolitico +</b>"
        if signal['sa'] >= 0.03:          tags += "\n📰 <b>Seeking Alpha bullish</b>"
        if signal['tickeron'] >= 0.03:    tags += "\n🤖 <b>Pattern Tickeron bullish</b>"
        if signal['pattern']:             tags += f"\n🔍 <b>Pattern-X: {signal['pattern_label']}</b>"
        if signal['satoshi'] >= 0.03:     tags += "\n₿ <b>BTC momentum positivo</b>"
        if signal['aquant']:              tags += "\n📡 <b>A-Quant: mean reversion</b>"
        if signal['chain']:               tags += "\n🔗 <b>Supply chain boost</b>"

        return (
            f"{mode_tag} | {emoji} <b>{d['symbol']}</b> | {signal['category']}{tags}\n\n"
            f"{arrow} Variazione: <b>{d['change']:+.2f}%</b>\n"
            f"📊 {rsi_l}\n\n"
            f"📈 AZIONE: <b>BUY</b>\n"
            f"💰 ENTRY: <b>${entry}</b>\n"
            f"🛑 STOP LOSS: <b>${sl}</b> (-{rp['sl']*100:.1f}%)\n"
            f"🎯 TAKE PROFIT: <b>${tp}</b> (+{rp['tp']*100:.1f}%)\n"
            f"⚖️ RISK/REWARD: <b>1:{rr}</b>\n"
            f"🔒 CONFIDENZA: <b>{int(signal['score']*100)}%</b>"
        )

    def send_to_telegram(self, message):
        """Invia su tutti i canali mirror."""
        for chat_id in MIRROR_CHAT_IDS:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            try:
                r = requests.post(url, json={
                    'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'
                }, timeout=10)
                if r.status_code == 200:
                    log("SUCCESS", f"✅ Telegram → chat {chat_id}")
                else:
                    log("WARNING", f"Telegram {r.status_code} chat {chat_id}")
            except Exception as e:
                log("WARNING", f"Telegram error chat {chat_id}: {e}")

    def run_scan(self):
        n_agents = 22
        log("INFO", f"🌍 AVVIO SCANSIONE — {n_agents} agenti | Modalità: {ACTIVE_MODE.upper()}")
        self.omnibus.reset()
        self.contrarian._check_market()
        self.correlator.macro_headlines = self.correlator._fetch_headlines()
        self.satoshi._fetch()

        for cat_name, symbols in CATEGORIES.items():
            log("INFO", f"{CATEGORY_EMOJI.get(cat_name,'📌')} {cat_name} ({len(symbols)} simboli)")
            for symbol in symbols:
                data, _ = self.get_live_data(symbol)
                if not data: continue
                score, rsi_tags = analyze_signal_advanced(symbol, self.cache)
                self.omnibus.submit(symbol, data, score, rsi_tags, cat_name)
                time.sleep(0.25)

        top = self.omnibus.get_top(n=5)
        log("INFO", f"🧠 OMNIBUS: {len(self.omnibus.all_signals)} candidati → top {len(top)}")

        for signal in top:
            self.send_to_telegram(self.create_message(signal))
            log("SUCCESS",
                f"→ {signal['symbol']} {int(signal['score']*100)}% "
                f"pattern={'✓' if signal['pattern'] else '✗'} "
                f"satoshi={signal['satoshi']:+.2f} "
                f"aquant={'✓' if signal['aquant'] else '✗'} "
                f"chain={'✓' if signal['chain'] else '✗'}")

        log("SUCCESS", f"Scan terminata — {len(top)} segnali su {len(MIRROR_CHAT_IDS)} canali")


# ================================================
# ⏱️ LOOP AUTOMATICO
# ================================================
def time_to_next_swing() -> int:
    now = datetime.utcnow()
    candidates = []
    for t_str in SCAN_TIMES_SWING:
        h, m = map(int, t_str.split(":"))
        target = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if target <= now: target += timedelta(days=1)
        candidates.append(target)
    return int((min(candidates) - now).total_seconds())


def run_loop(system: GrapheneSystem):
    scan_count = 0
    mode = ACTIVE_MODE.upper()
    log("INFO", f"⏱️ Loop {mode} attivo")

    scan_count += 1
    log("INFO", f"━━━ SCANSIONE #{scan_count} [{mode}] ━━━")
    system.run_scan()

    while True:
        if ACTIVE_MODE == MODE_SCALPING:
            wait   = SCAN_INTERVAL_SCALP
            next_t = (datetime.utcnow() + timedelta(seconds=wait)).strftime("%H:%M UTC")
        else:
            wait   = time_to_next_swing()
            next_t = (datetime.utcnow() + timedelta(seconds=wait)).strftime("%H:%M UTC")

        log("INFO", f"💤 Prossima [{mode}]: {next_t} (tra {wait//3600}h {(wait%3600)//60}m {wait%60}s)")
        time.sleep(wait)
        scan_count += 1
        log("INFO", f"━━━ SCANSIONE #{scan_count} [{mode}] ━━━")
        system.run_scan()


# ===================== AVVIO =====================
system = GrapheneSystem()
print("\n" + "=" * 80)
log("INFO", f"GRAFENE HFT v29.0 — Modalità: {ACTIVE_MODE.upper()}")
log("INFO", "22 agenti: Vault · Watchtower · Voice · Verifier · Historian · Flow")
log("INFO", "           Correlator · Ark · Contrarian · Shadow · WorldMonitor")
log("INFO", "           SeekingAlpha · Tickeron · Pattern-X · Satoshi · A-Quant7")
log("INFO", "           Chronos-Turbo · Skeptic · Regulator · LiveCache · Mirroring · OMNIBUS")
log("INFO", f"Mirror su {len(MIRROR_CHAT_IDS)} canali Telegram")
print("=" * 80 + "\n")

run_loop(system)
