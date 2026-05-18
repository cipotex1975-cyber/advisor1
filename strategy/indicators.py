import pandas as pd
import numpy as np
from typing import Dict

def detect_swing_points(df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    """Detecta máximos y mínimos de swing."""
    highs = df["High"].rolling(window * 2 + 1, center=True).max()
    lows  = df["Low"].rolling(window * 2 + 1, center=True).min()
    df["swing_high"] = df["High"] == highs
    df["swing_low"]  = df["Low"]  == lows
    
    # Forward fill the last swing high/low value for easy access
    df["last_swing_high"] = df["High"].where(df["swing_high"]).ffill()
    df["last_swing_low"]  = df["Low"].where(df["swing_low"]).ffill()
    return df

def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Añade EMA 50, EMA 200, RSI y VWAP al DataFrame."""
    df = df.copy()

    df["ema50"]  = df["Close"].ewm(span=50,  adjust=False).mean()
    df["ema200"] = df["Close"].ewm(span=200, adjust=False).mean()

    # RSI (14)
    delta = df["Close"].diff()
    gain  = delta.clip(lower=0)
    loss  = (-delta).clip(lower=0)
    avg_gain = gain.ewm(com=13, adjust=False).mean()
    avg_loss = loss.ewm(com=13, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["rsi"] = 100 - (100 / (1 + rs))

    # VWAP intradía
    df["date"] = df.index.date
    df["tp"]   = (df["High"] + df["Low"] + df["Close"]) / 3
    df["cum_tpv"] = (df["tp"] * df["Volume"]).groupby(df["date"]).cumsum()
    df["cum_vol"] = df["Volume"].groupby(df["date"]).cumsum()
    df["vwap"] = df["cum_tpv"] / df["cum_vol"].replace(0, np.nan)
    df.drop(columns=["date", "tp", "cum_tpv", "cum_vol"], inplace=True)
    
    df = detect_swing_points(df)
    return df

def align_timeframes(dfs: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Toma el diccionario de DataFrames, calcula indicadores,
    desplaza los índices mayores para evitar look-ahead bias,
    y fusiona todo en el DataFrame de 15m.
    """
    processed = {}
    for tf, df in dfs.items():
        processed[tf] = compute_indicators(df)
        
    # Shifting HTFs (Look-ahead bias prevention)
    # yfinance and Oanda typically label the candle with its start time.
    # To use a candle, we must wait for it to close.
    
    df_1d = processed["1d"].copy()
    df_1d.index = df_1d.index + pd.Timedelta(days=1)
    
    df_4h = processed["4h"].copy()
    df_4h.index = df_4h.index + pd.Timedelta(hours=4)
    
    df_1h = processed["1h"].copy()
    df_1h.index = df_1h.index + pd.Timedelta(hours=1)
    
    # Base dataframe (15m) doesn't need shift for internal evaluation, 
    # the signal is generated at the close of the 15m candle.
    df_base = processed["15m"].copy()
    
    # Renombrar columnas para evitar conflictos al hacer merge
    df_1d = df_1d.add_suffix('_1d')
    df_4h = df_4h.add_suffix('_4h')
    df_1h = df_1h.add_suffix('_1h')
    
    # Sort indexes (required for merge_asof)
    df_base = df_base.sort_index()
    df_1d = df_1d.sort_index()
    df_4h = df_4h.sort_index()
    df_1h = df_1h.sort_index()
    
    # Merge usando asof (busca el último valor válido <= al índice de df_base)
    merged = pd.merge_asof(df_base, df_1d, left_index=True, right_index=True, direction='backward')
    merged = pd.merge_asof(merged, df_4h, left_index=True, right_index=True, direction='backward')
    merged = pd.merge_asof(merged, df_1h, left_index=True, right_index=True, direction='backward')
    
    return merged
