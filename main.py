import os
import logging
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
import telebot
import requests

# — Configuración —
BOT_TOKEN = os.getenv("BOT_TOKEN")
VIP_CHANNEL_ID = int(os.getenv("VIP_CHANNEL_ID"))
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

# Datos de pago
USDT_PRICE = "10 USDT / mes"
USDT_NETWORK = "BSC (BEP-20)"
USDT_ADDRESS = "0xE9D895F59e29E5Ee3dEe54dD54BB1A759f9fE6Ad"

DATABASE_URL = os.getenv("DATABASE_URL")

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot de Telegram
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# — Funciones de base de datos —  
def get_conn():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    is_active BOOLEAN DEFAULT FALSE,
                    expiry TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    tx_hash TEXT,
                    amount TEXT,
                    network TEXT,
                    note TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT NOW(),
                    processed_by BIGINT,
                    processed_at TIMESTAMP
                );
            """)
            conn.commit()
    logger.info("Base de datos inicializada")

def upsert_user(u):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (user_id, username)
                VALUES (%s, %s)
                ON CONFLICT (user_id) DO UPDATE
                SET username = EXCLUDED.username;
            """, (u.id, u.username))
            conn.commit()

def add_payment(user_id, tx_hash, amount, network, note=None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO payments (user_id, tx_hash, amount, network, note)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id;
            """, (user_id, tx_hash, amount, network, note))
            pid = cur.fetchone()[0]
            conn.commit()
            return pid

def list_pending():
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM payments WHERE status = 'pending' ORDER BY created_at;")
            return cur.fetchall()

def update_payment_status(pid, status, admin_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE payments
                SET status = %s, processed_by = %s, processed_at = NOW()
                WHERE id = %s
                RETURNING user_id;
            """, (status, admin_id, pid))
            row = cur.fetchone()
            conn.commit()
            if row:
                return row[0]
    return None

def activate_user(user_id, days=30):
    expiry = datetime.utcnow() + timedelta(days=days)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users
                SET is_active = TRUE, expiry = %s
                WHERE user_id = %s;
            """, (expiry, user_id))
            conn.commit()
    return expiry

def deactivate_user(user_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users
                SET is_active = FALSE, expiry = NULL
                WHERE user_id = %s;
            """, (user_id,))
            conn.commit()

def get_user(user_id):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE user_id = %s;", (user_id,))
            return cur.fetchone()

# — Funciones Telegram —  
def create_invite_link():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/createChatInviteLink"
    params = {
        "chat_id": VIP_CHANNEL_ID,
        "member_limit": 1,
        "expire_date": int((datetime.utcnow() + timedelta(days=30)).timestamp())
    }
    resp = requests.post(url, json=params)
    if resp.ok:
        return resp.json()["result"]["invite_link"]
    else:
        logger.error("Error al crear enlace de invitación: %s", resp.text)
        return None

# — Comandos Bot —  
@bot.message_handler(commands=["start"])
def cmd_start(m):
    upsert_user(m.from_user)
    bot.send_message(m.chat.id,
        "👋 Bienvenido a *Cod-X Signals Bot*.\n\n"
        "Para ver cómo obtener acceso VIP, escribe /vip."
    )

@bot.message_handler(commands=["vip"])
def cmd_vip(m):
    upsert_user(m.from_user)
    text = (
        "💎 *Plan VIP – Cod-X Signals*\n\n"
        f"Precio mensual: *{USDT_PRICE}*\n"
        f"Red de pago: *{USDT_NETWORK}*\n"
        f"Dirección: `{USDT_ADDRESS}`\n\n"
        "Cuando hayas enviado el pago, usa /pago para registrar tu comprobante.\n"
        "Un administrador lo revisará y te dará acceso VIP si todo está correcto."
    )
    bot.send_message(m.chat.id, text, parse_mode="Markdown")

