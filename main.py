
import os
import sqlite3
import html
import telebot
from telebot import types

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
DB_PATH = os.getenv("DB_PATH", "/data/bot.db")

if not TOKEN or not ADMIN_ID:
    raise RuntimeError("BOT_TOKEN ve ADMIN_ID Railway Variables bölümünde ayarlanmalı.")

bot = telebot.TeleBot(TOKEN)
states = {}


# VERITABANI
def connect():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    return sqlite3.connect(DB_PATH, timeout=30)


def setup():
    with connect() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS slots (
                number INTEGER PRIMARY KEY,
                user_id INTEGER UNIQUE,
                team TEXT
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                user_id INTEGER PRIMARY KEY,
                status TEXT,
                receipt TEXT
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        for number in range(1, 26):
            con.execute(
                "INSERT OR IGNORE INTO slots(number) VALUES(?)",
                (number,)
            )

        defaults = {
            "mode": "free",
            "fee": "100",
            "iban": os.getenv("PAYMENT_IBAN", ""),
            "room_id": "",
            "room_password": ""
        }

        for key, value in defaults.items():
            con.execute(
                "INSERT OR IGNORE INTO settings(key, value) VALUES(?, ?)",
                (key, value)
            )


def get_setting(key):
    with connect() as con:
        row = con.execute(
            "SELECT value FROM settings WHERE key=?",
            (key,)
        ).fetchone()
        return row[0] if row else ""


def set_setting(key, value):
    with connect() as con:
        con.execute("""
            INSERT INTO settings(key, value) VALUES(?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
        """, (key, str(value)))


def get_payment(uid):
    with connect() as con:
        row = con.execute(
            "SELECT status FROM payments WHERE user_id=?",
            (uid,)
        ).fetchone()
        return row[0] if row else None


def get_slot(uid):
    with connect() as con:
        return con.execute(
            "SELECT number, team FROM slots WHERE user_id=?",
            (uid,)
        ).fetchone()


# MENULER
def main_menu(uid):
    menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
    menu.row("🏆 Turnuvaya Kayıt Ol", "📋 Slot Tablosu")
    menu.row("👤 Profilim", "🔑 Oda Bilgileri")
    menu.row("💬 Admin'e Mesaj Gönder")

    if uid == ADMIN_ID:
        menu.row("⚙️ Admin Paneli")

    return menu


def admin_panel(chat_id):
    menu = types.InlineKeyboardMarkup(row_width=2)

    buttons = [
        ("🟢 Ücretsiz Mod", "mode_free"),
        ("💳 Ücretli Mod", "mode_paid"),
        ("💰 Ücret Belirle", "fee"),
        ("🏦 IBAN Belirle", "iban"),
        ("🎮 Oda ID", "room_id"),
        ("🔒 Oda Şifresi", "room_password"),
        ("📨 Bekleyen Dekontlar", "pending"),
        ("♻️ Slotları Sıfırla", "reset")
    ]

    for label, action in buttons:
        menu.add(types.InlineKeyboardButton(
            label,
            callback_data=f"admin:{action}"
        ))

    bot.send_message(
        chat_id,
        "⚙️ ADMIN PANELİ",
        reply_markup=menu
    )


def show_slots(chat_id):
    with connect() as con:
        rows = con.execute(
            "SELECT number, user_id, team FROM slots ORDER BY number"
        ).fetchall()

    lines = ["📋 SLOT TABLOSU"]

    for number, uid, team in rows:
        if uid is None:
            lines.append(f"🟢 Slot {number} — Boş")
        else:
            lines.append(
                f"🔴 Slot {number} — {html.escape(team or '')}"
            )

    bot.send_message(chat_id, "\n".join(lines))


def slot_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=5)

    with connect() as con:
        rows = con.execute(
            "SELECT number, user_id FROM slots ORDER BY number"
        ).fetchall()

    for number, uid in rows:
        if uid is None:
            keyboard.add(types.InlineKeyboardButton(
                f"🟢 {number}",
                callback_data=f"slot:{number}"
            ))
        else:
            keyboard.add(types.InlineKeyboardButton(
                f"🔴 {number}",
                callback_data="occupied"
            ))

    return keyboard


def payment_keyboard(uid):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton(
            "✅ Onayla",
            callback_data=f"approve:{uid}"
        ),
        types.InlineKeyboardButton(
            "❌ Reddet",
            callback_data=f"reject:{uid}"
        )
    )
    return keyboard


