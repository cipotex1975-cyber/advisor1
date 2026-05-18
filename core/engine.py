import pandas as pd
from typing import Tuple

class BacktestEngine:
    """
    Simula la ejecución de las señales con gestión de capital
    profesional: 1 % de riesgo por operación, máximo 3 simultáneas,
    drawdown diario 3 %, semanal 6 %.
    """

    def __init__(self,
                 initial_capital: float = 10_000,
                 risk_pct: float = 0.005,
                 max_simultaneous: int = 3,
                 max_dd_daily: float = 0.02,
                 max_dd_weekly: float = 0.05,
                 max_dd_global: float = 0.15,
                 tp_levels: list = None):
        self.initial_capital  = initial_capital
        self.risk_pct         = risk_pct
        self.max_simultaneous = max_simultaneous
        self.max_dd_daily     = max_dd_daily
        self.max_dd_weekly    = max_dd_weekly
        self.max_dd_global    = max_dd_global
        # Fracciones del take-profit parcial
        self.tp_levels = tp_levels or [
            (1.0, 0.33),   # TP1 → cierre 33 %
            (2.0, 0.33),   # TP2 → cierre 33 %
            (3.0, 0.34),   # TP3 → cierre 34 %
        ]

    def _position_size(self, capital: float, entry: float, stop: float) -> float:
        risk_amount = capital * self.risk_pct
        distance    = abs(entry - stop)
        if distance == 0:
            return 0
        return risk_amount / distance

    def run(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        capital    = self.initial_capital
        equity     = []
        trades     = []
        open_pos   = []

        week_start_cap = capital
        day_start_cap  = capital
        peak_capital   = capital
        current_day    = None
        current_week   = None
        blocked_day    = False
        blocked_week   = False
        blocked_global = False

        price_array = df["Close"].values
        high_array  = df["High"].values
        low_array   = df["Low"].values
        dates       = df.index

        trade_id_counter = 1

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
            if capital > peak_capital:
                peak_capital = capital
                
            dd_global = (capital - peak_capital) / peak_capital
            dd_day  = (capital - day_start_cap)  / day_start_cap
            dd_week = (capital - week_start_cap) / week_start_cap
            
            if dd_global <= -self.max_dd_global:
                blocked_global = True
            if dd_day  <= -self.max_dd_daily:
                blocked_day  = True
            if dd_week <= -self.max_dd_weekly:
                blocked_week = True

            # ── abrir nuevas posiciones ──────────────────
            if (not blocked_global and not blocked_day and not blocked_week and
                    len(open_pos) < self.max_simultaneous):

                row = df.iloc[idx]
                sig = row["signal"]

                if sig != 0 and not pd.isna(row["entry_price"]):
                    size = self._position_size(capital, row["entry_price"], row["stop_loss"])
                    if size > 0:
                        pos = {
                            "trade_id":   trade_id_counter,
                            "direction":  int(sig),
                            "entry":      row["entry_price"],
                            "stop":       row["stop_loss"],
                            "tp1":        row["take_profit1"],
                            "tp2":        row["take_profit2"],
                            "tp3":        row["take_profit3"],
                            "size":       size,
                            "orig_size":  size,
                            "entry_date": dt,
                            "entry_reason": row.get("entry_reason", "")
                        }
                        open_pos.append(pos)
                        trade_id_counter += 1

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
