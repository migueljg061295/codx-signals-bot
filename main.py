import os
import time
import telebot
import pg8000
from datetime import datetime, timedelta

# -----------------------------
#   Leer variables de entorno
# -----------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_VIP = os.getenv("CHANNEL_VIP")
CHANNEL_FREE = os.getenv("CHANNEL_FREE")

DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")

ADMIN_ID = int(os.getenv("ADMIN_ID"))

DEFAULT_VIP_DAYS = int(os.getenv("DEFAULT_VIP_DAYS", 30))
MEMBERSHIP_CURRENCY = os.getenv("MEMBERSHIP_CURRENCY", "USDT")
MEMBERSHIP_PRICE = os.getenv("MEMBERSHIP_PRICE", "10")
NETWORK = os.getenv("NETWORK", "BSC BEP20")
CRYPTO_ADDRESS = os.getenv("CRYPTO_ADDRESS", "")

bot = telebot.TeleBot(BOT_TOKEN)

# -----------------------------
#   Conexión a PostgreSQL
# -----------------------------
def get_connection():
    return pg8000.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        ssl_context=True
    )

# -----------------------------
#   Inicializar tablas
# -----------------------------
def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            is_vip BOOLEAN DEFAULT FALSE,
            vip_until TIMESTAMP NULL
        );
    """)

    conn.commit()
    cur.close()
    conn.close()


# -----------------------------
#   Registrar usuario
# -----------------------------
def register_user(user):
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO users (user_id, username)
            VALUES (%s, %s)
            ON CONFLICT (user_id) DO NOTHING;
        """, (user.id, user.username))

        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print("Error guardando usuario:", e)


# -----------------------------
#   Revisar si usuario es VIP
# -----------------------------
def is_vip(user_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT is_vip, vip_until FROM users WHERE user_id=%s", (user_id,))
    data = cur.fetchone()

    cur.close()
    conn.close()

    if data is None:
        return False

    is_vip, vip_until = data

    if not is_vip:
        return False

    if vip_until is None:
        return False

    return datetime.utcnow() < vip_until


# -----------------------------
#   Activar VIP manualmente
# -----------------------------
def activate_vip(user_id, days=30):
    conn = get_connection()
    cur = conn.cursor()

    vip_until = datetime.utcnow() + timedelta(days=days)

    cur.execute("""
        UPDATE users
        SET is_vip = TRUE,
            vip_until = %s
        WHERE user_id = %s
    """, (vip_until, user_id))

    conn.commit()
    cur.close()
    conn.close()

    return vip_until


# -----------------------------
#   Comando /start
# -----------------------------
@bot.message_handler(commands=['start'])
def cmd_start(message):
    register_user(message.from_user)

    bot.reply_to(message, 
        "👋 Bienvenido al *CodX Signals Bot*\n\n"
        "Usa /vip para ver cómo comprar membresía.\n"
        "Usa /status para ver si eres VIP."
    )


# -----------------------------
#   Comando /vip (info de pago)
# -----------------------------
@bot.message_handler(commands=['vip'])
def cmd_vip(message):
    bot.reply_to(message,
        f"💎 *Membresía VIP*\n\n"
        f"Precio: *{MEMBERSHIP_PRICE} {MEMBERSHIP_CURRENCY}*\n"
        f"Red: *{NETWORK}*\n\n"
        f"📩 Dirección de pago:\n`{CRYPTO_ADDRESS}`\n\n"
        f"Envía *comprobante al admin* para activar manualmente."
    )


# -----------------------------
#   Comando /status
# -----------------------------
@bot.message_handler(commands=['status'])
def cmd_status(message):
    if is_vip(message.from_user.id):
        bot.reply_to(message, "✅ Eres *VIP activo*")
    else:
        bot.reply_to(message, "❌ No eres VIP")


# -----------------------------
#   Admin: activar VIP
# -----------------------------
@bot.message_handler(commands=['setvip'])
def cmd_setvip(message):
    if message.from_user.id != ADMIN_ID:
        return

    try:
        parts = message.text.split()
        user_id = int(parts[1])
        days = int(parts[2]) if len(parts) > 2 else DEFAULT_VIP_DAYS

        vip_until = activate_vip(user_id, days)

        bot.reply_to(message, f"VIP activado para {user_id} hasta {vip_until}")
        bot.send_message(user_id, "🎉 Tu VIP ha sido activado exitosamente.")
    except:
        bot.reply_to(message, "Uso: /setvip <user_id> <dias>")


# -----------------------------
#   Iniciar bot (polling)
# -----------------------------
print("Bot iniciado con polling...")
init_db()

bot.infinity_polling(skip_pending=True)


# -----------------------------
#   Mantener Render despierto
# -----------------------------
while True:
    time.sleep(86400)
