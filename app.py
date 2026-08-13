import streamlit as st
import pandas as pd
import datetime
import yfinance as yf
import requests

# Page Configuration
st.set_page_config(page_title="Enhanced NSE F&O Screener", page_icon="📈", layout="wide")

st.title("📊 Enhanced NSE Top 15 Volume Screener (ADX + Confluence Strategy)")
st.markdown("Integrates ADX Trend Strength filter to eliminate fake breakouts, alongside SuperTrend, VWAP, MACD, and EMA.")

# 1. COMPLETE UNIVERSE (Indices + Full Stock List)
@st.cache_data
def get_full_universe():
    universe = {
        "NIFTY 50": "^NSEI",
        "NIFTY BANK": "^NSEBANK",
        "NIFTY FIN SERVICES": "^CNXFIN",
        "NIFTY NEXT 50": "^CNXNXT50",
        "NIFTY MIDCAP SELECT": "^MIDCPNIFTY",
        "RELIANCE": "RELIANCE.NS", "TCS": "TCS.NS", "INFY": "INFY.NS", 
        "HDFCBANK": "HDFCBANK.NS", "ICICIBANK": "ICICIBANK.NS", "SBIN": "SBIN.NS", 
        "AXISBANK": "AXISBANK.NS", "ITC": "ITC.NS", "TATAMOTORS": "TATAMOTORS.NS", 
        "LT": "LT.NS", "BHARTIARTL": "BHARTIARTL.NS", "KOTAKBANK": "KOTAKBANK.NS",
        "HINDUNILVR": "HINDUNILVR.NS", "ASIANPAINT": "ASIANPAINT.NS", "MARUTI": "MARUTI.NS", 
        "SUNPHARMA": "SUNPHARMA.NS", "TITAN": "TITAN.NS", "BAJFINANCE": "BAJFINANCE.NS", 
        "ULTRACEMCO": "ULTRACEMCO.NS", "NTPC": "NTPC.NS", "POWERGRID": "POWERGRID.NS", 
        "TATASTEEL": "TATASTEEL.NS", "WIPRO": "WIPRO.NS", "HCLTECH": "HCLTECH.NS", 
        "ADANIENT": "ADANIENT.NS", "ADANIPORTS": "ADANIPORTS.NS", "COALINDIA": "COALINDIA.NS", 
        "GRASIM": "GRASIM.NS", "JSWSTEEL": "JSWSTEEL.NS", "ONGC": "ONGC.NS", 
        "BPCL": "BPCL.NS", "HEROMOTOCO": "HEROMOTOCO.NS", "EICHERMOT": "EICHERMOT.NS",
        "BRITANNIA": "BRITANNIA.NS", "NESTLEIND": "NESTLEIND.NS", "TATACONSUM": "TATACONSUM.NS", 
        "CIPLA": "CIPLA.NS", "DRREDDY": "DRREDDY.NS", "DIVISLAB": "DIVISLAB.NS", 
        "APOLLOHOSP": "APOLLOHOSP.NS", "BAJAJ-AUTO": "BAJAJ-AUTO.NS", "BAJAJFINSV": "BAJAJFINSV.NS", 
        "SBILIFE": "SBILIFE.NS", "HDFCLIFE": "HDFCLIFE.NS", "SHRIRAMFIN": "SHRIRAMFIN.NS", 
        "TRENT": "TRENT.NS", "BEL": "BEL.NS", "M&M": "M&M.NS", "INDUSINDBK": "INDUSINDBK.NS",
        "HINDALCO": "HINDALCO.NS", "HAL": "HAL.NS", "CHOLAFIN": "CHOLAFIN.NS", 
        "MUTHOOTFIN": "MUTHOOTFIN.NS", "DLF": "DLF.NS", "GODREJPROP": "GODREJPROP.NS", 
        "PIIND": "PIIND.NS", "SRF": "SRF.NS", "LUPIN": "LUPIN.NS", "AUROPHARMA": "AUROPHARMA.NS", 
        "CANBK": "CANBK.NS", "BANKBARODA": "BANKBARODA.NS", "PNB": "PNB.NS", 
        "IDFCFIRSTB": "IDFCFIRSTB.NS", "FEDERALBNK": "FEDERALBNK.NS", "IPCALAB": "IPCALAB.NS"
    }
    return universe

