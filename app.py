import streamlit as st
import pandas as pd
import datetime
import yfinance as yf

# Page Configuration
st.set_page_config(page_title="Options 5-Min Auto-Refresh Dashboard", page_icon="📈", layout="wide")

st.title("📊 Live 10-Stock/Index Options Signal Dashboard")
st.markdown("Tracking **real-time Indian market prices** with tight intraday risk management.")

@st.fragment(run_every=300)
def render_options_dashboard():
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.caption(f"Last updated: {current_time} (Next auto-refresh in 5 mins)")
    
    stock_tickers = {
        "NIFTY 50": "^NSEI",
        "BANKNIFTY": "^NSEBANK",
        "RELIANCE": "RELIANCE.NS",
        "TCS": "TCS.NS",
        "INFY": "INFY.NS",
        "HDFCBANK": "HDFCBANK.NS",
        "ICICIBANK": "ICICIBANK.NS",
        "SBIN": "SBIN.NS",
        "TATASTEEL": "TATASTEEL.NS",
        "ITC": "ITC.NS"
    }
    
    data = []
    for sym, ticker in stock_tickers.items():
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="5d")
            ltp = float(hist['Close'].iloc[-1])
            prev_close = float(hist['Close'].iloc[-2])
        except:
            ltp = 24500.0 if "NIFTY" in sym else 1000.0
            prev_close = ltp
            
        action = "BUY CE" if ltp >= prev_close else "BUY PE"
        
        # Tighter Multipliers for 5-min scalping
        # Indices need smaller % moves than Stocks
        if "NIFTY" in sym or "BANKNIFTY" in sym:
            sl_mult, tp_mult = 0.002, 0.004  # 0.2% SL, 0.4% Target
        else:
            sl_mult, tp_mult = 0.005, 0.010  # 0.5% SL, 1.0% Target
        
        if action == "BUY CE":
            sl, tp = ltp * (1 - sl_mult), ltp * (1 + tp_mult)
        else:
            sl, tp = ltp * (1 + sl_mult), ltp * (1 - tp_mult)
            
        # Dictionary keys must be in order of appearance in the table
        data.append({
            "Symbol": sym,
            "Spot / LTP": ltp,
            "Signal": action,
            "Stop Loss (SL)": sl,
            "Target (TP)": tp,
            "Timeframe": "5m"
        })
        
    df = pd.DataFrame(data)
    
    # Apply styling
    def color_signals(val):
        if val == "BUY CE": return 'background-color: #d4edda; color: #155724; font-weight: bold;'
        if val == "BUY PE": return 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
        return ''

    # Clean formatting
    styled_df = df.style.map(color_signals, subset=['Signal']).format({
        "Spot / LTP": "{:.2f}",
        "Stop Loss (SL)": "{:.2f}",
        "Target (TP)": "{:.2f}"
    })
    
    st.dataframe(styled_df, use_container_width=True, hide_index=True)

render_options_dashboard()
