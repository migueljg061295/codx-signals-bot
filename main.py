#!/usr/bin/env python3
# main.py - Cod-X subscription bot (manual payments USDT BSC, Neon DB)
import os
import time
import logging
from datetime import datetime, timedelta

import requests
import psycopg2
from psycopg2.extras import RealDictCursor
import telebot

# ---------------- CONFIG ----------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
VIP_CHANNEL_ID = int(os.getenv("VIP_CHANNEL_ID"))
DATABASE_URL = os.getenv("DATABASE_URL")
# ADMIN_IDS: comma separated (e.g. "12345678,87654321")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

# Membership info (from your inputs)
MEMBERSHIP_PRICE = os.getenv("MEMBERSHIP_PRICE", "10")
MEMBERSHIP_CURRENCY = os.getenv("MEMBERSHIP_CURRENCY", "USDT")
MEMBERSHIP_NETWORK = os.getenv("NETWORK", "BSC BEP20")
CRYPTO_ADDRESS = os.getenv("CRYPTO_ADDRESS")

# Defaults
DEFAULT_DAYS = int(os.getenv("DEFAULT_VIP_DAYS", "30"))

# ---------- sanity checks ----------
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN env var is required")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL env var is required")
if not CRYPTO_ADDRESS:
    raise RuntimeError("CRYPTO_ADDRESS env var is required")

# ---------- logging ----------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("codx_bot")

# ---------- bot init ----------
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# ---------- db helpers ----------
def get_conn():
    # Neon requires sslmode=require in the URL already; psycopg2 will accept it.
    return psycopg2.connect(DATABASE_URL)

def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                is_active BOOLEAN DEFAULT FALSE,
                expiry TIMESTAMP NULL,
                created_at TIMESTAMP DEFAULT now()
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
                created_at TIMESTAMP DEFAULT now(),
                processed_by BIGINT,
                processed_at TIMESTAMP
            );
            """)
            conn.commit()
    logger.info("DB initialized")

def upsert_user(user):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users(user_id, username)
                VALUES (%s, %s)
                ON CONFLICT (user_id) DO UPDATE SET username = EXCLUDED.username;
            """, (user.id, user.username))
            conn.commit()

def add_payment(user_id, tx_hash, amount, network, note=None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO payments(user_id, tx_hash, amount, network, note)
                VALUES (%s,%s,%s,%s,%s) RETURNING id;
            """, (user_id, tx_hash, amount, network, note))
            pid = cur.fetchone()[0]
            conn.commit()
            return pid

def list_pending():
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM payments WHERE status='pending' ORDER BY created_at;")
            return cur.fetchall()

def update_payment_status(pid, status, admin_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE payments SET status=%s, processed_by=%s, processed_at=now()
                WHERE id=%s RETURNING user_id;
            """, (status, admin_id, pid))
            row = cur.fetchone()
            conn.commit()
            return row[0] if row else None

