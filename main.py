
import os
import sqlite3
import telebot
from telebot import types

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
DB_PATH = os.getenv("DB_PATH", "/data/bot.db")

if not TOKEN or not ADMIN_ID:
    raise RuntimeError("Railway Variables bölümünde BOT_TOKEN ve ADMIN_ID ayarlanmalı.")

bot = telebot.TeleBot(TOKEN)
user_states = {}

def connect():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    return sqlite3.connect(DB_PATH, timeout=30)

def setup():
    with connect() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS slots(
            number INTEGER PRIMARY KEY,
            user_id INTEGER UNIQUE,
            team TEXT
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS payments(
            user_id INTEGER PRIMARY KEY,
            status TEXT,
            receipt TEXT
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS settings(
            key TEXT PRIMARY KEY,
            value TEXT
        )""")
        for n in range(1, 26):
            con.execute("INSERT OR IGNORE INTO slots(number) VALUES(?)", (n,))
        defaults = {
            "mode": "free",
            "fee": "100",
            "iban": os.getenv("PAYMENT_IBAN", ""),
            "room_id": "",
            "room_password": ""
        }
        for key, value in defaults.items():
            con.execute(
                "INSERT OR IGNORE INTO settings VALUES(?,?)",
                (key, value)
            )

def setting(key):
    with connect() as con:
        row = con.execute(
            "SELECT value FROM settings WHERE key=?", (key,)
        ).fetchone()
        return row[0] if row else ""

def change_setting(key, value):
    with connect() as con:
        con.execute(
            "INSERT INTO settings VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value))
        )

def payment_status(uid):
    with connect() as con:
        row = con.execute(
            "SELECT status FROM payments WHERE user_id=?", (uid,)
        ).fetchone()
        return row[0] if row else None

def player_slot(uid):
    with connect() as con:
        return con.execute(
            "SELECT number,team FROM slots WHERE user_id=?", (uid,)
        ).fetchone()

def menu(uid):
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.row("🏆 Turnuvaya Kayıt Ol", "📋 Slot Tablosu")
    m.row("👤 Profilim", "🔑 Oda Bilgileri")
    m.row("💬 Admin'e Mesaj Gönder")
    if uid == ADMIN_ID:
        m.row("⚙️ Admin Paneli")
    return m

def slots_keyboard():
    m = types.InlineKeyboardMarkup(row_width=5)
    with connect() as con:
        rows = con.execute(
            "SELECT number,user_id FROM slots ORDER BY number"
        ).fetchall()
    for number, uid in rows:
        label = f"🟢 {number}" if uid is None else f"🔴 {number}"
        m.add(types.InlineKeyboardButton(
            label,
            callback_data=f"slot:{number}" if uid is None else "full"
        ))
    return m

def show_slots(chat_id):
    with connect() as con:
        rows = con.execute(
            "SELECT number,user_id,team FROM slots ORDER BY number"
        ).fetchall()
    lines = ["📋 TURNUVA SLOT TABLOSU"]
    for number, uid, team in rows:
        lines.append(
            f"🟢 Slot {number} — Boş" if uid is None
            else f"🔴 Slot {number} — {team}"
        )
    bot.send_message(chat_id, "\n".join(lines))

def admin_panel(chat_id):
    m = types.InlineKeyboardMarkup(row_width=2)
    options = [
        ("Ücretsiz Mod", "mode_free"),
        ("Ücretli Mod", "mode_paid"),
        ("Ücret Belirle", "fee"),
        ("IBAN Belirle", "iban"),
        ("Oda ID", "room_id"),
        ("Oda Şifresi", "room_password"),
        ("Bekleyen Dekontlar", "pending"),
        ("Slotları Sıfırla", "reset")
    ]
    for label, action in options:
        m.add(types.InlineKeyboardButton(
            label, callback_data=f"admin:{action}"
        ))
    bot.send_message(chat_id, "⚙️ ADMIN PANELİ", reply_markup=m)

def payment_buttons(uid):
    m = types.InlineKeyboardMarkup()
    m.row(
        types.InlineKeyboardButton("Onayla", callback_data=f"approve:{uid}"),
        types.InlineKeyboardButton("Reddet", callback_data=f"reject:{uid}")
    )
    return m

@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "🏆 Turnuva botuna hoş geldin!",
        reply_markup=menu(message.from_user.id)
    )

@bot.message_handler(commands=["admin"])
def admin(message):
    if message.from_user.id != ADMIN_ID:
        return
    user_states[message.from_user.id] = "admin"
    admin_panel(message.chat.id)

@bot.callback_query_handler(func=lambda c: True)
def callbacks(call):
    uid = call.from_user.id
    data = call.data

    if data == "full":
        bot.answer_callback_query(call.id, "Bu slot dolu.")
        return

    if data.startswith("slot:"):
        if user_states.get(uid) != "choosing":
            bot.answer_callback_query(call.id, "Önce takım adını yazmalısın.")
            return
        number = int(data.split(":")[1])
        team = user_states.get(f"team:{uid}")
        if not team or player_slot(uid):
            bot.answer_callback_query(call.id, "Kayıt yapılamadı.")
            return
        with connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute(
                "SELECT user_id FROM slots WHERE number=?", (number,)
            ).fetchone()
            if not row or row[0] is not None:
                con.rollback()
                bot.answer_callback_query(call.id, "Slot artık boş değil.")
                return
            con.execute(
                "UPDATE slots SET user_id=?,team=? WHERE number=?",
                (uid, team, number)
            )
        user_states.pop(uid, None)
        user_states.pop(f"team:{uid}", None)
        bot.answer_callback_query(call.id, "Kayıt tamamlandı.")
        bot.send_message(call.message.chat.id, f"✅ Kayıt tamamlandı!\nTakım: {team}\nSlot: {number}")
        return

    if data.startswith("admin:"):
        if uid != ADMIN_ID:
            bot.answer_callback_query(call.id, "Yetkin yok.")
            return
        action = data.split(":", 1)[1]
        if action == "mode_free":
            change_setting("mode", "free")
            bot.answer_callback_query(call.id, "Ücretsiz mod açıldı.")
            return
        if action == "mode_paid":
            change_setting("mode", "paid")
            bot.answer_callback_query(call.id, "Ücretli mod açıldı.")
            return
        if action == "pending":
            with connect() as con:
                rows = con.execute(
                    "SELECT user_id,receipt FROM payments WHERE status='pending'"
                ).fetchall()
            bot.answer_callback_query(call.id)
            if not rows:
                bot.send_message(call.message.chat.id, "Bekleyen dekont yok.")
            for target, receipt in rows:
                bot.send_photo(
                    call.message.chat.id, receipt,
                    caption=f"Kullanıcı ID: {target}",
                    reply_markup=payment_buttons(target)
                )
            return
        if action == "reset":
            m = types.InlineKeyboardMarkup()
            m.add(
                types.InlineKeyboardButton("Evet", callback_data="reset_yes"),
                types.InlineKeyboardButton("Hayır", callback_data="reset_no")
            )
            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, "Bütün slotlar sıfırlansın mı?", reply_markup=m)
            return
        prompts = {
            "fee": "Yeni ücreti yaz:",
            "iban": "IBAN bilgisini yaz:",
            "room_id": "Oda ID bilgisini yaz:",
            "room_password": "Oda şifresini yaz:"
        }
        user_states[uid] = f"setting:{action}"
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, prompts[action])
        return

    if data.startswith("approve:") or data.startswith("reject:"):
        if uid != ADMIN_ID:
            bot.answer_callback_query(call.id, "Yetkin yok.")
            return
        action, target_text = data.split(":")
        target = int(target_text)
        status = "approved" if action == "approve" else "rejected"
        with connect() as con:
            con.execute(
                "UPDATE payments SET status=? WHERE user_id=? AND status='pending'",
                (status, target)
            )
        bot.answer_callback_query(call.id, "İşlem kaydedildi.")
        if status == "approved":
            user_states[target] = "team"
            bot.send_message(target, "✅ Ödemen onaylandı. Takım adını yaz.")
        else:
            bot.send_message(target, "Dekontun reddedildi. Adminle iletişime geç.")
        return

    if data == "receipt_done":
        if payment_status(uid) != "submitted":
            bot.answer_callback_query(call.id, "Önce dekont göndermelisin.")
            return
        with connect() as con:
            con.execute(
                "UPDATE payments SET status='pending' WHERE user_id=?",
                (uid,)
            )
            row = con.execute(
                "SELECT receipt FROM payments WHERE user_id=?", (uid,)
            ).fetchone()
        bot.send_photo(
            ADMIN_ID, row[0],
            caption=f"Yeni ödeme onayı bekliyor. Kullanıcı ID: {uid}",
            reply_markup=payment_buttons(uid)
        )
        bot.answer_callback_query(call.id, "Dekont admin'e iletildi.")
        return

    if data == "reset_yes":
        if uid != ADMIN_ID:
            bot.answer_callback_query(call.id, "Yetkin yok.")
            return
        with connect() as con:
            con.execute("UPDATE slots SET user_id=NULL,team=NULL")
            con.execute("DELETE FROM payments")
        bot.answer_callback_query(call.id, "Slotlar sıfırlandı.")
        return

    if data == "reset_no":
        bot.answer_callback_query(call.id, "İptal edildi.")
        return

@bot.message_handler(content_types=["photo"])
def photo(message):
    uid = message.from_user.id
    if setting("mode") != "paid":
        bot.send_message(message.chat.id, "Turnuva ücretsiz modda.")
        return
    receipt = message.photo[-1].file_id
    with connect() as con:
        con.execute(
            "INSERT INTO payments(user_id,status,receipt) VALUES(?,?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET status='submitted',receipt=excluded.receipt",
            (uid, "submitted", receipt)
        )
    m = types.InlineKeyboardMarkup()
    m.add(types.InlineKeyboardButton("Dekontu Gönderdim", callback_data="receipt_done"))
    bot.send_message(message.chat.id, "Dekont alındı. Butona basarak admin'e ilet.", reply_markup=m)

@bot.message_handler(content_types=["text"])
def messages(message):
    uid = message.from_user.id
    text = message.text.strip()
    state = user_states.get(uid)

    if text.startswith("/"):
        return

    if state == "setting:fee":
        change_setting("fee", text)
        user_states[uid] = "admin"
        bot.send_message(message.chat.id, "Ücret kaydedildi.")
        admin_panel(message.chat.id)
        return

    if state in ("setting:iban", "setting:room_id", "setting:room_password"):
        key = state.split(":")[1]
        change_setting(key, text)
        user_states[uid] = "admin"
        bot.send_message(message.chat.id, "Ayar kaydedildi.")
        admin_panel(message.chat.id)
        return

    if state == "team":
        if len(text) > 40:
            bot.send_message(message.chat.id, "Takım adı en fazla 40 karakter olabilir.")
            return
        if setting("mode") == "paid" and payment_status(uid) != "approved":
            bot.send_message(message.chat.id, "Ödemen onaylanmamış.")
            return
        user_states[f"team:{uid}"] = text
        user_states[uid] = "choosing"
        bot.send_message(message.chat.id, "Boş slot seç:", reply_markup=slots_keyboard())
        return

    if state == "contact":
        user_states.pop(uid, None)
        bot.send_message(ADMIN_ID, f"Kullanıcı mesajı\nID: {uid}\n{text}")
        bot.send_message(message.chat.id, "Mesajın admin'e iletildi.")
        return

    if text == "🏆 Turnuvaya Kayıt Ol":
        if player_slot(uid):
            bot.send_message(message.chat.id, "Zaten kayıtlısın.")
            return
        if setting("mode") == "paid" and payment_status(uid) != "approved":
            bot.send_message(
                message.chat.id,
                f"Katılım ücreti: {setting('fee')} TL\nIBAN:\n{setting('iban')}\nÖdeme yaptıktan sonra dekont fotoğrafını gönder."
            )
            return
        user_states[uid] = "team"
        bot.send_message(message.chat.id, "Takım adını yaz:")
        return

    if text == "📋 Slot Tablosu":
        show_slots(message.chat.id)
        return

    if text == "👤 Profilim":
        slot = player_slot(uid)
        details = f"Takım: {slot[1]}\nSlot: {slot[0]}" if slot else "Henüz kayıtlı değilsin."
        bot.send_message(message.chat.id, f"Profil\nID: {uid}\n{details}\nÖdeme: {payment_status(uid) or 'Gerek yok'}")
        return

    if text == "🔑 Oda Bilgileri":
        if not player_slot(uid):
            bot.send_message(message.chat.id, "Önce kayıt olmalısın.")
            return
        bot.send_message(
            message.chat.id,
            f"Oda ID: {setting('room_id') or 'Henüz girilmedi'}\nŞifre: {setting('room_password') or 'Henüz girilmedi'}"
        )
        return

    if text == "💬 Admin'e Mesaj Gönder":
        user_states[uid] = "contact"
        bot.send_message(message.chat.id, "Mesajını yaz:")
        return

    if text == "⚙️ Admin Paneli" and uid == ADMIN_ID:
        admin_panel(message.chat.id)
        return

    bot.send_message(message.chat.id, "Menüden bir işlem seç.", reply_markup=menu(uid))

setup()
print("Bot çalışıyor.")
bot.infinity_polling(skip_pending=True)
