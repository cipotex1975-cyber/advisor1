# Manual del Proyecto: Estrategia de Trading Multi-Timeframe

Bienvenido al sistema de backtesting modular. Este manual te guiará sobre la estructura del proyecto y cómo ejecutar la estrategia de trading utilizando el orquestador principal.

## 1. Estructura del Proyecto

El sistema ha sido dividido en una arquitectura de subdirectorios para facilitar su mantenimiento y escalabilidad:

- **`main.py`**: El punto de entrada principal (Orquestador). Une todas las piezas, orquesta las descargas de los 4 timeframes, invoca el backtest y genera los reportes/gráficos.
- **`data/data_loader.py`**: Encargado de descargar los datos financieros de 1D, 4H, 1H y 15m. Estandariza los nombres de las columnas para evitar conflictos entre `yfinance` y `oandapyV20`, y guarda cachés locales de cada timeframe.
- **`strategy/indicators.py`**: Contiene la lógica para calcular indicadores técnicos (EMA 50, 200, RSI, VWAP) y la función crucial `align_timeframes` que proyecta los valores de las temporalidades mayores al gráfico de 15m evitando sesgos de "ver el futuro" (*look-ahead bias*).
- **`strategy/signals.py`**: Motor de toma de decisiones. Evalúa simultáneamente la tendencia Diaria, el contexto y retrocesos en 4H, la ruptura estructural en 1H y el patrón de confirmación (gatillo) en 15m para emitir una señal perfecta.
- **`core/engine.py`**: El motor de backtesting. Simula la ejecución de las señales en la temporalidad base (15m) aplicando gestión institucional de riesgo (máximo riesgo, drawdown).
- **`core/metrics.py`**: Analiza los resultados generados por el motor y calcula métricas clave de rentabilidad.
- **`utils/visualization.py`**: Genera gráficos del dashboard general y el detalle individual por cada trade mostrando la confluencia de indicadores de distintos timeframes.

## 2. Archivos y Estructura Generada

Al ejecutar el sistema, se generará una estructura limpia:

1. **Datos CSV (Caché)**: Se guardan en `data/{symbol}/15m.csv` (y los otros TFs) automáticamente con deduplicación.
2. **Dashboard Global**: `backtest_results.png` en el directorio principal o donde indiques.
3. **Reporte de Operaciones (CSV)**: `logs/trades.csv`. Un registro detallado de todas las posiciones tomadas y la justificación (`entry_reason`) en JSON.
4. **Gráficos Individuales por Operación**: Se guardan en el directorio `charts/{symbol}/`. Verás una imagen PNG por cada trade con un panel principal (precio, EMAs, entry/stop) y un panel inferior (ATR y spread estimado).

## 3. Cómo Ejecutar el Sistema

Debes ejecutar el archivo `main.py` desde la línea de comandos utilizando Python (o `py` en algunos entornos Windows).

### Parámetros Disponibles

- `--source`: **Requerido**. Puede ser `yfinance`, `oanda`, `fxcm` o `alphavantage`.
- `--symbol`: **Requerido**. El par o ticker a procesar (ej. `EURUSD=X`, `BTC-USD`).
- `--start`: Fecha de inicio en formato `YYYY-MM-DD` (por defecto `2024-01-01`).
- `--end`: Fecha de fin en formato `YYYY-MM-DD` (por defecto es hoy).
- `--capital`: Capital inicial en USD (por defecto `10000`).
- `--risk`: Riesgo base inicial, actualmente sobreescrito a institucional (0.005 o 0.5% por operación).
- `--mode`: Modo de operación de la estrategia: `long`, `short`, o `both` (por defecto `both`).
- `--output`: Nombre del archivo de imagen con los resultados globales (por defecto `backtest_results.png`).
- `--no-plot`: Oculta la generación del gráfico general.
- `--no-trades`: Oculta la generación de los gráficos individuales por operación.
- `--alphavantage-key`: API key de Alpha Vantage (o puedes usar la variable de entorno `ALPHAVANTAGE_API_KEY`).

### Ejemplos de Uso

**Ejemplo 1: Ejecución básica con yFinance (Forex - Solo Longs)**
```bash
python main.py --source yfinance --symbol EURUSD=X --start 2024-01-01 --mode long
```

**Ejemplo 2: Ejecución para Criptomonedas (Ambas direcciones)**
```bash
python main.py --source yfinance --symbol BTC-USD --start 2023-06-01 --capital 50000 --mode both
```

**Ejemplo 3: Ejecución usando OANDA**
*(Requiere que tengas configurada la variable de entorno `OANDA_API_KEY` o que la pases como parámetro).*
```bash
python main.py --source oanda --symbol EUR_USD --oanda-key "TU_API_KEY"
```

**Ejemplo 4: Ejecución rápida sin generar imágenes individuales (solo resultados y CSV en logs/)**
```bash
python main.py --source yfinance --symbol GBPUSD=X --no-trades
```

**Ejemplo 5: Ejecución usando FXCM**
*(Requiere que tengas configuradas las variables de entorno `FXCM_USER` y `FXCM_PASS` o que las pases como parámetro).*
```bash
python main.py --source fxcm --symbol EUR/USD --fxcm-user "TU_USUARIO" --fxcm-pass "TU_PASSWORD"
```

**Ejemplo 6: Ejecución usando Alpha Vantage**
*(Requiere que tengas configurada la variable de entorno `ALPHAVANTAGE_API_KEY` o que la pases como parámetro).*
```bash
python main.py --source alphavantage --symbol EURUSD --alphavantage-key "TU_API_KEY"
```

## 4. Notas Adicionales

- El orquestador descargará e interpolará los 4 timeframes de manera asíncrona pero determinista para evitar ver el futuro.
- El log principal estará siempre vivo en `logs/trades.csv`, que puedes abrir en Excel o Google Sheets para realizar una auditoría de por qué se tomó cada entrada basándote en la columna `entry_reason`.
