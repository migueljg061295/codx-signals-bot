import os
from flask import Flask, request, jsonify
import telebot
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_VIP = os.getenv("CHANNEL_VIP")
CHANNEL_FREE = os.getenv("CHANNEL_FREE")

bot = telebot.TeleBot(BOT_TOKEN)

app = Flask(__name__)

# Endpoint para recibir alertas de TradingView
@app.route("/alert", methods=["POST"])
def receive_alert():
    data = request.json
    if not data:
        return jsonify({"error": "No data received"}), 400

    # Ejemplo de datos que podrías enviar desde TradingView:
    # { "symbol": "BTCUSDT", "action": "BUY", "entry": 50000, "leverage": 10, "winrate": 80 }
    symbol = data.get("symbol")
    action = data.get("action")
    entry = data.get("entry")
    leverage = data.get("leverage")
    winrate = data.get("winrate")

    message = (
        f"🚀 Nueva señal COD-X\n"
        f"Symbol: {symbol}\n"
        f"Acción: {action}\n"
        f"Entrada: {entry} USDT\n"
        f"Apalancamiento: {leverage}x\n"
        f"Winrate estimado: {winrate}%"
    )

    # Enviar al canal Free o VIP según tu lógica
    bot.send_message(CHANNEL_FREE, message)
    bot.send_message(CHANNEL_VIP, message)

    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
