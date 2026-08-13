import streamlit as st
import pandas as pd
import datetime
import yfinance as yf
import requests

# Page Configuration
st.set_page_config(page_title="10-15 Min Momentum Screener", page_icon="⚡", layout="wide")

st.title("⚡ NSE 10-15 Min Momentum & Volume Surge Screener")
st.markdown("Optimized for short-duration intraday trades using Volume Spikes, Session VWAP, and Recent Price Momentum.")

# Liquid F&O Universe for Fast Scanning
@st.cache_data
def get_momentum_universe():
    return {
        "RELIANCE": "RELIANCE.NS", "TCS": "TCS.NS", "INFY": "INFY.NS", 
        "HDFCBANK": "HDFCBANK.NS", "ICICIBANK": "ICICIBANK.NS", "SBIN": "SBIN.NS", 
        "AXISBANK": "AXISBANK.NS", "ITC": "ITC.NS", "TATAMOTORS": "TATAMOTORS.NS", 
        "LT": "LT.NS", "BHARTIARTL": "BHARTIARTL.NS", "KOTAKBANK": "KOTAKBANK.NS",
        "HINDUNILVR": "HINDUNILVR.NS", "ASIANPAINT": "ASIANPAINT.NS", "MARUTI": "MARUTI.NS", 
        "SUNPHARMA": "SUNPHARMA.NS", "TITAN": "TITAN.NS", "BAJFINANCE": "BAJFINANCE.NS", 
        "ULTRACEMCO": "ULTRACEMCO.NS", "NTPC": "NTPC.NS", "POWERGRID": "POWERGRID.NS", 
        "TATASTEEL": "TATASTEEL.NS", "WIPRO": "WIPRO.NS", "HCLTECH": "HCLTECH.NS", 
        "ADANIENT": "ADANIENT.NS", "ADANIPORTS": "ADANIPORTS.NS", "COALINDIA": "COALINDIA.NS", 
        "JSWSTEEL": "JSWSTEEL.NS", "ONGC": "ONGC.NS", "BPCL": "BPCL.NS", 
        "TRENT": "TRENT.NS", "BEL": "BEL.NS", "M&M": "M&M.NS", "INDUSINDBK": "INDUSINDBK.NS",
        "HINDALCO": "HINDALCO.NS", "HAL": "HAL.NS", "DLF": "DLF.NS", "NIFTY 50": "^NSEI"
    }

# Fast Auto-Refresh Fragment (Every 2 minutes for quicker updates)
@st.fragment(run_every=120)
def run_momentum_screener():
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.caption(f"Last scanned at: {current_time} (Auto-refreshes every 2 mins)")
    
    universe = get_momentum_universe()
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    
    with st.spinner("Scanning for volume spikes and momentum breakouts..."):
        volume_data = []
        tickers_list = list(universe.values())
        
        try:
            bulk_df = yf.download(tickers_list, period="2d", group_by='ticker', progress=False, threads=True)
            for sym, ticker in universe.items():
                try:
                    if ticker in bulk_df.columns.levels[0]:
                        df_t = bulk_df[ticker].dropna()
                        if not df_t.empty:
                            latest_vol = float(df_t['Volume'].iloc[-1])
                            volume_data.append({"Symbol": sym, "Ticker": ticker, "Volume": latest_vol})
                except Exception:
                    continue
        except Exception as e:
            st.error(f"Error fetching data: {e}")
            return

    if not volume_data:
        st.warning("Could not retrieve market data.")
        return

    # Focus on top 20 high-volume tickers for speed and liquidity
    vol_df = pd.DataFrame(volume_data)
    top_active = vol_df.sort_values(by="Volume", ascending=False).head(20)
    
    st.subheader("🚀 High-Momentum Breakout Candidates")
    
    scanned_results = []
    progress_bar = st.progress(0, text="Analyzing 5-minute momentum & volume surges...")
    
    for idx, row in enumerate(top_active.iterrows()):
        sym = row[1]["Symbol"]
        ticker = row[1]["Ticker"]
        
        progress_bar.progress((idx + 1) / len(top_active), text=f"Checking: {sym}")
        
        try:
            t = yf.Ticker(ticker, session=session)
            hist = t.history(period="2d", interval="5m")
            
            if hist.empty or len(hist) < 15:
                continue
                
            hist.index = pd.to_datetime(hist.index)
            hist['Date'] = hist.index.date
            
            # 1. Session VWAP Calculation
            hist['VWAP'] = hist.groupby('Date').apply(
                lambda x: (x['Volume'] * ((x['High'] + x['Low']) / 2)).cumsum() / x['Volume'].cumsum()
            ).reset_index(level=0, drop=True)
            
            # 2. Volume Surge Check (Latest volume vs 10-period average volume)
            hist['Avg_Volume'] = hist['Volume'].rolling(window=10).mean()
            
            # Extract latest candle variables
            ltp = float(hist['Close'].iloc[-1])
            prev_close = float(hist['Close'].iloc[-2])
            vwap = float(hist['VWAP'].iloc[-1])
            latest_vol = float(hist['Volume'].iloc[-1])
            avg_vol = float(hist['Avg_Volume'].iloc[-1])
            
            # Momentum Rules for 10-15 min trades:
            # - Volume surge: Latest volume is at least 1.5x the 10-period average
            # - Price momentum: Last 2 consecutive green/red candles
            is_volume_surge = latest_vol > (1.5 * avg_vol)
            
            green_candle_1 = hist['Close'].iloc[-1] > hist['Open'].iloc[-1]
            green_candle_2 = hist['Close'].iloc[-2] > hist['Open'].iloc[-2]
            red_candle_1 = hist['Close'].iloc[-1] < hist['Open'].iloc[-1]
            red_candle_2 = hist['Close'].iloc[-2] < hist['Open'].iloc[-2]
            
            is_bullish_momentum = is_volume_surge and (ltp > vwap) and green_candle_1 and green_candle_2
            is_bearish_momentum = is_volume_surge and (ltp < vwap) and red_candle_1 and red_candle_2
            
            if is_bullish_momentum:
                status = "MOMENTUM BUY (CE)"
                action = "LONG"
            elif is_bearish_momentum:
                status = "MOMENTUM SELL (PE)"
                action = "SHORT"
            else:
                status = "WATCHING"
                action = "NEUTRAL"
            
            # Only display active momentum signals to keep the interface clean
            if action != "NEUTRAL":
                scanned_results.append({
                    "Symbol": sym,
                    "LTP": ltp,
                    "VWAP": vwap,
                    "Vol Spike Multiplier": round(latest_vol / avg_vol, 2) if avg_vol > 0 else 0,
                    "Signal": status
                })
        except Exception:
            continue
            
    progress_bar.empty()
    
    if scanned_results:
        res_df = pd.DataFrame(scanned_results)
        
        def color_signals(val):
            if "BUY" in val: return 'background-color: #d4edda; color: #155724; font-weight: bold;'
            elif "SELL" in val: return 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
            return ''

        styled_df = res_df.style.map(color_signals, subset=['Signal']).format({
            "LTP": "{:.2f}",
            "VWAP": "{:.2f}",
            "Vol Spike Multiplier": "{:.2f}x"
        })
        
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
    else:
        st.info("Scanning active tickers... No immediate 10-15 minute volume breakout triggers found right now. Re-scanning automatically.")

run_momentum_screener()
