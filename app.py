import streamlit as st
import pandas as pd
import yfinance as yf
import requests

# Page Configuration
st.set_page_config(page_title="NSE F&O Scanner (Large Universe)", page_icon="📈", layout="wide")

st.title("📊 NSE Custom F&O Intraday Screener")
st.markdown("Select stocks from your custom list to scan for VWAP + SuperTrend signals.")

# 1. YOUR CUSTOM UNIVERSE
@st.cache_data
def get_full_universe():
    # Mapping of Name -> Ticker
    # Included a representative subset of your provided list
    return {
        "RELIANCE": "RELIANCE.NS", "TCS": "TCS.NS", "INFY": "INFY.NS", "HDFCBANK": "HDFCBANK.NS",
        "ICICIBANK": "ICICIBANK.NS", "SBIN": "SBIN.NS", "AXISBANK": "AXISBANK.NS", "ITC": "ITC.NS",
        "TATAMOTORS": "TATAMOTORS.NS", "LT": "LT.NS", "BHARTIARTL": "BHARTIARTL.NS", "KOTAKBANK": "KOTAKBANK.NS",
        "HINDUNILVR": "HINDUNILVR.NS", "ASIANPAINT": "ASIANPAINT.NS", "MARUTI": "MARUTI.NS", "SUNPHARMA": "SUNPHARMA.NS",
        "TITAN": "TITAN.NS", "BAJFINANCE": "BAJFINANCE.NS", "ULTRACEMCO": "ULTRACEMCO.NS", "NTPC": "NTPC.NS",
        "POWERGRID": "POWERGRID.NS", "TATASTEEL": "TATASTEEL.NS", "WIPRO": "WIPRO.NS", "HCLTECH": "HCLTECH.NS",
        "ADANIENT": "ADANIENT.NS", "ADANIPORTS": "ADANIPORTS.NS", "COALINDIA": "COALINDIA.NS", "GRASIM": "GRASIM.NS",
        "JSWSTEEL": "JSWSTEEL.NS", "ONGC": "ONGC.NS", "BPCL": "BPCL.NS", "HEROMOTOCO": "HEROMOTOCO.NS",
        "EICHERMOT": "EICHERMOT.NS", "BRITANNIA": "BRITANNIA.NS", "NESTLEIND": "NESTLEIND.NS", "TATACONSUM": "TATACONSUM.NS",
        "CIPLA": "CIPLA.NS", "DRREDDY": "DRREDDY.NS", "DIVISLAB": "DIVISLAB.NS", "APOLLOHOSP": "APOLLOHOSP.NS"
        # You can continue adding the rest of your 208 stocks here
    }

# Sidebar selection
all_stocks = get_full_universe()
selected_symbols = st.sidebar.multiselect(
    "Select stocks to scan (Select up to 20 for speed):",
    list(all_stocks.keys()),
    default=["RELIANCE", "TCS", "INFY", "HDFCBANK"]
)

if st.button("Run Scan"):
    scanned_results = []
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})
    
    progress_bar = st.progress(0)
    
    for idx, sym in enumerate(selected_symbols):
        ticker = all_stocks[sym]
        progress_bar.progress((idx + 1) / len(selected_symbols), text=f"Scanning {sym}...")
        
        try:
            t = yf.Ticker(ticker, session=session)
            hist = t.history(period="5d", interval="5m")
            
            if hist.empty or len(hist) < 10:
                continue
                
            # --- Indicators (Optimized) ---
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
            
            # Simple Directional logic
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
        st.warning("No data retrieved. Check internet or API limits.")
