# Manual del Bot en Vivo (Alertas por Telegram)

Este manual te guiará para configurar tu bot y que empiece a buscar señales en el mercado real cada 15 minutos, enviando notificaciones directamente a tu teléfono a través de Telegram.

## 1. Configurar tu Bot de Telegram

Para que el programa pueda enviarte mensajes, necesitas crear un "Bot" en Telegram y obtener tu "Chat ID".

### Paso A: Crear el Bot
1. Abre Telegram y busca al usuario **@BotFather** (el oficial tiene un check azul).
2. Envíale el comando `/newbot`.
3. Sigue las instrucciones para darle un nombre y un usuario a tu bot (ej. `mi_estrategia_bot`).
4. Al finalizar, BotFather te dará un **Token HTTP API** (es una cadena larga como `123456789:ABCdefGhIJKlmNoPQRstuVwXyz`). **Guarda este token**.

### Paso B: Obtener tu Chat ID
1. Busca tu nuevo bot en Telegram (por el usuario que le asignaste) y presiona "Iniciar" (o envíale cualquier mensaje como "Hola").
2. Abre tu navegador web y visita la siguiente URL, reemplazando `<TU_TOKEN>` con el token que guardaste:
   `https://api.telegram.org/bot<TU_TOKEN>/getUpdates`
3. Verás una respuesta en formato de texto o JSON. Busca el apartado `"chat":{"id": 123456789}`. Ese número (ej. `123456789`) es tu **Chat ID**. **Guárdalo**.

---

## 2. Ejecutar el Bot en Tu Computadora

Una vez que tengas tu Token y tu Chat ID, abre la terminal o consola de comandos en la carpeta de tu proyecto. Tienes dos formas de ejecutar el bot:

### Modo Continuo (Recomendado para pruebas rápidas)
En este modo, el script se quedará "abierto" y pausado. Cuando el reloj de tu sistema llegue al minuto 01, 16, 31 o 46 de la hora, el bot se despertará, descargará los datos y verificará si hay señal.

```bash
python live_bot.py --source yfinance --symbols EURUSD=X USDCAD=X USDJPY=X --telegram-token "TU_TOKEN" --telegram-chat "TU_CHAT_ID"
```
*(Nota: Si cierras la terminal o apagas la computadora, el bot se detendrá).*

### Modo de Una Sola Vez (Ideal para Tareas Programadas / Servidores)
Si quieres usar el *Programador de Tareas* de Windows o `Cron` en Linux para que ellos se encarguen de despertar al script cada 15 minutos, debes ejecutarlo con el argumento `--run-once`.

```bash
python live_bot.py --source yfinance --symbols EURUSD=X USDCAD=X USDJPY=X --telegram-token "TU_TOKEN" --telegram-chat "TU_CHAT_ID" --run-once
```
En este modo, el bot verifica los datos inmediatamente, envía la notificación si existe, y el script termina.

---

## 3. Ejemplo de Notificación

Cuando el sistema detecte la configuración perfecta (1D: Tendencia EMAs, 4H: Contexto, 15m: Gatillo de rechazo y pullback) respetando las restricciones de riesgo y volatilidad, recibirás un mensaje así en tu Telegram:

> 🚨 **NUEVA SEÑAL MULTI-TF DETECTADA** 🚨
> 
> 🪙 **Activo:** EURUSD=X
> ⏱ **Hora de Cierre:** 2024-05-17 15:15:00 UTC
> 📈 **Dirección:** LONG 🟢
> 
> 🎯 **Entrada:** `1.08500`
> 🛑 **Stop Loss (ATR basado):** `1.08250`
> ✅ **TP 1:** `1.08750`
> ✅ **TP 2:** `1.09000`
> 
> ⚠️ _Razón: {"macro_trend": "bullish", "rejection_candle": true...}_

---

## 4. Despliegue en Servidor VPS (Siguiente Paso)

Cuando estés feliz con los resultados del simulador, querrás alquilar un Servidor Privado Virtual (VPS) muy barato (ej. AWS EC2 t2.micro, DigitalOcean Droplet de $4/mes, o Contabo). 

1. Subes esta misma carpeta al servidor (es recomendable usar GitHub).
2. Instalas Python y las librerías (`pip install -r requirements.txt`).
3. Ejecutas el comando de **Modo Continuo** dentro de un `screen` o `tmux` para que siga corriendo aunque cierres tu conexión con el servidor. ¡Y listo! Tendrás tu bot monitoreando el mercado 24/7 sin gastar batería de tu computadora.
