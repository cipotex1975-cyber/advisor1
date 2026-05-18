# Backtesting – Estrategia Multi-Timeframe Forex & Crypto

Sistema de backtesting basado en el documento **"Estrategia Profesional de Trading Multi-Timeframe"**.

---

## Instalación de dependencias

```bash
pip install pandas numpy matplotlib yfinance
# Si usas OANDA o FXCM:
pip install oandapyV20 fxcmpy
```

---

## Uso desde la terminal

### Con yfinance (más fácil, sin cuenta)

```bash
# Ejemplo: EUR/USD Multi-Timeframe (descarga auto de 1d, 4h, 1h, 15m), 2023-2024
python main.py \
  --source yfinance \
  --symbol "EURUSD=X" \
  --start 2023-01-01 \
  --end   2024-12-31 \
  --capital 10000 \
  --mode both

# Bitcoin (BTC) solo longs
python main.py \
  --source yfinance \
  --symbol "BTC-USD" \
  --start 2023-06-01 \
  --end   2024-06-01 \
  --capital 10000 \
  --mode long
```

### Con OANDA

```bash
# Requiere API key de OANDA (cuenta demo gratuita)
python main.py \
  --source oanda \
  --symbol "EUR_USD" \
  --start 2023-01-01 \
  --end   2024-12-31 \
  --oanda-key TU_API_KEY \
  --oanda-env practice \
  --capital 10000 \
  --mode both
```

### Con FXCM

```bash
# Requiere credenciales de FXCM
python main.py \
  --source fxcm \
  --symbol "EUR/USD" \
  --start 2023-01-01 \
  --end   2024-12-31 \
  --fxcm-user TU_USUARIO \
  --fxcm-pass TU_PASSWORD \
  --capital 10000 \
  --mode both
```

### Con Dukascopy

```bash
# Datos históricos gratuitos (descarga y procesa archivos .bi5 automáticamente)
python main.py \
  --source dukascopy \
  --symbol "EURUSD" \
  --start 2023-01-01 \
  --end   2023-02-01 \
  --capital 10000 \
  --mode both
```

---

## Parámetros completos

| Parámetro        | Descripción                                    | Defecto        |
|------------------|------------------------------------------------|----------------|
| `--source`       | `yfinance`, `oanda`, `fxcm` o `dukascopy`      | requerido      |
| `--symbol`       | Ticker o par (ver dependencias de formato)     | requerido      |
| `--start`        | Fecha inicio `YYYY-MM-DD`                      | `2024-01-01`   |
| `--end`          | Fecha fin    `YYYY-MM-DD`                      | hoy            |
| `--capital`      | Capital inicial en USD                         | `10000`        |
| `--risk`         | Riesgo por operación (0–1)                     | `0.01` (1%)    |
| `--mode`         | Modo de estrategia: `long`, `short` o `both`   | `both`         |
| `--oanda-key`    | API key de OANDA                               | `OANDA_API_KEY`|
| `--fxcm-user`    | Usuario de FXCM                                | `FXCM_USER`    |
| `--fxcm-pass`    | Contraseña de FXCM                             | `FXCM_PASS`    |
| `--oanda-env`    | Entorno OANDA (`practice` / `live`)            | `practice`     |
| `--fxcm-env`     | Entorno FXCM (`demo` / `real`)                 | `demo`         |
| `--output`       | Ruta del gráfico PNG global                    | `backtest_results.png` |
| `--no-plot`      | Omitir generación del gráfico global           | —              |
| `--no-trades`    | Omitir la generación de gráficos individuales  | —              |

---

## Formato de Símbolos por Fuente

| Fuente     | Formato Típico | Ejemplo     |
|------------|----------------|-------------|
| yFinance   | `BASEQUOTE=X`  | `EURUSD=X`  |
| OANDA      | `BASE_QUOTE`   | `EUR_USD`   |
| FXCM       | `BASE/QUOTE`   | `EUR/USD`   |
| Dukascopy  | `BASEQUOTE`    | `EURUSD`    |

---

## Archivos y Directorios Generados

El bot crea automáticamente una estructura limpia:
- `/data/{symbol}/` — Guarda los CSV (15m.csv, 1h.csv, 4h.csv, 1d.csv) deduplicados.
- `/charts/{symbol}/` — Gráficos individuales de cada trade analizado con 2 paneles (Precio y ATR/Spread).
- `/logs/trades.csv` — Registro detallado de todas las operaciones y la justificación JSON (`entry_reason`).
- `/reports`, `/backtests`, `/strategies` — Carpetas reservadas para expansiones futuras.

---

## Reglas de la estrategia implementadas

- **Contexto Macro (1D):** EMA50 > EMA200 (Long) o EMA50 < EMA200 (Short).
- **Estructura (4H):** Precio por encima de EMA50 (Long) o por debajo de EMA50 (Short).
- **Gatillo (15m):** Vela de rechazo con mecha clara + pullback previo.
- **Stop Loss:** Calculado de forma dinámica usando la estructura de 15m/1H con un colchón basado en el **ATR de 15m**. Nunca stops fijos.
- **Take Profit:** Parcial en niveles 1:1, 1:2, 1:3.
- **Gestión Institucional de Riesgo:**
  - Máximo 0.5% de riesgo por operación.
  - Drawdown diario máximo: 2%.
  - Drawdown semanal máximo: 5%.
  - Drawdown global absoluto máximo: 15%.
  - Máximo 3 operaciones simultáneas.
