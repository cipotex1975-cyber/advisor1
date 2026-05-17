"""
=============================================================
  Estrategia Profesional de Trading Multi-Timeframe
  Backtesting System – Forex & Crypto
=============================================================
Basado en: Estructura de mercado, análisis multi-timeframe,
           gestión institucional de riesgo y setups de alta
           probabilidad.

Fuentes de datos: OANDA o yfinance (selección del usuario)
=============================================================
"""

import os
import sys
import warnings
import argparse
from datetime import datetime, timedelta
from typing import Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.dates as mdates
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────────────────
# 1.  DATA LOADERS
# ──────────────────────────────────────────────────────────

def load_yfinance(symbol: str, start: str, end: str, interval: str = "1h") -> pd.DataFrame:
    """Descarga datos con yfinance."""
    try:
        import yfinance as yf
    except ImportError:
        sys.exit("[ERROR] yfinance no instalado. Ejecuta: pip install yfinance")

    print(f"[yfinance] Descargando {symbol} | {interval} | {start} → {end}")
    df = yf.download(symbol, start=start, end=end, interval=interval, progress=False, auto_adjust=True)
    if df.empty:
        sys.exit(f"[ERROR] No se obtuvieron datos para {symbol} con yfinance.")
    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.index = pd.to_datetime(df.index)
    df.index.name = "datetime"
    print(f"[yfinance] {len(df)} velas descargadas.")
    return df


def load_oanda(symbol: str, start: str, end: str,
               granularity: str = "H1",
               api_key: Optional[str] = None,
               account_type: str = "practice") -> pd.DataFrame:
    """Descarga datos con oandapyV20."""
    try:
        import oandapyV20
        import oandapyV20.endpoints.instruments as instruments
        from oandapyV20 import API
    except ImportError:
        sys.exit("[ERROR] oandapyV20 no instalado. Ejecuta: pip install oandapyV20")

    if not api_key:
        api_key = os.environ.get("OANDA_API_KEY", "")
    if not api_key:
        sys.exit("[ERROR] API key de OANDA no encontrada. Usa --oanda-key o la variable OANDA_API_KEY.")

    environment = "practice" if account_type == "practice" else "live"
    client = API(access_token=api_key, environment=environment)

    from_dt = pd.Timestamp(start).strftime("%Y-%m-%dT%H:%M:%SZ")
    to_dt   = pd.Timestamp(end).strftime("%Y-%m-%dT%H:%M:%SZ")

    print(f"[OANDA] Descargando {symbol} | {granularity} | {start} → {end}")

    params = {"from": from_dt, "to": to_dt, "granularity": granularity, "count": 5000}
    r = instruments.InstrumentsCandles(symbol, params=params)
    client.request(r)

    records = []
    for candle in r.response["candles"]:
        if candle["complete"]:
            records.append({
                "datetime": pd.Timestamp(candle["time"]),
                "Open":   float(candle["mid"]["o"]),
                "High":   float(candle["mid"]["h"]),
                "Low":    float(candle["mid"]["l"]),
                "Close":  float(candle["mid"]["c"]),
                "Volume": int(candle["volume"]),
            })

    if not records:
        sys.exit("[ERROR] No se obtuvieron datos de OANDA.")

    df = pd.DataFrame(records).set_index("datetime")
    print(f"[OANDA] {len(df)} velas descargadas.")
    return df


# ──────────────────────────────────────────────────────────
# 2.  INDICADORES TÉCNICOS
# ──────────────────────────────────────────────────────────

