import sqlite3
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Bot Ayarları
TOKEN = "9110504722:AAGddP_BnHguYkzLnC5X3-YC4i9l6SES1oI"
ADMIN_PASSWORD = "631363"

# Loglama
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- VERİTABANI BAŞLANGICI ---
conn = sqlite3.connect("pubg_turnuva.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS slots (
    slot_id INTEGER PRIMARY KEY,
    user_id INTEGER,
    username TEXT,
    team_name TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    text TEXT
)
""")

# Varsayılan ayarlar
cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('mode', 'BEDAVA')")
cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('fee', '0 TL')")
cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('room_id', 'Henüz verilmedi')")
cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('room_pass', 'Henüz verilmedi')")

# 25 slotu oluştur
for i in range(1, 26):
    cursor.execute("INSERT OR IGNORE INTO slots (slot_id, user_id, username, team_name) VALUES (?, NULL, NULL, NULL)", (i,))
conn.commit()

def get_setting(key):
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    res = cursor.fetchone()
    return res[0] if res else None

def set_setting(key, value):
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()

# Kullanıcı geçici durum hafızası (Memory State)
user_states = {}

# --- ANA MENÜ ---
def main_menu_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🎮 Slot Seç / Tablo", callback_data="menu_slots"),
            InlineKeyboardButton("👤 Profilim", callback_data="menu_profile"),
        ],
        [
            InlineKeyboardButton("💬 Admine Mesaj Gönder", callback_data="menu_msg")
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_states[user.id] = "IDLE"
    text = (
        f"🏆 **PUBG MOBILE TURNUVA BOTU** 🏆\n\n"
        f"Selamlar **{user.first_name}**! Harika bir turnuvaya hazır mısın?\n"
        f"Aşağıdaki butonları kullanarak slotunu seçebilir, profilini inceleyebilir veya admine mesaj yazabilirsin! 🔥"
    )
    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_menu_keyboard())
    elif update.callback_query:
        await update.callback_query.message.edit_text(text, parse_mode="Markdown", reply_markup=main_menu_keyboard())

# --- SLOT & TABLO İŞLEMLERİ ---
async def show_slots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cursor.execute("SELECT slot_id, team_name FROM slots ORDER BY slot_id ASC")
    rows = cursor.fetchall()

    keyboard = []
    row_buttons = []
    for slot_id, team_name in rows:
        if team_name:
            btn_text = f"❌ {slot_id}. Slot ({team_name})"
            callback_data = f"slot_full_{slot_id}"
        else:
            btn_text = f"✅ {slot_id}. Slot (BOŞ)"
            callback_data = f"slot_select_{slot_id}"

        row_buttons.append(InlineKeyboardButton(btn_text, callback_data=callback_data))
        if len(row_buttons) == 1:
            keyboard.append(row_buttons)
            row_buttons = []

    if row_buttons:
        keyboard.append(row_buttons)

    keyboard.append([InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu")])

    mode = get_setting("mode")
    fee = get_setting("fee")

    info_text = f"🎯 **SLOT DURUM TABLOSU (25 Slot)**\nMod: **{mode}**"
    if mode == "ÜCRETLİ":
        info_text += f"\nÜcret: **{fee}**\nIBAN: `TR18 0011 1000 0000 0138 7181 38`\nAlıcı: **Polat Karaer**"

    await query.message.edit_text(info_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def slot_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user

    if data.startswith("slot_full_"):
        await query.answer("Bu slot dolu!", show_alert=True)
        return

    if data.startswith("slot_select_"):
        slot_id = data.split("_")[2]

        cursor.execute("SELECT slot_id FROM slots WHERE user_id = ?", (user.id,))
        existing = cursor.fetchone()
        if existing:
            await query.answer(f"Zaten {existing[0]}. slotta kayıtlısın!", show_alert=True)
            return

        user_states[user.id] = f"WAITING_TEAM_NAME_{slot_id}"

        await query.message.edit_text(
            f"🎯 **{slot_id}. Slotu Seçtiniz!**\n\nLütfen **Takım Adınızı** chat kısmına yazıp gönderin:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 İptal", callback_data="menu_slots")]]),
        )

# --- PROFİL EKRANI ---
async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    cursor.execute("SELECT slot_id, team_name FROM slots WHERE user_id = ?", (user.id,))
    res = cursor.fetchone()

    room_id = get_setting("room_id")
    room_pass = get_setting("room_pass")
    mode = get_setting("mode")

    if res:
        slot_id, team_name = res
        profile_text = (
            f"👤 **OYUNCU PROFİLİ**\n\n"
            f"• **Ad Soyad:** {user.first_name}\n"
            f"• **Takım Adı:** {team_name}\n"
            f"• **Kayıtlı Slot:** {slot_id}. Slot\n"
            f"• **Turnuva Türü:** {mode}\n\n"
            f"🔑 **Oda Bilgileri:**\n"
            f"• **Oda ID:** `{room_id}`\n"
            f"• **Şifre:** `{room_pass}`"
        )
    else:
        profile_text = f"👤 **OYUNCU PROFİLİ**\n\n• **Ad Soyad:** {user.first_name}\n• **Durum:** Henüz bir slot seçmediniz! ❌"

    await query.message.edit_text(
        profile_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu")]]),
    )

# --- ADMİNE MESAJ ---
async def ask_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    user_states[user.id] = "WAITING_ADMIN_MSG"

    await query.message.edit_text(
        "💬 **Admine Mesaj Gönder**\n\nLütfen yetkiliye iletmek istediğin mesajı aşağıya yaz:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 İptal", callback_data="main_menu")]]),
    )

# --- ADMIN PANELİ ---
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_states[user.id] = "WAITING_ADMIN_PASSWORD"
    await update.message.reply_text(
        "🔐 Lütfen Admin Şifresini Girin:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ İptal", callback_data="main_menu")]]),
    )

async def open_admin_panel_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = get_setting("mode")
    room_id = get_setting("room_id")
    room_pass = get_setting("room_pass")

    text = f"⚙️ **ADMİN PANELİ** ⚙️\n\n• **Mevcut Mod:** {mode}\n• **Oda ID:** {room_id} | **Şifre:** {room_pass}"
    keyboard = [
        [InlineKeyboardButton(f"🔄 Mod Değiştir (Şuan: {mode})", callback_data="adm_toggle_mode")],
        [InlineKeyboardButton("🔑 Oda ID & Şifre Belirle", callback_data="adm_set_room")],
        [InlineKeyboardButton("🗑️ Slot Sil / Boşalt", callback_data="adm_del_slot_menu"), InlineKeyboardButton("♻️ Sıfırla", callback_data="adm_reset_all")],
        [InlineKeyboardButton("📥 Gelen Mesajlar", callback_data="adm_view_msgs")],
        [InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu")],
    ]
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def open_admin_panel_query(query):
    mode = get_setting("mode")
    room_id = get_setting("room_id")
    room_pass = get_setting("room_pass")

    text = f"⚙️ **ADMİN PANELİ** ⚙️\n\n• **Mevcut Mod:** {mode}\n• **Oda ID:** {room_id} | **Şifre:** {room_pass}"
    keyboard = [
        [InlineKeyboardButton(f"🔄 Mod Değiştir (Şuan: {mode})", callback_data="adm_toggle_mode")],
        [InlineKeyboardButton("🔑 Oda ID & Şifre Belirle", callback_data="adm_set_room")],
        [InlineKeyboardButton("🗑️ Slot Sil / Boşalt", callback_data="adm_del_slot_menu"), InlineKeyboardButton("♻️ Sıfırla", callback_data="adm_reset_all")],
        [InlineKeyboardButton("📥 Gelen Mesajlar", callback_data="adm_view_msgs")],
        [InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu")],
    ]
    await query.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

# --- MESAJ YÖNETİCİSİ ---
async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    state = user_states.get(user.id, "IDLE")

    if state == "WAITING_ADMIN_PASSWORD":
        user_states[user.id] = "IDLE"
        if text == ADMIN_PASSWORD:
            await update.message.reply_text("✅ Şifre Doğru!")
            await open_admin_panel_msg(update, context)
        else:
            await update.message.reply_text("❌ Hatalı şifre! /admin yazarak tekrar deneyebilirsin.")
        return

    if state.startswith("WAITING_TEAM_NAME_"):
        slot_id = state.split("_")[3]
        user_states[user.id] = "IDLE"

        cursor.execute("UPDATE slots SET user_id = ?, username = ?, team_name = ? WHERE slot_id = ?", (user.id, user.username, text, slot_id))
        conn.commit()

        await update.message.reply_text(
            f"🎉 **Tebrikler!** Başarıyla **{slot_id}. Slotu** kaptın.\nTakım Adı: **{text}**",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(),
        )
        return

    if state == "WAITING_ADMIN_MSG":
        user_states[user.id] = "IDLE"
        cursor.execute("INSERT INTO messages (user_id, username, text) VALUES (?, ?, ?)", (user.id, user.username or user.first_name, text))
        conn.commit()

        await update.message.reply_text("✅ Mesajın admine iletildi!", reply_markup=main_menu_keyboard())
        return

    if state == "WAITING_ROOM_INFO":
        user_states[user.id] = "IDLE"
        parts = text.split(",")
