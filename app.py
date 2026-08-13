import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Indian Market Breakout Screener", layout="wide")

st.sidebar.header("⚙️ Strategy & Parameters")

# Strategy Selection
strategy = st.sidebar.selectbox(
    "Choose Strategy", 
    ["1. Recent Breakout (Last 3-5 Days)", "2. Tight Consolidation Squeeze (Watchlist)"]
)

timeframe = st.sidebar.selectbox("Timeframe", ["1d", "1wk"], index=0)
lookback_days = st.sidebar.slider("Check Breakout Over Last N Candles", 1, 5, 3)
max_consolidation = st.sidebar.number_input("Max Consolidation Range (%)", value=15.0)
min_rel_vol = st.sidebar.number_input("Min Relative Volume (x)", value=1.2)
min_body_size = st.sidebar.number_input("Min Candle Body Size (%)", value=2.0)

# Expanded Nifty 100 Ticker List
NIFTY_100 = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", 
    "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "LARSEN.NS", "TATAMOTORS.NS", 
    "SUNPHARMA.NS", "NTPC.NS", "KOTAKBANK.NS", "MARUTI.NS", "ONGC.NS",
    "ZOMATO.NS", "TATASTEEL.NS", "COALINDIA.NS", "BAJFINANCE.NS", "HAL.NS",
    "BEL.NS", "PERSISTENT.NS", "TRENT.NS", "DIXON.NS", "MAZDOCK.NS",
    "IRFC.NS", "RVNL.NS", "SUZLON.NS", "BHEL.NS", "MOTHERSON.NS",
    "AXISBANK.NS", "POWERGRID.NS", "ULTRACEMCO.NS", "ASIANPAINT.NS", "TITAN.NS",
    "DMART.NS", "ADANIENT.NS", "ADANIPORTS.NS", "BAJAJFINSV.NS", "HCLTECH.NS",
    "NESTLEIND.NS", "SIEMENS.NS", "IOC.NS", "DLF.NS", "VBL.NS", "JINDALSTEL.NS",
    "TATAPOWER.NS", "INDIGO.NS", "HAVELLS.NS", "AMBUJACEM.NS", "POLYCAB.NS"
]

@st.cache_data(ttl=600)
def run_screener(tickers, interval, max_cons, min_rvol, min_body, lookback, strat):
    results = []
    charts = {}
    
    progress_bar = st.progress(0)
    total_tickers = len(tickers)
    
    for i, ticker in enumerate(tickers):
        progress_bar.progress((i + 1) / total_tickers)
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="6mo", interval=interval)
            
            if df.empty or len(df) < 40:
                continue
                
            # Strategy 1: Recent Breakout (Checks last N candles)
            if "1. Recent Breakout" in strat:
                passed = False
                breakout_idx = None
                
                # Check if ANY of the last N candles broke out
                for check_idx in range(-1, -1 - lookback, -1):
                    candle = df.iloc[check_idx]
                    prev_window = df.iloc[check_idx - 20 : check_idx] # 20 candles prior to breakout
                    
                    if len(prev_window) < 20:
                        continue
                        
                    cons_high = prev_window['High'].max()
                    cons_low = prev_window['Low'].min()
                    cons_range = ((cons_high - cons_low) / cons_low) * 100
                    
                    avg_vol = prev_window['Volume'].mean()
                    rvol = candle['Volume'] / avg_vol if avg_vol > 0 else 0
                    body_size = (abs(candle['Close'] - candle['Open']) / candle['Open']) * 100
                    
                    is_breakout = candle['Close'] > cons_high
                    
                    if is_breakout and (cons_range <= max_cons) and (rvol >= min_rvol) and (body_size >= min_body):
                        passed = True
                        breakout_idx = check_idx
                        results.append({
                            "Ticker": ticker,
                            "Current Price (₹)": round(df.iloc[-1]['Close'], 2),
                            "Breakout Date": candle.name.strftime('%Y-%m-%d'),
                            "Breakout Price (₹)": round(candle['Close'], 2),
                            "Volume Spike": f"{round(rvol, 2)}x",
                            "Consolidation Range": f"{round(cons_range, 2)}%"
                        })
                        charts[ticker] = {
                            "data": df.iloc[-60:],
                            "cons_high": cons_high,
                            "cons_low": cons_low,
                            "breakout_date": candle.name
                        }
                        break # Stop checking older candles once found

            # Strategy 2: Tight Consolidation Squeeze (Watchlist)
            else:
                window = df.iloc[-20:]
                cons_high = window['High'].max()
                cons_low = window['Low'].min()
                cons_range = ((cons_high - cons_low) / cons_low) * 100
                latest = df.iloc[-1]
                
                # Near high (within 3% of 20-day high) and tight consolidation (< 10%)
                near_high = latest['Close'] >= (cons_high * 0.97)
                
                if (cons_range <= 10.0) and near_high:
                    results.append({
                        "Ticker": ticker,
                        "Price (₹)": round(latest['Close'], 2),
                        "20-Day High (₹)": round(cons_high, 2),
                        "Tightness Range": f"{round(cons_range, 2)}%",
                        "Status": "Coiling near resistance ⚡"
                    })
                    charts[ticker] = {
                        "data": df.iloc[-60:],
                        "cons_high": cons_high,
                        "cons_low": cons_low,
                        "breakout_date": None
                    }

        except Exception as e:
            continue
            
    progress_bar.empty()
    return results, charts

# --- Main UI ---
st.title("📈 Indian Market Stock Screener")
st.caption(f"Active Strategy: **{strategy}**")

if st.button("🚀 Run Scan", type="primary"):
    with st.spinner("Scanning top liquid NSE stocks..."):
        results, charts = run_screener(
            NIFTY_100, timeframe, max_consolidation, 
            min_rel_vol, min_body_size, lookback_days, strategy
        )
        
        if not results:
            st.warning("No stocks found matching these exact criteria right now. Try expanding 'Check Breakout Over Last N Candles' or increasing 'Max Consolidation Range'.")
        else:
            st.success(f"Found {len(results)} matching stock(s)!")
            st.dataframe(pd.DataFrame(results), use_container_width=True)
            
            st.markdown("### 📊 Interactive Charts")
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
                
                # Highlight resistance box
                fig.add_shape(
                    type="rect",
                    x0=df_chart.index[-25], y0=chart_info["cons_low"],
                    x1=df_chart.index[-1], y1=chart_info["cons_high"],
                    fillcolor="rgba(0, 255, 0, 0.08)",
                    line=dict(color="green", width=1, dash="dot"),
                )
                
                fig.update_layout(
                    title=f"{ticker} - Chart Setup",
                    yaxis_title="Price (₹)",
                    xaxis_rangeslider_visible=False,
                    height=380,
                    margin=dict(l=0, r=0, t=35, b=0)
                )
                st.plotly_chart(fig, use_container_width=True)