def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Añade EMA 50, EMA 200, RSI y VWAP al DataFrame."""
    df = df.copy()

    # EMAs
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

    # VWAP (acumulado por sesión – aproximación diaria)
    df["date"] = df.index.date
    df["tp"]   = (df["High"] + df["Low"] + df["Close"]) / 3
    df["cum_tpv"] = df.groupby("date", group_keys=False).apply(
        lambda x: (x["tp"] * x["Volume"]).cumsum()
    )
    df["cum_vol"] = df.groupby("date", group_keys=False).apply(
        lambda x: x["Volume"].cumsum()
    )
    df["vwap"] = df["cum_tpv"] / df["cum_vol"].replace(0, np.nan)
    df.drop(columns=["date", "tp", "cum_tpv", "cum_vol"], inplace=True)

    return df


# ──────────────────────────────────────────────────────────
# 3.  GENERADOR DE SEÑALES
# ──────────────────────────────────────────────────────────

def detect_swing_points(df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    """Detecta máximos y mínimos de swing."""
    df = df.copy()
    highs = df["High"].rolling(window * 2 + 1, center=True).max()
    lows  = df["Low"].rolling(window * 2 + 1, center=True).min()
    df["swing_high"] = df["High"] == highs
    df["swing_low"]  = df["Low"]  == lows
    return df


def generate_signals(df: pd.DataFrame, rr_min: float = 2.0) -> pd.DataFrame:
    """
    Genera señales de entrada LONG y SHORT siguiendo las reglas del PDF:

    LONG:
      - Close > EMA 200
      - EMA 50 > EMA 200
      - Retroceso hacia EMA 50 (precio toca zona EMA 50 ± 0.2%)
      - RSI entre 35–65 (no sobrecomprado/vendido en extremo)
      - Vela alcista de confirmación

    SHORT:
      - Close < EMA 200
      - EMA 50 < EMA 200
      - Retroceso hacia EMA 50
      - RSI entre 35–65
      - Vela bajista de confirmación
    """
    df = detect_swing_points(df)
    df["signal"]      = 0      # 1 = LONG, -1 = SHORT
    df["entry_price"] = np.nan
    df["stop_loss"]   = np.nan
    df["take_profit1"]= np.nan
    df["take_profit2"]= np.nan
    df["take_profit3"]= np.nan

    tolerance = 0.002  # 0.2 % alrededor de EMA 50

    for i in range(201, len(df) - 1):
        row   = df.iloc[i]
        prev  = df.iloc[i - 1]
        close = row["Close"]
        high  = row["High"]
        low   = row["Low"]
        ema50 = row["ema50"]
        ema200= row["ema200"]
        rsi   = row["rsi"]

        if pd.isna(ema50) or pd.isna(ema200) or pd.isna(rsi):
            continue

        near_ema50 = abs(close - ema50) / ema50 <= tolerance

        # ── LONG ──────────────────────────────────────────
        if (close > ema200 and
                ema50 > ema200 and
                near_ema50 and
                35 <= rsi <= 65 and
                close > prev["Close"]):            # vela alcista

            # Buscamos el mínimo estructural reciente (últimas 10 velas)
            recent_low = df["Low"].iloc[max(0, i-10):i].min()
            stop = recent_low * 0.999
            risk = close - stop
            if risk <= 0:
                continue
            df.iloc[i, df.columns.get_loc("signal")]       = 1
            df.iloc[i, df.columns.get_loc("entry_price")]  = close
            df.iloc[i, df.columns.get_loc("stop_loss")]    = stop
            df.iloc[i, df.columns.get_loc("take_profit1")] = close + risk * 1
            df.iloc[i, df.columns.get_loc("take_profit2")] = close + risk * 2
            df.iloc[i, df.columns.get_loc("take_profit3")] = close + risk * 3

        # ── SHORT ─────────────────────────────────────────
        elif (close < ema200 and
                ema50 < ema200 and
                near_ema50 and
                35 <= rsi <= 65 and
                close < prev["Close"]):            # vela bajista

            recent_high = df["High"].iloc[max(0, i-10):i].max()
            stop = recent_high * 1.001
            risk = stop - close
            if risk <= 0:
                continue
            df.iloc[i, df.columns.get_loc("signal")]       = -1
            df.iloc[i, df.columns.get_loc("entry_price")]  = close
            df.iloc[i, df.columns.get_loc("stop_loss")]    = stop
            df.iloc[i, df.columns.get_loc("take_profit1")] = close - risk * 1
            df.iloc[i, df.columns.get_loc("take_profit2")] = close - risk * 2
            df.iloc[i, df.columns.get_loc("take_profit3")] = close - risk * 3

    return df


# ──────────────────────────────────────────────────────────
# 4.  MOTOR DE BACKTESTING
# ──────────────────────────────────────────────────────────

class BacktestEngine:
    """
    Simula la ejecución de las señales con gestión de capital
    profesional: 1 % de riesgo por operación, máximo 3 simultáneas,
    drawdown diario 3 %, semanal 6 %.
    """

    def __init__(self,
                 initial_capital: float = 10_000,
                 risk_pct: float = 0.01,
                 max_simultaneous: int = 3,
                 max_dd_daily: float = 0.03,
                 max_dd_weekly: float = 0.06,
                 tp_levels: list = None):
        self.initial_capital  = initial_capital
        self.risk_pct         = risk_pct
        self.max_simultaneous = max_simultaneous
        self.max_dd_daily     = max_dd_daily
        self.max_dd_weekly    = max_dd_weekly
        # Fracciones del take-profit parcial
        self.tp_levels = tp_levels or [
            (1.0, 0.33),   # TP1 → cierre 33 %
            (2.0, 0.33),   # TP2 → cierre 33 %
            (3.0, 0.34),   # TP3 → cierre 34 %
        ]

    # ── helpers ──────────────────────────────────────────

    def _position_size(self, capital: float, entry: float, stop: float) -> float:
        risk_amount = capital * self.risk_pct
        distance    = abs(entry - stop)
        if distance == 0:
            return 0
        # unidades de activo
        return risk_amount / distance

    # ── main loop ────────────────────────────────────────

    def run(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Ejecuta el backtest y devuelve:
          - equity_curve: pd.Series con curva de capital
          - trades:       pd.DataFrame con registro de operaciones
        """
        capital    = self.initial_capital
        equity     = []
        trades     = []
        open_pos   = []      # lista de posiciones abiertas

        # control drawdown
        week_start_cap = capital
        day_start_cap  = capital
        current_day    = None
        current_week   = None
        blocked_day    = False
        blocked_week   = False

        signals = df[df["signal"] != 0].copy()

        price_array = df["Close"].values
        high_array  = df["High"].values
        low_array   = df["Low"].values
        dates       = df.index

        for idx in range(len(df)):
            dt    = dates[idx]
            close = price_array[idx]
            high  = high_array[idx]
            low   = low_array[idx]

            # reset drawdown diario
            if dt.date() != current_day:
                current_day    = dt.date()
                day_start_cap  = capital
                blocked_day    = False

            # reset drawdown semanal (lunes)
            week_num = dt.isocalendar()[1]
            if week_num != current_week:
                current_week   = week_num
                week_start_cap = capital
                blocked_week   = False

            # ── gestión de posiciones abiertas ──────────
            remaining = []
            for pos in open_pos:
                closed = False

                if pos["direction"] == 1:   # LONG
                    # Stop loss
                    if low <= pos["stop"]:
                        pnl = (pos["stop"] - pos["entry"]) * pos["size"]
                        capital += pnl
                        trades.append({**pos, "exit_price": pos["stop"],
                                       "exit_date": dt, "pnl": pnl, "exit_reason": "SL"})
                        closed = True
                    else:
                        # Take profits parciales
                        for tp_key, frac in [("tp1", 0.33), ("tp2", 0.33), ("tp3", 0.34)]:
                            if tp_key in pos and not pos.get(f"{tp_key}_hit") and high >= pos[tp_key]:
                                partial_size = pos["orig_size"] * frac
                                pnl_partial  = (pos[tp_key] - pos["entry"]) * partial_size
                                capital += pnl_partial
                                pos[f"{tp_key}_hit"] = True
                                # mover SL a breakeven en TP1
                                if tp_key == "tp1":
                                    pos["stop"] = pos["entry"]
                                trades.append({**pos, "exit_price": pos[tp_key],
                                               "exit_date": dt, "pnl": pnl_partial,
                                               "exit_reason": tp_key.upper(), "size": partial_size})

                else:                        # SHORT
                    if high >= pos["stop"]:
                        pnl = (pos["entry"] - pos["stop"]) * pos["size"]
                        capital += pnl
                        trades.append({**pos, "exit_price": pos["stop"],
                                       "exit_date": dt, "pnl": pnl, "exit_reason": "SL"})
                        closed = True
                    else:
                        for tp_key, frac in [("tp1", 0.33), ("tp2", 0.33), ("tp3", 0.34)]:
                            if tp_key in pos and not pos.get(f"{tp_key}_hit") and low <= pos[tp_key]:
                                partial_size = pos["orig_size"] * frac
                                pnl_partial  = (pos["entry"] - pos[tp_key]) * partial_size
                                capital += pnl_partial
                                pos[f"{tp_key}_hit"] = True
                                if tp_key == "tp1":
                                    pos["stop"] = pos["entry"]
                                trades.append({**pos, "exit_price": pos[tp_key],
                                               "exit_date": dt, "pnl": pnl_partial,
                                               "exit_reason": tp_key.upper(), "size": partial_size})

                if not closed:
                    remaining.append(pos)
            open_pos = remaining

            # ── drawdown checks ─────────────────────────
            dd_day  = (capital - day_start_cap)  / day_start_cap
            dd_week = (capital - week_start_cap) / week_start_cap
            if dd_day  <= -self.max_dd_daily:
                blocked_day  = True
            if dd_week <= -self.max_dd_weekly:
                blocked_week = True

            # ── abrir nuevas posiciones ──────────────────
            if (not blocked_day and not blocked_week and
                    len(open_pos) < self.max_simultaneous):

                row = df.iloc[idx]
                sig = row["signal"]

                if sig != 0 and not pd.isna(row["entry_price"]):
                    size = self._position_size(capital, row["entry_price"], row["stop_loss"])
                    if size > 0:
                        pos = {
                            "direction":  int(sig),
                            "entry":      row["entry_price"],
                            "stop":       row["stop_loss"],
                            "tp1":        row["take_profit1"],
                            "tp2":        row["take_profit2"],
                            "tp3":        row["take_profit3"],
                            "size":       size,
                            "orig_size":  size,
                            "entry_date": dt,
                        }
                        open_pos.append(pos)

            equity.append({"datetime": dt, "capital": capital})

        # cerrar posiciones abiertas al precio final
        final_close = price_array[-1]
        final_dt    = dates[-1]
        for pos in open_pos:
            if pos["direction"] == 1:
                pnl = (final_close - pos["entry"]) * pos["size"]
            else:
                pnl = (pos["entry"] - final_close) * pos["size"]
            capital += pnl
            trades.append({**pos, "exit_price": final_close,
                           "exit_date": final_dt, "pnl": pnl, "exit_reason": "EOD"})

        equity_df = pd.DataFrame(equity).set_index("datetime")
        trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()
        return equity_df, trades_df


