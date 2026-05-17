# Backtesting – Estrategia Multi-Timeframe Forex & Crypto

Sistema de backtesting basado en el documento **"Estrategia Profesional de Trading Multi-Timeframe"**.

---

## Instalación de dependencias

```bash
pip install pandas numpy matplotlib yfinance
# Solo si usas OANDA:
pip install oandapyV20
```

---

## Uso desde la terminal

### Con yfinance (más fácil, sin cuenta)

```bash
# Ejemplo: EUR/USD horario, 2023-2024
python backtesting_strategy.py \
  --source yfinance \
  --symbol "EURUSD=X" \
  --start 2023-01-01 \
  --end   2024-12-31 \
  --interval 1h \
  --capital 10000

# Bitcoin (BTC) horario
python backtesting_strategy.py \
  --source yfinance \
  --symbol "BTC-USD" \
  --start 2023-06-01 \
  --end   2024-06-01 \
  --capital 10000

# Oro (XAU) diario
python backtesting_strategy.py \
  --source yfinance \
  --symbol "GC=F" \
  --start 2022-01-01 \
  --end   2024-01-01 \
  --interval 1d \
  --capital 50000
```

### Con OANDA

```bash
# Requiere API key de OANDA (cuenta demo gratuita)
python backtesting_strategy.py \
  --source oanda \
  --symbol "EUR_USD" \
  --start 2023-01-01 \
  --end   2024-12-31 \
  --granularity H1 \
  --oanda-key TU_API_KEY \
  --oanda-env practice \
  --capital 10000
```

---

## Parámetros completos

| Parámetro        | Descripción                                    | Defecto        |
|------------------|------------------------------------------------|----------------|
| `--source`       | `yfinance` o `oanda`                           | requerido      |
| `--symbol`       | Ticker o par (ver tabla abajo)                 | requerido      |
| `--start`        | Fecha inicio `YYYY-MM-DD`                      | `2023-01-01`   |
| `--end`          | Fecha fin    `YYYY-MM-DD`                      | hoy            |
| `--interval`     | Intervalo yfinance (`1h`, `4h`, `1d` …)        | `1h`           |
| `--granularity`  | Granularidad OANDA (`H1`, `H4`, `D` …)         | `H1`           |
| `--capital`      | Capital inicial en USD                         | `10000`        |
| `--risk`         | Riesgo por operación (0–1)                     | `0.01` (1%)    |
| `--oanda-key`    | API key de OANDA                               | `OANDA_API_KEY`|
| `--oanda-env`    | Entorno OANDA (`practice` / `live`)            | `practice`     |
| `--output`       | Ruta del gráfico PNG                           | `backtest_results.png` |
| `--no-plot`      | Omitir generación del gráfico                  | —              |

---

## Símbolos de ejemplo

### yfinance
| Instrumento | Símbolo yfinance |
|-------------|-----------------|
| EUR/USD     | `EURUSD=X`      |
| GBP/USD     | `GBPUSD=X`      |
| USD/JPY     | `USDJPY=X`      |
| BTC/USD     | `BTC-USD`       |
| ETH/USD     | `ETH-USD`       |
| Oro         | `GC=F`          |
| S&P 500     | `^GSPC`         |

### OANDA
| Instrumento | Símbolo OANDA |
|-------------|---------------|
| EUR/USD     | `EUR_USD`     |
| GBP/USD     | `GBP_USD`     |
| USD/JPY     | `USD_JPY`     |
| BTC/USD     | `BTC_USD`     |
| XAU/USD     | `XAU_USD`     |

---

## Archivos generados

- `backtest_results.png` — Dashboard con 4 gráficos: precio + EMAs, RSI, curva de equity, métricas
- `backtest_results_trades.csv` — Registro detallado de todas las operaciones

---

## Métricas calculadas

- Capital inicial / final
- Retorno total %
- Número de operaciones
- Win Rate %
- Profit Factor
- Máximo Drawdown %
- Expectativa matemática ($)
- Sharpe Ratio
- Desglose longs / shorts

**Umbrales objetivo del PDF:**
- Win Rate > 40 %
- Profit Factor > 1.5

---

## Reglas de la estrategia implementadas

- Confirmación con EMA 50 y EMA 200
- Señal LONG / SHORT con retroceso hacia EMA 50 (tolerancia ±0.2%)
- RSI filtrado entre 35–65
- Stop Loss dinámico basado en mínimo/máximo estructural reciente
- Take Profit parcial en 1:1 (33%), 1:2 (33%), 1:3 (34%)
- Máximo 1% de riesgo por operación
- Máximo 3 operaciones simultáneas
- Drawdown diario máximo: 3%
- Drawdown semanal máximo: 6%
- Move to breakeven en TP1
