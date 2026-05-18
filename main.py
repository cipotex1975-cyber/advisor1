import argparse
import os
import sys
from datetime import datetime

# Añadir subdirectorios al path si es necesario
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.data_loader import load_multi_timeframe
from strategy.indicators import align_timeframes
from strategy.signals import generate_signals
from core.engine import BacktestEngine
from core.metrics import compute_metrics
from utils.visualization import plot_results, plot_trade

def parse_args():
    p = argparse.ArgumentParser(
        description="Backtesting – Estrategia Multi-Timeframe Forex/Crypto",
        formatter_class=argparse.RawTextHelpFormatter
    )
    p.add_argument("--source",   choices=["yfinance", "oanda", "fxcm", "dukascopy"], required=True,
                   help="Fuente de datos: yfinance | oanda | fxcm | dukascopy")
    p.add_argument("--symbol",   required=True,
                   help="Par o ticker (ej. EURUSD=X, BTC-USD)")
    p.add_argument("--start",    default="2024-01-01",
                   help="Fecha inicio YYYY-MM-DD  (default: 2024-01-01)")
    p.add_argument("--end",      default=datetime.today().strftime("%Y-%m-%d"),
                   help="Fecha fin   YYYY-MM-DD  (default: hoy)")
    p.add_argument("--capital",  type=float, default=10_000,
                   help="Capital inicial en USD  (default: 10000)")
    p.add_argument("--risk",     type=float, default=0.01,
                   help="Riesgo por operación 0-1  (default: 0.01 = 1%%)")
    p.add_argument("--oanda-key", default=None,
                   help="API key de OANDA (o usa OANDA_API_KEY)")
    p.add_argument("--fxcm-user", default=None,
                   help="Usuario de FXCM (o usa FXCM_USER)")
    p.add_argument("--fxcm-pass", default=None,
                   help="Password de FXCM (o usa FXCM_PASS)")
    p.add_argument("--fxcm-env", default="demo", choices=["demo","real"],
                   help="Entorno FXCM  (default: demo)")
    p.add_argument("--oanda-env", default="practice", choices=["practice","live"],
                   help="Entorno OANDA  (default: practice)")
    p.add_argument("--output",   default="backtest_results.png",
                   help="Ruta del gráfico de salida general")
    p.add_argument("--no-plot",  action="store_true",
                   help="Omitir la generación del gráfico general")
    p.add_argument("--no-trades", action="store_true",
                   help="Omitir la generación de gráficos individuales por operación")
    p.add_argument("--trades-dir", default="charts",
                   help="Directorio donde guardar los gráficos de cada trade")
    p.add_argument("--mode", choices=["long", "short", "both"], default="both",
                   help="Modo de operación: long, short o both (default: both)")
    return p.parse_args()

def main():
    args = parse_args()

    # ── 0. Crear directorios ─────────────────────────────
    for d in ["reports", "backtests", "strategies", "charts", "logs"]:
        os.makedirs(d, exist_ok=True)

    # ── 1. Carga de Datos Múltiples ──────────────────────
    print("[INFO] Descargando/Cargando datos Multi-Timeframe (1D, 4H, 1H, 15m)...")
    dfs = load_multi_timeframe(
        source=args.source,
        symbol=args.symbol,
        start=args.start,
        end=args.end,
        oanda_key=args.oanda_key,
        oanda_env=args.oanda_env,
        fxcm_user=args.fxcm_user,
        fxcm_pass=args.fxcm_pass,
        fxcm_env=args.fxcm_env
    )

    # ── 2. Indicadores y Alineación ──────────────────────
    print("[INFO] Calculando indicadores y alineando timeframes (previniendo look-ahead bias)...")
    merged_df = align_timeframes(dfs)
    
    # Check si quedaron datos tras el merge (por ejemplo, al principio no hay datos 1D suficientes)
    if merged_df.empty:
        print("[ERROR] El DataFrame fusionado está vacío. Prueba con un rango de fechas mayor.")
        sys.exit(1)

    # ── 3. Generador de Señales ──────────────────────────
    print(f"[INFO] Evaluando reglas y generando señales (Mode: {args.mode})...")
    df_signals = generate_signals(merged_df, mode=args.mode)
    
    total_signals = (df_signals["signal"] != 0).sum()
    longs  = (df_signals["signal"] ==  1).sum()
    shorts = (df_signals["signal"] == -1).sum()
    print(f"[INFO] Señales encontradas: {total_signals}  (LONG={longs}, SHORT={shorts})")

    # ── 4. Motor de Backtesting ──────────────────────────
    print("[INFO] Ejecutando backtesting...")
    engine = BacktestEngine(
        initial_capital=args.capital,
        risk_pct=args.risk,
    )
    equity_df, trades_df = engine.run(df_signals)

    # ── 5. Métricas ──────────────────────────────────────
    metrics = compute_metrics(equity_df, trades_df, args.capital)

    print("\n" + "═"*52)
    print("  RESULTADOS DEL BACKTEST MULTI-TIMEFRAME")
    print("═"*52)
    for k, v in metrics.items():
        if k == "error":
            print(f"  ⚠  {v}")
            continue
        label = k.replace("_", " ").title()
        print(f"  {label:<26} {v}")
    print("═"*52 + "\n")

    # ── 6. Gráficos ──────────────────────────────────────
    if not args.no_plot:
        plot_results(df_signals, equity_df, trades_df, metrics,
                     symbol=args.symbol,
                     save_path=args.output)

    # ── 7. Exportación y Gráficos Individuales ───────────
    if not trades_df.empty:
        csv_path = os.path.join("logs", "trades.csv")
        trades_df.to_csv(csv_path, index=False)
        print(f"[CSV]   Trades exportados: {csv_path}")

        if not args.no_trades and "trade_id" in trades_df.columns:
            print(f"[INFO] Generando gráficos de operaciones individuales en '{args.trades_dir}'...")
            grouped = trades_df.groupby("trade_id")
            for trade_id, group in grouped:
                first_row = group.iloc[0]
                last_row = group.iloc[-1]
                total_pnl = group["pnl"].sum()
                
                trade_summary = {
                    "trade_id": trade_id,
                    "entry_date": first_row["entry_date"],
                    "exit_date": last_row["exit_date"],
                    "direction": first_row["direction"],
                    "entry": first_row["entry"],
                    "stop": first_row["stop"],
                    "tp1": first_row["tp1"],
                    "tp2": first_row["tp2"],
                    "tp3": first_row["tp3"],
                    "pnl": total_pnl
                }
                
                plot_trade(df_signals, trade_summary, args.symbol, args.trades_dir)

            print(f"[INFO] Se generaron gráficos para {len(grouped)} operaciones.")

if __name__ == "__main__":
    main()