# BASLANGIC
@bot.message_handler(commands=["start"])
def start(message):
    if message.chat.type != "private":
        return

    bot.send_message(
        message.chat.id,
        "🏆 Turnuva botuna hoş geldin!",
        reply_markup=main_menu(message.from_user.id)
    )


# ADMIN
@bot.message_handler(commands=["admin"])
def admin_command(message):
    if message.from_user.id != ADMIN_ID:
        return

    admin_panel(message.chat.id)


# BUTONLAR
@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    uid = call.from_user.id
    data = call.data

    if data == "occupied":
        bot.answer_callback_query(call.id, "Bu slot dolu.")
        return

    # SLOT SECIMI
    if data.startswith("slot:"):
        if states.get(uid) != "choosing":
            bot.answer_callback_query(
                call.id,
                "Önce takım adını yazmalısın."
            )
            return

        number = int(data.split(":")[1])
        team = states.get(f"team:{uid}")

        if not team or get_slot(uid):
            bot.answer_callback_query(
                call.id,
                "Kayıt yapılamadı."
            )
            return

        with connect() as con:
            con.execute("BEGIN IMMEDIATE")

            row = con.execute(
                "SELECT user_id FROM slots WHERE number=?",
                (number,)
            ).fetchone()

            if not row or row[0] is not None:
                con.rollback()
                bot.answer_callback_query(call.id, "Slot dolu.")
                return

            con.execute(
                "UPDATE slots SET user_id=?, team=? WHERE number=?",
                (uid, team, number)
            )

        states.pop(uid, None)
        states.pop(f"team:{uid}", None)

        bot.answer_callback_query(call.id, "Kayıt tamamlandı.")
        bot.send_message(
            call.message.chat.id,
            f"🎉 KAYDIN TAMAMLANDI\n"
            f"Takım: {html.escape(team)}\n"
            f"Slot: {number}"
        )
        return

    # ADMIN AYARLARI
    if data.startswith("admin:"):
        if uid != ADMIN_ID:
            bot.answer_callback_query(call.id, "Yetkin yok.")
            return

        action = data.split(":", 1)[1]

        if action == "mode_free":
            set_setting("mode", "free")
            bot.answer_callback_query(call.id, "Ücretsiz mod açıldı.")
            return

        if action == "mode_paid":
            set_setting("mode", "paid")
            bot.answer_callback_query(call.id, "Ücretli mod açıldı.")
            return

        if action == "pending":
            with connect() as con:
                rows = con.execute(
                    "SELECT user_id, receipt FROM payments "
                    "WHERE status='pending'"
                ).fetchall()

            bot.answer_callback_query(call.id)

            if not rows:
                bot.send_message(
                    call.message.chat.id,
                    "Bekleyen dekont yok."
                )
                return

            for target, receipt in rows:
                bot.send_photo(
                    call.message.chat.id,
                    receipt,
                    caption=f"Kullanıcı ID: {target}",
                    reply_markup=payment_keyboard(target)
                )
            return

        if action == "reset":
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(
                types.InlineKeyboardButton(
                    "Evet",
                    callback_data="reset_yes"
                ),
                types.InlineKeyboardButton(
                    "Hayır",
                    callback_data="reset_no"
                )
            )
            bot.answer_callback_query(call.id)
            bot.send_message(
                call.message.chat.id,
                "Bütün slotlar ve ödeme kayıtları sıfırlansın mı?",
                reply_markup=keyboard
            )
            return

        prompts = {
            "fee": "Yeni katılım ücretini TL olarak yaz:",
            "iban": "IBAN bilgisini yaz:",
            "room_id": "Oda ID bilgisini yaz:",
            "room_password": "Oda şifresini yaz:"
        }

        states[uid] = f"setting:{action}"
        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id,
            prompts[action]
        )
        return

    # ODEME ONAYI
    if data.startswith("approve:") or data.startswith("reject:"):
        if uid != ADMIN_ID:
            bot.answer_callback_query(call.id, "Yetkin yok.")
            return

        action, target_text = data.split(":")
        target = int(target_text)

        with connect() as con:
            row = con.execute(
                "SELECT status FROM payments WHERE user_id=?",
                (target,)
            ).fetchone()

            if not row or row[0] != "pending":
                bot.answer_callback_query(
                    call.id,
                    "Bu ödeme artık beklemede değil."
                )
                return

            status = "approved" if action == "approve" else "rejected"

            con.execute(
                "UPDATE payments SET status=? WHERE user_id=?",
                (status, target)
            )

        bot.answer_callback_query(call.id, "İşlem kaydedildi.")

        if status == "approved":
            states[target] = "team"
            bot.send_message(
                target,
                "✅ Ödemen onaylandı. Şimdi takım adını yaz."
            )
        else:
            bot.send_message(
                target,
                "❌ Dekontun reddedildi. Adminle iletişime geç."
            )
        return

    # DEKONTU ADMIN'E GONDER
    if data == "receipt_done":
        if get_payment(uid) != "submitted":
            bot.answer_callback_query(
                call.id,
                "Önce dekont fotoğrafı göndermelisin."
            )
            return

        with connect() as con:
            con.execute(
                "UPDATE payments SET status='pending' WHERE user_id=?",
                (uid,)
            )
            row = con.execute(
                "SELECT receipt FROM payments WHERE user_id=?",
                (uid,)
            ).fetchone()

        try:
            bot.send_photo(
                ADMIN_ID,
                row[0],
                caption=f"Yeni dekont bekliyor.\nKullanıcı ID: {uid}",
                reply_markup=payment_keyboard(uid)
            )
            bot.answer_callback_query(
                call.id,
                "Dekont admin'e gönderildi."
            )
        except Exception:
            bot.answer_callback_query(
                call.id,
                "Admin bota /start yazmalı."
            )
        return

    # SLOT SIFIRLAMA
    if data == "reset_yes":
        if uid != ADMIN_ID:
            bot.answer_callback_query(call.id, "Yetkin yok.")
            return

        with connect() as con:
            con.execute("UPDATE slots SET user_id=NULL, team=NULL")
            con.execute("DELETE FROM payments")

        states.clear()
        bot.answer_callback_query(call.id, "Slotlar sıfırlandı.")
        bot.send_message(
            call.message.chat.id,
            "♻️ Tüm slotlar sıfırlandı."
        )
        return

    if data == "reset_no":
        bot.answer_callback_query(call.id, "İptal edildi.")
        return


