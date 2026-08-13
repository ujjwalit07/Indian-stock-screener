import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Indian Market Breakout Screener", layout="wide")

st.sidebar.header("⚙️ Screener Mode & Parameters")

mode = st.sidebar.radio(
    "Scan Mode", 
    ["🔥 Top Breakout Candidates (Always Shows Results)", "🎯 Strict Filter Only"]
)

timeframe = st.sidebar.selectbox("Timeframe", ["1d", "1wk"], index=0)
max_consolidation = st.sidebar.slider("Max Consolidation Range (%)", 5.0, 30.0, 20.0)
min_rel_vol = st.sidebar.slider("Min Relative Volume (x)", 0.5, 3.0, 1.0)
min_body_size = st.sidebar.slider("Min Candle Body Size (%)", 0.5, 5.0, 1.0)

# Top 50 Highly Liquid NSE Stocks
NIFTY_TICKERS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", 
    "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "LARSEN.NS", "TATAMOTORS.NS", 
    "SUNPHARMA.NS", "NTPC.NS", "KOTAKBANK.NS", "MARUTI.NS", "ONGC.NS",
    "ZOMATO.NS", "TATASTEEL.NS", "COALINDIA.NS", "BAJFINANCE.NS", "HAL.NS",
    "BEL.NS", "PERSISTENT.NS", "TRENT.NS", "DIXON.NS", "MAZDOCK.NS",
    "IRFC.NS", "RVNL.NS", "SUZLON.NS", "BHEL.NS", "MOTHERSON.NS",
    "AXISBANK.NS", "POWERGRID.NS", "ULTRACEMCO.NS", "ASIANPAINT.NS", "TITAN.NS",
    "DMART.NS", "ADANIENT.NS", "ADANIPORTS.NS", "BAJAJFINSV.NS", "HCLTECH.NS",
    "NESTLEIND.NS", "SIEMENS.NS", "IOC.NS", "DLF.NS", "VBL.NS", "JINDALSTEL.NS",
    "TATAPOWER.NS", "INDIGO.NS", "HAVELLS.NS", "POLYCAB.NS"
]

@st.cache_data(ttl=300)
def fetch_and_scan(tickers, interval, mode_choice, max_cons, min_rvol, min_body):
    tickers_str = " ".join(tickers)
    period = "6mo" if interval == "1d" else "2y"
    
    # Download ALL stocks in one single request to avoid rate limits
    try:
        data = yf.download(tickers_str, period=period, interval=interval, group_by='ticker', auto_adjust=True, progress=False)
    except Exception as e:
        return [], {}, f"Data Fetch Error: {str(e)}"

    scanned_data = []
    charts = {}

    for ticker in tickers:
        try:
            df = data[ticker].dropna() if len(tickers) > 1 else data.dropna()
                
            if df.empty or len(df) < 30:
                continue

            latest = df.iloc[-1]
            prev_20 = df.iloc[-21:-1]
            
            cons_high = float(prev_20['High'].max())
            cons_low = float(prev_20['Low'].min())
            cons_range = ((cons_high - cons_low) / cons_low) * 100
            
            avg_vol = float(prev_20['Volume'].mean())
            latest_vol = float(latest['Volume'])
            rel_vol = (latest_vol / avg_vol) if avg_vol > 0 else 0
            
            latest_close = float(latest['Close'])
            latest_open = float(latest['Open'])
            body_size = (abs(latest_close - latest_open) / latest_open) * 100
            
            dist_from_high = ((latest_close - cons_high) / cons_high) * 100
            
            is_breakout = latest_close >= cons_high
            cons_ok = cons_range <= max_cons
            vol_ok = rel_vol >= min_rvol
            body_ok = body_size >= min_body

            # Breakout Readiness Score
            score = 0
            if is_breakout: score += 50
            if cons_ok: score += 20
            if vol_ok: score += 15
            if body_ok: score += 15
            score += min(rel_vol * 10, 30)
            score += min(body_size * 5, 20)

            record = {
                "Ticker": ticker,
                "Price (₹)": round(latest_close, 2),
                "Dist from High (%)": f"{round(dist_from_high, 2)}%",
                "Volume Spike": f"{round(rel_vol, 2)}x",
                "Candle Body": f"{round(body_size, 2)}%",
                "Consolidation Range": f"{round(cons_range, 2)}%",
                "Status": "🔥 Breaking Out!" if is_breakout else "⚡ Coiling Near High",
                "_score": score,
                "_passed_all": is_breakout and cons_ok and vol_ok and body_ok
            }

            charts[ticker] = {"data": df.iloc[-60:], "high": cons_high, "low": cons_low}

            if mode_choice == "🎯 Strict Filter Only":
                if record["_passed_all"]:
                    scanned_data.append(record)
            else:
                scanned_data.append(record)

        except Exception:
            continue

    # Sorting
    scanned_data.sort(key=lambda x: x["_score"], reverse=True)
    
    if mode_choice != "🎯 Strict Filter Only":
        scanned_data = scanned_data[:10] # Show top 10 best setups

    return scanned_data, charts, None

# Main UI Layout
st.title("📈 Indian Market Breakout & Momentum Screener")

if st.button("🚀 Run Scan", type="primary"):
    with st.spinner("Downloading NSE batch data and scanning setups..."):
        results, charts, err = fetch_and_scan(
            NIFTY_TICKERS, timeframe, mode, 
            max_consolidation, min_rel_vol, min_body_size
        )
        
        if err:
            st.error(f"Error: {err}")
        elif not results:
            st.warning("No stocks matched the strict filter right now. Try switching Scan Mode to '🔥 Top Breakout Candidates'.")
        else:
            st.success(f"Displaying top {len(results)} setup(s)!")
            
            # Render Clean Table
            display_df = pd.DataFrame(results).drop(columns=["_score", "_passed_all"])
            st.dataframe(display_df, use_container_width=True)
            
            st.markdown("### 📊 Interactive Setup Charts")
            for res in results:
                ticker = res["Ticker"]
                if ticker in charts:
                    chart_info = charts[ticker]
                    df_chart = chart_info["data"]
                    
                    fig = go.Figure(data=[go.Candlestick(
                        x=df_chart.index,
                        open=df_chart['Open'], high=df_chart['High'],
                        low=df_chart['Low'], close=df_chart['Close'],
                        name="Price"
                    )])
                    
                    # Resistance / Consolidation Box
                    fig.add_shape(
                        type="rect",
                        x0=df_chart.index[-21], y0=chart_info["low"],
                        x1=df_chart.index[-1], y1=chart_info["high"],
                        fillcolor="rgba(0, 255, 0, 0.08)",
                        line=dict(color="green", width=1, dash="dot"),
                    )
                    
                    fig.update_layout(
                        title=f"{ticker} | Price: ₹{res['Price (₹)']} | Vol Spike: {res['Volume Spike']} | Status: {res['Status']}",
                        yaxis_title="Price (₹)",
                        xaxis_rangeslider_visible=False,
                        height=380,
                        margin=dict(l=0, r=0, t=35, b=0)
                    )
                    st.plotly_chart(fig, use_container_width=True)
