import pandas as pd
import numpy as np

def compute_metrics(equity_df: pd.DataFrame,
                    trades_df: pd.DataFrame,
                    initial_capital: float) -> dict:
    """Calcula métricas profesionales de backtesting."""
    if trades_df.empty:
        return {"error": "Sin operaciones registradas."}

    equity = equity_df["capital"]
    returns = equity.pct_change().dropna()

    # filtrar solo cierres completos (SL, TP*) o EOD
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
