import os
import pg8000
import telebot
import time

# ==================== VARIABLES DE ENTORNO ====================
DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = os.getenv("ADMIN_IDS")  # Puedes poner IDs separados por coma si hay varios

# ==================== DEBUG ====================
print("DB_USER =", DB_USER)
print("DB_HOST =", DB_HOST)
print("DB_NAME =", DB_NAME)
print("BOT_TOKEN =", "OK" if BOT_TOKEN else "NO TOKEN")

# ==================== CONEXIÓN A POSTGRES ====================
def get_connection():
    try:
        conn = pg8000.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            ssl_context=True
        )
        return conn
    except Exception as e:
        print("Error conectando a DB:", e)
        return None

def init_db():
    conn = get_connection()
    if conn is None:
        raise Exception("No se pudo conectar a la base de datos")
    cursor = conn.cursor()
    # Tabla de suscriptores
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS subscribers (
        id SERIAL PRIMARY KEY,
        telegram_id BIGINT UNIQUE NOT NULL,
        vip BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT NOW()
    )
    """)
    conn.commit()
    cursor.close()
    conn.close()
    print("Base de datos inicializada")

# ==================== BOT TELEGRAM ====================
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Bienvenido a Cod-X Signals!\nPara acceder al canal VIP, haz tu suscripción y confirma con /subscribe.")

@bot.message_handler(commands=['subscribe'])
def subscribe_user(message):
    telegram_id = message.from_user.id
    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        # Inserta o actualiza suscriptor
        cursor.execute("""
        INSERT INTO subscribers (telegram_id, vip)
        VALUES (%s, TRUE)
        ON CONFLICT (telegram_id) DO UPDATE SET vip = TRUE
        """, (telegram_id,))
        conn.commit()
        cursor.close()
        conn.close()
        bot.reply_to(message, "¡Suscripción VIP confirmada! ✅")
    else:
        bot.reply_to(message, "No se pudo procesar tu suscripción, intenta más tarde.")

# ==================== FUNCIÓN PRINCIPAL ====================
def main():
    init_db()
    print("Bot iniciado")
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            print("Error en polling:", e)
            time.sleep(5)

if __name__ == "__main__":
    main()
