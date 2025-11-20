import os
from flask import Flask, request
import telegram

# ---------------------------
# Configuración
# ---------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_FREE = os.getenv("CHANNEL_FREE")
CHANNEL_VIP = os.getenv("CHANNEL_VIP")

# Inicializar bot
bot = telegram.Bot(token=BOT_TOKEN)
app = Flask(__name__)

# ---------------------------
# Funciones de envío de mensajes
# ---------------------------
def send_signal(channel_id, signal):
    """
    Envía la señal inicial al canal correspondiente.
    signal debe ser un diccionario con: symbol, action, leverage, entry_price, win_rate
    """
    text = (
        f"💹 *Nueva Señal*\n"
        f"Símbolo: {signal['symbol']}\n"
        f"Acción: {signal['action']}\n"
        f"Leverage recomendado: {signal['leverage']}x\n"
        f"Precio de entrada: {signal['entry_price']}\n"
        f"Winrate estimado: {signal['win_rate']}%"
    )
    bot.send_message(chat_id=channel_id, text=text, parse_mode=telegram.ParseMode.MARKDOWN)

def send_close(channel_id, signal, outcome):
    """
    Envía el mensaje de cierre con ganancia o pérdida.
    outcome: 'TP' o 'SL'
    """
    if outcome == "TP":
        percent_gain = round(signal.get("gain_percent", 1) * signal["leverage"], 2)
        result_text = f"✅ *Take Profit alcanzado*\nGanancia: {percent_gain}%"
    else:
        percent_loss = round(-1.2 * signal["leverage"], 2)
        result_text = f"❌ *Stop Loss alcanzado*\nPérdida: {percent_loss}%"

    text = (
        f"{result_text}\n"
        f"Símbolo: {signal['symbol']}\n"
        f"Acción: {signal['action']}\n"
        f"Entrada: {signal['entry_price']}\n"
        f"Leverage: {signal['leverage']}x\n"
        f"Winrate estimado: {signal['win_rate']}%"
    )
    bot.send_message(chat_id=channel_id, text=text, parse_mode=telegram.ParseMode.MARKDOWN)

# ---------------------------
# Rutas Webhook
# ---------------------------
@app.route("/webhook/free", methods=["POST"])
def webhook_free():
    data = request.json
    send_signal(CHANNEL_FREE, data)
    return "ok", 200

@app.route("/webhook/vip", methods=["POST"])
def webhook_vip():
    data = request.json
    send_signal(CHANNEL_VIP, data)
    return "ok", 200

@app.route("/webhook/free/close", methods=["POST"])
def close_free():
    data = request.json
    send_close(CHANNEL_FREE, data, data["outcome"])
    return "ok", 200

@app.route("/webhook/vip/close", methods=["POST"])
def close_vip():
    data = request.json
    send_close(CHANNEL_VIP, data, data["outcome"])
    return "ok", 200

# ---------------------------
# Run Flask
# ---------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # Render asigna puerto dinámico
    app.run(host="0.0.0.0", port=port)
