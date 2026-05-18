import os
import sys
import pandas as pd
from typing import Optional, Dict

def get_csv_filename(symbol: str, tf: str) -> str:
    clean_symbol = symbol.replace('/', '_').replace('=', '_')
    dir_path = os.path.join("data", clean_symbol)
    os.makedirs(dir_path, exist_ok=True)
    return os.path.join(dir_path, f"{tf}.csv")

def _standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Asegura que las columnas se llamen Open, High, Low, Close, Volume"""
    rename_map = {c: c.capitalize() for c in df.columns if c.lower() in ['open', 'high', 'low', 'close', 'volume']}
    df = df.rename(columns=rename_map)
    cols = ["Open", "High", "Low", "Close", "Volume"]
    for c in cols:
        if c not in df.columns:
            df[c] = 0.0 if c != "Volume" else 0
    return df[cols].copy()

def load_yfinance_tf(symbol: str, tf: str, start: str, end: str) -> pd.DataFrame:
    csv_file = get_csv_filename(symbol, tf)
    df_cache = pd.DataFrame()
    fetch_start = start

    if os.path.exists(csv_file):
        df_cache = pd.read_csv(csv_file, index_col="datetime", parse_dates=True)
        if not df_cache.empty:
            # Empezamos a descargar desde el día de la última vela guardada
            last_dt = df_cache.index[-1]
            fetch_start = last_dt.strftime("%Y-%m-%d")
            print(f"[YF] Caché local encontrado. Actualizando {symbol} | {tf} desde {fetch_start}...")

    try:
        import yfinance as yf
    except ImportError:
        sys.exit("[ERROR] Instala yfinance: pip install yfinance")

    if df_cache.empty:
        print(f"[YF] Descargando histórico completo {symbol} | {tf} | {start} → {end}")

    df_new = yf.download(symbol, start=fetch_start, end=end, interval=tf, progress=False, auto_adjust=True)
    
    if not df_new.empty:
        if isinstance(df_new.columns, pd.MultiIndex):
            df_new.columns = df_new.columns.get_level_values(0)

        df_new.index = pd.to_datetime(df_new.index)
        df_new.index.name = "datetime"
        df_new = _standardize_columns(df_new)
        
        if not df_cache.empty:
            # Combinar y eliminar duplicados (quedándonos con la información más reciente si la vela se actualizó)
            df_combined = pd.concat([df_cache, df_new])
            df_combined = df_combined[~df_combined.index.duplicated(keep='last')]
            df_combined.sort_index(inplace=True)
        else:
            df_combined = df_new
            
        # Guardar el caché actualizado
        df_combined.to_csv(csv_file)
        return df_combined
    else:
        if not df_cache.empty:
            print(f"[YF] Datos ya actualizados para {symbol} | {tf}.")
            return df_cache
        sys.exit(f"[ERROR] Sin datos para {symbol} en {tf}.")

def load_oanda_tf(symbol: str, granularity: str, start: str, end: str, api_key: str, env: str) -> pd.DataFrame:
    # OANDA granularities mapping for file names (to match user expected 15m, 1h, 4h, 1d)
    gran_map = {"M15": "15m", "H1": "1h", "H4": "4h", "D": "1d"}
    file_tf = gran_map.get(granularity, granularity)
    csv_file = get_csv_filename(symbol, file_tf)
    df_cache = pd.DataFrame()
    
    from_dt = pd.Timestamp(start).strftime("%Y-%m-%dT%H:%M:%SZ")
    to_dt   = pd.Timestamp(end).strftime("%Y-%m-%dT%H:%M:%SZ")

    if os.path.exists(csv_file):
        df_cache = pd.read_csv(csv_file, index_col="datetime", parse_dates=True)
        if not df_cache.empty:
            last_dt = df_cache.index[-1]
            from_dt = pd.Timestamp(last_dt).strftime("%Y-%m-%dT%H:%M:%SZ")
            print(f"[OANDA] Caché local encontrado. Actualizando {symbol} | {granularity} desde {from_dt}...")

    try:
        import oandapyV20
        import oandapyV20.endpoints.instruments as instruments
        from oandapyV20 import API
    except ImportError:
        sys.exit("[ERROR] Instala oandapyV20: pip install oandapyV20")

    client = API(access_token=api_key, environment=env)
    
    if df_cache.empty:
        print(f"[OANDA] Descargando histórico completo {symbol} | {granularity} | Desde {from_dt}")
        
    params = {"from": from_dt, "to": to_dt, "granularity": granularity, "count": 5000, "price": "MBA"}
    
    records = []
    r = instruments.InstrumentsCandles(symbol, params=params)
    try:
        client.request(r)
        for candle in r.response.get("candles", []):
            if candle["complete"]:
                records.append({
                    "datetime": pd.Timestamp(candle["time"]),
                    "Open":   float(candle["mid"]["o"]),
                    "High":   float(candle["mid"]["h"]),
                    "Low":    float(candle["mid"]["l"]),
                    "Close":  float(candle["mid"]["c"]),
                    "Volume": int(candle["volume"]),
                    "spread": float(candle["ask"]["c"]) - float(candle["bid"]["c"]) if "ask" in candle and "bid" in candle else 0.0
                })
    except Exception as e:
        sys.exit(f"[ERROR] OANDA API: {e}")

    if records:
        df_new = pd.DataFrame(records).set_index("datetime")
        df_new = _standardize_columns(df_new)
        
        if not df_cache.empty:
            df_combined = pd.concat([df_cache, df_new])
            df_combined = df_combined[~df_combined.index.duplicated(keep='last')]
            df_combined.sort_index(inplace=True)
        else:
            df_combined = df_new
            
        df_combined.to_csv(csv_file)
        return df_combined
    else:
        if not df_cache.empty:
            print(f"[OANDA] Datos ya actualizados para {symbol} | {granularity}.")
            return df_cache
        sys.exit(f"[ERROR] Sin datos de OANDA para {symbol} en {granularity}.")

def load_multi_timeframe(source: str, symbol: str, start: str, end: str, oanda_key: Optional[str]=None, oanda_env: str="practice") -> Dict[str, pd.DataFrame]:
    """Descarga o carga de caché los 4 timeframes requeridos."""
    dfs = {}
    
    if source == "yfinance":
        tfs = {"1d": "1d", "4h": "4h", "1h": "1h", "15m": "15m"}
        for key, tf in tfs.items():
            try:
                dfs[key] = load_yfinance_tf(symbol, tf, start, end)
            except Exception as e:
                print(f"[ADVERTENCIA] Fallo al cargar {tf} en yFinance: {e}")
                sys.exit(1)
                
    elif source == "oanda":
        tfs = {"1d": "D", "4h": "H4", "1h": "H1", "15m": "M15"}
        if not oanda_key:
            oanda_key = os.environ.get("OANDA_API_KEY", "")
        if not oanda_key:
            sys.exit("[ERROR] OANDA API key requerida.")
            
        for key, gran in tfs.items():
            dfs[key] = load_oanda_tf(symbol, gran, start, end, oanda_key, env=oanda_env)
            
    return dfs
