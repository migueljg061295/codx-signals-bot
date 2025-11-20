print("DB_USER =", DB_USER)
print("DB_PASSWORD =", DB_PASSWORD)

import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import pg8000

# ===========================
# VARIABLES DE ENTORNO
# ===========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME")
ADMIN_IDS = os.getenv("ADMIN_IDS", "").split(",")

bot = telebot.TeleBot(BOT_TOKEN)

# ===========================
# CONEXIÓN A POSTGRESQL (pg8000)
# ===========================

def get_connection():
    return pg8000.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        ssl_context=True
    )

# Crear tabla de usuarios si no existe
def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            is_vip BOOLEAN DEFAULT FALSE,
            expires TIMESTAMP NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ===========================
# COMANDO /start
# ===========================
@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.from_user.id

    markup = InlineKeyboardMarkup()
    vip_btn = InlineKeyboardButton("🔑 Acceder VIP", callback_data="vip")
    free_btn = InlineKeyboardButton("📨 Canal Free", callback_data="free")

    markup.add(vip_btn)
    markup.add(free_btn)

    bot.send_message(
        user_id,
        "🤖 *Bienvenido a Cod-X Signals Bot*\n\n"
        "Aquí podrás acceder al canal *FREE* y gestionar tu acceso al canal *VIP*.",
        parse_mode="Markdown",
        reply_markup=markup
    )

# ===========================
# HANDLERS DE BOTONES
# ===========================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id

    if call.data == "free":
        bot.send_message(user_id, "📨 Canal FREE:\nhttps://t.me/codx_signals_free")
    elif call.data == "vip":
        send_vip_instructions(user_id)

# ===========================
# INSTRUCCIONES VIP
# ===========================
def send_vip_instructions(user_id):
    markup = InlineKeyboardMarkup()
    pay_btn = InlineKeyboardButton("💸 Enviar comprobante", callback_data="send_proof")
    markup.add(pay_btn)

    bot.send_message(
        user_id,
        "🔐 *Acceso VIP Cod-X*\n\n"
        "💵 Precio mensual: *10 USDT*\n"
        "🪙 Red: *BSC (BEP20)*\n"
        "📥 Dirección de pago:\n`0xE9D895F59e29E5Ee3dEe54dD54BB1A759f9fE6Ad`\n\n"
        "Cuando completes el pago, presiona el botón:",
        parse_mode="Markdown",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "send_proof")
def ask_payment_proof(call):
    bot.send_message(call.from_user.id,
                     "📤 Envía aquí una captura del pago.\nUn administrador verificará manualmente tu acceso.")

# ===========================
# ADMIN PANEL
# ===========================
@bot.message_handler(commands=["admin"])
def admin_panel(message):
    user_id = str(message.from_user.id)

    if user_id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "⛔ No tienes acceso.")
        return

    markup = InlineKeyboardMarkup()
    approve_btn = InlineKeyboardButton("✔ Aprobar pago", callback_data="approve")
    users_btn = InlineKeyboardButton("👥 Ver VIP", callback_data="list_vip")

    markup.add(approve_btn)
    markup.add(users_btn)

    bot.send_message(message.chat.id,
                     "🔧 *Panel Admin*",
                     parse_mode="Markdown",
                     reply_markup=markup)

# ===========================
# INICIO DEL BOT
# ===========================
print("🚀 BOT INICIADO (Render / Python 3.13 / pg8000)")
bot.infinity_polling(skip_pending=True)
