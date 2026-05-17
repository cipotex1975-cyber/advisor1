import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.dates as mdates

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
    
    # Plot 15m close
    ax1.plot(df.index, df["Close"],  color="#58a6ff", lw=0.8, label="Precio (15m)", zorder=2)
    
    if "ema50_4h" in df.columns:
        ax1.plot(df.index, df["ema50_4h"],  color=yellow,    lw=1.5, label="EMA 50 (4H)", zorder=3)
    if "ema200_1d" in df.columns:
        ax1.plot(df.index, df["ema200_1d"], color=red,       lw=1.5, label="EMA 200 (1D)", zorder=3)

    if not trades_df.empty and "entry_date" in trades_df.columns:
        longs  = trades_df[trades_df["direction"] ==  1]
        shorts = trades_df[trades_df["direction"] == -1]
        for _, t in longs.drop_duplicates("entry_date").iterrows():
            ax1.axvline(t["entry_date"], color=accent, alpha=0.4, lw=0.8)
        for _, t in shorts.drop_duplicates("entry_date").iterrows():
            ax1.axvline(t["entry_date"], color=red, alpha=0.4, lw=0.8)

    ax1.set_title(f"Precio (15m) + EMAs Multi-TF  ·  {symbol}", color="white", fontsize=13, pad=8)
    ax1.tick_params(colors=gray)
    ax1.spines[:].set_color("#30363d")
    ax1.legend(facecolor="#161b22", edgecolor="#30363d", labelcolor="white", fontsize=9)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))

    # ── 2. RSI ──────────────────────────────────────────
    ax2 = fig.add_subplot(gs[1, :])
    ax2.set_facecolor("#161b22")
    if "rsi_1h" in df.columns:
        ax2.plot(df.index, df["rsi_1h"], color="#7ee787", lw=0.8, label="RSI (1H)")
    else:
        ax2.plot(df.index, df["rsi"], color="#7ee787", lw=0.8, label="RSI (15m)")
        
    ax2.axhline(70, color=red,    ls="--", lw=0.7, alpha=0.7)
    ax2.axhline(30, color=accent, ls="--", lw=0.7, alpha=0.7)
    ax2.axhline(50, color=gray,   ls=":",  lw=0.5, alpha=0.5)
    ax2.fill_between(df.index, 30, 70, alpha=0.04, color="white")
    ax2.set_ylim(0, 100)
    ax2.set_title("RSI Contexto", color="white", fontsize=11, pad=6)
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

    fig.suptitle(f"Backtest · Estrategia Multi-Timeframe  ·  {symbol}",
                 color="white", fontsize=15, fontweight="bold", y=0.975)

    plt.savefig(save_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"\n[Chart] Guardado en: {save_path}")


def plot_trade(df: pd.DataFrame, trade: dict, symbol: str, save_dir: str):
    """Genera un gráfico individual de entrada/salida para una operación."""
    os.makedirs(save_dir, exist_ok=True)
    
    entry_date = trade['entry_date']
    exit_date = trade['exit_date']
    
    # Tomamos un margen antes de la entrada y después de la salida (ej: 100 velas de 15m = 25 horas)
    idx_entry = df.index.get_loc(entry_date)
    idx_exit = df.index.get_loc(exit_date)
    
    start_idx = max(0, idx_entry - 100)
    end_idx = min(len(df) - 1, idx_exit + 100)
    
    df_slice = df.iloc[start_idx:end_idx+1]
    
    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(12, 6), facecolor="#0d1117")
    ax.set_facecolor("#161b22")
    
    ax.vlines(df_slice.index, df_slice['Low'], df_slice['High'], color='#58a6ff', alpha=0.3, linewidth=1)
    ax.plot(df_slice.index, df_slice['Close'], color='#58a6ff', lw=1.2, label='Precio (15m)')
    
    if "ema50_4h" in df.columns:
        ax.plot(df_slice.index, df_slice["ema50_4h"],  color="#ffd60a", lw=1.5, label="EMA 50 (4H)")
    if "ema200_1d" in df.columns:
        ax.plot(df_slice.index, df_slice["ema200_1d"], color="#ff4d6d", lw=1.5, label="EMA 200 (1D)")
    
    ax.axhline(trade['entry'], color='white', linestyle='--', lw=1, label=f"Entry: {trade['entry']:.5f}")
    ax.axhline(trade['stop'], color='#ff4d6d', linestyle='-', lw=1, label=f"SL: {trade['stop']:.5f}")
    
    if not pd.isna(trade['tp1']):
        ax.axhline(trade['tp1'], color='#00d4aa', linestyle='--', lw=0.8, alpha=0.7)
    if not pd.isna(trade['tp2']):
        ax.axhline(trade['tp2'], color='#00d4aa', linestyle='--', lw=0.8, alpha=0.7)
    if not pd.isna(trade['tp3']):
        ax.axhline(trade['tp3'], color='#00d4aa', linestyle='--', lw=0.8, alpha=0.7, label="TPs")

    marker_color = '#00d4aa' if trade['direction'] == 1 else '#ff4d6d'
    marker_label = 'LONG Entry' if trade['direction'] == 1 else 'SHORT Entry'
    
    ax.scatter(entry_date, trade['entry'], color=marker_color, s=100, zorder=5, label=marker_label, marker='^' if trade['direction']==1 else 'v')
    
    pnl_color = '#00d4aa' if trade['pnl'] > 0 else '#ff4d6d'
    ax.scatter(exit_date, df.loc[exit_date, 'Close'], color=pnl_color, s=100, zorder=5, label='Última Salida', marker='o')
    
    trade_type = "LONG" if trade['direction'] == 1 else "SHORT"
    res_str = "WIN" if trade['pnl'] > 0 else "LOSS"
    
    ax.set_title(f"Trade #{trade['trade_id']} | {symbol} | {trade_type} | PnL: {trade['pnl']:.2f} ({res_str})", color="white", fontsize=12, pad=10)
    
    ax.tick_params(colors="#8b949e")
    ax.spines[:].set_color("#30363d")
    ax.legend(facecolor="#161b22", edgecolor="#30363d", labelcolor="white", fontsize=9, loc="best")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M"))
    
    fig.autofmt_xdate()
    
    filename = f"trade_{trade['trade_id']:03d}_{trade_type}_{res_str}.png"
    filepath = os.path.join(save_dir, filename)
    plt.savefig(filepath, dpi=100, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
