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

## 2. Archivos Generados

Al ejecutar el sistema, se generarán varios archivos dependiendo de tus parámetros:

1. **Datos CSV (Caché)**: `data_{symbol}_{interval}_{start}_{end}.csv`. Se guarda automáticamente para acelerar pruebas futuras y se lee si ya existe.
2. **Dashboard de Resultados**: Por defecto `backtest_results.png`. Muestra el gráfico de precio con señales, RSI, curva de equidad y tabla de métricas.
3. **Reporte de Operaciones (CSV)**: `backtest_results_trades.csv`. Un registro detallado de todas las posiciones tomadas.
4. **Gráficos Individuales por Operación**: Se guardan en el directorio `trade_charts/`. Verás una imagen PNG por cada trade con un acercamiento (zoom) a las velas donde ocurrió la entrada y la salida, mostrando los EMAs y el PnL resultante.

## 3. Cómo Ejecutar el Sistema

Debes ejecutar el archivo `main.py` desde la línea de comandos utilizando Python (o `py` en algunos entornos Windows).

### Parámetros Disponibles

- `--source`: **Requerido**. Puede ser `yfinance` u `oanda`.
- `--symbol`: **Requerido**. El par o ticker a procesar (ej. `EURUSD=X`, `BTC-USD`).
- `--start`: Fecha de inicio en formato `YYYY-MM-DD` (por defecto `2023-01-01`).
- `--end`: Fecha de fin en formato `YYYY-MM-DD` (por defecto es hoy).
- `--interval`: Intervalo de tiempo para yfinance (ej. `1h`, `4h`, `1d`). Por defecto `1h`.
- `--granularity`: Granularidad de OANDA (ej. `H1`, `H4`). Por defecto `H1`.
- `--capital`: Capital inicial en USD (por defecto `10000`).
- `--risk`: Porcentaje de riesgo por trade (0 a 1). Ej. `0.01` equivale a 1%.
- `--output`: Nombre del archivo de imagen con los resultados globales (por defecto `backtest_results.png`).
- `--no-plot`: Oculta la generación del gráfico general si solo quieres ver la salida por consola y el CSV.
- `--no-trades`: Oculta la generación de los gráficos individuales por operación para ahorrar espacio y tiempo.
- `--trades-dir`: Define un nombre o ruta alternativa para la carpeta de gráficos individuales (por defecto `trade_charts`).

### Ejemplos de Uso

**Ejemplo 1: Ejecución básica con yFinance (Forex)**
```bash
python main.py --source yfinance --symbol EURUSD=X --start 2024-01-01 --end 2024-03-01 --interval 1h
```

**Ejemplo 2: Ejecución para Criptomonedas con ajustes de capital**
```bash
python main.py --source yfinance --symbol BTC-USD --start 2023-06-01 --capital 50000 --risk 0.02
```

**Ejemplo 3: Ejecución usando OANDA**
*(Requiere que tengas configurada la variable de entorno `OANDA_API_KEY` o que la pases como parámetro).*
```bash
python main.py --source oanda --symbol EUR_USD --granularity H1 --oanda-key "TU_API_KEY"
```

**Ejemplo 4: Ejecución rápida sin generar imágenes individuales (solo resultados)**
```bash
python main.py --source yfinance --symbol GBPUSD=X --no-trades
```

## 4. Notas Adicionales

- Si has ejecutado el sistema previamente y cambias de idea sobre un periodo, recuerda que el caché se guarda por *rango de fecha* e *intervalo*. Si un CSV local cubre exactamente los mismos parámetros, se cargará en milisegundos evitando descargas repetidas.
- Elimina el archivo `backtesting_strategy.py` antiguo de forma manual si ya has validado que el sistema modular funciona correctamente, esto evitará conflictos o confusiones en tu editor.
