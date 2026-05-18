import os
import sys
import time
import argparse
from datetime import datetime, timedelta

import schedule
import pandas as pd

# Añadir subdirectorios al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.data_loader import load_multi_timeframe
from strategy.indicators import align_timeframes
from strategy.signals import generate_signals
from utils.telegram_notifier import send_telegram_message

def get_recent_data(symbol, source, oanda_key, oanda_env, fxcm_key=None):
    """
    Descarga los últimos 300 días de datos para asegurar el cálculo
    correcto de la EMA 200 en temporalidad diaria.
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=300)
    
    start_str = start_date.strftime("%Y-%m-%d")
    # Agregar un día extra a la fecha final para asegurar incluir la vela actual
    end_str = (end_date + timedelta(days=1)).strftime("%Y-%m-%d")
    
    dfs = load_multi_timeframe(
        source=source,
        symbol=symbol,
        start=start_str,
        end=end_str,
        oanda_key=oanda_key,
        oanda_env=oanda_env,
        fxcm_key=fxcm_key
    )
    return dfs

def check_market(symbol, source, oanda_key, oanda_env, tg_token, tg_chat, fxcm_key=None):
    """
    Función central que descarga datos, evalúa la última vela y
    envía notificaciones si existe una señal.
    """
    print(f"\n[{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC] 🔄 Comprobando mercado para {symbol}...")
    
    try:
        # 1. Obtener y alinear datos
        dfs = get_recent_data(symbol, source, oanda_key, oanda_env, fxcm_key=fxcm_key)
        merged_df = align_timeframes(dfs)
        
        if merged_df.empty:
            print("[ERROR] DataFrame vacío. Abortando chequeo.")
            return

        # 2. Generar Señales
        df_signals = generate_signals(merged_df)
        
        # 3. Evaluar LA ÚLTIMA vela de 15m (cerrada)
        # Ojo: dependiendo de la API, la última vela podría estar en formación.
        # Por seguridad, tomamos la penúltima (-2) si sabemos que la -1 aún no cierra,
        # pero yfinance/oanda en este flujo asumen velas estáticas históricas.
        # Asumiremos la última fila disponible con señal.
        
        ultima_vela = df_signals.iloc[-1]
        timestamp = ultima_vela.name
        signal = ultima_vela.get("signal", 0)
        
        if signal != 0:
            direccion = "LONG 🟢" if signal == 1 else "SHORT 🔴"
            entry = ultima_vela['entry_price']
            sl = ultima_vela['stop_loss']
            tp1 = ultima_vela['take_profit1']
            tp2 = ultima_vela['take_profit2']
            
            # Formatear el mensaje
            msg = (
                f"🚨 *NUEVA SEÑAL MULTI-TF DETECTADA* 🚨\n\n"
                f"🪙 *Activo:* {symbol}\n"
                f"⏱ *Hora de Cierre:* {timestamp} UTC\n"
                f"📈 *Dirección:* {direccion}\n\n"
                f"🎯 *Entrada:* `{entry:.5f}`\n"
                f"🛑 *Stop Loss:* `{sl:.5f}`\n"
                f"✅ *TP 1:* `{tp1:.5f}`\n"
                f"✅ *TP 2:* `{tp2:.5f}`\n\n"
                f"⚠️ _Asegúrate de validar la estructura antes de operar._"
            )
            
            print(f"[ALERTA] Señal {direccion} detectada. Enviando a Telegram...")
            send_telegram_message(tg_token, tg_chat, msg)
        else:
            print(f"[INFO] Sin señal en la vela de las {timestamp} UTC.")
            
    except Exception as e:
        print(f"[ERROR] Fallo al comprobar el mercado: {e}")

def main():
    p = argparse.ArgumentParser(description="Bot de Trading en Vivo - Envío de Señales por Telegram")
    p.add_argument("--source", choices=["yfinance", "oanda", "fxcm"], required=True, help="Fuente de datos")
    p.add_argument("--symbols", nargs="+", required=True, help="Lista de símbolos a evaluar separados por espacio (ej. EURUSD=X USDCAD=X USDJPY=X)")
    p.add_argument("--telegram-token", default=os.environ.get("TELEGRAM_BOT_TOKEN", ""), help="Token del Bot de Telegram")
    p.add_argument("--telegram-chat", default=os.environ.get("TELEGRAM_CHAT_ID", ""), help="Tu Chat ID de Telegram")
    p.add_argument("--oanda-key", default=os.environ.get("OANDA_API_KEY", ""), help="API key de OANDA")
    p.add_argument("--fxcm-key", default=os.environ.get("FXCM_API_KEY", ""), help="API key de FXCM")
    p.add_argument("--oanda-env", default="practice", choices=["practice","live"])
    p.add_argument("--run-once", action="store_true", help="Ejecutar una vez y salir (Ideal para Cron)")
    
    args = p.parse_args()
    
    if not args.telegram_token or not args.telegram_chat:
        print("[ADVERTENCIA] No has configurado Telegram. Las señales solo se imprimirán en consola.")
        
    print("==================================================")
    print(f"🤖 BOT EN VIVO INICIADO")
    print(f"📡 Fuente: {args.source.upper()}")
    print(f"🌍 Símbolos monitoreados: {', '.join(args.symbols)}")
    print("==================================================")

    def job_scanner():
        """Función envoltura para escanear todos los pares uno por uno."""
        for sym in args.symbols:
            check_market(sym, args.source, args.oanda_key, args.oanda_env, args.telegram_token, args.telegram_chat, fxcm_key=args.fxcm_key)
            time.sleep(2)  # Pausa breve para evitar saturar la API (Rate Limiting)

    if args.run_once:
        job_scanner()
        sys.exit(0)
        
    # Programar para ejecutarse en cada cuarto de hora
    # Minutos 01, 16, 31 y 46 para dar un minuto de margen a las APIs de cargar el cierre exacto
    schedule.every().hour.at(":01").do(job_scanner)
    schedule.every().hour.at(":16").do(job_scanner)
    schedule.every().hour.at(":31").do(job_scanner)
    schedule.every().hour.at(":46").do(job_scanner)
    
    # Ejecutamos una vez al arrancar para no esperar hasta el siguiente cuarto de hora
    job_scanner()
    
    print("[INFO] Bucle de eventos iniciado. Esperando la siguiente vela...")
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()