# ──────────────────────────────────────────────────────────
# 5.  MÉTRICAS
# ──────────────────────────────────────────────────────────

def compute_metrics(equity_df: pd.DataFrame,
                    trades_df: pd.DataFrame,
                    initial_capital: float) -> dict:
    """Calcula métricas profesionales de backtesting."""
    if trades_df.empty:
        return {"error": "Sin operaciones registradas."}

    equity = equity_df["capital"]
    returns = equity.pct_change().dropna()

    # filtrar solo cierres completos (SL, TP*)
    closed = trades_df[trades_df["exit_reason"].isin(["SL","TP1","TP2","TP3","EOD"])]

    # PnL por trade agrupado (entry_date + direction)
    if "entry_date" in closed.columns:
        trade_pnl = closed.groupby(["entry_date","direction"])["pnl"].sum().reset_index()
    else:
        trade_pnl = closed.copy()

    wins   = trade_pnl[trade_pnl["pnl"] > 0]["pnl"]
    losses = trade_pnl[trade_pnl["pnl"] <= 0]["pnl"]

    win_rate = len(wins) / len(trade_pnl) if len(trade_pnl) > 0 else 0

    gross_profit = wins.sum()
    gross_loss   = abs(losses.sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf

    # Drawdown
    roll_max = equity.cummax()
    drawdown = (equity - roll_max) / roll_max
    max_dd   = drawdown.min()

    # Expectativa matemática
    avg_win  = wins.mean()  if len(wins)   > 0 else 0
    avg_loss = losses.mean() if len(losses) > 0 else 0
    expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)

    # Sharpe (anualizado, asumiendo 252 días de trading)
    sharpe = (returns.mean() / returns.std() * np.sqrt(252 * 6.5)
              if returns.std() > 0 else 0)

    final_capital = equity.iloc[-1]
    total_return  = (final_capital - initial_capital) / initial_capital * 100

    return {
        "capital_inicial":    initial_capital,
        "capital_final":      round(final_capital, 2),
        "retorno_total_%":    round(total_return, 2),
        "n_operaciones":      len(trade_pnl),
        "win_rate_%":         round(win_rate * 100, 2),
        "profit_factor":      round(profit_factor, 3),
        "max_drawdown_%":     round(max_dd * 100, 2),
        "expectativa_$":      round(expectancy, 2),
        "sharpe_ratio":       round(sharpe, 3),
        "ganancia_bruta_$":   round(gross_profit, 2),
        "perdida_bruta_$":    round(abs(losses.sum()), 2),
        "promedio_ganancia":  round(avg_win, 2),
        "promedio_perdida":   round(avg_loss, 2),
        "longs":              int((trade_pnl["direction"] == 1).sum())  if "direction" in trade_pnl else "N/A",
        "shorts":             int((trade_pnl["direction"] == -1).sum()) if "direction" in trade_pnl else "N/A",
    }


