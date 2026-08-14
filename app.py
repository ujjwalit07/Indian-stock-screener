import streamlit as st
import pandas as pd
import datetime
import pytz
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

# Check if NSE Market is Currently Open (IST Timezone)
def is_market_open():
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.datetime.now(ist)
    
    # Check if weekend (Saturday = 5, Sunday = 6)
    if now_ist.weekday() >= 5:
        return False, "Market is Closed (Weekend)"
        
    market_start = now_ist.replace(hour=9, minute=15, second=0, microsecond=0)
    market_end = now_ist.replace(hour=15, minute=30, second=0, microsecond=0)
    
    if market_start <= now_ist <= market_end:
        return True, "Market is Open"
    else:
        return False, "Market is Closed (Active hours: 09:15 AM - 03:30 PM IST)"

# Fast Auto-Refresh Fragment
@st.fragment(run_every=120)
def run_momentum_screener():
    ist = pytz.timezone('Asia/Kolkata')
    current_time = datetime.datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S IST")
    st.caption(f"Last scanned at: {current_time} (Auto-refreshes every 2 mins)")
    
    open_status, message = is_market_open()
    
    if not open_status:
        st.warning(f"⚠️ **{message}**. Live intraday screening is paused to prevent stale post-market data distortion. Check back during trading hours (9:15 AM - 3:30 PM IST).")
        return

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
            
            if hist.empty or len(hist) < 5:
                continue
                
            hist.index = pd.to_datetime(hist.index)
            hist['Date'] = hist.index.date
            
            # Session VWAP Calculation
            hist['VWAP'] = hist.groupby('Date').apply(
                lambda x: (x['Volume'] * ((x['High'] + x['Low']) / 2)).cumsum() / x['Volume'].cumsum()
            ).reset_index(level=0, drop=True)
            
            # Volume Surge Check (Reduced to 3 periods / 15 minutes for fast initialization)
            hist['Avg_Volume'] = hist['Volume'].rolling(window=3).mean()
            
            ltp = float(hist['Close'].iloc[-1])
            vwap = float(hist['VWAP'].iloc[-1])
            latest_vol = float(hist['Volume'].iloc[-1])
            avg_vol = float(hist['Avg_Volume'].iloc[-1])
            
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
        st.info("Scanning active tickers... No immediate 10-15 minute volume breakout triggers found right now.")

run_momentum_screener()
