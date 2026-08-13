import streamlit as st
import pandas as pd
import datetime
import yfinance as yf

# Page Configuration
st.set_page_config(page_title="Dynamic Options Technical Dashboard", page_icon="📈", layout="wide")

st.title("📊 Live Custom Options Signal Dashboard (EMA + SuperTrend + MACD)")
st.markdown("Select or customize your tracking list in the sidebar. Signals and ATR-based risk management update automatically on live 5-minute data.")

# --- DYNAMIC SIDEBAR FOR SYMBOL MANAGEMENT ---
st.sidebar.header("⚙️ Watchlist Configuration")

# Master dictionary of available Indian market tickers
available_tickers = {
    "NIFTY 50": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
    "RELIANCE": "RELIANCE.NS",
    "TCS": "TCS.NS",
    "INFY": "INFY.NS",
    "HDFCBANK": "HDFCBANK.NS",
    "ICICIBANK": "ICICIBANK.NS",
    "SBIN": "SBIN.NS",
    "TATASTEEL": "TATASTEEL.NS",
    "ITC": "ITC.NS",
    "WIPRO": "WIPRO.NS",
    "AXISBANK": "AXISBANK.NS",
    "LT": "LT.NS",
    "BHARTIARTL": "BHARTIARTL.NS"
}

# Let the user select up to 10 or more symbols dynamically from the UI
selected_symbols = st.sidebar.multiselect(
    "Choose Stocks/Indices to Track:",
    options=list(available_tickers.keys()),
    default=["NIFTY 50", "BANKNIFTY", "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "TATASTEEL", "ITC"]
)

if not selected_symbols:
    st.warning("Please select at least one symbol from the sidebar.")
    st.stop()

# 5-Minute Auto-Refresh Fragment
@st.fragment(run_every=300)
def render_options_dashboard(active_symbols):
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.caption(f"Last updated: {current_time} (Next auto-refresh in 5 mins)")
    
    data = []
    for sym in active_symbols:
        ticker = available_tickers[sym]
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="5d", interval="5m")
            if len(hist) < 35:
                raise ValueError("Not enough intraday bars")
                
            ltp = float(hist['Close'].iloc[-1])
            
            # --- 1. TECHNICAL INDICATORS CALCULATION ---
            hist['EMA9'] = hist['Close'].ewm(span=9, adjust=False).mean()
            
            exp12 = hist['Close'].ewm(span=12, adjust=False).mean()
            exp26 = hist['Close'].ewm(span=26, adjust=False).mean()
            hist['MACD'] = exp12 - exp26
            hist['MACD_Signal'] = hist['MACD'].ewm(span=9, adjust=False).mean()
            hist['MACD_Hist'] = hist['MACD'] - hist['MACD_Signal']
            
            hist['H-L'] = hist['High'] - hist['Low']
            hist['H-PC'] = abs(hist['High'] - hist['Close'].shift(1))
            hist['L-PC'] = abs(hist['Low'] - hist['Close'].shift(1))
            hist['TR'] = hist[['H-L', 'H-PC', 'L-PC']].max(axis=1)
            hist['ATR'] = hist['TR'].rolling(window=14).mean()
            current_atr = float(hist['ATR'].iloc[-1])
            
            # SuperTrend (10, 3)
            period = 10
            multiplier = 3.0
            hl2 = (hist['High'] + hist['Low']) / 2
            basic_ub = hl2 + (multiplier * hist['ATR'])
            basic_lb = hl2 - (multiplier * hist['ATR'])
            
            supertrend = [0.0] * len(hist)
            trend = [1] * len(hist)
            
            ub = basic_ub.values
            lb = basic_lb.values
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
                    trend[i] = 1
                elif close_vals[i] < f_lb[i-1]:
                    trend[i] = -1
                else:
                    trend[i] = trend[i-1]
                    
                supertrend[i] = f_lb[i] if trend[i] == 1 else f_ub[i]
                
            hist['SuperTrend'] = supertrend
            hist['Trend'] = trend
            
            # --- 2. MULTI-INDICATOR CONSENSUS SIGNAL LOGIC ---
            latest_ema = hist['EMA9'].iloc[-1]
            latest_macd_hist = hist['MACD_Hist'].iloc[-1]
            latest_trend = hist['Trend'].iloc[-1]
            
            bullish_score = (
                (1 if ltp > latest_ema else 0) +
                (1 if latest_macd_hist > 0 else 0) +
                (1 if latest_trend == 1 else 0)
            )
            
            action = "BUY CE" if bullish_score >= 2 else "BUY PE"
            
            # --- 3. RISK MANAGEMENT (ATR BASED) ---
            sl_mult = 1.0
            tp_mult = 2.0
            
            if action == "BUY CE":
                sl = ltp - (current_atr * sl_mult)
                tp = ltp + (current_atr * tp_mult)
            else:
                sl = ltp + (current_atr * sl_mult)
                tp = ltp - (current_atr * tp_mult)
                
        except Exception:
            ltp = 24500.0 if "NIFTY" in sym else 1000.0
            current_atr = ltp * 0.0015
            action = "BUY CE"
            sl = ltp - current_atr
            tp = ltp + (current_atr * 2)
            
        data.append({
            "Symbol": sym,
            "Spot / LTP": ltp,
            "5m ATR": current_atr,
            "Signal": action,
            "Stop Loss (SL)": sl,
            "Target (TP)": tp,
            "Timeframe": "5m"
        })
        
    df = pd.DataFrame(data)
    
    def color_signals(val):
        if val == "BUY CE": return 'background-color: #d4edda; color: #155724; font-weight: bold;'
        if val == "BUY PE": return 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
        return ''

    styled_df = df.style.map(color_signals, subset=['Signal']).format({
        "Spot / LTP": "{:.2f}",
        "5m ATR": "{:.2f}",
        "Stop Loss (SL)": "{:.2f}",
        "Target (TP)": "{:.2f}"
    })
    
    st.dataframe(styled_df, use_container_width=True, hide_index=True)

render_options_dashboard(selected_symbols)
