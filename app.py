import streamlit as st
import pandas as pd
import yfinance as yf
import requests

# Page Configuration
st.set_page_config(page_title="NSE F&O Scanner (Large Universe)", page_icon="📈", layout="wide")

st.title("📊 NSE Custom F&O Intraday Screener")
st.markdown("Select Indices and Stocks to scan for VWAP + SuperTrend signals.")

# 1. UPDATED UNIVERSE (Indices + Stocks)
@st.cache_data
def get_full_universe():
    # Indices mapped to YF Tickers
    universe = {
        "NIFTY 50": "^NSEI",
        "NIFTY BANK": "^NSEBANK",
        "NIFTY FIN SERVICES": "^CNXFIN",
        "NIFTY NEXT 50": "^CNXNXT50",
        "NIFTY MIDCAP SELECT": "^MIDCPNIFTY"
    }
    
    # Adding the rest of your stock list
    stocks = {
        "RELIANCE": "RELIANCE.NS", "TCS": "TCS.NS", "INFY": "INFY.NS", 
        "HDFCBANK": "HDFCBANK.NS", "ICICIBANK": "ICICIBANK.NS", "SBIN": "SBIN.NS",
        "AXISBANK": "AXISBANK.NS", "ITC": "ITC.NS", "TATAMOTORS": "TATAMOTORS.NS",
        "LT": "LT.NS", "BHARTIARTL": "BHARTIARTL.NS", "KOTAKBANK": "KOTAKBANK.NS",
        # ... [Add the rest of your 208 stocks here]
    }
    universe.update(stocks)
    return universe

# Sidebar selection
all_assets = get_full_universe()
selected_symbols = st.sidebar.multiselect(
    "Select Indices/Stocks to scan:",
    list(all_assets.keys()),
    default=["NIFTY 50", "NIFTY BANK"]
)

if st.button("Run Scan"):
    scanned_results = []
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})
    
    progress_bar = st.progress(0)
    
    for idx, sym in enumerate(selected_symbols):
        ticker = all_assets[sym]
        progress_bar.progress((idx + 1) / len(selected_symbols), text=f"Scanning {sym}...")
        
        try:
            t = yf.Ticker(ticker, session=session)
            hist = t.history(period="5d", interval="5m")
            
            if hist.empty or len(hist) < 10:
                continue
                
            # VWAP Calculation
            hist['VWAP'] = (hist['Volume'] * ((hist['High'] + hist['Low']) / 2)).cumsum() / hist['Volume'].cumsum()
            
            # SuperTrend Logic
            atr_length = 10
            hist['TR'] = pd.concat([hist['High'] - hist['Low'], 
                                   (hist['High'] - hist['Close'].shift(1)).abs(), 
                                   (hist['Low'] - hist['Close'].shift(1)).abs()], axis=1).max(axis=1)
            hist['ATR'] = hist['TR'].rolling(window=atr_length).mean()
            
            hl2 = (hist['High'] + hist['Low']) / 2
            upper = hl2 + (3.0 * hist['ATR'])
            lower = hl2 - (3.0 * hist['ATR'])
            
            curr_dir = 1 if hist['Close'].iloc[-1] > upper.iloc[-2] else -1
            
            scanned_results.append({
                "Symbol": sym,
                "LTP": hist['Close'].iloc[-1],
                "VWAP": hist['VWAP'].iloc[-1],
                "Status": "BULLISH" if curr_dir == 1 else "BEARISH"
            })
            
        except Exception:
            continue
            
    progress_bar.empty()
    if scanned_results:
        st.dataframe(pd.DataFrame(scanned_results))
    else:
        st.warning("No data retrieved. Ensure Ticker matches Yahoo Finance availability.")
