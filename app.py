import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Intraday screener", layout="wide")

st.title("Intraday screener")
st.markdown("Scanning F&O stocks for the **200 EMA High / 50 EMA Low** pullback channel, **Supertrend**, and **Daily Bias** setup.")

# Complete list of F&O tickers
fno_tickers_list = [
    "^NSEI", "360ONE.NS", "ABB.NS", "APLAPOLLOS.NS", "AUBANK.NS", "ADANENSOL.NS", 
    "ADANIENT.NS", "ADANIGREEN.NS", "ADANIPORTS.NS", "ADANIPOWER.NS", "ABCAPITAL.NS", 
    "ALKEM.NS", "AMBER.NS", "AMBUJACEM.NS", "ANGELONE.NS", "APOLLOHOSP.NS", 
    "ASHOKLEY.NS", "ASIANPAINT.NS", "ASTRAL.NS", "AUROPHARMA.NS", "DMART.NS", 
    "AXISBANK.NS", "BSE.NS", "BAJAJ-AUTO.NS", "BAJFINANCE.NS", "BAJAJFINSV.NS", 
    "BAJAJHLDNG.NS", "BANDHANBNK.NS", "BANKBARODA.NS", "BANKINDIA.NS", "BDL.NS", 
    "BEL.NS", "BHARATFORG.NS", "BHEL.NS", "BPCL.NS", "BHARTIARTL.NS", "BIOCON.NS", 
    "BLUESTARCO.NS", "BOSCHLTD.NS", "BRITANNIA.NS", "CGPOWER.NS", "CANBK.NS", 
    "CDSL.NS", "CHOLAFIN.NS", "CIPLA.NS", "COALINDIA.NS", "COCHINSHIP.NS", 
    "COFORGE.NS", "COLPAL.NS", "CAMS.NS", "CONCOR.NS", "CROMPTON.NS", 
    "CUMMINSIND.NS", "DLF.NS", "DABUR.NS", "DALBHARAT.NS", "DELHIVERY.NS", 
    "DIVISLAB.NS", "DIXON.NS", "DRREDDY.NS", "ETERNAL.NS", "EICHERMOT.NS", 
    "FORCEMOT.NS", "NYKAA.NS", "FORTIS.NS", "GAIL.NS", "GVT&D.NS", "GMRAIRPORT.NS", 
    "GLENMARK.NS", "GODFRYPHLP.NS", "GODREJCP.NS", "GODREJPROP.NS", "GRASIM.NS", 
    "HCLTECH.NS", "HDFCAMC.NS", "HDFCBANK.NS", "HDFCLIFE.NS", "HAVELLS.NS", 
    "HEROMOTOCO.NS", "HINDALCO.NS", "HAL.NS", "HINDPETRO.NS", "HINDUNILVR.NS", 
    "HINDZINC.NS", "POWERINDIA.NS", "HYUNDAI.NS", "ICICIBANK.NS", "ICICIGI.NS", 
    "ICICIPRULI.NS", "IDFCFIRSTB.NS", "ITC.NS", "INDIANB.NS", "IEX.NS", "IOC.NS", 
    "IRFC.NS", "IREDA.NS", "INDUSTOWER.NS", "INDUSINDBK.NS", "NAUKRI.NS", 
    "INFY.NS", "INOXWIND.NS", "INDIGO.NS", "JINDALSTEL.NS", "JSWENERGY.NS", 
    "JSWSTEEL.NS", "JIOFIN.NS", "JUBLFOOD.NS", "KEI.NS", "KPITTECH.NS", 
    "KALYANKJIL.NS", "KAYNES.NS", "KFINTECH.NS", "KOTAKBANK.NS", "LT.NS", 
    "LICI.NS", "LTIM.NS", "LUPIN.NS", "M&M.NS", "MANAPPURAM.NS", "MANKIND.NS", 
    "MARICO.NS", "MARUTI.NS", "MFSL.NS", "MAXHEALTH.NS", "MAZDOCK.NS", 
    "MOTILALOFS.NS", "MPHASIS.NS", "MCX.NS", "MUTHOOTFIN.NS", "NBCC.NS", 
    "NHPC.NS", "NMDC.NS", "NTPC.NS", "NATIONALUM.NS", "NESTLEIND.NS", 
    "NAM-INDIA.NS", "OBEROIRLTY.NS", "ONGC.NS", "OIL.NS", "PAYTM.NS", "OFSS.NS", 
    "POLICYBZR.NS", "PGEL.NS", "PIIND.NS", "PNBHOUSING.NS", "PAGEIND.NS", 
    "PATANJALI.NS", "PERSISTENT.NS", "PETRONET.NS", "PIDILITIND.NS", "POLYCAB.NS", 
    "PFC.NS", "POWERGRID.NS", "PREMIERENE.NS", "PRESTIGE.NS", "PNB.NS", 
    "RBLBANK.NS", "RECLTD.NS", "RADICO.NS", "RVNL.NS", "RELIANCE.NS", "SBICARD.NS", 
    "SBILIFE.NS", "SHREECEM.NS", "SRF.NS", "MOTHERSON.NS", "SHRIRAMFIN.NS", 
    "SIEMENS.NS", "SOLARINDS.NS", "SONACOMS.NS", "SBIN.NS", "SAIL.NS", 
    "SUNPHARMA.NS", "SUPREMEIND.NS", "SUZLON.NS", "SWIGGY.NS", "TATACONSUM.NS", 
    "TATASTEEL.NS", "TVSMOTOR.NS", "TCS.NS", "TATAELXSI.NS", "TMPV.NS", 
    "TATAPOWER.NS", "TECHM.NS", "FEDERALBNK.NS", "INDHOTEL.NS", "PHOENIXLTD.NS", 
    "TITAN.NS", "TORNTPOWER.NS", "TRENT.NS", "TIINDIA.NS", "UNOMINDA.NS", 
    "UPL.NS", "UNIONBANK.NS", "UNITDSPR.NS", "VBL.NS", "VEDL.NS", "VMM.NS", 
    "IDEA.NS", "VOLTAS.NS", "WAAREENER.NS", "WIPRO.NS", "YESBANK.NS", "ZYDUSLIFE.NS"
]

