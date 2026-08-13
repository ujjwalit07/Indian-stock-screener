import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import datetime

st.set_page_config(page_title="Indian Breakout Screener", layout="wide")

# Sidebar Configuration matches the "Configurable Parameters Panel" in the video
st.sidebar.header("⚙️ Screener Parameters")
timeframe = st.sidebar.selectbox("Timeframe", ["1d", "1wk", "1h"], index=0)
consolidation_pct = st.sidebar.number_input("Max Consolidation Range (%)", value=12.0)
breakout_close_pct = st.sidebar.number_input("Breakout Above Range (%)", value=2.0)
body_size_pct = st.sidebar.number_input("Min Candle Body Size (%)", value=5.0) # Corrected Rule
rel_volume_min = st.sidebar.number_input("Min Relative Volume (x)", value=1.5) # Corrected Rule
min_avg_vol = st.sidebar.number_input("Min Avg Volume", value=500000)

# Sample Nifty 50 Tickers (Add more as needed)
NIFTY_TICKERS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", 
    "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "LARSEN.NS", "TATAMOTORS.NS", 
    "SUNPHARMA.NS", "NTPC.NS", "KOTAKBANK.NS", "MARUTI.NS", "ONGC.NS",
    "ZOMATO.NS", "TATASTEEL.NS", "COALINDIA.NS", "BAJFINANCE.NS"
]

@st.cache_data(ttl=3600) # Cache for 1 hour to prevent hitting API limits
def scan_stocks(tickers, interval):
    results = []
    charts = {}
    
    for ticker in tickers:
        try:
            # Fetch data
            stock = yf.Ticker(ticker)
            df = stock.history(period="6mo", interval=interval)
            
            if len(df) < 60: 
                continue
                
            # Current (Breakout) Candle and Previous Data (Consolidation)
            latest = df.iloc[-1]
            prev_df = df.iloc[-21:-1] # Lookback 20 periods
            
            # 1. Consolidation Range (< 12%)
            cons_high = prev_df['High'].max()
            cons_low = prev_df['Low'].min()
            range_pct = ((cons_high - cons_low) / cons_low) * 100
            
            # 2. Breakout Close (> 2% above range)
            breakout_level = cons_high * (1 + (breakout_close_pct / 100))
            is_breakout = latest['Close'] > breakout_level
            
            # 3. Candle Body Size (>= 5%)
            body_size = (abs(latest['Close'] - latest['Open']) / latest['Open']) * 100
            is_convincing = body_size >= body_size_pct
            
            # 5. & 6. Volume rules
            avg_vol = prev_df['Volume'].mean()
            rel_vol = latest['Volume'] / avg_vol if avg_vol > 0 else 0
            is_high_vol = rel_vol >= rel_volume_min
            is_liquid = avg_vol > min_avg_vol
            
            # 7. & 8. Trend and Momentum
            high_50 = df['High'].rolling(50).max().iloc[-2]
            sma_20 = df['Close'].rolling(20).mean().iloc[-1]
            sma_50 = df['Close'].rolling(50).mean().iloc[-1]
            
            near_high = latest['Close'] >= (high_50 * 0.90)
            uptrend = (latest['Close'] > sma_20) and (latest['Close'] > sma_50)
            
            # Check if all conditions pass
            if is_breakout and is_convincing and is_high_vol and is_liquid and near_high and uptrend and (range_pct <= consolidation_pct):
                results.append({
                    "Ticker": ticker,
                    "Price (₹)": round(latest['Close'], 2),
                    "Volume Spike": f"{round(rel_vol, 2)}x",
                    "Body Size": f"{round(body_size, 2)}%",
                    "Consolidation": f"{round(range_pct, 2)}%"
                })
                
                # Save data for charting
                charts[ticker] = {
                    "data": df.iloc[-60:], # Last 60 candles for visual
                    "cons_high": cons_high,
                    "cons_low": cons_low
                }
                
        except Exception as e:
            pass # Skip ticker on error
            
    return results, charts

# --- UI Layout ---
st.title("📈 Indian Market Breakout Screener")
st.markdown("Scans NSE stocks for tight consolidation followed by high-volume breakouts.")

if st.button("🚀 Run Scan", type="primary"):
    with st.spinner(f"Scanning {len(NIFTY_TICKERS)} stocks on {timeframe} timeframe..."):
        results, charts = scan_stocks(NIFTY_TICKERS, timeframe)
        
        if not results:
            st.warning("No stocks met the tight breakout criteria right now. (Try lowering the Min Candle Body Size or changing the timeframe).")
        else:
            st.success(f"Found {len(results)} breakout(s)!")
            st.dataframe(pd.DataFrame(results), use_container_width=True)
            
            # Draw Charts (Just like the video's UI)
            st.markdown("### 📊 Breakout Charts")
            
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
                
                # Draw the Consolidation Box
                fig.add_shape(
                    type="rect",
                    x0=df_chart.index[-21], y0=chart_info["cons_low"],
                    x1=df_chart.index[-2], y1=chart_info["cons_high"],
                    fillcolor="rgba(255, 0, 0, 0.1)",
                    line=dict(color="red", width=1),
                )
                
                fig.update_layout(
                    title=f"{ticker} - Breakout from Consolidation Range",
                    yaxis_title="Price (₹)",
                    xaxis_rangeslider_visible=False,
                    height=400,
                    margin=dict(l=0, r=0, t=40, b=0)
                )
                
                st.plotly_chart(fig, use_container_width=True)