# ──────────────────────────────────────────────────────────
# 6.  VISUALIZACIÓN
# ──────────────────────────────────────────────────────────

def plot_results(df: pd.DataFrame,
                 equity_df: pd.DataFrame,
                 trades_df: pd.DataFrame,
                 metrics: dict,
                 symbol: str,
                 save_path: str = "backtest_results.png"):
    """Genera un dashboard completo con 4 subplots."""

    plt.style.use("dark_background")
    fig = plt.figure(figsize=(20, 14), facecolor="#0d1117")
    gs  = gridspec.GridSpec(3, 2, figure=fig,
                            hspace=0.45, wspace=0.3,
                            left=0.06, right=0.97,
                            top=0.93, bottom=0.06)

    accent = "#00d4aa"
    red    = "#ff4d6d"
    yellow = "#ffd60a"
    gray   = "#8b949e"

    # ── 1. Precio + EMAs + señales ──────────────────────
    ax1 = fig.add_subplot(gs[0, :])
    ax1.set_facecolor("#161b22")
    ax1.plot(df.index, df["Close"],  color="#58a6ff", lw=0.8, label="Precio", zorder=2)
    ax1.plot(df.index, df["ema50"],  color=yellow,    lw=1.2, label="EMA 50", zorder=3)
    ax1.plot(df.index, df["ema200"], color=red,       lw=1.2, label="EMA 200", zorder=3)

    if not trades_df.empty and "entry_date" in trades_df.columns:
        longs  = trades_df[trades_df["direction"] ==  1]
        shorts = trades_df[trades_df["direction"] == -1]
        for _, t in longs.drop_duplicates("entry_date").iterrows():
            ax1.axvline(t["entry_date"], color=accent, alpha=0.25, lw=0.6)
        for _, t in shorts.drop_duplicates("entry_date").iterrows():
            ax1.axvline(t["entry_date"], color=red, alpha=0.25, lw=0.6)

    ax1.set_title(f"Precio + EMAs  ·  {symbol}", color="white", fontsize=13, pad=8)
    ax1.tick_params(colors=gray)
    ax1.spines[:].set_color("#30363d")
    ax1.legend(facecolor="#161b22", edgecolor="#30363d", labelcolor="white", fontsize=8)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))

    # ── 2. RSI ──────────────────────────────────────────
    ax2 = fig.add_subplot(gs[1, :])
    ax2.set_facecolor("#161b22")
    ax2.plot(df.index, df["rsi"], color="#7ee787", lw=0.8, label="RSI 14")
    ax2.axhline(70, color=red,    ls="--", lw=0.7, alpha=0.7)
    ax2.axhline(30, color=accent, ls="--", lw=0.7, alpha=0.7)
    ax2.axhline(50, color=gray,   ls=":",  lw=0.5, alpha=0.5)
    ax2.fill_between(df.index, 30, 70, alpha=0.04, color="white")
    ax2.set_ylim(0, 100)
    ax2.set_title("RSI 14", color="white", fontsize=11, pad=6)
    ax2.tick_params(colors=gray)
    ax2.spines[:].set_color("#30363d")
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))

    # ── 3. Curva de equity ──────────────────────────────
    ax3 = fig.add_subplot(gs[2, 0])
    ax3.set_facecolor("#161b22")
    eq = equity_df["capital"]
    ax3.plot(eq.index, eq.values, color=accent, lw=1.4, label="Capital")
    ax3.fill_between(eq.index, eq.values, eq.values.min(),
                     color=accent, alpha=0.08)
    ax3.axhline(metrics["capital_inicial"], color=gray, ls="--", lw=0.8)

    color_ret = accent if metrics["retorno_total_%"] >= 0 else red
    ax3.set_title(f"Curva de Equity  |  Retorno: {metrics['retorno_total_%']}%",
                  color=color_ret, fontsize=11, pad=6)
    ax3.tick_params(colors=gray)
    ax3.spines[:].set_color("#30363d")
    ax3.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))

    # ── 4. Tabla de métricas ────────────────────────────
    ax4 = fig.add_subplot(gs[2, 1])
    ax4.set_facecolor("#161b22")
    ax4.axis("off")

    metric_rows = [
        ("Capital inicial",    f"${metrics['capital_inicial']:,.2f}"),
        ("Capital final",      f"${metrics['capital_final']:,.2f}"),
        ("Retorno total",      f"{metrics['retorno_total_%']}%"),
        ("Operaciones",        str(metrics["n_operaciones"])),
        ("Win Rate",           f"{metrics['win_rate_%']}%"),
        ("Profit Factor",      str(metrics["profit_factor"])),
        ("Max Drawdown",       f"{metrics['max_drawdown_%']}%"),
        ("Expectativa",        f"${metrics['expectativa_$']:,.2f}"),
        ("Sharpe Ratio",       str(metrics["sharpe_ratio"])),
        ("Longs / Shorts",     f"{metrics['longs']} / {metrics['shorts']}"),
    ]

    y_pos = 0.96
    for label, value in metric_rows:
        ax4.text(0.05, y_pos, label, transform=ax4.transAxes,
                 color=gray, fontsize=9.5, va="top")
        ax4.text(0.65, y_pos, value, transform=ax4.transAxes,
                 color="white", fontsize=9.5, va="top", fontweight="bold")
        y_pos -= 0.095

    ax4.set_title("Métricas del Backtest", color="white", fontsize=11, pad=6)

    # ── título global ────────────────────────────────────
    fig.suptitle(f"Backtest · Estrategia Multi-Timeframe  ·  {symbol}",
                 color="white", fontsize=15, fontweight="bold", y=0.975)

    plt.savefig(save_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    print(f"\n[Chart] Guardado en: {save_path}")
    return fig


# ──────────────────────────────────────────────────────────
# 7.  CLI PRINCIPAL
# ──────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(
        description="Backtesting – Estrategia Multi-Timeframe Forex/Crypto",
        formatter_class=argparse.RawTextHelpFormatter
    )
    p.add_argument("--source",   choices=["yfinance", "oanda"], required=True,
                   help="Fuente de datos: yfinance | oanda")
    p.add_argument("--symbol",   required=True,
                   help="Par o ticker (ej. EUR_USD, BTC-USD, EURUSD=X)")
    p.add_argument("--start",    default="2023-01-01",
                   help="Fecha inicio YYYY-MM-DD  (default: 2023-01-01)")
    p.add_argument("--end",      default=datetime.today().strftime("%Y-%m-%d"),
                   help="Fecha fin   YYYY-MM-DD  (default: hoy)")
    p.add_argument("--interval", default="1h",
                   help="Intervalo yfinance: 1h, 4h, 1d …  (default: 1h)")
    p.add_argument("--granularity", default="H1",
                   help="Granularidad OANDA: M15, H1, H4, D …  (default: H1)")
    p.add_argument("--capital",  type=float, default=10_000,
                   help="Capital inicial en USD  (default: 10000)")
    p.add_argument("--risk",     type=float, default=0.01,
                   help="Riesgo por operación 0-1  (default: 0.01 = 1%%)")
    p.add_argument("--oanda-key", default=None,
                   help="API key de OANDA (o usa OANDA_API_KEY)")
    p.add_argument("--oanda-env", default="practice", choices=["practice","live"],
                   help="Entorno OANDA  (default: practice)")
    p.add_argument("--output",   default="backtest_results.png",
                   help="Ruta del gráfico de salida")
    p.add_argument("--no-plot",  action="store_true",
                   help="Omitir la generación del gráfico")
    return p.parse_args()