# ADX Calculation Helper Function
def calculate_adx(df, n=14):
    high, low, close = df['High'], df['Low'], df['Close']
    plus_dm = high.diff()
    minus_dm = low.diff()
    
    plus_dm = plus_dm.apply(lambda x: x if (x > 0 and x > -minus_dm.loc[plus_dm.index[plus_dm.index.get_loc(plus_dm.index)]]) else 0) # simplified standard dm
    # Using clean vectorized approach:
    # +DM
    hd = high.diff()
    ld = -low.diff()
    plus_dm = pd.Series(where((hd > ld) & (hd > 0), hd, 0.0), index=high.index)
    minus_dm = pd.Series(where((ld > hd) & (ld > 0), ld, 0.0), index=low.index)
    
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    atr = tr.rolling(window=n).mean()
    plus_di = 100 * (plus_dm.rolling(window=n).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=n).mean() / atr)
    
    dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di))
    adx = dx.rolling(window=n).mean()
    return adx

from numpy import where

# 5-Minute Auto-Refresh Fragment
@st.fragment(run_every=300)
def run_strategy_screener():
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.caption(f"Last scanned at: {current_time} (Auto-refreshes every 5 mins)")
    
    universe = get_full_universe()
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    
    with st.spinner("Scanning market universe for highest volume leaders..."):
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
            st.error(f"Error fetching bulk volume data: {e}")
            return

    if not volume_data:
        st.warning("Could not retrieve volume rankings. Please check your network connection.")
        return

    # Select Top 15 Tickers by Volume
    vol_df = pd.DataFrame(volume_data)
    top_15 = vol_df.sort_values(by="Volume", ascending=False).head(15)
    
    st.subheader("🔥 Top 15 Active Volume Tickers - Enhanced Strategy Signals")
    
    scanned_results = []
    progress_bar = st.progress(0, text="Calculating advanced indicators (ADX, SuperTrend, VWAP, MACD, EMA)...")
    
    for idx, row in enumerate(top_15.iterrows()):
        sym = row[1]["Symbol"]
        ticker = row[1]["Ticker"]
        vol = row[1]["Volume"]
        
        progress_bar.progress((idx + 1) / 15, text=f"Processing: {sym}")
        
        try:
            t = yf.Ticker(ticker, session=session)
            hist = t.history(period="5d", interval="5m")
            
            if hist.empty or len(hist) < 30:
                continue
                
            hist.index = pd.to_datetime(hist.index)
            hist['Date'] = hist.index.date
            
            # 1. Session VWAP
            if 'Volume' in hist.columns and hist['Volume'].sum() > 0:
                hist['VWAP'] = hist.groupby('Date').apply(
                    lambda x: (x['Volume'] * ((x['High'] + x['Low']) / 2)).cumsum() / x['Volume'].cumsum()
                ).reset_index(level=0, drop=True)
            else:
                hist['VWAP'] = (hist['High'] + hist['Low'] + hist['Close']) / 3
            
            # 2. SuperTrend (10, 3)
            atr_length = 10
            factor = 3.0
            hl2 = (hist['High'] + hist['Low']) / 2
            
            tr1 = hist['High'] - hist['Low']
            tr2 = (hist['High'] - hist['Close'].shift(1)).abs()
            tr3 = (hist['Low'] - hist['Close'].shift(1)).abs()
            hist['TR'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            hist['ATR'] = hist['TR'].rolling(window=atr_length).mean()
            
            upper_basic = hl2 + (factor * hist['ATR'])
            lower_basic = hl2 - (factor * hist['ATR'])
            
            supertrend = [0.0] * len(hist)
            direction = [1] * len(hist)
            ub, lb = upper_basic.values, lower_basic.values
            close_vals = hist['Close'].values
            f_ub, f_lb = ub.copy(), lb.copy()
            
            for i in range(1, len(hist)):
                if not pd.isna(ub[i]) and not pd.isna(f_ub[i-1]):
                    f_ub[i] = ub[i] if (ub[i] < f_ub[i-1] or close_vals[i-1] > f_ub[i-1]) else f_ub[i-1]
                if not pd.isna(lb[i]) and not pd.isna(f_lb[i-1]):
                    f_lb[i] = lb[i] if (lb[i] > f_lb[i-1] or close_vals[i-1] < f_lb[i-1]) else f_lb[i-1]
                
                direction[i] = 1 if (not pd.isna(close_vals[i]) and not pd.isna(f_ub[i-1]) and close_vals[i] > f_ub[i-1]) else (-1 if (not pd.isna(close_vals[i]) and not pd.isna(f_lb[i-1]) and close_vals[i] < f_lb[i-1]) else direction[i-1])
                supertrend[i] = f_lb[i] if direction[i] == 1 else f_ub[i]
                
            hist['SuperTrend'], hist['Direction'] = supertrend, direction
            
            # 3. MACD (12, 26, 9)
            ema12 = hist['Close'].ewm(span=12, adjust=False).mean()
            ema26 = hist['Close'].ewm(span=26, adjust=False).mean()
            hist['MACD'] = ema12 - ema26
            hist['MACD_Signal'] = hist['MACD'].ewm(span=9, adjust=False).mean()
            hist['MACD_Hist'] = hist['MACD'] - hist['MACD_Signal']
            
            # 4. EMAs (9 & 21)
            hist['EMA_9'] = hist['Close'].ewm(span=9, adjust=False).mean()
            hist['EMA_21'] = hist['Close'].ewm(span=21, adjust=False).mean()
            
            # 5. ADX (14)
            hist['ADX'] = calculate_adx(hist, n=14)
            
            # Extract Latest Metric Values
            ltp = float(hist['Close'].iloc[-1])
            vwap = float(hist['VWAP'].iloc[-1])
            st_val = float(hist['SuperTrend'].iloc[-1])
            curr_dir = int(hist['Direction'].iloc[-1])
            macd_hist = float(hist['MACD_Hist'].iloc[-1])
            ema_9 = float(hist['EMA_9'].iloc[-1])
            ema_21 = float(hist['EMA_21'].iloc[-1])
            adx_val = float(hist['ADX'].iloc[-1]) if not pd.isna(hist['ADX'].iloc[-1]) else 0.0
            
            # Enhanced Confluence Logic with ADX Filter (> 20)
            is_trending = adx_val > 20
            
            is_bullish = is_trending and (ltp > vwap) and (curr_dir == 1) and (macd_hist > 0) and (ema_9 > ema_21)
            is_bearish = is_trending and (ltp < vwap) and (curr_dir == -1) and (macd_hist < 0) and (ema_9 < ema_21)
            
            if is_bullish:
                signal_status = "STRONG BULLISH"
                action = "BUY CE"
            elif is_bearish:
                signal_status = "STRONG BEARISH"
                action = "BUY PE"
            else:
                signal_status = "RANGING / NO TREND" if not is_trending else "MIXED SIGNALS"
                action = "NO TRADE"
            
            scanned_results.append({
                "Symbol": sym,
                "Volume": int(vol),
                "Spot / LTP": ltp,
                "ADX": adx_val,
                "VWAP": vwap,
                "SuperTrend": st_val,
                "MACD Hist": macd_hist,
                "EMA Status": "Bullish" if ema_9 > ema_21 else "Bearish",
                "Status": signal_status,
                "Action": action
            })
        except Exception:
            continue
            
    progress_bar.empty()
    
    if scanned_results:
        res_df = pd.DataFrame(scanned_results)
        
        def color_status(val):
            if "STRONG BULLISH" in val: return 'background-color: #d4edda; color: #155724; font-weight: bold;'
            elif "STRONG BEARISH" in val: return 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
            return 'background-color: #fff3cd; color: #856404;'

        styled_df = res_df.style.map(color_status, subset=['Status']).format({
            "Volume": "{:,}",
            "Spot / LTP": "{:.2f}",
            "ADX": "{:.1f}",
            "VWAP": "{:.2f}",
            "SuperTrend": "{:.2f}",
            "MACD Hist": "{:.2f}"
        })
        
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
    else:
        st.warning("No active trending setups met the full confluence criteria at this moment.")

run_strategy_screener()
