import pandas as pd
import numpy as np

def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Genera señales evaluando la matriz Multi-Timeframe (1D, 4H, 1H, 15m).
    El DataFrame de entrada `df` ya tiene todas las temporalidades alineadas.
    """
    df = df.copy()
    df["signal"]      = 0      # 1 = LONG, -1 = SHORT
    df["entry_price"] = np.nan
    df["stop_loss"]   = np.nan
    df["take_profit1"]= np.nan
    df["take_profit2"]= np.nan
    df["take_profit3"]= np.nan

    # Tolerancia para pullback a EMA 50 en 4H (ej. 0.5%)
    tol_4h = 0.005 

    for i in range(10, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]

        # Validar que tengamos datos de todos los timeframes
        if pd.isna(row.get("ema200_1d")) or pd.isna(row.get("ema50_4h")) or pd.isna(row.get("last_swing_high_1h")):
            continue

        # Validar horario operativo (Apertura de Londres hasta cierre de NY)
        # Rango aproximado: 08:00 a 21:00 (hora del servidor/UTC)
        current_hour = df.index[i].hour
        if not (8 <= current_hour <= 21):
            continue

        close_15m = row["Close"]
        open_15m  = row["Open"]
        low_15m   = row["Low"]
        high_15m  = row["High"]

        # --- REGLAS LONG ---
        # 1D: Tendencia principal
        trend_1d_up = row["Close_1d"] > row["ema200_1d"]
        
        # 4H: Contexto operativo
        context_4h_up = row["ema50_4h"] > row["ema200_4h"]
        pullback_4h_up = abs(row["Close_4h"] - row["ema50_4h"]) / row["ema50_4h"] <= tol_4h
        
        # 1H: Confirmación estructural (BOS alcista)
        # El precio de 1H rompió recientemente su último swing high
        bos_1h_up = row["Close_1h"] > row["last_swing_high_1h"]
        
        # 15m: Gatillo
        # Vela de rechazo alcista en zona de soporte/pullback
        trigger_15m_up = (close_15m > open_15m) and (prev["Close"] < prev["Open"])

        if trend_1d_up and context_4h_up and pullback_4h_up and bos_1h_up and trigger_15m_up:
            stop = row["last_swing_low_1h"] if not pd.isna(row["last_swing_low_1h"]) else (low_15m * 0.998)
            risk = close_15m - stop
            if risk > 0:
                df.iloc[i, df.columns.get_loc("signal")]       = 1
                df.iloc[i, df.columns.get_loc("entry_price")]  = close_15m
                df.iloc[i, df.columns.get_loc("stop_loss")]    = stop
                df.iloc[i, df.columns.get_loc("take_profit1")] = close_15m + (risk * 1)
                df.iloc[i, df.columns.get_loc("take_profit2")] = close_15m + (risk * 2)
                df.iloc[i, df.columns.get_loc("take_profit3")] = close_15m + (risk * 3)

        # --- REGLAS SHORT ---
        # 1D: Tendencia principal
        trend_1d_down = row["Close_1d"] < row["ema200_1d"]
        
        # 4H: Contexto operativo
        context_4h_down = row["ema50_4h"] < row["ema200_4h"]
        pullback_4h_down = abs(row["Close_4h"] - row["ema50_4h"]) / row["ema50_4h"] <= tol_4h
        
        # 1H: Confirmación estructural (BOS bajista)
        bos_1h_down = row["Close_1h"] < row["last_swing_low_1h"]
        
        # 15m: Gatillo
        trigger_15m_down = (close_15m < open_15m) and (prev["Close"] > prev["Open"])

        if trend_1d_down and context_4h_down and pullback_4h_down and bos_1h_down and trigger_15m_down:
            stop = row["last_swing_high_1h"] if not pd.isna(row["last_swing_high_1h"]) else (high_15m * 1.002)
            risk = stop - close_15m
            if risk > 0:
                df.iloc[i, df.columns.get_loc("signal")]       = -1
                df.iloc[i, df.columns.get_loc("entry_price")]  = close_15m
                df.iloc[i, df.columns.get_loc("stop_loss")]    = stop
                df.iloc[i, df.columns.get_loc("take_profit1")] = close_15m - (risk * 1)
                df.iloc[i, df.columns.get_loc("take_profit2")] = close_15m - (risk * 2)
                df.iloc[i, df.columns.get_loc("take_profit3")] = close_15m - (risk * 3)

    return df
