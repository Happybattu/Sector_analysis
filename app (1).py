"""
╔══════════════════════════════════════════════════════════════════════════════╗
║         NSE SECTOR ANALYZER — STREAMLIT APP                                ║
║         By: Harry | R2R x Python x Markets                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝

USAGE:
    streamlit run app.py

INSTALL DEPS (run once):
    pip install streamlit yfinance pandas numpy plotly requests
"""

import warnings
warnings.filterwarnings("ignore")

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import json
import time
import urllib.request
import urllib.parse
import concurrent.futures
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG  (must be first Streamlit call)
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NSE Sector Analyzer",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Metric cards ─────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: #1e2330;
    border-radius: 10px;
    padding: 12px 16px;
    border-left: 4px solid #00c4ff;
}
/* ── Section headers ──────────────────────────────────────── */
.section-header {
    font-size: 1.05rem;
    font-weight: 700;
    color: #00c4ff;
    border-bottom: 1px solid #333;
    padding-bottom: 4px;
    margin-top: 1.2rem;
    margin-bottom: 0.6rem;
    letter-spacing: 0.04em;
}
/* ── Verdict badges ───────────────────────────────────────── */
.badge-buy      { background:#145a32; color:#2ecc71; border-radius:6px; padding:2px 8px; font-size:0.82rem; font-weight:700; }
.badge-watchlist{ background:#7d6608; color:#f9e79f; border-radius:6px; padding:2px 8px; font-size:0.82rem; font-weight:700; }
.badge-neutral  { background:#2c3e50; color:#aab7b8; border-radius:6px; padding:2px 8px; font-size:0.82rem; font-weight:700; }
.badge-caution  { background:#641e16; color:#f1948a; border-radius:6px; padding:2px 8px; font-size:0.82rem; font-weight:700; }
.badge-avoid    { background:#4a235a; color:#d7bde2; border-radius:6px; padding:2px 8px; font-size:0.82rem; font-weight:700; }
/* ── Disclaimer ───────────────────────────────────────────── */
.disclaimer {
    font-size: 0.78rem;
    color: #777;
    text-align: center;
    margin-top: 1.5rem;
    padding: 8px;
    border-top: 1px solid #333;
}
/* ── Top pick card ────────────────────────────────────────── */
.pick-card {
    background: #1a2030;
    border-radius: 10px;
    padding: 10px 14px;
    margin-bottom: 6px;
    border-left: 3px solid #2ecc71;
}
.avoid-card {
    background: #1a2030;
    border-radius: 10px;
    padding: 10px 14px;
    margin-bottom: 6px;
    border-left: 3px solid #e74c3c;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# NSE LIVE STOCK FETCHER
# ─────────────────────────────────────────────────────────────────────────────
_NSE_INDEX_MAP = {
    "IT":          "NIFTY IT",
    "BANK":        "NIFTY BANK",
    "PHARMA":      "NIFTY PHARMA",
    "AUTO":        "NIFTY AUTO",
    "FMCG":        "NIFTY FMCG",
    "METAL":       "NIFTY METAL",
    "ENERGY":      "NIFTY ENERGY",
    "INFRA":       "NIFTY INFRA",
    "REALTY":      "NIFTY REALTY",
    "MEDIA":       "NIFTY MEDIA",
    "TELECOM":     "NIFTY MEDIA",
    "CHEMICAL":    "NIFTY CHEMICALS",
    "CEMENT":      "NIFTY INDIA CONSUMPTION",
    "FINANCE":     "NIFTY FINANCIAL SERVICES",
    "DEFENCE":     "NIFTY INDIA DEFENCE",
    "PSU":         "NIFTY PSU BANK",
    "POWER":       "NIFTY ENERGY",
    "CONSUMPTION": "NIFTY INDIA CONSUMPTION",
    "MIDCAP":      "NIFTY MIDCAP 100",
    "TEXTILE":     None,
    "Oil&Gas":     "NIFTY OIL & GAS"
}

_NSE_HEADERS = {
    "User-Agent"      : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept"          : "application/json, text/plain, */*",
    "Accept-Language" : "en-US,en;q=0.9",
    "Referer"         : "https://www.nseindia.com/market-data/live-equity-market",
    "X-Requested-With": "XMLHttpRequest",
}

@st.cache_data(ttl=3600)   # cache 1 hour — avoid hammering NSE
def fetch_nse_live_stocks(sector_key: str) -> list | None:
    index_name = _NSE_INDEX_MAP.get(sector_key)
    if not index_name:
        return None
    try:
        # get session cookies
        req = urllib.request.Request("https://www.nseindia.com", headers=_NSE_HEADERS)
        with urllib.request.urlopen(req, timeout=8) as resp:
            cookie_hdr = resp.headers.get("Set-Cookie", "")
            cookies = "; ".join(
                part.split(";")[0].strip()
                for part in cookie_hdr.split(",")
                if "=" in part.split(";")[0]
            )

        hdrs = {**_NSE_HEADERS, "Cookie": cookies}
        encoded = urllib.parse.quote(index_name)
        url = f"https://www.nseindia.com/api/equity-stockIndices?index={encoded}"
        req2 = urllib.request.Request(url, headers=hdrs)
        with urllib.request.urlopen(req2, timeout=10) as resp2:
            data = json.loads(resp2.read().decode("utf-8"))

        stocks_raw = data.get("data", [])[1:]
        symbols = [row["symbol"] for row in stocks_raw if row.get("symbol")]
        return symbols if len(symbols) >= 5 else None
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# HARDCODED FALLBACK STOCK LISTS
# ─────────────────────────────────────────────────────────────────────────────
SECTOR_STOCKS = {
    "IT": [
        "TCS","INFY","WIPRO","HCLTECH","TECHM","LTM.NS","MPHASIS","PERSISTENT",
        "COFORGE","NIITLTD.NS","KPITTECH","ZENSARTECH","TATAELXSI","MASTEK",
        "HEXT.NS","NEWGEN","CYIENT","BSOFT.NS","ECLERX","OFSS", "HEXT", "KPITTECH","FRACTAL","IDREAM","ZENSARTECH","CYIENT","BSOFT","E2E","SONATSOFTW","TANLA","NEWGEN",
        "ASMTEC",
        "INTELLECT", "ZENSARTECH", "RATEGAIN",
        "LATENTVIEW", "HAPPSTMNDS", "AURIONPRO", "MASTEK", "MAPMYINDIA", "CAPILLARY",
        "63MOONS", "TECHNVISN", "RAMCOSYS", "SILVERTUC", "SAKSOFT", "NUCLEUS", "CEINSYS", "ACCELYA", "MCLOUD", "INFOBEAN",
        "KODYTECH", "NINSYS", "UNIECOM", "QUICKHEAL", "TAC","XCHANGING", "KSOLVES", "SUBEXLTD", "MINDTECK", "INNOVANA",
        "SOFTTECH", "IRIS", "CYBERTECH", "XTGLOBAL", "ABMKNO","VGINFOTECH-SM.NS", "3IINFOLTD", "TREJHARA", "SYSTANGO", "ALLETEC",
        "GOLDTECH", "EMPOWER", "EQUIPPP", "FIDEL", "DRCSYSTEMS", "TECHLABS", "VIRINCHI", "TRIGYN", "SECMARK", "XELPMOC",
        "CANARYS", "GVPTECH", "RSSOFTWARE", "MOBILISE-SM.NS", "DELAPLEX", "CURAA", "TRUST", "PARAMATRIX-SM.NS", "ORCHASP", "CTE",
        "CALSOFT", "SATECH-SM.NS", "QUICKTOUCH", "YUDIZ", "MICROPRO", "QUINTEGRA",        
    ],
    "BANK": [
        "HDFCBANK","ICICIBANK","SBIN","KOTAKBANK","AXISBANK","INDUSINDBK",
        "PNB","BANKBARODA","CANARABANK","UNIONBANK","BANDHANBNK","IDFCFIRSTB",
        "FEDERALBNK","RBLBANK","DCBBANK","KARNATAKABK","SOUTHBANK","CSBBANK",
    ],
    "PHARMA": [
        "SUNPHARMA","DIVISLAB","DRREDDY","CIPLA","AUROPHARMA","ALKEM",
        "TORNTPHARM","LUPIN","BIOCON","GLAND","IPCALAB","NATCO","AJANTPHARM",
        "GRANULES","LAURUSLABS","PFIZER","ABBOTINDIA","SANOFI",
    ],
    "AUTO": [
        "MARUTI","TATAMOTORS","M&M","BAJAJ-AUTO","HEROMOTOCO","EICHERMOT",
        "TVSMOTORS","ASHOKLEY","ESCORTS","BALKRISIND","APOLLOTYRE",
        "MRF","MOTHERSON","BOSCHLTD","BHARATFORG","EXIDEIND","SUNDRMFAST","SONACOMS.NS"
    ],
    "FMCG": [
        "HINDUNILVR","ITC","NESTLEIND","BRITANNIA","DABUR","MARICO","GODREJCP",
        "COLPAL","EMAMILTD","TATACONSUM","VBL","RADICO","MCDOWELL-N",
        "PGHH","GILLETTE","HATSUN","BIKAJI","DEVYANI","WESTLIFE",
    ],
    "METAL": [
        "TATASTEEL","JSWSTEEL","HINDALCO","VEDL","NATIONALUM","SAIL",
        "JINDALSTEL","HINDZINC","NMDC","COALINDIA","MOIL","RATNAMANI",
        "TINPLATE","GRAPHITE","HINDCOPPER","MIDHANI",
    ],
    "ENERGY": [
        "RELIANCE","ONGC","IOC","BPCL","HPCL","GAIL","OIL","MGL","IGL",
        "PETRONET","GUJGASLTD","ATGL","CESC","TATAPOWER","ADANIGREEN",
        "TORNTPOWER","JSWENERGY","NTPC","POWERGRID",
    ],
    "INFRA": [
        "LT","ADANIPORTS","GMRAIRPORT","IRB","ASHOKA","KNRCON","PNC",
        "HGINFRA","GRINFRA","DELHIVERY","CONCOR","RVNL","IRCON","NCC","NBCC","PSPPROJECT",
    ],
    "REALTY": [
        "DLF","GODREJPROP","OBEROIRLTY","PHOENIXLTD","BRIGADE","PRESTIGE",
        "SOBHA","MAHLIFE","KOLTEPATIL","SUNTECK","LODHA","ANANTRAJ",
    ],
    "MEDIA": [
        "ZEEL","SUNTV","PVRINOX","NAZARA","NETWORK18","TV18BRDCST",
        "SAREGAMA","TIPS","BALAJITELE","NDTV","TVTODAY","JAGRAN","DBCORP",
    ],
    "TELECOM": [
        "BHARTIARTL","IDEA","TATACOMM","STLTECH","HFCL",
        "ROUTE","TANLA","RAILTEL","INDUSTOWER","ITI","TEJAS",
    ],
    "CHEMICAL": [
        "PIDILITIND","DEEPAKNITR","ALKYLAMIN","FINOLEXIND","NAVINFLUOR",
        "SRF","ATUL","VINATIORGA","GUJALKALI","NOCIL","GALAXYSURF",
        "TATACHEM","AARTI","VINATI","FINEORG","HSCL","PCBL","TATACHEM","SWANCORP","SUMICHEM",
    ],
    "CEMENT": [
        "ULTRACEMCO","AMBUJACEM","ACC","SHREECEM","JKCEMENT","RAMCOCEM",
        "HEIDELBERG","PRISMCEM","JKLAKSHMI","BIRLACORPN","INDIACEM","STARCEMENT",
    ],
    "FINANCE": [
        "BAJFINANCE","BAJAJFINSV","CHOLAFIN","MUTHOOTFIN","MANAPPURAM",
        "LICHSGFIN","SBICARD","HDFCLIFE","ICICIPRULI","SBILIFE",
        "ICICIGI","PNBHOUSING","CANFINHOME","APTUS","HOMEFIRST","SBFC",
    ],
    "DEFENCE": [
        "HAL","BEL","BEML","BHEL","MAZDOCK.NS","GRSE","COCHINSHIP",
        "ASTRAMICRO.NS","PARAS","MTARTECH.NS","CENTUM","SOLARINDS.NS","DYNAMATECH","MIDHANI","COCHINSHIP","BHARATFORG","APOLLO",
    ],
    "TEXTILE": [
        "PAGEIND","WELSPUNLIVING","ARVIND","RAYMOND","VARDHMAN",
        "TRIDENT","KPRMILL","GARFIBRES","FILATEX","GRASIM",
        "SUTLEJTEX","RSWM","AMBIKCO","HIMATSEIDE",
    ],
    "POWER": [
        "NTPC","POWERGRID","TATAPOWER","ADANIGREEN","CESC","TORNTPOWER",
        "JSWENERGY","NHPC","SJVN","IREDA","INOXWIND","SUZLON",
        "KALPATPOWR","KEC","ABB","SIEMENS",
    ],
    "CONSUMPTION": [
        "TITAN","RELAXO","BATA","WHIRLPOOL","VOLTAS","HAVELLS","CROMPTON",
        "SAFARI","PCJEWELLER","SENCO","KALYANKJIL","METRO","TRENT","DMART",
    ],
    "PSU": [
        "SBIN","PNB","BANKBARODA","CANARABANK","UNIONBANK","ONGC","IOC",
        "BPCL","HPCL","SAIL","NMDC","BHEL","HAL","BEL","BEML",
        "IRCTC","RVNL","IRCON","NBCC",
    ],
    "MIDCAP": [
        "GODREJPROP","TATAELXSI","PERSISTENT","COFORGE","BIKAJI","DEVYANI",
        "LATENTVIEW","DELHIVERY","NYKAA","ZOMATO","POLICYBZR",
        "EASEMYTRIP","RATEGAIN","MAPMYINDIA","MTAR","SYRMA",
        "RELIANCE",	"BPCL",	"ATGL",	"HINDPETRO", "IOC",	"GAIL",	"ONGC",	"OIL",	
        "CHENNPETRO",	"AEGISLOG",	"PETRONET",	"IGL",	"MGL",	"CASTROLIND",
        "AEGISVOPAK"
    ],
    "OilGas": [
        "RELIANCE",	"BPCL",	"ATGL",	"HINDPETRO", "IOC",	"GAIL",	"ONGC",	"OIL",	
        "CHENNPETRO",	"AEGISLOG",	"PETRONET",	"IGL",	"MGL",	"CASTROLIND",	
        "AEGISVOPAK",
    ]
}

SECTOR_ALIASES = {
    "INFORMATION TECHNOLOGY": "IT", "TECHNOLOGY": "IT", "SOFTWARE": "IT",
    "BANKING": "BANK", "BANKS": "BANK", "NIFTY BANK": "BANK",
    "PHARMACEUTICAL": "PHARMA", "PHARMACEUTICALS": "PHARMA", "HEALTHCARE": "PHARMA",
    "AUTOMOBILE": "AUTO", "AUTOMOBILES": "AUTO", "AUTOMOTIVE": "AUTO",
    "OIL": "ENERGY", "OIL & GAS": "ENERGY",
    "METALS": "METAL", "STEEL": "METAL",
    "REAL ESTATE": "REALTY",
    "CHEMICALS": "CHEMICAL",
    "CONSUMER": "CONSUMPTION", "CONSUMER GOODS": "CONSUMPTION",
    "FAST MOVING CONSUMER GOODS": "FMCG",
    "INFRASTRUCTURE": "INFRA",
    "DEFENSE": "DEFENCE",
    "FINANCIAL SERVICES": "FINANCE", "NBFC": "FINANCE",
    "Oil & GAS" : "OilGas"
}

def resolve_sector(name: str):
    key = name.strip().upper()
    key = SECTOR_ALIASES.get(key, key)
    if key in SECTOR_STOCKS:
        return key, SECTOR_STOCKS[key]
    for k in SECTOR_STOCKS:
        if key in k or k in key:
            return k, SECTOR_STOCKS[k]
    return None, None


# ─────────────────────────────────────────────────────────────────────────────
# TECHNICAL INDICATORS
# ─────────────────────────────────────────────────────────────────────────────
def compute_technicals(df: pd.DataFrame) -> dict:
    close = df["Close"]
    high  = df["High"]
    low   = df["Low"]
    vol   = df["Volume"]

    ma20  = close.rolling(20).mean()
    ma50  = close.rolling(50).mean()
    ma200 = close.rolling(200).mean()
    ema9  = close.ewm(span=9,  adjust=False).mean()
    ema21 = close.ewm(span=21, adjust=False).mean()

    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rsi   = 100 - (100 / (1 + gain / loss.replace(0, np.nan)))

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd  = ema12 - ema26
    signal= macd.ewm(span=9, adjust=False).mean()
    macd_hist = macd - signal

    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low  - close.shift()).abs()
    ], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()

    vol_sma20 = vol.rolling(20).mean()
    w52_high  = close.rolling(252).max()
    w52_low   = close.rolling(252).min()

    last = -1
    return {
        "close"     : round(float(close.iloc[last]), 2),
        "ma50"      : round(float(ma50.iloc[last]),  2),
        "ma200"     : round(float(ma200.iloc[last]), 2),
        "ema9"      : round(float(ema9.iloc[last]),  2),
        "ema21"     : round(float(ema21.iloc[last]), 2),
        "rsi"       : round(float(rsi.iloc[last]),   2),
        "macd"      : round(float(macd.iloc[last]),   4),
        "macd_signal": round(float(signal.iloc[last]), 4),
        "macd_hist" : round(float(macd_hist.iloc[last]), 4),
        "atr"       : round(float(atr.iloc[last]),    2),
        "vol_today" : int(vol.iloc[last]),
        "vol_sma20" : int(vol_sma20.iloc[last]),
        "w52_high"  : round(float(w52_high.iloc[last]), 2),
        "w52_low"   : round(float(w52_low.iloc[last]),  2),
        "mom1m"     : round(float(close.pct_change(21).iloc[last] * 100), 2),
        "mom3m"     : round(float(close.pct_change(63).iloc[last] * 100), 2),
        "mom6m"     : round(float(close.pct_change(126).iloc[last]* 100), 2),
    }


# ─────────────────────────────────────────────────────────────────────────────
# SCORING ENGINE
# ─────────────────────────────────────────────────────────────────────────────
def score_stock(tech: dict, fund: dict) -> int:
    score = 0
    c, m50, m200 = tech["close"], tech["ma50"], tech["ma200"]
    e9, e21, rsi  = tech["ema9"], tech["ema21"], tech["rsi"]

    if c > m50 * 1.02:   score += 1
    elif c < m50 * 0.98: score -= 1
    if c > m200 * 1.02:  score += 1
    elif c < m200 * 0.98:score -= 1
    score += 1 if m50 > m200 else -1
    score += 1 if e9 > e21 else -1

    if rsi < 30:   score += 2
    elif rsi > 70: score -= 1
    elif 60 < rsi <= 70: score += 1

    if tech["macd"] > tech["macd_signal"] and tech["macd_hist"] > 0: score += 1
    elif tech["macd"] < tech["macd_signal"] and tech["macd_hist"] < 0: score -= 1

    vr = tech["vol_today"] / tech["vol_sma20"] if tech["vol_sma20"] > 0 else 1
    if vr >= 1.5: score += 1
    elif vr < 0.5: score -= 1

    w52h, w52l = tech["w52_high"], tech["w52_low"]
    if w52h != w52l:
        pos = (c - w52l) / (w52h - w52l)
        if pos >= 0.85:   score += 2
        elif pos <= 0.15: score -= 1

    if tech["mom1m"] > 5:    score += 1
    elif tech["mom1m"] < -10: score -= 1

    pe  = fund.get("trailingPE")
    if pe and 5 < pe < 25: score += 1
    elif pe and pe > 60:   score -= 1

    roe = fund.get("returnOnEquity")
    if roe and roe >= 0.20: score += 1

    pm = fund.get("profitMargins")
    if pm and pm >= 0.15:  score += 1
    elif pm and pm < 0:    score -= 1

    rg = fund.get("rev_growth_yoy") or (fund.get("revenueGrowth") or 0) * 100
    if rg >= 15:  score += 1
    elif rg < 0:  score -= 1

    dte = fund.get("debtToEquity")
    if dte is not None:
        if dte < 30:   score += 1
        elif dte > 150: score -= 1

    rec = fund.get("recommendationKey", "")
    if rec in ("strong_buy", "buy"):    score += 1
    elif rec in ("sell", "strong_sell"): score -= 1

    return score


def verdict_label(score: int) -> str:
    if score >= 12: return "🔥 STRONG BUY"
    elif score >= 7: return "✅ BUY"
    elif score >= 4: return "👀 WATCHLIST"
    elif score >= 0: return "⏳ NEUTRAL"
    elif score >= -5: return "⚠️ CAUTION"
    else:            return "❌ AVOID"


def verdict_badge(verdict: str) -> str:
    cls = {
        "🔥 STRONG BUY": "badge-buy",
        "✅ BUY":        "badge-buy",
        "👀 WATCHLIST":  "badge-watchlist",
        "⏳ NEUTRAL":    "badge-neutral",
        "⚠️ CAUTION":   "badge-caution",
        "❌ AVOID":      "badge-avoid",
    }.get(verdict, "badge-neutral")
    return f'<span class="{cls}">{verdict}</span>'


# ─────────────────────────────────────────────────────────────────────────────
# FUNDAMENTALS
# ─────────────────────────────────────────────────────────────────────────────
def get_fundamentals(ticker: yf.Ticker) -> dict:
    info = {}
    try:
        raw = ticker.info
        for f in [
            "longName","marketCap","trailingPE","forwardPE","priceToBook",
            "trailingEps","profitMargins","operatingMargins","returnOnEquity",
            "revenueGrowth","earningsGrowth","totalDebt","totalCash",
            "debtToEquity","currentRatio","dividendYield","beta",
            "recommendationKey","numberOfAnalystOpinions",
            "heldPercentInsiders","heldPercentInstitutions",
        ]:
            info[f] = raw.get(f)
    except:
        pass
    try:
        fin = ticker.financials
        if fin is not None and "Total Revenue" in fin.index and fin.shape[1] >= 2:
            r0, r1 = fin.loc["Total Revenue"].iloc[0], fin.loc["Total Revenue"].iloc[1]
            if r1 and r1 != 0:
                info["rev_growth_yoy"] = round((r0 - r1) / abs(r1) * 100, 2)
    except:
        info["rev_growth_yoy"] = None
    return info


# ─────────────────────────────────────────────────────────────────────────────
# SINGLE STOCK SCAN
# ─────────────────────────────────────────────────────────────────────────────
def scan_one(sym: str) -> dict | None:
    for suffix in [".NS", ".BO", ""]:
        ticker_sym = sym + suffix if suffix else sym
        try:
            t  = yf.Ticker(ticker_sym)
            df = t.history(period="2y", interval="1d", auto_adjust=True)
            if df is None or len(df) < 60:
                continue

            tech = compute_technicals(df)
            fund = get_fundamentals(t)
            sc   = score_stock(tech, fund)
            vl   = verdict_label(sc)

            mc   = fund.get("marketCap")
            mc_str = f"₹{mc/1e7:.0f}Cr" if mc else "N/A"

            rg  = fund.get("rev_growth_yoy") or (fund.get("revenueGrowth") or 0) * 100
            pe  = fund.get("trailingPE")
            roe = fund.get("returnOnEquity")
            pm  = fund.get("profitMargins")
            w52h, w52l = tech["w52_high"], tech["w52_low"]
            w52pos = round((tech["close"] - w52l) / (w52h - w52l) * 100, 1) if w52h != w52l else 50

            return {
                "symbol"    : sym,
                "name"      : (fund.get("longName") or sym)[:30],
                "cmp"       : tech["close"],
                "rsi"       : tech["rsi"],
                "macd_bull" : tech["macd"] > tech["macd_signal"],
                "ma50_bull" : tech["close"] > tech["ma50"],
                "ma200_bull": tech["close"] > tech["ma200"],
                "gc"        : tech["ma50"] > tech["ma200"],
                "mom1m"     : tech["mom1m"],
                "mom3m"     : tech["mom3m"],
                "mom6m"     : tech["mom6m"],
                "w52pos"    : w52pos,
                "vol_ratio" : round(tech["vol_today"] / tech["vol_sma20"], 2) if tech["vol_sma20"] else 1,
                "atr_pct"   : round(tech["atr"] / tech["close"] * 100, 2),
                "mktcap"    : mc,
                "mktcap_str": mc_str,
                "pe"        : round(pe, 2) if pe else None,
                "roe_pct"   : round(roe * 100, 2) if roe else None,
                "pm_pct"    : round(pm * 100, 2) if pm else None,
                "rev_growth": round(rg, 2) if rg else None,
                "de"        : fund.get("debtToEquity"),
                "rec"       : fund.get("recommendationKey","N/A"),
                "score"     : sc,
                "verdict"   : vl,
                "beta"      : fund.get("beta"),
                "div_yield" : fund.get("dividendYield"),
                "insider"   : fund.get("heldPercentInsiders"),
            }
        except Exception:
            continue
    return None


# ─────────────────────────────────────────────────────────────────────────────
# SECTOR METRICS
# ─────────────────────────────────────────────────────────────────────────────
def sector_metrics(results: list) -> dict:
    valid = [r for r in results if r]
    if not valid:
        return {}
    scores = [r["score"] for r in valid]
    rsies  = [r["rsi"]   for r in valid]
    moms1m = [r["mom1m"] for r in valid if r["mom1m"] is not None]
    moms3m = [r["mom3m"] for r in valid if r["mom3m"] is not None]
    return {
        "total"      : len(valid),
        "avg_score"  : round(np.mean(scores), 2),
        "avg_rsi"    : round(np.mean(rsies), 2),
        "avg_mom1m"  : round(np.mean(moms1m), 2) if moms1m else 0,
        "avg_mom3m"  : round(np.mean(moms3m), 2) if moms3m else 0,
        "bull_count" : sum(1 for r in valid if r["score"] >= 4),
        "bear_count" : sum(1 for r in valid if r["score"] < 0),
        "gc_count"   : sum(1 for r in valid if r["gc"]),
        "ma50_count" : sum(1 for r in valid if r["ma50_bull"]),
        "macd_count" : sum(1 for r in valid if r["macd_bull"]),
        "overbought" : sum(1 for r in valid if r["rsi"] > 70),
        "oversold"   : sum(1 for r in valid if r["rsi"] < 30),
    }


def sector_strength_label(avg_score: float) -> tuple:
    """Returns (label_text, color)"""
    if avg_score >= 8:  return "🔥 VERY STRONG — Bull Run", "green"
    elif avg_score >= 5: return "✅ STRONG — Good Momentum", "green"
    elif avg_score >= 2: return "👀 MODERATE — Selective picks", "orange"
    elif avg_score >= 0: return "⏳ NEUTRAL — Wait for direction", "gray"
    elif avg_score >= -3: return "⚠️ WEAK — Caution advised", "red"
    else:                return "❌ BEARISH — Avoid broadly", "red"


# ─────────────────────────────────────────────────────────────────────────────
# HELPER FORMATTERS
# ─────────────────────────────────────────────────────────────────────────────
def fmt_pct(v):
    return f"{v:.2f}%" if v is not None else "N/A"

def fmt_pe(v):
    return f"{v:.1f}x" if v is not None else "N/A"

def pct_color(v):
    """Return colored string for dataframe display"""
    if v is None: return "N/A"
    return f"+{v:.2f}%" if v > 0 else f"{v:.2f}%"

def score_color(sc):
    if sc is None: return "—"
    return str(sc)


# ─────────────────────────────────────────────────────────────────────────────
# STREAMLIT UI — SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📈 NSE Sector Analyzer")
    st.markdown("*Harry's Edition*")
    st.markdown("---")

    sector_choice = st.selectbox(
        "📂 Select Sector",
        options=list(SECTOR_STOCKS.keys()),
        index=0,
    )

    use_live = st.toggle("🌐 Try NSE Live Fetch", value=True,
                         help="Fetch live index constituents from NSE India. Falls back to built-in list if blocked.")

    st.markdown("---")
    max_workers = st.slider("⚙️ Parallel Workers", min_value=2, max_value=10, value=5,
                            help="Higher = faster scan but more API load")

    scan_btn = st.button("🚀 Run Sector Scan", type="primary", use_container_width=True)

    st.markdown("---")
    st.markdown("##### Sectors Available")
    for s in list(SECTOR_STOCKS.keys()):
        st.markdown(f"• `{s}`")

    st.markdown("---")
    st.caption("⚠️ Algorithmic analysis only. Not SEBI-registered advice. DYOR.")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PAGE
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("# 📊 NSE Sector Analyzer")
st.markdown(f"**{datetime.now():%d %B %Y, %H:%M IST}**  |  *Live market data via Yahoo Finance*")
st.markdown("---")

if not scan_btn:
    # ── Landing splash ──────────────────────────────────────────────────────
    cols = st.columns(4)
    cols[0].metric("Sectors Covered", len(SECTOR_STOCKS))
    cols[1].metric("Avg Stocks / Sector", "~17")
    cols[2].metric("Data Period", "2 Years")
    cols[3].metric("Indicators", "Tech + Fund")

    st.markdown("""
    ### How to use
    1. **Select sector** from the sidebar dropdown
    2. Toggle **NSE Live Fetch** (recommended — pulls real-time index constituents)
    3. Click **Run Sector Scan**
    4. Results show in seconds with full scorecard, charts, top picks, and CSV download

    ### Indicators computed
    - **Technical:** RSI, MACD, MA20/50/200, EMA9/21, Bollinger Bands, ATR, Volume Ratio, 52W Position, Momentum (1M/3M/6M)
    - **Fundamental:** P/E, ROE, Profit Margin, Revenue Growth YoY, D/E Ratio, Market Cap, Analyst Rating
    """)
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
# SCAN EXECUTION
# ─────────────────────────────────────────────────────────────────────────────
sector_key, fallback_symbols = resolve_sector(sector_choice)

if sector_key is None:
    st.error(f"Sector '{sector_choice}' not found.")
    st.stop()

# Resolve symbols — try live NSE first
symbols = fallback_symbols
source_label = "Built-in list"

if use_live:
    with st.spinner("🌐 Fetching live constituents from NSE India..."):
        live = fetch_nse_live_stocks(sector_key)
    if live:
        symbols = live
        source_label = f"NSE Live ({len(live)} stocks)"
        st.success(f"✅ NSE Live: {len(live)} stocks fetched for **{sector_key}**")
    else:
        st.warning("⚠️ NSE fetch unavailable — using built-in stock list")

st.info(f"🔍 Scanning **{len(symbols)} stocks** in **{sector_key}** sector  |  Source: *{source_label}*")

# ── Parallel scan with progress bar ─────────────────────────────────────────
progress_bar = st.progress(0, text="Starting scan...")
status_box   = st.empty()
results      = []
failed       = []
start_t      = time.time()
done_count   = 0

with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
    futures = {ex.submit(scan_one, sym): sym for sym in symbols}
    for fut in concurrent.futures.as_completed(futures):
        sym = futures[fut]
        done_count += 1
        pct = done_count / len(symbols)
        try:
            res = fut.result()
            if res:
                results.append(res)
                badge = "✅" if res["score"] >= 4 else ("❌" if res["score"] < 0 else "⏳")
                status_box.markdown(
                    f"`[{done_count:02d}/{len(symbols)}]` {badge} **{sym}** — "
                    f"Score: `{res['score']}` | RSI: `{res['rsi']:.0f}` | "
                    f"1M: `{fmt_pct(res['mom1m'])}` | {res['verdict']}"
                )
            else:
                failed.append(sym)
                status_box.markdown(f"`[{done_count:02d}/{len(symbols)}]` ⚠️ **{sym}** — No data")
        except Exception as e:
            failed.append(sym)
            status_box.markdown(f"`[{done_count:02d}/{len(symbols)}]` ❌ **{sym}** — Error")
        progress_bar.progress(pct, text=f"Scanning... {done_count}/{len(symbols)}")

elapsed = round(time.time() - start_t, 1)
progress_bar.progress(1.0, text=f"✅ Scan complete in {elapsed}s")
status_box.empty()

if not results:
    st.error("❌ No data fetched. Check internet connection or try again.")
    st.stop()

sm = sector_metrics(results)
st.success(f"✅ Scan complete in **{elapsed}s** — {len(results)} stocks fetched, {len(failed)} failed" +
           (f" ({', '.join(failed)})" if failed else ""))


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — SECTOR PULSE (KPI cards)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="section-header">⚡ SECTOR PULSE</div>', unsafe_allow_html=True)

strength_txt, strength_color = sector_strength_label(sm["avg_score"])

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Stocks Scanned",   sm["total"])
c2.metric("Avg Signal Score", sm["avg_score"],
          delta=f"{'Bullish' if sm['avg_score'] > 3 else 'Bearish'}")
c3.metric("Avg RSI",          f"{sm['avg_rsi']:.1f}",
          delta="Overbought" if sm["avg_rsi"] > 65 else ("Oversold" if sm["avg_rsi"] < 35 else "Neutral"))
c4.metric("Avg 1M Return",    fmt_pct(sm["avg_mom1m"]))
c5.metric("Bullish Stocks",   f"{sm['bull_count']} / {sm['total']}")
c6.metric("Bearish Stocks",   f"{sm['bear_count']} / {sm['total']}")

st.markdown(f"**Sector Strength:** :{strength_color}[{strength_txt}]")

# Technical breadth
col_a, col_b = st.columns(2)
with col_a:
    tech_data = {
        "Signal":         ["Above MA50", "Golden Cross", "MACD Bullish", "RSI Overbought>70", "RSI Oversold<30"],
        "Count":          [sm["ma50_count"], sm["gc_count"], sm["macd_count"], sm["overbought"], sm["oversold"]],
        "Out of":         [sm["total"]] * 5,
    }
    st.dataframe(pd.DataFrame(tech_data), use_container_width=True, hide_index=True)

with col_b:
    try:
        import plotly.graph_objects as go
        bull_pct  = sm["bull_count"] / sm["total"] * 100
        bear_pct  = sm["bear_count"] / sm["total"] * 100
        neut_pct  = 100 - bull_pct - bear_pct

        fig = go.Figure(go.Pie(
            labels=["Bullish", "Bearish", "Neutral"],
            values=[bull_pct, bear_pct, neut_pct],
            hole=0.45,
            marker_colors=["#2ecc71", "#e74c3c", "#95a5a6"],
            textinfo="label+percent",
        ))
        fig.update_layout(
            height=240,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="white",
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        st.info("Install plotly for charts: `pip install plotly`")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — TOP PICKS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="section-header">🏆 TOP PICKS</div>', unsafe_allow_html=True)

valid = [r for r in results if r]
buys   = sorted([r for r in valid if r["score"] >= 4], key=lambda x: x["score"], reverse=True)[:5]
avoids = sorted([r for r in valid if r["score"] < 0],  key=lambda x: x["score"])[:5]

col_buy, col_avoid = st.columns(2)

with col_buy:
    st.markdown("**★ Bullish Setups**")
    if buys:
        for r in buys:
            gc_tag = " 🌟 GC" if r["gc"] else ""
            st.markdown(
                f'<div class="pick-card">'
                f'<b>{r["symbol"]}</b>{gc_tag} &nbsp; Score: <b>{r["score"]}</b> &nbsp; '
                f'CMP: ₹{r["cmp"]:,.2f} &nbsp; 1M: {fmt_pct(r["mom1m"])} &nbsp; '
                f'{verdict_badge(r["verdict"])}'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        st.info("No bullish setups in this sector currently.")

with col_avoid:
    st.markdown("**✘ Bearish / Avoid**")
    if avoids:
        for r in avoids:
            st.markdown(
                f'<div class="avoid-card">'
                f'<b>{r["symbol"]}</b> &nbsp; Score: <b>{r["score"]}</b> &nbsp; '
                f'CMP: ₹{r["cmp"]:,.2f} &nbsp; 1M: {fmt_pct(r["mom1m"])} &nbsp; '
                f'{verdict_badge(r["verdict"])}'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        st.info("No strongly bearish stocks found.")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — QUICK LISTS (Momentum / Value / Oversold / Volume)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="section-header">🔍 QUICK LISTS</div>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["⚡ Momentum Leaders", "💎 Value Picks", "🎯 Oversold Watch", "📊 Volume Breakouts"])

with tab1:
    mom = sorted([r for r in valid if r["mom3m"] is not None], key=lambda x: x["mom3m"], reverse=True)[:8]
    if mom:
        df_mom = pd.DataFrame([{
            "Symbol": r["symbol"], "CMP ₹": f"₹{r['cmp']:,.2f}",
            "1M %": fmt_pct(r["mom1m"]), "3M %": fmt_pct(r["mom3m"]),
            "6M %": fmt_pct(r["mom6m"]), "RSI": f"{r['rsi']:.0f}", "Score": r["score"],
        } for r in mom])
        st.dataframe(df_mom, use_container_width=True, hide_index=True)

with tab2:
    val = [r for r in valid if r["pe"] and r["roe_pct"] and r["pe"] < 30 and r["roe_pct"] >= 15]
    val = sorted(val, key=lambda x: x["roe_pct"] / x["pe"], reverse=True)[:8]
    if val:
        df_val = pd.DataFrame([{
            "Symbol": r["symbol"], "CMP ₹": f"₹{r['cmp']:,.2f}",
            "P/E": fmt_pe(r["pe"]), "ROE %": fmt_pct(r["roe_pct"]),
            "Rev Growth %": fmt_pct(r["rev_growth"]), "D/E": r["de"] or "N/A",
            "Score": r["score"],
        } for r in val])
        st.dataframe(df_val, use_container_width=True, hide_index=True)
    else:
        st.info("No strong value picks (P/E < 30 & ROE ≥ 15%) found.")

with tab3:
    ov = sorted([r for r in valid if r["rsi"] < 40], key=lambda x: x["rsi"])[:8]
    if ov:
        df_ov = pd.DataFrame([{
            "Symbol": r["symbol"], "CMP ₹": f"₹{r['cmp']:,.2f}",
            "RSI": f"{r['rsi']:.1f}", "1M %": fmt_pct(r["mom1m"]),
            "52W Pos %": f"{r['w52pos']:.0f}%", "Score": r["score"], "Verdict": r["verdict"],
        } for r in ov])
        st.dataframe(df_ov, use_container_width=True, hide_index=True)
    else:
        st.info("No oversold stocks (RSI < 40) currently.")

with tab4:
    vol_bk = sorted([r for r in valid if r["vol_ratio"] and r["vol_ratio"] >= 1.5],
                    key=lambda x: x["vol_ratio"], reverse=True)[:8]
    if vol_bk:
        df_vol = pd.DataFrame([{
            "Symbol": r["symbol"], "CMP ₹": f"₹{r['cmp']:,.2f}",
            "Vol Ratio": f"{r['vol_ratio']:.2f}x", "RSI": f"{r['rsi']:.0f}",
            "1M %": fmt_pct(r["mom1m"]), "Score": r["score"],
        } for r in vol_bk])
        st.dataframe(df_vol, use_container_width=True, hide_index=True)
    else:
        st.info("No significant volume breakouts (ratio ≥ 1.5x) today.")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 — FULL SCORECARD
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="section-header">📋 FULL SECTOR SCORECARD</div>', unsafe_allow_html=True)

ranked = sorted(valid, key=lambda x: x["score"], reverse=True)
df_full = pd.DataFrame([{
    "#"           : i + 1,
    "Symbol"      : r["symbol"],
    "Name"        : r["name"],
    "CMP ₹"       : r["cmp"],
    "Score"       : r["score"],
    "Verdict"     : r["verdict"],
    "RSI"         : round(r["rsi"], 1),
    "1M %"        : r["mom1m"],
    "3M %"        : r["mom3m"],
    "6M %"        : r["mom6m"],
    "52W Pos %"   : r["w52pos"],
    "Vol Ratio"   : r["vol_ratio"],
    "P/E"         : r["pe"],
    "ROE %"       : r["roe_pct"],
    "RevGrowth %" : r["rev_growth"],
    "D/E"         : r["de"],
    "Mkt Cap"     : r["mktcap_str"],
    "Beta"        : r["beta"],
    "Analyst"     : r["rec"],
} for i, r in enumerate(ranked)])

st.dataframe(
    df_full,
    use_container_width=True,
    hide_index=True,
    column_config={
        "CMP ₹":       st.column_config.NumberColumn(format="₹%.2f"),
        "1M %":        st.column_config.NumberColumn(format="%.2f%%"),
        "3M %":        st.column_config.NumberColumn(format="%.2f%%"),
        "6M %":        st.column_config.NumberColumn(format="%.2f%%"),
        "52W Pos %":   st.column_config.NumberColumn(format="%.0f%%"),
        "ROE %":       st.column_config.NumberColumn(format="%.2f%%"),
        "RevGrowth %": st.column_config.NumberColumn(format="%.2f%%"),
        "Score":       st.column_config.NumberColumn(),
    }
)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5 — CHARTS
# ─────────────────────────────────────────────────────────────────────────────
try:
    import plotly.graph_objects as go
    import plotly.express as px

    st.markdown("---")
    st.markdown('<div class="section-header">📈 CHARTS</div>', unsafe_allow_html=True)

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown("**Score Distribution**")
        fig_bar = px.bar(
            df_full.head(15),
            x="Symbol", y="Score",
            color="Score",
            color_continuous_scale=["#e74c3c", "#f39c12", "#2ecc71"],
            title="Top 15 Stocks by Score",
        )
        fig_bar.update_layout(
            height=320,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="white",
            margin=dict(l=10, r=10, t=40, b=10),
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with chart_col2:
        st.markdown("**RSI vs 1M Momentum (Bubble = MktCap)**")
        df_bubble = df_full.dropna(subset=["RSI","1M %"]).copy()
        fig_scatter = px.scatter(
            df_bubble,
            x="RSI", y="1M %",
            text="Symbol",
            color="Score",
            color_continuous_scale=["#e74c3c","#f39c12","#2ecc71"],
            title="RSI vs 1M Return",
        )
        fig_scatter.add_vline(x=30, line_dash="dash", line_color="#2ecc71", annotation_text="Oversold")
        fig_scatter.add_vline(x=70, line_dash="dash", line_color="#e74c3c", annotation_text="Overbought")
        fig_scatter.update_traces(textposition="top center", marker=dict(size=10))
        fig_scatter.update_layout(
            height=320,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="white",
            margin=dict(l=10, r=10, t=40, b=10),
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

except ImportError:
    st.info("Install plotly for charts: `pip install plotly`")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6 — CSV DOWNLOAD
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
csv_data = df_full.to_csv(index=False).encode("utf-8")
st.download_button(
    label="⬇️ Download Full Scorecard as CSV",
    data=csv_data,
    file_name=f"nse_{sector_key.lower()}_{datetime.now():%Y%m%d_%H%M}.csv",
    mime="text/csv",
    use_container_width=True,
)


# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="disclaimer">⚠️ Algorithmic analysis only. Not SEBI-registered investment advice. '
    'Always do your own research (DYOR) before investing or trading. '
    'Data via Yahoo Finance — may have delays.</div>',
    unsafe_allow_html=True,
)
