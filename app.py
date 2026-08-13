import streamlit as st
import pandas as pd
import datetime
import yfinance as yf
import requests

# Page Configuration
st.set_page_config(page_title="Dynamic ORB + SuperTrend Screener", page_icon="📈", layout="wide")

st.title("📊 Fully Dynamic Intraday Screener (Live Nifty 50 + VWAP + SuperTrend)")
st.markdown("Dynamically pulls stock tickers from live sources with proper request headers.")

# 1. DYNAMICALLY FETCH STOCK UNIVERSE (With User-Agent Headers to fix 403)
@st.cache_data(ttl=86400)
def get_dynamic_universe():
    universe = {
        "NIFTY 50": "^NSEI",
        "BANKNIFTY": "^NSEBANK"
    }
    try:
        url = "https://en.wikipedia.org/wiki/NIFTY_50"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            tables = pd.read_html(response.text)
            df = tables[1]
            symbols = df['Symbol'].tolist()
            for sym in symbols:
                universe[sym] = f"{sym}.NS"
        else:
            raise Exception(f"HTTP status {response.status_code}")
            
    except Exception as e:
        st.warning(f"Using fallback stock basket due to network restriction: {e}")
        fallback = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "AXISBANK", "ITC"]
        for sym in fallback:
            universe[sym] = f"{sym}.NS"
            
    return universe

# 5-Minute Auto-Refresh Fragment
@st.fragment(run_every=300)
def run_options_screener():
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.caption(f"Last scanned at: {current_time} (Auto-refreshes every 5 mins)")
    
    fo_universe = get_dynamic_universe()
    scanned_results = []
    
    for sym, ticker in fo_universe.items():
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="5d", interval="5m")
            if len(hist) < 35:
                continue
                
            hist.index = pd.to_datetime(hist.index)
            hist['Date'] = hist.index.date
            
            # --- 1. SESSION VWAP ---
            if 'Volume' in hist.columns and hist['Volume'].sum() > 0:
                hist['VWAP'] = hist.groupby('Date').apply(
                    lambda x: (x['Volume'] * ((x['High'] + x['Low']) / 2)).cumsum() / x['Volume'].cumsum()
                ).reset_index(level=0, drop=True)
            else:
                hist['VWAP'] = (hist['High'] + hist['Low'] + hist['Close']) / 3
            
            # --- 2. 5-MIN OPENING RANGE (ORB) ---
            latest_date = hist['Date'].iloc[-1]
            day_df = hist[hist['Date'] == latest_date]
            if len(day_df) > 0:
                or_high = float(day_df['High'].iloc[0])
                or_low = float(day_df['Low'].iloc[0])
            else:
                or_high, or_low = 0.0, 0.0
                
            # --- 3. SUPERTREND (10, 3) ---
            atr_length = 10
            factor = 3.0
            hl2 = (hist['High'] + hist['Low']) / 2
            
            tr1 = hist['High'] - hist['Low']
            tr2 = abs(hist['High'] - hist['Close'].shift(1))
            tr3 = abs(hist['Low'] - hist['Close'].shift(1))
            hist['TR'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            hist['ATR'] = hist['TR'].rolling(window=atr_length).mean()
            
            upper_basic = hl2 + (factor * hist['ATR'])
            lower_basic = hl2 - (factor * hist['ATR'])
            
            supertrend = [0.0] * len(hist)
            direction = [1] * len(hist)
            
            ub = upper_basic.values
            lb = lower_basic.values
            close_vals = hist['Close'].values
            
            f_ub = ub.copy()
            f_lb = lb.copy()
            
            for i in range(1, len(hist)):
                if not pd.isnan(ub[i]) and not pd.isnan(f_ub[i-1]):
                    f_ub[i] = ub[i] if (ub[i] < f_ub[i-1] or close_vals[i-1] > f_ub[i-1]) else f_ub[i-1]
                if not pd.isnan(lb[i]) and not pd.isnan(f_lb[i-1]):
                    f_lb[i] = lb[i] if (lb[i] > f_lb[i-1] or close_vals[i-1] < f_lb[i-1]) else f_lb[i-1]
                    
                if not pd.isnan(close_vals[i]) and not pd.isnan(f_ub[i-1]) and close_vals[i] > f_ub[i-1]:
                    direction[i] = 1
                elif not pd.isnan(close_vals[i]) and not pd.isnan(f_lb[i-1]) and close_vals[i] < f_lb[i-1]:
                    direction[i] = -1
                else:
                    direction[i] = direction[i-1]
                    
                supertrend[i] = f_lb[i] if direction[i] == 1 else f_ub[i]
                
            hist['SuperTrend'] = supertrend
            hist['Direction'] = direction
            
            # --- 4. REVERSAL WARNING & METRICS ---
            ltp = float(hist['Close'].iloc[-1])
            st_val = float(hist['SuperTrend'].iloc[-1])
            curr_atr = float(hist['ATR'].iloc[-1]) if not pd.isna(hist['ATR'].iloc[-1]) else 1.0
            curr_dir = int(hist['Direction'].iloc[-1])
            curr_vwap = float(hist['VWAP'].iloc[-1])
            
            dist_to_st = (ltp - st_val) / curr_atr if curr_dir == 1 else (st_val - ltp) / curr_atr
            warning_dist = 0.6
            warning_triggered = (dist_to_st <= warning_dist) and (dist_to_st > 0)
            
            signal_status = "BULLISH (Hold)" if curr_dir == 1 else "BEARISH (Exit)"
            if warning_triggered:
                signal_status = "⚠️ REVERSAL WARNING"
                
            if curr_dir == 1:
                sl = ltp - (curr_atr * 1.0)
                tp = ltp + (curr_atr * 2.0)
                action = "BUY CE"
            else:
                sl = ltp + (curr_atr * 1.0)
                tp = ltp - (curr_atr * 2.0)
                action = "BUY PE"
                
            scanned_results.append({
                "Symbol": sym,
                "Spot / LTP": ltp,
                "OR High": or_high,
                "OR Low": or_low,
                "VWAP": curr_vwap,
                "SuperTrend": st_val,
                "Dist to ST (ATR)": dist_to_st,
                "Status": signal_status,
                "Action": action,
                "Stop Loss": sl,
                "Target": tp,
                "Timeframe": "5m"
            })
            
        except Exception:
            continue
            
    if not scanned_results:
        st.info("Scanning market... No valid data retrieved for the current cycle.")
        return
        
    df = pd.DataFrame(scanned_results)
    
    def color_status(val):
        if "BULLISH" in val: return 'background-color: #d4edda; color: #155724; font-weight: bold;'
        elif "BEARISH" in val: return 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
        elif "WARNING" in val: return 'background-color: #fff3cd; color: #856404; font-weight: bold;'
        return ''

    styled_df = df.style.map(color_status, subset=['Status']).format({
        "Spot / LTP": "{:.2f}",
        "OR High": "{:.2f}",
        "OR Low": "{:.2f}",
        "VWAP": "{:.2f}",
        "SuperTrend": "{:.2f}",
        "Dist to ST (ATR)": "{:.2f}",
        "Stop Loss": "{:.2f}",
        "Target": "{:.2f}"
    })
    
    st.dataframe(styled_df, use_container_width=True, hide_index=True)

run_options_screener()