@bot.message_handler(commands=["pago"])
def cmd_pago(m):
    upsert_user(m.from_user)
    text = (
        "🔍 Por favor, responde con el siguiente formato para reportar el pago:\n\n"
        "`<tx_hash>;<amount>;<network>;<nota opcional>`\n\n"
        "Ejemplo:\n"
        "`0xabc123…;10;BSC;Pago por mensualidad`"
    )
    bot.send_message(m.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text and ";" in m.text)
def handle_pago_report(m):
    upsert_user(m.from_user)
    parts = m.text.split(";")
    if len(parts) < 3:
        bot.reply_to(m, "Formato inválido. Usa: `tx_hash;amount;network;nota (opcional)`")
        return
    tx_hash = parts[0].strip()
    amount = parts[1].strip()
    network = parts[2].strip()
    note = parts[3].strip() if len(parts) >= 4 else None

    pid = add_payment(m.from_user.id, tx_hash, amount, network, note)
    bot.reply_to(m, f"✅ Pago reportado. ID de registro: *{pid}*. Espera a que un admin lo apruebe.")

    # Notificar admin
    for admin in ADMIN_IDS:
        bot.send_message(admin,
            f"💰 Nuevo pago pendiente:\n"
            f"ID: `{pid}`\n"
            f"User: `{m.from_user.id}`\n"
            f"Tx: `{tx_hash}`\n"
            f"Monto: `{amount}`\n"
            f"Red: `{network}`\n"
            f"Nota: `{note}`\n\n"
            f"Usa `/aprobar_{pid}` o `/rechazar_{pid}`"
        )

@bot.message_handler(commands=["status"])
def cmd_status(m):
    upsert_user(m.from_user)
    user = get_user(m.from_user.id)
    if not user:
        bot.send_message(m.chat.id, "No hay registro de tu usuario.")
        return
    if user["is_active"]:
        bot.send_message(m.chat.id, f"✅ Activo hasta: *{user['expiry']}*", parse_mode="Markdown")
    else:
        bot.send_message(m.chat.id, "❌ No tienes suscripción activa.")

# — ADMIN —  
@bot.message_handler(func=lambda m: m.text and m.text.startswith("/aprobar_"))
def cmd_admin_approve(m):
    if m.from_user.id not in ADMIN_IDS:
        return
    try:
        pid = int(m.text.split("_", 1)[1])
    except:
        bot.reply_to(m, "Formato inválido. Usa `/aprobar_ID`")
        return
    user_id = update_payment_status(pid, "approved", m.from_user.id)
    if not user_id:
        bot.reply_to(m, "Pago no encontrado.")
        return

    expiry = activate_user(user_id, days=30)
    link = create_invite_link()
    if link:
        bot.send_message(user_id, f"🎉 Tu pago ha sido aprobado. Aquí está tu enlace VIP:\n{link}\n\nTu suscripción expira el *{expiry}*.", parse_mode="Markdown")
    bot.reply_to(m, f"Pago {pid} aprobado, usuario {user_id} activado hasta {expiry}.")

@bot.message_handler(func=lambda m: m.text and m.text.startswith("/rechazar_"))
def cmd_admin_reject(m):
    if m.from_user.id not in ADMIN_IDS:
        return
    try:
        pid = int(m.text.split("_", 1)[1])
    except:
        bot.reply_to(m, "Formato inválido. Usa `/rechazar_ID`")
        return
    user_id = update_payment_status(pid, "rejected", m.from_user.id)
    if not user_id:
        bot.reply_to(m, "Pago no encontrado.")
        return
    bot.send_message(user_id, f"❌ Tu pago (ID {pid}) fue rechazado. Contacta soporte si crees que esto es un error.")

@bot.message_handler(func=lambda m: m.text and m.text.startswith("/desactivar_"))
def cmd_admin_deactivate(m):
    if m.from_user.id not in ADMIN_IDS:
        return
    try:
        target = int(m.text.split("_", 1)[1])
    except:
        bot.reply_to(m, "Formato inválido. Usa `/desactivar_ID`")
        return
    deactivate_user(target)
    bot.send_message(m.chat.id, f"Usuario {target} desactivado.")

# — Iniciar bot —  
if __name__ == "__main__":
    init_db()
    bot.infinity_polling()
