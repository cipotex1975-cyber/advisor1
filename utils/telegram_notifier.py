import requests
import sys

def send_telegram_message(bot_token: str, chat_id: str, message: str) -> bool:
    """
    Envía un mensaje usando la API HTTP de Telegram.
    Retorna True si fue exitoso, False de lo contrario.
    """
    if not bot_token or not chat_id:
        print("[Telegram] ADVERTENCIA: Token o Chat ID no configurados. Omitiendo mensaje.")
        return False
        
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        print("[Telegram] ✅ Mensaje enviado correctamente.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"[Telegram] ❌ Error enviando mensaje: {e}")
        return False
