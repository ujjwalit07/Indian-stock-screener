import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Intraday screener", layout="wide")

st.title("Intraday screener")
st.markdown("Scanning F&O stocks for the **200 EMA High / 50 EMA Low** pullback channel, **Supertrend**, and **Daily Bias** setup.")

# Optimized high-liquidity F&O default list to prevent timeouts
fno_tickers_list = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", 
    "SBIN.NS", "BHARTIARTL.NS", "LTIM.NS", "ITC.NS", "AXISBANK.NS", 
    "KOTAKBANK.NS", "LT.NS", "BAJFINANCE.NS", "MARUTI.NS", "SUNPHARMA.NS", 
    "TITAN.NS", "ASIANPAINT.NS", "HCLTECH.NS", "TATAMOTORS.NS", "TATASTEEL.NS"
]

default_text = ", ".join(fno_tickers_list)

tickers_input = st.text_area(
    "Edit or add Yahoo Finance Tickers (comma-separated):",
    value=default_text,
    height=100
)

tickers = [t.strip() for t in tickers_input.split(",") if t.strip()]

def calculate_supertrend(df, period=10, multiplier=3):
    high = df['High']
    low = df['Low']
    close = df['Close']
    
    price_hl2 = (high + low) / 2
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(span=period, adjust=False).mean()
    
    basic_ub = price_hl2 + multiplier * atr
    basic_lb = price_hl2 - multiplier * atr
    
    final_ub = basic_ub.copy()
    final_lb = basic_lb.copy()
    trend = pd.Series(1, index=df.index)
    
    for i in range(1, len(df)):
        if basic_ub.iloc[i] < final_ub.iloc[i-1] or close.iloc[i-1] > final_ub.iloc[i-1]:
            final_ub.iloc[i] = basic_ub.iloc[i]
        else:
            final_ub.iloc[i] = final_ub.iloc[i-1]
            
        if basic_lb.iloc[i] > final_lb.iloc[i-1] or close.iloc[i-1] < final_lb.iloc[i-1]:
            final_lb.iloc[i] = basic_lb.iloc[i]
        else:
            final_lb.iloc[i] = final_lb.iloc[i-1]
            
        if close.iloc[i] > final_ub.iloc[i-1]:
            trend.iloc[i] = 1
        elif close.iloc[i] < final_lb.iloc[i-1]:
            trend.iloc[i] = -1
        else:
            trend.iloc[i] = trend.iloc[i-1]
            
    df['Supertrend_Dir'] = trend
    return df

# Run button
if st.button("Run Intraday Scanner", type="primary"):
    results = []
    progress_bar = st.progress(0)
    total = len(tickers)
    
    for idx, ticker in enumerate(tickers):
        try:
            # 1. Fetch Daily Data for Bias
            df_daily = yf.download(ticker, period="5d", interval="1d", progress=False)
            if df_daily is None or df_daily.empty or len(df_daily) < 2:
                continue
            
            if isinstance(df_daily.columns, pd.MultiIndex):
                df_daily.columns = df_daily.columns.get_level_values(0)

            prev_day_close = float(df_daily['Close'].iloc[-2])
            prev_day_open = float(df_daily['Open'].iloc[-2])
            is_bullish_day = prev_day_close > prev_day_open
            is_bearish_day = prev_day_close < prev_day_open

            # 2. Fetch 5-Minute Intraday Data
            df_5m = yf.download(ticker, period="5d", interval="5m", progress=False)
            if df_5m is None or df_5m.empty or len(df_5m) < 100:
                continue
                
            if isinstance(df_5m.columns, pd.MultiIndex):
                df_5m.columns = df_5m.columns.get_level_values(0)

            # 3. Calculate Indicators natively
            df_5m['EMA_High'] = df_5m['High'].ewm(span=200, adjust=False).mean()
            df_5m['EMA_Low'] = df_5m['Low'].ewm(span=50, adjust=False).mean()
            df_5m = calculate_supertrend(df_5m, period=10, multiplier=3)

            latest = df_5m.iloc[-1]
            
            band_top = max(float(latest['EMA_High']), float(latest['EMA_Low']))
            band_bottom = min(float(latest['EMA_High']), float(latest['EMA_Low']))
            close_price = float(latest['Close'])
            
            in_band = (close_price >= band_bottom) and (close_price <= band_top)
            st_dir = int(latest['Supertrend_Dir'])
            
            is_supertrend_bullish = (st_dir == 1)
            is_supertrend_bearish = (st_dir == -1)
            
            # Strategy Match Logic
            signal = "None"
            if is_bullish_day and in_band and is_supertrend_bearish:
                signal = "Buy CE Setup"
            elif is_bearish_day and in_band and is_supertrend_bullish:
                signal = "Buy PE Setup"

            if signal != "None":
                results.append({
                    "Ticker": ticker,
                    "Current Price": round(close_price, 2),
                    "Signal": signal,
                    "Daily Bias": "Bullish" if is_bullish_day else "Bearish"
                })

        except Exception:
            pass
        
        progress_bar.progress((idx + 1) / total)

    progress_bar.empty()
    
    if results:
        st.success(f"Successfully found {len(results)} active setups!")
        df_res = pd.DataFrame(results)
        st.dataframe(df_res, use_container_width=True)
    else:
        st.info("Scan completed successfully. No active setups matching the EMA band pullback criteria found right now.")