# DEKONT FOTOGRAFI
@bot.message_handler(content_types=["photo"])
def photo_handler(message):
    uid = message.from_user.id

    if get_setting("mode") != "paid":
        bot.send_message(
            message.chat.id,
            "Turnuva şu anda ücretsiz modda."
        )
        return

    if get_slot(uid):
        bot.send_message(
            message.chat.id,
            "Zaten turnuvaya kayıtlısın."
        )
        return

    receipt = message.photo[-1].file_id

    with connect() as con:
        con.execute("""
            INSERT INTO payments(user_id, status, receipt)
            VALUES(?, 'submitted', ?)
            ON CONFLICT(user_id)
            DO UPDATE SET status='submitted', receipt=excluded.receipt
        """, (uid, receipt))

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(
        "✅ Dekontu Gönderdim",
        callback_data="receipt_done"
    ))

    bot.send_message(
        message.chat.id,
        "Dekont alındı. Admin'e iletmek için butona bas.",
        reply_markup=keyboard
    )


# MESAJLAR
@bot.message_handler(content_types=["text"])
def messages(message):
    uid = message.from_user.id
    text = message.text.strip()
    state = states.get(uid)

    if message.chat.type != "private":
        return

    if text.startswith("/"):
        return

    # ADMIN AYARLARI
    if state and state.startswith("setting:"):
        if uid != ADMIN_ID:
            return

        key = state.split(":", 1)[1]

        if key == "fee":
            try:
                fee = float(text.replace(",", "."))
                if fee <= 0:
                    raise ValueError
            except ValueError:
                bot.send_message(
                    message.chat.id,
                    "Geçerli bir ücret yaz."
                )
                return

            text = str(fee)

        set_setting(key, text)
        states.pop(uid, None)

        bot.send_message(
            message.chat.id,
            "✅ Ayar kaydedildi."
        )
        admin_panel(message.chat.id)
        return

    # TAKIM ADI
    if state == "team":
        if len(text) > 40:
            bot.send_message(
                message.chat.id,
                "Takım adı en fazla 40 karakter olabilir."
            )
            return

        if get_slot(uid):
            states.pop(uid, None)
            bot.send_message(
                message.chat.id,
                "Zaten kayıtlısın."
            )
            return

        if (
            get_setting("mode") == "paid"
            and get_payment(uid) != "approved"
        ):
            bot.send_message(
                message.chat.id,
                "Ödemen henüz onaylanmadı."
            )
            return

        states[f"team:{uid}"] = text
        states[uid] = "choosing"

        bot.send_message(
            message.chat.id,
            "Takım adın kaydedildi. Boş slot seç:",
            reply_markup=slot_keyboard()
        )
        return

    # ADMIN'E MESAJ
    if state == "contact":
        states.pop(uid, None)

        try:
            bot.send_message(
                ADMIN_ID,
                f"💬 Kullanıcı mesajı\n"
                f"ID: {uid}\n\n{text}"
            )
            bot.send_message(
                message.chat.id,
                "Mesajın admin'e gönderildi."
            )
        except Exception:
            bot.send_message(
                message.chat.id,
                "Mesaj gönderilemedi. Admin bota /start yazmalı."
            )
        return

    # TURNUVA KAYDI
    if text == "🏆 Turnuvaya Kayıt Ol":
        if get_slot(uid):
            bot.send_message(
                message.chat.id,
                "Zaten kayıtlısın."
            )
            return

        if get_setting("mode") == "paid":
            if get_payment(uid) != "approved":
                iban = get_setting("iban")

                if not iban:
                    bot.send_message(
                        message.chat.id,
                        "IBAN henüz admin tarafından ayarlanmamış."
                    )
                    return

                bot.send_message(
                    message.chat.id,
                    f"💳 KATILIM ÜCRETİ\n\n"
                    f"Ücret: {get_setting('fee')} TL\n"
                    f"IBAN:\n<code>{html.escape(iban)}</code>\n\n"
                    f"Ödeme yaptıktan sonra dekont fotoğrafını gönder.",
                    parse_mode="HTML"
                )
                return

        states[uid] = "team"
        bot.send_message(
            message.chat.id,
            "Takım adını yaz:"
        )
        return

    # SLOT TABLOSU
    if text == "📋 Slot Tablosu":
        show_slots(message.chat.id)
        return

    # PROFIL
    if text == "👤 Profilim":
        slot = get_slot(uid)

        if slot:
            details = (
                f"Takım: {html.escape(slot[1] or '')}\n"
                f"Slot: {slot[0]}"
            )
        else:
            details = "Henüz kayıtlı değilsin."

        bot.send_message(
            message.chat.id,
            f"👤 PROFİLİM\n"
            f"ID: {uid}\n"
            f"{details}\n"
            f"Ödeme: {get_payment(uid) or 'Gerek yok'}",
            parse_mode="HTML"
        )
        return

    # ODA BILGILERI
    if text == "🔑 Oda Bilgileri":
        if not get_slot(uid):
            bot.send_message(
                message.chat.id,
                "Oda bilgilerini görmek için önce kayıt olmalısın."
            )
            return

        room_id = get_setting("room_id")
        password = get_setting("room_password")

        if room_id and password:
            bot.send_message(
                message.chat.id,
                f"🔑 ODA BİLGİLERİ\n"
                f"Oda ID: {html.escape(room_id)}\n"
                f"Şifre: {html.escape(password)}",
                parse_mode="HTML"
            )
        else:
            bot.send_message(
                message.chat.id,
                "Oda bilgileri henüz admin tarafından girilmedi."
            )
        return

    # ADMIN'E MESAJ GONDER
    if text == "💬 Admin'e Mesaj Gönder":
        states[uid] = "contact"
        bot.send_message(
            message.chat.id,
            "Admin'e göndermek istediğin mesajı yaz:"
        )
        return

    # ADMIN PANEL
    if text == "⚙️ Admin Paneli" and uid == ADMIN_ID:
        admin_panel(message.chat.id)
        return

    bot.send_message(
        message.chat.id,
        "Menüden bir işlem seç.",
        reply_markup=main_menu(uid)
    )


# BOTU BASLAT
setup()
print("Bot çalışıyor...")
bot.infinity_polling(
    skip_pending=True,
    timeout=30,
    long_polling_timeout=30
)