def activate_user(user_id, days=DEFAULT_DAYS):
    expiry = datetime.utcnow() + timedelta(days=days)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users(user_id, username, is_active, expiry, created_at)
                VALUES (%s, %s, TRUE, %s, now())
                ON CONFLICT (user_id) DO UPDATE SET is_active = TRUE, expiry = EXCLUDED.expiry;
            """, (user_id, None, expiry))
            conn.commit()
    return expiry

def deactivate_user(user_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET is_active = FALSE, expiry = NULL WHERE user_id=%s", (user_id,))
            conn.commit()

def get_user(user_id):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE user_id=%s", (user_id,))
            return cur.fetchone()

# ---------- Telegram helpers ----------
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def create_invite_link(days=DEFAULT_DAYS):
    payload = {
        "chat_id": VIP_CHANNEL_ID,
        "expire_date": int((datetime.utcnow() + timedelta(days=days)).timestamp()),
        "member_limit": 1
    }
    r = requests.post(f"{API_URL}/createChatInviteLink", json=payload)
    if r.ok:
        data = r.json()
        if data.get("ok"):
            return data["result"]["invite_link"]
    logger.error("createChatInviteLink failed: %s", r.text)
    return None

def is_admin(user_id):
    return user_id in ADMIN_IDS

# ---------- Bot command handlers ----------
@bot.message_handler(commands=["start", "help"])
def cmd_start(m):
    upsert_user(m.from_user)
    text = (
        "👋 *Cod-X Signals Bot*\n\n"
        "Este bot gestiona acceso VIP (pago manual USDT).\n\n"
        "Comandos:\n"
        "/vip - Ver precio y método de pago\n"
        "/pago - Reportar pago (tx hash)\n"
        "/status - Ver estado de tu suscripción\n"
    )
    bot.send_message(m.chat.id, text)

@bot.message_handler(commands=["vip"])
def cmd_vip(m):
    upsert_user(m.from_user)
    text = (
        f"💎 *Membresía VIP Cod-X*\n\n"
        f"Precio: *{MEMBERSHIP_PRICE} {MEMBERSHIP_CURRENCY} / mes*\n"
        f"Red: *{MEMBERSHIP_NETWORK}*\n"
        f"Dirección: `{CRYPTO_ADDRESS}`\n\n"
        "Pasos:\n"
        "1) Envía el pago (ej. 10 USDT) a la dirección indicada.\n"
        "2) Usa /pago y responde con: `tx_hash;amount;network;nota`\n"
        "   Ejemplo: `0xabc123...;10;BSC;Pago mensual`\n"
        "3) Un admin revisará y aprobará tu pago. Al aprobar se te enviará el enlace VIP.\n"
    )
    bot.send_message(m.chat.id, text)

@bot.message_handler(commands=["pago"])
def cmd_pago(m):
    upsert_user(m.from_user)
    text = (
        "🔔 *Registrar pago*\n\n"
        "Responde a este mensaje con (texto):\n"
        "`tx_hash;amount;network;nota opcional`\n\n"
        "Ejemplo:\n"
        "`0xabc123...;10;BSC;Pago mensual`"
    )
    bot.send_message(m.chat.id, text)

@bot.message_handler(func=lambda m: m.text and ";" in m.text)
def handle_pago_text(m):
    upsert_user(m.from_user)
    parts = [p.strip() for p in m.text.split(";")]
    if len(parts) < 3:
        bot.reply_to(m, "Formato inválido. Usa: `tx_hash;amount;network;nota (opc)`")
        return
    tx_hash, amount, network = parts[0], parts[1], parts[2]
    note = parts[3] if len(parts) > 3 else None
    pid = add_payment(m.from_user.id, tx_hash, amount, network, note)
    bot.reply_to(m, f"✅ Pago registrado (ID: {pid}). Espera validación de admin.")
    # notify admins
    for aid in ADMIN_IDS:
        try:
            bot.send_message(aid,
                f"💰 Nuevo pago pendiente\nID:{pid}\nUser:{m.from_user.id}\nTx:{tx_hash}\nAmt:{amount} {network}\nNote:{note}\n\nUse /list_pending or /aprobar_{pid} /rechazar_{pid}"
            )
        except Exception as e:
            logger.error("notify admin failed: %s", e)

@bot.message_handler(commands=["status"])
def cmd_status(m):
    upsert_user(m.from_user)
    u = get_user(m.from_user.id)
    if not u:
        bot.send_message(m.chat.id, "No hay registro para tu usuario.")
        return
    if u.get("is_active"):
        bot.send_message(m.chat.id, f"✅ Activo hasta: *{u.get('expiry')}*", parse_mode="Markdown")
    else:
        bot.send_message(m.chat.id, "❌ No tienes suscripción activa.")

# ---------- Admin handlers ----------
@bot.message_handler(commands=["list_pending"])
def cmd_list_pending(m):
    if not is_admin(m.from_user.id):
        return
    pend = list_pending()
    if not pend:
        bot.send_message(m.chat.id, "No hay pagos pendientes.")
        return
    txt = "🔎 Pagos pendientes:\n"
    for p in pend:
        txt += f"#{p['id']} user:{p['user_id']} tx:{p['tx_hash']} amt:{p['amount']} net:{p['network']} at:{p['created_at']}\n"
    bot.send_message(m.chat.id, txt)

@bot.message_handler(func=lambda m: m.text and m.text.startswith("/aprobar_"))
def cmd_approve(m):
    if not is_admin(m.from_user.id):
        return
    try:
        pid = int(m.text.split("_",1)[1])
    except:
        bot.reply_to(m, "Formato inválido. Usa /aprobar_<id>")
        return
    user_id = update_payment_status(pid, "approved", m.from_user.id)
    if not user_id:
        bot.reply_to(m, "Pago no encontrado.")
        return
    expiry = activate_user(user_id, days=DEFAULT_DAYS)
    link = create_invite_link(days=DEFAULT_DAYS)
    if link:
        try:
            bot.send_message(user_id, f"🎉 Pago aprobado. Enlace VIP (válido {DEFAULT_DAYS} días):\n{link}\n\nExpira: {expiry}")
        except Exception as e:
            logger.error("failed to send invite to user: %s", e)
    bot.reply_to(m, f"Pago {pid} aprobado. Usuario {user_id} activado hasta {expiry}.")

@bot.message_handler(func=lambda m: m.text and m.text.startswith("/rechazar_"))
def cmd_reject(m):
    if not is_admin(m.from_user.id):
        return
    try:
        pid = int(m.text.split("_",1)[1])
    except:
        bot.reply_to(m, "Formato inválido. Usa /rechazar_<id>")
        return
    user_id = update_payment_status(pid, "rejected", m.from_user.id)
    if not user_id:
        bot.reply_to(m, "Pago no encontrado.")
        return
    try:
        bot.send_message(user_id, f"❌ Tu pago (id {pid}) fue rechazado. Contacta al admin.")
    except Exception as e:
        logger.error("notify user failed: %s", e)
    bot.reply_to(m, f"Pago {pid} rechazado.")

@bot.message_handler(func=lambda m: m.text and m.text.startswith("/desactivar_"))
def cmd_desactivar(m):
    if not is_admin(m.from_user.id):
        return
    try:
        uid = int(m.text.split("_",1)[1])
    except:
        bot.reply_to(m, "Formato inválido. Usa /desactivar_<user_id>")
        return
    deactivate_user(uid)
    bot.reply_to(m, f"Usuario {uid} desactivado.")

# ---------- background: expire check ----------
def expire_check_loop():
    while True:
        try:
            with get_conn() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT user_id, expiry FROM users WHERE is_active = TRUE AND expiry <= now();")
                    rows = cur.fetchall()
                    for r in rows:
                        try:
                            deactivate_user(r['user_id'])
                            logger.info("Deactivated expired user %s", r['user_id'])
                        except:
                            pass
        except Exception as e:
            logger.error("expire loop error: %s", e)
        time.sleep(3600)  # check every hour

# ---------- start ----------
if __name__ == "__main__":
    init_db()
    # start expire checker in background
    import threading
    t = threading.Thread(target=expire_check_loop, daemon=True)
    t.start()
    logger.info("Bot starting polling...")
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            logger.exception("Polling failed, restarting in 5s")
            time.sleep(5)
