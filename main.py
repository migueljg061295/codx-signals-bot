import os
from flask import Flask, request, jsonify
import telegram

# Cargar variables de entorno
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_FREE = os.getenv("CHANNEL_FREE")
CHANNEL_VIP = os.getenv("CHANNEL_VIP")

# Inicializar bot de Telegram
bot = telegram.Bot(token=BOT_TOKEN)

# Inicializar Flask
app = Flask(__name__)

def send_telegram_message(channel, message):
    try:
        bot.send_message(chat_id=channel, text=message, parse_mode=telegram.ParseMode.MARKDOWN)
        return True
    except Exception as e:
        print(f"Error enviando mensaje a {channel}: {e}")
        return False

# ------------------------
# Rutas Webhook
# ------------------------

# Entrada Free
@app.route("/webhook/free/entry", methods=["POST"])
def free_entry():
    data = request.json
    symbol = data.get("symbol")
    action = data.get("action")  # BUY o SELL
    price = data.get("price")
    leverage = data.get("leverage", 10)
    win_rate = data.get("win_rate", "80%")

    message = f"*Nueva señal FREE*\n\n" \
              f"Par: {symbol}\n" \
              f"Acción: {action}\n" \
              f"Precio de entrada: {price}\n" \
              f"Apalancamiento recomendado: {leverage}x\n" \
              f"Winrate estimado: {win_rate}"

    send_telegram_message(CHANNEL_FREE, message)
    return jsonify({"status": "ok"}), 200

# Cierre Free
@app.route("/webhook/free/close", methods=["POST"])
def free_close():
    data = request.json
    symbol = data.get("symbol")
    action = data.get("action")  # BUY o SELL
    close_price = data.get("close_price")
    profit_percent = data.get("profit_percent")  # % ganancia basado en apalancamiento

    message = f"*Cierre de señal FREE*\n\n" \
              f"Par: {symbol}\n" \
              f"Acción: {action}\n" \
              f"Precio de cierre: {close_price}\n" \
              f"Ganancia: {profit_percent}%"

    send_telegram_message(CHANNEL_FREE, message)
    return jsonify({"status": "ok"}), 200

# Entrada VIP
@app.route("/webhook/vip/entry", methods=["POST"])
def vip_entry():
    data = request.json
    symbol = data.get("symbol")
    action = data.get("action")  # BUY o SELL
    price = data.get("price")
    leverage = data.get("leverage", 10)
    win_rate = data.get("win_rate", "80%")

    message = f"*Nueva señal VIP*\n\n" \
              f"Par: {symbol}\n" \
              f"Acción: {action}\n" \
              f"Precio de entrada: {price}\n" \
              f"Apalancamiento recomendado: {leverage}x\n" \
              f"Winrate estimado: {win_rate}"

    send_telegram_message(CHANNEL_VIP, message)
    return jsonify({"status": "ok"}), 200

# Cierre VIP
@app.route("/webhook/vip/close", methods=["POST"])
def vip_close():
    data = request.json
    symbol = data.get("symbol")
    action = data.get("action")  # BUY o SELL
    close_price = data.get("close_price")
    profit_percent = data.get("profit_percent")  # % ganancia basado en apalancamiento

    message = f"*Cierre de señal VIP*\n\n" \
              f"Par: {symbol}\n" \
              f"Acción: {action}\n" \
              f"Precio de cierre: {close_price}\n" \
              f"Ganancia: {profit_percent}%"

    send_telegram_message(CHANNEL_VIP, message)
    return jsonify({"status": "ok"}), 200

# Ruta principal
@app.route("/", methods=["GET"])
def index():
    return "Bot de señales activo ✅", 200

# Ejecutar app
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