default_text = ", ".join(fno_tickers_list)

tickers_input = st.text_area(
    "Edit or add Yahoo Finance Tickers (comma-separated):",
    value=default_text,
    height=150
)

tickers = [t.strip() for t in tickers_input.split(",") if t.strip()]

def calculate_supertrend(df, period=10, multiplier=3):
    high = df['High']
    low = df['Low']
    close = df['Close']
    
    price_hl2 = (high + low) / 2
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
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

            # 3. Calculate Indicators natively
            df_5m['EMA_High'] = df_5m['High'].ewm(span=200, adjust=False).mean()
            df_5m['EMA_Low'] = df_5m['Low'].ewm(span=50, adjust=False).mean()
            df_5m = calculate_supertrend(df_5m, period=10, multiplier=3)

            latest = df_5m.iloc[-1]
            
            band_top = max(latest['EMA_High'], latest['EMA_Low'])
            band_bottom = min(latest['EMA_High'], latest['EMA_Low'])
            
            in_band = (latest['Close'] >= band_bottom) and (latest['Close'] <= band_top)
            st_dir = latest['Supertrend_Dir']
            
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
                    "Current Price": round(float(latest['Close']), 2),
                    "Signal": signal,
                    "Daily Bias": "Bullish" if is_bullish_day else "Bearish"
                })

        except Exception as _e:
            pass
        
        progress_bar.progress((idx + 1) / total)

    progress_bar.empty()
    
    if results:
        st.success(f"Successfully found {len(results)} active setups across the F&O list!")
        df_res = pd.DataFrame(results)
        st.dataframe(df_res, use_container_width=True)
    else:
        st.info("No active F&O setups matching the EMA band pullback criteria found right now.")
