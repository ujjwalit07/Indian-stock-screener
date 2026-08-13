import streamlit as st
import pandas as pd
import datetime
import yfinance as yf

# Page Configuration
st.set_page_config(page_title="ORB + SuperTrend + VWAP Intraday Scanner", page_icon="📈", layout="wide")

st.title("📊 Automated F&O Intraday Screener (ORB + VWAP + SuperTrend)")
st.markdown("Translating your Pine Script strategy into a live automated Python scanner using **5-minute intraday data**.")

# 5-Minute Auto-Refresh Fragment
@st.fragment(run_every=300)
def run_options_screener():
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.caption(f"Last scanned at: {current_time} (Auto-refreshes every 5 mins)")
    
    # Liquid NSE F&O Universe (Top indices and high-volume stocks)
    fo_universe = {
        "NIFTY 50": "^NSEI",
        "BANKNIFTY": "^NSEBANK",
        "RELIANCE": "RELIANCE.NS",
        "TCS": "TCS.NS",
        "INFY": "INFY.NS",
        "HDFCBANK": "HDFCBANK.NS",
        "ICICIBANK": "ICICIBANK.NS",
        "SBIN": "SBIN.NS",
        "AXISBANK": "AXISBANK.NS",
        "TATASTEEL": "TATASTEEL.NS",
        "ITC": "ITC.NS",
        "BAJFINANCE": "BAJFINANCE.NS",
        "MARUTI": "MARUTI.NS",
        "SUNPHARMA": "SUNPHARMA.NS",
        "TITAN": "TITAN.NS",
        "TATAMOTORS": "TATAMOTORS.NS"
    }
    
    scanned_results = []
    
    for sym, ticker in fo_universe.items():
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="5d", interval="5m")
            if len(hist) < 35:
                continue
                
            # Clean dataframe timezone / index
            hist.index = pd.to_datetime(hist.index)
            hist['Date'] = hist.index.date
            
            # --- 1. SESSION VWAP ---
            hl2 = (hist['High'] + hist['Low']) / 2
            hist['VWAP'] = hist.groupby('Date').apply(
                lambda x: (x['Volume'] * ((x['High'] + x['Low']) / 2)).cumsum() / x['Volume'].cumsum()
            ).reset_index(level=0, drop=True)
            
            # --- 2. 5-MIN OPENING RANGE (ORB) ---
            # First bar high/low of the current trading day
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
                if ub[i] < f_ub[i-1] or close_vals[i-1] > f_ub[i-1]:
                    f_ub[i] = ub[i]
                else:
                    f_ub[i] = f_ub[i-1]
                    
                if lb[i] > f_lb[i-1] or close_vals[i-1] < f_lb[i-1]:
                    f_lb[i] = lb[i]
                else:
                    f_lb[i] = f_lb[i-1]
                    
                if close_vals[i] > f_ub[i-1]:
                    direction[i] = 1
                elif close_vals[i] < f_lb[i-1]:
                    direction[i] = -1
                else:
                    direction[i] = direction[i-1]
                    
                supertrend[i] = f_lb[i] if direction[i] == 1 else f_ub[i]
                
            hist['SuperTrend'] = supertrend
            hist['Direction'] = direction
            
            # --- 4. REVERSAL WARNING LOGIC ---
            ltp = float(hist['Close'].iloc[-1])
            st_val = float(hist['SuperTrend'].iloc[-1])
            curr_atr = float(hist['ATR'].iloc[-1])
            curr_dir = int(hist['Direction'].iloc[-1])
            curr_vwap = float(hist['VWAP'].iloc[-1])
            
            dist_to_st = (ltp - st_val) / curr_atr if curr_dir == 1 else (st_val - ltp) / curr_atr
            warning_dist = 0.6
            warning_triggered = (dist_to_st <= warning_dist) and (dist_to_st > 0)
            
            signal_status = "BULLISH (Hold)" if curr_dir == 1 else "BEARISH (Exit)"
            if warning_triggered:
                signal_status = "⚠️ REVERSAL WARNING"
                
            # Risk Management (ATR-based SL & Target)
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
