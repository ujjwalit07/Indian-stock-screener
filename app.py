import streamlit as st
import pandas as pd
import numpy as np
import datetime

# Page Configuration
st.set_page_config(
    page_title="Options 5-Min Auto-Refresh Dashboard",
    page_icon="📈",
    layout="wide"
)

st.title("📊 10-Stock/Index Options Signal Dashboard")
st.markdown("Tracks 10 major Indian indices & equities, generating **CE/PE** signals with dynamic **Stop Loss** levels. **Auto-refreshes every 5 minutes.**")

# 5-Minute Auto-Refresh Fragment
@st.fragment(run_every=300)
def render_options_dashboard():
    # Timestamp indicator
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.caption(f"Last updated: {current_time} (Next refresh in 5 mins)")
    
    # 10 Target Symbols (Indices & Liquid Stocks)
    symbols = [
        "NIFTY 50", "BANKNIFTY", "RELIANCE", "TCS", 
        "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "TATASTEEL", "ITC"
    ]
    
    # Simulating/Fetching real-time calculation loop (Replace with your actual strategy logic or API feed)
    np.random.seed(int(datetime.datetime.now().timestamp() // 300)) # Changes state every 5 mins
    
    data = []
    for sym in symbols:
        # Base price bracket estimation for Indian market items
        base_price = np.random.uniform(22000, 25000) if "NIFTY" in sym else np.random.uniform(500, 3000)
        ltp = round(base_price, 2)
        
        # Determine Call (CE) or Put (PE) based on simulated market trend
        action = np.random.choice(["BUY CE", "BUY PE"])
        
        # Dynamic Stop Loss and Target Calculation (e.g., 1.2% Risk, 2.5% Reward)
        sl_multiplier = 0.012
        target_multiplier = 0.025
        
        if action == "BUY CE":
            stop_loss = round(ltp * (1 - sl_multiplier), 2)
            target = round(ltp * (1 + target_multiplier), 2)
        else:
            stop_loss = round(ltp * (1 + sl_multiplier), 2)
            target = round(ltp * (1 - target_multiplier), 2)
            
        data.append({
            "Symbol": sym,
            "Spot / LTP": ltp,
            "Signal": action,
            "Stop Loss (SL)": stop_loss,
            "Target (TP)": target,
            "Timeframe": "5m"
        })
        
    df = pd.DataFrame(data)
    
    # Styling the dataframe to highlight Calls vs Puts
    def color_signals(val):
        if val == "BUY CE":
            return 'background-color: #d4edda; color: #155724; font-weight: bold;'
        elif val == "BUY PE":
            return 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
        return ''

    styled_df = df.style.applymap(color_signals, subset=['Signal'])
    
    # Render table on UI
    st.dataframe(styled_df, use_container_width=True, hide_index=True)

# Call the fragment function
render_options_dashboard()
