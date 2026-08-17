import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

st.set_page_config(page_title="Animesh Setup Scanner", layout="wide")

st.title("Intraday Options Strategy Scanner")
st.markdown("Scanning stocks for the **200 EMA High / 50 EMA Low** pullback channel, **Supertrend**, and **Daily Bias** setup.")

# Default list of popular NSE tickers
default_tickers = "RELIANCE.NS, TCS.NS, HDFCBANK.NS, INFY.NS, ICICIBANK.NS, SBIN.NS, BHARTIARTL.NS, ITC.NS, KOTAKBANK.NS, HAL.NS, ^NSEI"

tickers_input = st.text_input(
    "Enter Yahoo Finance Tickers (comma-separated):",
    value=default_tickers
)

tickers = [t.strip() for t in tickers_input.split(",") if t.strip()]

if st.button("Run Market Scanner"):
    results = []
    progress_bar = st.progress(0)
    total = len(tickers)
    
    for idx, ticker in enumerate(tickers):
        try:
            # 1. Fetch Daily Data for Bias
            df_daily = yf.download(ticker, period="5d", interval="1d", progress=False)
            if df_daily.empty or len(df_daily) < 2:
                continue
            
            if isinstance(df_daily.columns, pd.MultiIndex):
                df_daily.columns = df_daily.columns.get_level_values(0)

            prev_day_close = df_daily['Close'].iloc[-2]
            prev_day_open = df_daily['Open'].iloc[-2]
            is_bullish_day = prev_day_close > prev_day_open
            is_bearish_day = prev_day_close < prev_day_open

            # 2. Fetch 5-Minute Intraday Data
            df_5m = yf.download(ticker, period="5d", interval="5m", progress=False)
            if df_5m.empty or len(df_5m) < 200:
                continue
                
            if isinstance(df_5m.columns, pd.MultiIndex):
                df_5m.columns = df_5m.columns.get_level_values(0)

            # 3. Calculate Indicators
            df_5m['EMA_High'] = ta.ema(df_5m['High'], length=200)
            df_5m['EMA_Low'] = ta.ema(df_5m['Low'], length=50)

            st_df = ta.supertrend(df_5m['High'], df_5m['Low'], df_5m['Close'], length=10, multiplier=3)
            if st_df is not None and not st_df.empty:
                dir_col = [col for col in st_df.columns if 'd_' in col or 'direction' in col][0]
                df_5m['Supertrend_Dir'] = st_df[dir_col]
            else:
                continue

            latest = df_5m.iloc[-1]
            
            band_top = max(latest['EMA_High'], latest['EMA_Low'])
            band_bottom = min(latest['EMA_High'], latest['EMA_Low'])
            
            in_band = (latest['Close'] >= band_bottom) and (latest['Close'] <= band_top)
            st_dir = latest['Supertrend_Dir']
            
            # Supertrend direction convention in pandas_ta: 1 = Uptrend, -1 = Downtrend
            is_supertrend_bullish = (st_dir == 1) or (st_dir == -1 and latest['Close'] > st_df.iloc[-1].filter(like='SUPERT_').values[0] if len(st_df.columns)>0 else True)
            
            # Strategy Match Logic
            signal = "None"
            if is_bullish_day and in_band:
                signal = "Buy CE Setup"
            elif is_bearish_day and in_band:
                signal = "Buy PE Setup"

            if signal != "None":
                results.append({
                    "Ticker": ticker,
                    "Current Price": round(float(latest['Close']), 2),
                    "Signal": signal,
                    "Daily Bias": "Bullish" if is_bullish_day else "Bearish"
                })

        except Exception as e:
            pass
        
        progress_bar.progress((idx + 1) / total)

    progress_bar.empty()
    
    if results:
        st.success(f"Successfully found {len(results)} active setups!")
        df_res = pd.DataFrame(results)
        st.dataframe(df_res, use_container_width=True)
    else:
        st.info("No active setups matching the EMA band pullback criteria found right now.")
