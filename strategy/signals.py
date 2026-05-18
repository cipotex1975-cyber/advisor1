import pandas as pd
import numpy as np

import json

def generate_signals(df: pd.DataFrame, mode: str = "both") -> pd.DataFrame:
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
    df["entry_reason"]= ""

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
        if mode in ["long", "both"]:
            # 1D: Tendencia principal (EMA50 > EMA200)
            trend_1d_up = row.get("ema50_1d", 0) > row.get("ema200_1d", 0)
            if pd.isna(row.get("ema50_1d")): trend_1d_up = False # Fallback si no hay 1D EMA50
            
            # 4H: Contexto operativo (precio > EMA50)
            context_4h_up = row["Close_4h"] > row["ema50_4h"]
            
            # 15m: Gatillo (pullback + rejection candle + break alcista de la vela anterior)
            # Rejection candle: mecha inferior larga (cierre en la mitad superior) o vela alcista fuerte
            rejection_up = (close_15m > open_15m) and ((close_15m - low_15m) > (high_15m - low_15m) * 0.5)
            # Pullback: venimos de una caída reciente
            pullback_up = prev["Close"] < prev["Open"]
            # Break: rompemos el máximo de la vela de rechazo
            break_up = close_15m > prev["High"] # Simplificación del trigger break
            trigger_15m_up = rejection_up and pullback_up

            if trend_1d_up and context_4h_up and trigger_15m_up:
                # Stop = swing low 1H o 15M, menos un margen ATR
                atr = row.get("atr", 0.001)
                base_stop = row["last_swing_low"] if not pd.isna(row["last_swing_low"]) else low_15m
                stop = base_stop - atr
                
                risk = close_15m - stop
                if risk > 0:
                    df.iloc[i, df.columns.get_loc("signal")]       = 1
                    df.iloc[i, df.columns.get_loc("entry_price")]  = close_15m
                    df.iloc[i, df.columns.get_loc("stop_loss")]    = stop
                    df.iloc[i, df.columns.get_loc("take_profit1")] = close_15m + (risk * 1)
                    df.iloc[i, df.columns.get_loc("take_profit2")] = close_15m + (risk * 2)
                    df.iloc[i, df.columns.get_loc("take_profit3")] = close_15m + (risk * 3)
                    
                    reason = {
                        "macro_trend": "bullish",
                        "ema_alignment": bool(trend_1d_up),
                        "structure_4h": bool(context_4h_up),
                        "rejection_candle": bool(trigger_15m_up),
                        "atr_value": atr
                    }
                    df.iloc[i, df.columns.get_loc("entry_reason")] = json.dumps(reason)

        # --- REGLAS SHORT ---
        if mode in ["short", "both"]:
            # 1D: Tendencia principal (EMA50 < EMA200)
            trend_1d_down = row.get("ema50_1d", 0) < row.get("ema200_1d", float('inf'))
            if pd.isna(row.get("ema50_1d")): trend_1d_down = False
            
            # 4H: Contexto operativo (precio < EMA50)
            context_4h_down = row["Close_4h"] < row["ema50_4h"]
            
            # 15m: Gatillo
            rejection_down = (close_15m < open_15m) and ((high_15m - close_15m) > (high_15m - low_15m) * 0.5)
            pullback_down = prev["Close"] > prev["Open"]
            trigger_15m_down = rejection_down and pullback_down

            if trend_1d_down and context_4h_down and trigger_15m_down:
                atr = row.get("atr", 0.001)
                base_stop = row["last_swing_high"] if not pd.isna(row["last_swing_high"]) else high_15m
                stop = base_stop + atr
                
                risk = stop - close_15m
                if risk > 0:
                    df.iloc[i, df.columns.get_loc("signal")]       = -1
                    df.iloc[i, df.columns.get_loc("entry_price")]  = close_15m
                    df.iloc[i, df.columns.get_loc("stop_loss")]    = stop
                    df.iloc[i, df.columns.get_loc("take_profit1")] = close_15m - (risk * 1)
                    df.iloc[i, df.columns.get_loc("take_profit2")] = close_15m - (risk * 2)
                    df.iloc[i, df.columns.get_loc("take_profit3")] = close_15m - (risk * 3)
                    
                    reason = {
                        "macro_trend": "bearish",
                        "ema_alignment": bool(trend_1d_down),
                        "structure_4h": bool(context_4h_down),
                        "rejection_candle": bool(trigger_15m_down),
                        "atr_value": atr
                    }
                    df.iloc[i, df.columns.get_loc("entry_reason")] = json.dumps(reason)

    return df
