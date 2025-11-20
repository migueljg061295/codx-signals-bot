import os
import pg8000
import telebot

# Cargar variables de entorno
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_VIP = os.getenv("CHANNEL_VIP")
CHANNEL_FREE = os.getenv("CHANNEL_FREE")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT"))
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")

# Inicializar bot
bot = telebot.TeleBot(BOT_TOKEN)

# Conexión a PostgreSQL
def get_connection():
    return pg8000.connect(
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        ssl_context=True
    )

# Inicializar DB (tabla de suscriptores VIP)
def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vip_users (
        id SERIAL PRIMARY KEY,
        telegram_id BIGINT UNIQUE,
        approved BOOLEAN DEFAULT FALSE
    );
    """)
    conn.commit()
    cursor.close()
    conn.close()

init_db()

# Comandos básicos
@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(message.chat.id,
                     f"Bienvenido {message.from_user.first_name}!\n\n"
                     f"Para acceder al canal VIP, envía tu comprobante de pago y espera la aprobación del admin.")

@bot.message_handler(commands=["vip"])
def vip_command(message):
    bot.send_message(message.chat.id,
                     "Envía tu comprobante de pago y el admin verificará tu acceso.")

@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    # Aquí podrías guardar el mensaje como comprobante
    if message.chat.id != ADMIN_ID:
        bot.send_message(ADMIN_ID, f"Nuevo comprobante de {message.from_user.first_name}: {message.text}")
        bot.send_message(message.chat.id, "Comprobante recibido. Espera la aprobación del admin.")

# Ejecutar bot
PORT = int(os.environ.get("PORT", 5000))
bot.infinity_polling()
