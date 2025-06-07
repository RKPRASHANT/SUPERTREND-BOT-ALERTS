import yfinance as yf
import pandas as pd
import requests

# === CONFIG ===
CRYPTO_LIST = ["WLD-USD", "XRP-USD", "DOT-USD", "ADA-USD", "LINK-USD"]
INTERVAL = "15m"
PERIOD = "1d"
ATR_PERIOD = 10
FACTOR = 3.0
BOT_TOKEN = "7047452384:AAG54yMe2IndhiGQ90ZsiRHZBsQdaeHiH8o"  # Replace with your token
CHAT_ID = "5360673914"      # Replace with your chat ID

# === LOOP THROUGH EACH COIN ===
for coin in CRYPTO_LIST:
    try:
        df = yf.download(coin, interval=INTERVAL, period=PERIOD)

        if df.empty or len(df) < ATR_PERIOD + 2:
            print(f"Not enough data for {coin}")
            continue

        # 🔧 Flatten multi-index columns if any
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]

        # 🔧 Rename to standard column names
        df.columns = [col.title() for col in df.columns]

        # --- SuperTrend Calculation ---
        df['H-L'] = df['High'] - df['Low']
        df['H-PC'] = abs(df['High'] - df['Close'].shift(1))
        df['L-PC'] = abs(df['Low'] - df['Close'].shift(1))
        df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
        df['ATR'] = df['TR'].rolling(ATR_PERIOD).mean()
        hl2 = (df['High'] + df['Low']) / 2
        df['UpperBand'] = hl2 + (FACTOR * df['ATR'])
        df['LowerBand'] = hl2 - (FACTOR * df['ATR'])
        df['inUptrend'] = True

        for i in range(1, len(df)):
            if df['Close'].iloc[i] > df['UpperBand'].iloc[i - 1]:
                df.at[df.index[i], 'inUptrend'] = True
            elif df['Close'].iloc[i] < df['LowerBand'].iloc[i - 1]:
                df.at[df.index[i], 'inUptrend'] = False
            else:
                df.at[df.index[i], 'inUptrend'] = df['inUptrend'].iloc[i - 1]
                if df['inUptrend'].iloc[i] and df['LowerBand'].iloc[i] < df['LowerBand'].iloc[i - 1]:
                    df.at[df.index[i], 'LowerBand'] = df['LowerBand'].iloc[i - 1]
                if not df['inUptrend'].iloc[i] and df['UpperBand'].iloc[i] > df['UpperBand'].iloc[i - 1]:
                    df.at[df.index[i], 'UpperBand'] = df['UpperBand'].iloc[i - 1]

        # --- Alert logic ---
        if df['inUptrend'].iloc[-1] and not df['inUptrend'].iloc[-2]:
            message = f"🚀 BUY SIGNAL for {coin} at {df['Close'].iloc[-1]:.4f} ({df.index[-1]})"
        elif not df['inUptrend'].iloc[-1] and df['inUptrend'].iloc[-2]:
            message = f"🔻 SELL SIGNAL for {coin} at {df['Close'].iloc[-1]:.4f} ({df.index[-1]})"
        else:
            message = None

        # --- Send Telegram Alert ---
        if message:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage" 
            payload = {"chat_id": CHAT_ID, "text": message}
            response = requests.post(url, data=payload)
            print(f"Sent: {message} | Status: {response.status_code}")

    except Exception as e:
        print(f"❌ Error with {coin}: {e}")