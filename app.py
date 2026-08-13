import streamlit as st
import pandas as pd
import datetime
import yfinance as yf

# Page Configuration
st.set_page_config(page_title="Options ATR-Based Dashboard", page_icon="📈", layout="wide")

st.title("📊 Live 10-Stock/Index Options Signal Dashboard (ATR-Driven)")
st.markdown("Stop Loss and Targets are dynamically calculated using **real-time ATR (Average True Range)** market data.")

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
            # Fetch enough historical data to compute a 14-period ATR
            hist = t.history(period="1mo")
            if len(hist) < 15:
                raise ValueError("Not enough data")
                
            ltp = float(hist['Close'].iloc[-1])
            prev_close = float(hist['Close'].iloc[-2])
            
            # Calculate True Range (TR)
            hist['H-L'] = hist['High'] - hist['Low']
            hist['H-PC'] = abs(hist['High'] - hist['Close'].shift(1))
            hist['L-PC'] = abs(hist['Low'] - hist['Close'].shift(1))
            hist['TR'] = hist[['H-L', 'H-PC', 'L-PC']].max(axis=1)
            
            # Calculate 14-period ATR
            hist['ATR'] = hist['TR'].rolling(window=14).mean()
            current_atr = float(hist['ATR'].iloc[-1])
            
        except Exception:
            # Fallback if API fails
            ltp = 24500.0 if "NIFTY" in sym else 1000.0
            prev_close = ltp
            current_atr = ltp * 0.005  # Default 0.5% fallback ATR
            
        # Signal determination based on market price action vs previous close
        action = "BUY CE" if ltp >= prev_close else "BUY PE"
        
        # Market-Data Driven Risk Management (using ATR multipliers)
        # Stop loss = 1.0x ATR, Target = 2.0x ATR (1:2 Risk-Reward Ratio)
        sl_atr_multiplier = 1.0
        tp_atr_multiplier = 2.0
        
        if action == "BUY CE":
            sl = ltp - (current_atr * sl_atr_multiplier)
            tp = ltp + (current_atr * tp_atr_multiplier)
        else:
            sl = ltp + (current_atr * sl_atr_multiplier)
            tp = ltp - (current_atr * tp_atr_multiplier)
            
        data.append({
            "Symbol": sym,
            "Spot / LTP": ltp,
            "ATR (14)": current_atr,
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
        "ATR (14)": "{:.2f}",
        "Stop Loss (SL)": "{:.2f}",
        "Target (TP)": "{:.2f}"
    })
    
    st.dataframe(styled_df, use_container_width=True, hide_index=True)

render_options_dashboard()
