# Resumen de Cambios: Estrategia Modular y Documentación

## Cambios Realizados

1. **Modularización del Sistema**:
   Hemos descompuesto el monolito `backtesting_strategy.py` en 7 archivos distintos, separando responsabilidades:
   - [data_loader.py](file:///c:/Users/ceavalos/Documents/github/Estretegia_ia1/files/data_loader.py)
   - [indicators.py](file:///c:/Users/ceavalos/Documents/github/Estretegia_ia1/files/indicators.py)
   - [signals.py](file:///c:/Users/ceavalos/Documents/github/Estretegia_ia1/files/signals.py)
   - [engine.py](file:///c:/Users/ceavalos/Documents/github/Estretegia_ia1/files/engine.py)
   - [metrics.py](file:///c:/Users/ceavalos/Documents/github/Estretegia_ia1/files/metrics.py)
   - [visualization.py](file:///c:/Users/ceavalos/Documents/github/Estretegia_ia1/files/visualization.py)
   - [main.py](file:///c:/Users/ceavalos/Documents/github/Estretegia_ia1/files/main.py)

2. **Caché en CSV**:
   La carga de datos ahora revisa si un archivo local con los mismos parámetros existe antes de contactar a `yfinance` o a la API de `OANDA`. En caso de descargar información nueva, esta se guardará automáticamente en formato CSV para reducir el tiempo de ejecución de las pruebas posteriores.

3. **Gráficos Individuales de Operaciones**:
   Se implementó la función `plot_trade` en el módulo de visualización. Ahora el script creará un directorio llamado `trade_charts` donde se generará un gráfico `.png` por cada operación, enfocado específicamente en el momento de entrada, la evolución del precio, los retrocesos a los EMAs, el Take Profit y el Stop Loss, indicando si el trade fue un *WIN* o *LOSS*.

4. **Creación del Manual de Proyecto**:
   Añadí el archivo `MANUAL.md`, el cual sirve de guía de inicio rápido y manual de referencia. Contiene ejemplos de comandos por consola, explicaciones de la nueva arquitectura y una lista de argumentos aceptados.

## Notas Adicionales
> [!NOTE]
> Dado que la modularización fue exitosa, el archivo original `backtesting_strategy.py` puede ser eliminado cuando lo consideres seguro. No lo he borrado automáticamente para que puedas comparar si lo deseas.

> [!TIP]
> Si en algún momento no deseas generar todas las imágenes de cada operación para un backtest muy largo, puedes usar el flag `--no-trades` al ejecutar `main.py`.
