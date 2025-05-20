import pandas as pd
import numpy as np
import yfinance as yf
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split

BIST_40 = [
    "AKBNK", "AKSEN", "ALARK", "ASELS", "BIMAS", "DOHOL", "EKGYO", "ENJSA", "EREGL", "FROTO",
    "GARAN", "GUBRF", "HALKB", "HEKTS", "ISCTR", "KCHOL", "KOZAA", "KOZAL", "KRDMD", "MGROS",
    "PETKM", "PGSUS", "SAHOL", "SASA", "SISE", "TAVHL", "TCELL", "THYAO", "TKFEN", "TOASO",
    "TSKB", "TTKOM", "TTRAK", "TUPRS", "VAKBN", "VESBE", "YKBNK", "SOKM", "SKBNK", "ARCLK"
]

def get_hisse_verisi(symbol="AKBNK", gun=90):
    symbol_yf = symbol + ".IS"
    df = yf.download(symbol_yf, period=f"{gun}d", interval="1d", progress=False)
    if df is None or len(df) < 30:
        raise ValueError("Yetersiz veri")
    df = df.reset_index()
    df.rename(columns={"Date": "date", "Close": "close"}, inplace=True)
    df["EMA_10"] = df["close"].ewm(span=10).mean()
    df["EMA_20"] = df["close"].ewm(span=20).mean()
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df["RSI_14"] = 100 - (100 / (1 + rs))
    ema12 = df["close"].ewm(span=12).mean()
    ema26 = df["close"].ewm(span=26).mean()
    df["MACD"] = ema12 - ema26
    df["volume_change"] = df["Volume"].pct_change()
    df["prev_return"] = df["close"].pct_change()
    df["price_diff_3day"] = df["close"] - df["close"].shift(3)
    df["price_volatility"] = df["close"].rolling(window=5).std()
    df.dropna(inplace=True)
    return df

def strateji_ml_temel(df):
    features = ["EMA_10", "EMA_20", "RSI_14", "MACD", "volume_change", "prev_return", "price_diff_3day", "price_volatility"]

    df = df.copy()
    df["y"] = (df["close"].shift(-1) > df["close"]).astype(int)
    df.dropna(subset=features + ["y"], inplace=True)

    if len(df) < 10:
        raise ValueError("Yetersiz veri")

    X = df[features]
    y = df["y"]

    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(X)

    X_train = X_scaled[:-1]
    y_train = y.iloc[:-1]

    model = HistGradientBoostingClassifier(max_iter=200, max_depth=5, random_state=42)
    model.fit(X_train, y_train)

    latest_features = scaler.transform([X.iloc[-1].values])
    tahmin = model.predict(latest_features)[0]

    return int(tahmin), round(model.score(X_train, y_train), 2)


def strateji_rsi_only(df):
    latest = df.iloc[-1]
    rsi = latest["RSI_14"]
    tahmin = 1 if rsi > 50 else 0
    return tahmin, 0.5

def backtest_strateji(symbol, strateji_fn, gun_sayisi=60, baslangic_bakiye=100000):
    try:
        df = get_hisse_verisi(symbol, gun=gun_sayisi + 30)
    except:
        return pd.DataFrame()

    df = df.reset_index()
    results = []
    bakiye = baslangic_bakiye

    for i in range(20, len(df) - 1):
        df_train = df.iloc[:i]
        df_next = df.iloc[i + 1]

        try:
            tahmin, acc = strateji_fn(df_train)
            if tahmin is None:
                continue
        except:
            continue

        close_today = df.iloc[i]["close"]
        close_tomorrow = df_next["close"]
        gercek_degisim = (close_tomorrow - close_today) / close_today * 100

        birim_yatirim = bakiye / 20
        getiri = birim_yatirim * (gercek_degisim / 100) if tahmin == 1 else -birim_yatirim * (gercek_degisim / 100)
        bakiye += getiri

        hedef = 1 if (gercek_degisim >= 3 and tahmin == 1) or (gercek_degisim <= -3 and tahmin == 0) else 0

        results.append({
            "tarih": df.iloc[i]["date"].strftime("%Y-%m-%d"),
            "tahmin": "⬆️" if tahmin == 1 else "⬇️",
            "gerçek (%)": round(gercek_degisim, 2),
            "hedefe_ulaştı": hedef,
            "bakiye": round(bakiye, 2)
        })

    return pd.DataFrame(results)

