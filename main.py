from flask import Flask, request
import os
from telegram import Bot

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_FREE = os.getenv("CHANNEL_FREE")
CHANNEL_VIP = os.getenv("CHANNEL_VIP")

bot = Bot(token=BOT_TOKEN)


# ---------------------------------------
# SEND OPEN SIGNAL
# ---------------------------------------
def send_open(channel, data):
    action = data.get("action", "").upper()
    symbol = data.get("symbol", "")
    price = data.get("price", "")
    leverage = data.get("leverage", "")
    winrate = data.get("winrate", "")

    msg = (
        f"📢 *Nueva Señal*\n"
        f"🔸 *Acción:* {action}\n"
        f"🔸 *Par:* {symbol}\n"
        f"🔸 *Precio de Entrada:* {price}\n"
        f"🔸 *Apalancamiento:* {leverage}\n"
        f"🔸 *Winrate Estimado:* {winrate}\n\n"
        f"⏳ Espera el mensaje de cierre."
    )

    bot.send_message(chat_id=channel, text=msg, parse_mode="Markdown")


# ---------------------------------------
# SEND CLOSE SIGNAL
# ---------------------------------------
def send_close(channel, data):
    status = data.get("status", "").upper()
    symbol = data.get("symbol", "")
    pnl = data.get("pnl", "")
    leverage = data.get("leverage", "")

    msg = (
        f"📉 *Cierre de Señal*\n"
        f"🔸 *Par:* {symbol}\n"
        f"🔸 *Resultado:* {status}\n"
        f"🔸 *Ganancia/Perdida (con apalancamiento):* {pnl}\n"
        f"🔸 *Apalancamiento:* {leverage}"
    )

    bot.send_message(chat_id=channel, text=msg, parse_mode="Markdown")


# ---------------------------------------------------------
#   ROUTES MATCHING YOUR TRADINGVIEW ALERT CONFIGURATION
# ---------------------------------------------------------

@app.route("/webhook/free/entry", methods=["POST"])
def free_entry():
    data = request.json
    send_open(CHANNEL_FREE, data)
    return {"status": "ok"}, 200


@app.route("/webhook/free/close", methods=["POST"])
def free_close():
    data = request.json
    send_close(CHANNEL_FREE, data)
    return {"status": "ok"}, 200


@app.route("/webhook/vip/entry", methods=["POST"])
def vip_entry():
    data = request.json
    send_open(CHANNEL_VIP, data)
    return {"status": "ok"}, 200


@app.route("/webhook/vip/close", methods=["POST"])
def vip_close():
    data = request.json
    send_close(CHANNEL_VIP, data)
    return {"status": "ok"}, 200


@app.route("/", methods=["GET"])
def home():
    return "CODX SIGNAL BOT RUNNING", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
