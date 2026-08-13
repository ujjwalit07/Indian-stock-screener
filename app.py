import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Indian Breakout Screener", layout="wide")

st.sidebar.header("⚙️ Screener Parameters")
timeframe = st.sidebar.selectbox("Timeframe", ["1d", "1wk", "1h"], index=0)
consolidation_pct = st.sidebar.number_input("Max Consolidation Range (%)", value=25.0)
breakout_close_pct = st.sidebar.number_input("Breakout Above Range (%)", value=0.0) # Set to 0 to catch any 20-day high
body_size_pct = st.sidebar.number_input("Min Candle Body Size (%)", value=1.0)
rel_volume_min = st.sidebar.number_input("Min Relative Volume (x)", value=0.8)
min_avg_vol = st.sidebar.number_input("Min Avg Volume", value=100000)
show_debug = st.sidebar.checkbox("Show Debug Details", value=False)

# Expanded list of top NSE tickers
NIFTY_TICKERS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", 
    "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "LARSEN.NS", "TATAMOTORS.NS", 
    "SUNPHARMA.NS", "NTPC.NS", "KOTAKBANK.NS", "MARUTI.NS", "ONGC.NS",
    "ZOMATO.NS", "TATASTEEL.NS", "COALINDIA.NS", "BAJFINANCE.NS", "HAL.NS",
    "BEL.NS", "PERSISTENT.NS", "TRENT.NS", "DIXON.NS", "MAZDOCK.NS"
]

# Passed parameters as arguments so Streamlit invalidates cache when sliders change
@st.cache_data(ttl=300)
def scan_stocks(tickers, interval, cons_pct, breakout_pct, body_pct, rel_vol_m, min_vol):
    results = []
    charts = {}
    debug_logs = []
    
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="6mo", interval=interval)
            
            if df.empty or len(df) < 30: 
                debug_logs.append(f"❌ {ticker}: No data returned from Yahoo Finance.")
                continue
                
            latest = df.iloc[-1]
            prev_df = df.iloc[-21:-1]
            
            # 1. Consolidation Range
            cons_high = prev_df['High'].max()
            cons_low = prev_df['Low'].min()
            range_pct = ((cons_high - cons_low) / cons_low) * 100
            
            # 2. Breakout Level
            breakout_level = cons_high * (1 + (breakout_pct / 100))
            is_breakout = latest['Close'] >= breakout_level
            
            # 3. Body Size
            body_size = (abs(latest['Close'] - latest['Open']) / latest['Open']) * 100
            is_convincing = body_size >= body_pct
            
            # 4. Volume
            avg_vol = prev_df['Volume'].mean()
            rel_vol = latest['Volume'] / avg_vol if avg_vol > 0 else 0
            is_high_vol = rel_vol >= rel_vol_m
            is_liquid = avg_vol >= min_vol
            
            # Evaluate all
            if is_breakout and is_convincing and is_high_vol and is_liquid and (range_pct <= cons_pct):
                results.append({
                    "Ticker": ticker,
                    "Price (₹)": round(latest['Close'], 2),
                    "Volume Spike": f"{round(rel_vol, 2)}x",
                    "Body Size": f"{round(body_size, 2)}%",
                    "Consolidation": f"{round(range_pct, 2)}%"
                })
                charts[ticker] = {
                    "data": df.iloc[-60:],
                    "cons_high": cons_high,
                    "cons_low": cons_low
                }
                debug_logs.append(f"✅ {ticker}: PASSED ALL CHECKS!")
            else:
                reasons = []
                if not is_breakout: reasons.append(f"Close (₹{round(latest['Close'],1)}) < Breakout Level (₹{round(breakout_level,1)})")
                if not is_convincing: reasons.append(f"Body ({round(body_size,1)}%) < Min ({body_pct}%)")
                if not is_high_vol: reasons.append(f"RelVol ({round(rel_vol,1)}x) < Min ({rel_vol_m}x)")
                if range_pct > cons_pct: reasons.append(f"Consolidation ({round(range_pct,1)}%) > Max ({cons_pct}%)")
                
                debug_logs.append(f"⚠️ {ticker}: Failed -> " + ", ".join(reasons))
                
        except Exception as e:
            debug_logs.append(f"❌ {ticker}: Exception -> {str(e)}")
            
    return results, charts, debug_logs

# --- UI Layout ---
st.title("📈 Indian Market Breakout Screener")

if st.button("🚀 Run Scan", type="primary"):
    with st.spinner("Scanning NSE stocks..."):
        results, charts, debug_logs = scan_stocks(
            NIFTY_TICKERS, timeframe, consolidation_pct, 
            breakout_close_pct, body_size_pct, rel_volume_min, min_avg_vol
        )
        
        if not results:
            st.warning("No stocks met the criteria for the latest candle.")
        else:
            st.success(f"Found {len(results)} matching stock(s)!")
            st.dataframe(pd.DataFrame(results), use_container_width=True)
            
            for res in results:
                ticker = res["Ticker"]
                chart_info = charts[ticker]
                df_chart = chart_info["data"]
                
                fig = go.Figure(data=[go.Candlestick(
                    x=df_chart.index,
                    open=df_chart['Open'], high=df_chart['High'],
                    low=df_chart['Low'], close=df_chart['Close'],
                    name="Price"
                )])
                
                fig.add_shape(
                    type="rect",
                    x0=df_chart.index[-21], y0=chart_info["cons_low"],
                    x1=df_chart.index[-2], y1=chart_info["cons_high"],
                    fillcolor="rgba(255, 0, 0, 0.1)",
                    line=dict(color="red", width=1),
                )
                
                fig.update_layout(
                    title=f"{ticker} - Breakout Chart",
                    yaxis_title="Price (₹)",
                    xaxis_rangeslider_visible=False,
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True)
                
        if show_debug:
            st.markdown("---")
            st.markdown("### 🔍 Debug Logs")
            for log in debug_logs:
                st.text(log)
