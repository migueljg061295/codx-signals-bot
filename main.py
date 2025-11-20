import os
import pg8000
import telebot
from datetime import datetime, timedelta

# ---------------------------
# Configuración de Variables
# ---------------------------

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

DEFAULT_VIP_DAYS = int(os.getenv("DEFAULT_VIP_DAYS", 30))
MEMBERSHIP_CURRENCY = os.getenv("MEMBERSHIP_CURRENCY", "USDT")
MEMBERSHIP_PRICE = float(os.getenv("MEMBERSHIP_PRICE", 10))
NETWORK = os.getenv("NETWORK", "BSC BEP20")
CRYPTO_ADDRESS = os.getenv("CRYPTO_ADDRESS", "")

# ---------------------------
# Funciones de DB
# ---------------------------

def get_connection():
    return pg8000.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        ssl_context=True
    )

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id BIGINT PRIMARY KEY,
            is_vip BOOLEAN DEFAULT FALSE,
            vip_until TIMESTAMP
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

def add_vip_user(chat_id):
    conn = get_connection()
    cursor = conn.cursor()
    vip_until = datetime.utcnow() + timedelta(days=DEFAULT_VIP_DAYS)
    cursor.execute("""
        INSERT INTO users(chat_id, is_vip, vip_until)
        VALUES(%s, TRUE, %s)
        ON CONFLICT (chat_id) DO UPDATE
        SET is_vip = TRUE,
            vip_until = EXCLUDED.vip_until
    """, (chat_id, vip_until))
    conn.commit()
    cursor.close()
    conn.close()

# ---------------------------
# Comandos de Telegram
# ---------------------------

@bot.message_handler(commands=["start"])
def start_command(message):
    bot.send_message(
        message.chat.id,
        "Bienvenido a Cod-X Signals Bot!\n"
        "Usa /free para recibir señales gratuitas.\n"
        "Usa /vip para información de membresía VIP."
    )

@bot.message_handler(commands=["free"])
def free_command(message):
    bot.send_message(
        message.chat.id,
        "Este es el canal gratuito. Recibirás señales básicas aquí."
    )

@bot.message_handler(commands=["vip"])
def vip_command(message):
    bot.send_message(
        message.chat.id,
        f"Para activar tu membresía VIP debes pagar {MEMBERSHIP_PRICE} {MEMBERSHIP_CURRENCY}.\n"
        f"Red: {NETWORK}\n"
        f"Wallet: {CRYPTO_ADDRESS}\n\n"
        "Envía tu comprobante de pago para que un administrador lo confirme."
    )

@bot.message_handler(commands=["confirm"])
def confirm_vip(message):
    # Solo admin puede usar esto, por simplicidad
    chat_id = message.text.split()[1]
    add_vip_user(int(chat_id))
    bot.send_message(chat_id, f"Tu membresía VIP ha sido activada por {DEFAULT_VIP_DAYS} días!")

# ---------------------------
# Inicio del bot
# ---------------------------

if __name__ == "__main__":
    init_db()
    print("Bot iniciado...")
    bot.infinity_polling()