def main():
    args = parse_args()

    # ── carga de datos ───────────────────────────────────
    if args.source == "yfinance":
        df_raw = load_yfinance(args.symbol, args.start, args.end, args.interval)
    else:
        df_raw = load_oanda(args.symbol, args.start, args.end,
                            granularity=args.granularity,
                            api_key=args.oanda_key,
                            account_type=args.oanda_env)

    # ── indicadores ──────────────────────────────────────
    print("[INFO] Calculando indicadores técnicos...")
    df = compute_indicators(df_raw)

    # ── señales ──────────────────────────────────────────
    print("[INFO] Generando señales de trading...")
    df = generate_signals(df)
    total_signals = (df["signal"] != 0).sum()
    longs  = (df["signal"] ==  1).sum()
    shorts = (df["signal"] == -1).sum()
    print(f"[INFO] Señales encontradas: {total_signals}  (LONG={longs}, SHORT={shorts})")

    # ── backtest ─────────────────────────────────────────
    print("[INFO] Ejecutando backtesting...")
    engine = BacktestEngine(
        initial_capital=args.capital,
        risk_pct=args.risk,
    )
    equity_df, trades_df = engine.run(df)

    # ── métricas ─────────────────────────────────────────
    metrics = compute_metrics(equity_df, trades_df, args.capital)

    print("\n" + "═"*52)
    print("  RESULTADOS DEL BACKTEST")
    print("═"*52)
    for k, v in metrics.items():
        if k == "error":
            print(f"  ⚠  {v}")
            continue
        label = k.replace("_", " ").title()
        print(f"  {label:<26} {v}")
    print("═"*52 + "\n")

    # ── validación métricas ideales PDF ─────────────────
    if "win_rate_%" in metrics:
        wr = metrics["win_rate_%"]
        pf = metrics["profit_factor"]
        print("  Métricas objetivo (PDF):")
        print(f"    Win Rate > 40%      → {'✅' if wr>40 else '❌'}  ({wr}%)")
        print(f"    Profit Factor > 1.5 → {'✅' if pf>1.5 else '❌'}  ({pf})")
        print()

    # ── gráficos ─────────────────────────────────────────
    if not args.no_plot:
        plot_results(df, equity_df, trades_df, metrics,
                     symbol=args.symbol,
                     save_path=args.output)

    # ── exportar trades ──────────────────────────────────
    if not trades_df.empty:
        csv_path = args.output.replace(".png", "_trades.csv")
        trades_df.to_csv(csv_path, index=False)
        print(f"[CSV]   Trades exportados: {csv_path}")


if __name__ == "__main__":
    main()
