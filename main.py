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

# Tabloları oluştur
cursor.execute(
    """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)
"""
)

cursor.execute(
    """
CREATE TABLE IF NOT EXISTS slots (
    slot_id INTEGER PRIMARY KEY,
    user_id INTEGER,
    username TEXT,
    team_name TEXT
)
"""
)

cursor.execute(
    """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    text TEXT
)
"""
)

# Varsayılan ayarları ekle
cursor.execute(
    "INSERT OR IGNORE INTO settings (key, value) VALUES ('mode', 'BEDAVA')"
)
cursor.execute(
    "INSERT OR IGNORE INTO settings (key, value) VALUES ('fee', '0 TL')"
)
cursor.execute(
    "INSERT OR IGNORE INTO settings (key, value) VALUES ('room_id', 'Henüz verilmedi')"
)
cursor.execute(
    "INSERT OR IGNORE INTO settings (key, value) VALUES ('room_pass', 'Henüz verilmedi')"
)
cursor.execute(
    "INSERT OR IGNORE INTO settings (key, value) VALUES ('admin_state', 'IDLE')"
)

# 25 slotu oluştur
for i in range(1, 26):
    cursor.execute(
        "INSERT OR IGNORE INTO slots (slot_id, user_id, username, team_name) VALUES (?, NULL, NULL, NULL)",
        (i,),
    )
conn.commit()


def get_setting(key):
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    return cursor.fetchone()[0]


def set_setting(key, value):
    cursor.execute(
        "UPDATE settings SET value = ? WHERE key = ?", (value, str(value))
    )
    conn.commit()


# --- ANA MENÜ ---
def main_menu_keyboard(user_id):
    mode = get_setting("mode")
    keyboard = [
        [
            InlineKeyboardButton("🎮 Slot Seç / Tablo", callback_data="menu_slots"),
            InlineKeyboardButton("👤 Profilim", callback_data="menu_profile"),
        ],
        [
            InlineKeyboardButton(
                "💬 Admine Mesaj Gönder", callback_data="menu_msg"
            )
        ],
    ]
    # Admin kontrolü (İsteyen kullanıcı doğrudan komutla da şifre girebilir)
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"🏆 **PUBG MOBILE TURNUVA BOTU** 🏆\n\n"
        f"Selamlar **{user.first_name}**! Harika bir turnuvaya hazır mısın?\n"
        f"Aşağıdaki butonları kullanarak slotunu seçebilir, profilini inceleyebilir veya admine mesaj yazabilirsin! 🔥"
    )
    if update.message:
        await update.message.reply_text(
            text, parse_mode="Markdown", reply_markup=main_menu_keyboard(user.id)
        )
    elif update.callback_query:
        await update.callback_query.message.edit_text(
            text, parse_mode="Markdown", reply_markup=main_menu_keyboard(user.id)
        )


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

        row_buttons.append(
            InlineKeyboardButton(btn_text, callback_data=callback_data)
        )
        if len(row_buttons) == 1:  # Her satırda 1 slot listesi veya yan yana 2 tane
            keyboard.append(row_buttons)
            row_buttons = []

    if row_buttons:
        keyboard.append(row_buttons)

    keyboard.append([InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu")])

    mode = get_setting("mode")
    fee = get_setting("fee")

    info_text = f"🎯 **SLOT DURUM TABLOSU (25 Slot)**\nMod: **{mode}**"
    if mode == "ÜCRETLİ":
        info_text += (
            f"\nÜcret: **{fee}**\nIBAN: `TR18 0011 1000 0000 0138 7181 38`\nAlıcı: **Polat Karaer**"
        )

    await query.message.edit_text(
        info_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def slot_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # Zaten dolu bir slota tıklandıysa
    if data.startswith("slot_full_"):
        await query.answer("Bu slot dolu!", show_alert=True)
        return

    # Boş bir slota tıklandıysa
    if data.startswith("slot_select_"):
        slot_id = data.split("_")[2]

        # Kullanıcının zaten bir slotu var mı kontrol et
        cursor.execute(
            "SELECT slot_id FROM slots WHERE user_id = ?", (query.from_user.id,)
        )
        existing = cursor.fetchone()
        if existing:
            await query.answer(
                f"Zaten {existing[0]}. slotta kayıtlısın! Her kullanıcı 1 slot alabilir.",
                show_alert=True,
            )
            return

        # Takım adı girmesini isteyeceğiz, context'e slot_id kaydedelim
        context.user_data["selecting_slot"] = slot_id
        set_setting(f"state_{query.from_user.id}", f"WAITING_TEAM_NAME_{slot_id}")

        await query.message.edit_text(
            f"🎯 **{slot_id}. Slotu Seçtiniz!**\n\nLütfen **Takım Adınızı** (veya Kendi Adınızı) chat kısmına yazıp gönderin:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 İptal / Slotlar", callback_data="menu_slots")]]
            ),
        )


# --- PROFİL EKRANI ---
async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    cursor.execute(
        "SELECT slot_id, team_name FROM slots WHERE user_id = ?", (user.id,)
    )
    res = cursor.fetchone()

    room_id = get_setting("room_id")
    room_pass = get_setting("room_pass")
    mode = get_setting("mode")

    if res:
        slot_id, team_name = res
        profile_text = (
            f"👤 **OYUNCU PROFİLİ**\n\n"
            f"• **Ad Soyad:** {user.first_name}\n"
            f"• **Kullanıcı Adı:** @{user.username if user.username else 'Yok'}\n"
            f"• **Takım Adı:** {team_name}\n"
            f"• **Kayıtlı Slot:** {slot_id}. Slot\n"
            f"• **Turnuva Türü:** {mode}\n\n"
            f"🔑 **Oda Bilgileri:**\n"
            f"• **Oda ID:** `{room_id}`\n"
            f"• **Şifre:** `{room_pass}`"
        )
    else:
        profile_text = (
            f"👤 **OYUNCU PROFİLİ**\n\n"
            f"• **Ad Soyad:** {user.first_name}\n"
            f"• **Durum:** Henüz bir slot seçmediniz! ❌"
        )

    await query.message.edit_text(
        profile_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu")]]
        ),
    )


# --- ADMİNE MESAJ GÖNDERME ---
async def ask_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    set_setting(f"state_{query.from_user.id}", "WAITING_ADMIN_MSG")

    await query.message.edit_text(
        "💬 **Admine Mesaj Gönder**\n\nLütfen yetkiliye iletmek istediğin mesajı aşağıya yaz:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 İptal", callback_data="main_menu")]]
        ),
    )


# --- ADMIN PANELİ & ŞİFRE KONTROLÜ ---
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Eğer komutla geldiyse
    if update.message:
        await update.message.reply_text(
            "🔐 Lütfen Admin Şifresini Girin:",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("❌ İptal", callback_data="main_menu")]]
            ),
        )
        set_setting(f"state_{update.effective_user.id}", "WAITING_ADMIN_PASSWORD")


async def open_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    mode = get_setting("mode")
    room_id = get_setting("room_id")
    room_pass = get_setting("room_pass")

    text = (
        f"⚙️ **ADMİN PANELİ** ⚙️\n\n"
        f"• **Mevcut Mod:** {mode}\n"
        f"• **Oda ID:** {room_id} | **Oda Şifre:** {room_pass}\n\n"
        f"İşlem seçin:"
    )

    keyboard = [
        [
            InlineKeyboardButton(
                f"🔄 Mod Değiştir (Şuan: {mode})", callback_data="adm_toggle_mode"
            )
        ],
        [
            InlineKeyboardButton(
                "🔑 Oda ID & Şifre Belirle", callback_data="adm_set_room"
            )
        ],
        [
            InlineKeyboardButton("🗑️ Slot Sil / Boşalt", callback_data="adm_del_slot_menu"),
            InlineKeyboardButton("♻️ Turnuvayı Sıfırla", callback_data="adm_reset_all"),
        ],
        [InlineKeyboardButton("📥 Gelen Mesajlar", callback_data="adm_view_msgs")],
        [InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu")],
    ]

    await query.message.edit_text(
        text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )


# --- METİN VE DURUM YÖNETİCİSİ (MessageHandler) ---
async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    state = get_setting(f"state_{user.id}")

    # 1. Admin Şifre Kontrolü
    if state == "WAITING_ADMIN_PASSWORD":
        set_setting(f"state_{user.id}", "IDLE")
        if text == ADMIN_PASSWORD:
            # Fake bir callbackquery oluşturalım ki paneli açabilelim
            await update.message.reply_text("✅ Şifre Doğru! Admin Paneli Açılıyor...")
            # Panel arayüzünü gönder
            mode = get_setting("mode")
            room_id = get_setting("room_id")
            room_pass = get_setting("room_pass")
            keyboard = [
                [
                    InlineKeyboardButton(
                        f"🔄 Mod Değiştir (Şuan: {mode})",
                        callback_data="adm_toggle_mode",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🔑 Oda ID & Şifre Belirle",
                        callback_data="adm_set_room",
                    )
                ],
                [
                    InlineKeyboardButton("🗑️ Slot Sil / Boşalt", callback_data="adm_del_slot_menu"),
                    InlineKeyboardButton("♻️ Turnuvayı Sıfırla", callback_data="adm_reset_all"),
                ],
                [InlineKeyboardButton("📥 Gelen Mesajlar", callback_data="adm_view_msgs")],
                [InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu")],
            ]
            await update.message.reply_text(
                "⚙️ **ADMİN PANELİ** ⚙️",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        else:
            await update.message.reply_text("❌ Hatalı şifre! /admin yazarak tekrar deneyebilirsin.")
        return

    # 2. Takım Adı Kaydetme
    if state and state.startswith("WAITING_TEAM_NAME_"):
        slot_id = state.split("_")[3]
        set_setting(f"state_{user.id}", "IDLE")

        # Veritabanına kaydet
        cursor.execute(
            "UPDATE slots SET user_id = ?, username = ?, team_name = ? WHERE slot_id = ?",
            (user.id, user.username, text, slot_id),
        )
        conn.commit()

        await update.message.reply_text(
            f"🎉 **Tebrikler!** Başarıyla **{slot_id}. Slotu** kaptın.\nTakım Adı: **{text}**\n\nProfilinden kontrol edebilirsin!",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(user.id),
        )
        return

    # 3. Admine Mesaj Gönderme
    if state == "WAITING_ADMIN_MSG":
        set_setting(f"state_{user.id}", "IDLE")
        cursor.execute(
            "INSERT INTO messages (user_id, username, text) VALUES (?, ?, ?)",
            (user.id, user.username or user.first_name, text),
        )
        conn.commit()

        await update.message.reply_text(
            "✅ Mesajın başarıyla admine iletildi! En kısa sürede dönüş yapılacaktır.",
            reply_markup=main_menu_keyboard(user.id),
        )
        return

    # 4. Oda ID ve Şifre Belirleme (Admin yazıyor)
    if state == "WAITING_ROOM_INFO":
        set_setting(f"state_{user.id}", "IDLE")
        parts = text.split(",")
        if len(parts) == 2:
            r_id = parts[0].strip()
            r_pass = parts[1].strip()
            set_setting("room_id", r_id)
            set_setting("room_pass", r_pass)
            await update.message.reply_text(
                f"✅ Oda bilgileri güncellendi!\nOda ID: `{r_id}`\nŞifre: `{r_pass}`",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(
                "❌ Hatalı format! Lütfen şu şekilde yazın: `OdaID, Sifre` (Örn: `1234567, 1234`)"
            )
        return

    # Normal mesajlar
    await update.message.reply_text(
        "Lütfen menüyü kullanın 👇", reply_markup=main_menu_keyboard(user.id)
    )


# --- ADMIN CALLBACK İŞLEMLERİ ---
async def admin_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data == "main_menu":
        await start(update, context)
        return

    if data == "menu_slots":
        await show_slots(update, context)
    elif data == "menu_profile":
        await show_profile(update, context)
    elif data == "menu_msg":
        await ask_admin_message(update, context)

    # Admin Paneli Tuşları
    elif data == "adm_toggle_mode":
        current_mode = get_setting("mode")
        new_mode = "ÜCRETLİ" if current_mode == "BEDAVA" else "BEDAVA"
        set_setting("mode", new_mode)
        if new_mode == "ÜCRETLİ":
            set_setting("fee", "50 TL")
        else:
            set_setting("fee", "0 TL")
        await query.answer(f"Mod değiştirildi: {new_mode}", show_alert=True)
        await open_admin_panel(update, context)

    elif data == "adm_set_room":
        set_setting(f"state_{query.from_user.id}", "WAITING_ROOM_INFO")
        await query.message.edit_text(
            "🔑 Lütfen yeni Oda ID ve Şifreyi araya virgül koyarak yazın:\n\n*Örnek Format:* `9876543, 5678`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Admin Panele Dön", callback_data="adm_panel_back")]]
            ),
        )

    elif data == "adm_reset_all":
        cursor.execute("UPDATE slots SET user_id = NULL, username = NULL, team_name = NULL")
        set_setting("room_id", "Henüz verilmedi")
        set_setting("room_pass", "Henüz verilmedi")
        conn.commit()
        await query.answer("Turnuva tamamen sıfırlandı!", show_alert=True)
        await open_admin_panel(update, context)

    elif data == "adm_del_slot_menu":
        # Slot silme menüsü göster
        cursor.execute("SELECT slot_id, team_name FROM slots WHERE team_name IS NOT NULL")
        rows = cursor.fetchall()
        if not rows:
            await query.answer("Dolu slot bulunmuyor!", show_alert=True)
            return
        keyboard = []
        for s_id, t_name in rows:
            keyboard.append([InlineKeyboardButton(f"Sil: {s_id}. Slot ({t_name})", callback_data=f"adm_del_{s_id}")])
        keyboard.append([InlineKeyboardButton("🔙 Admin Panele Dön", callback_data="adm_panel_back")])
        await query.message.edit_text("🗑️ Silmek istediğiniz slotu seçin:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("adm_del_"):
        slot_id = data.split("_")[2]
        cursor.execute("UPDATE slots SET user_id = NULL, username = NULL, team_name = NULL WHERE slot_id = ?", (slot_id,))
        conn.commit()
        await query.answer(f"{slot_id}. slot boşaltıldı!", show_alert=True)
        await open_admin_panel(update, context)

    elif data == "adm_view_msgs":
        cursor.execute("SELECT username, text FROM messages ORDER BY id DESC LIMIT 10")
        rows = cursor.fetchall()
        if not rows:
            msg_text = "📥 Hiç mesaj yok."
        else:
            msg_text = "📥 **Son Gelen Mesajlar:**\n\n"
            for uname, mtext in rows:
                msg_text += f"👤 @{uname}:\n💬 {mtext}\n------------------\n"
        
        await query.message.edit_text(
            msg_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Admin Panele Dön", callback_data="adm_panel_back")]]
            ),
        )

    elif data == "adm_panel_back":
        # Şifre sormadan direkt admin paneli arayüzünü aç
        mode = get_setting("mode")
        room_id = get_setting("room_id")
        room_pass = get_setting("room_pass")
        keyboard = [
            [InlineKeyboardButton(f"🔄 Mod Değiştir (Şuan: {mode})", callback_data="adm_toggle_mode")],
            [InlineKeyboardButton("🔑 Oda ID & Şifre Belirle", callback_data="adm_set_room")],
            [InlineKeyboardButton("🗑️ Slot Sil / Boşalt", callback_data="adm_del_slot_menu"), InlineKeyboardButton("♻️ Turnuvayı Sıfırla", callback_data="adm_reset_all")],
            [InlineKeyboardButton("📥 Gelen Mesajlar", callback_data="adm_view_msgs")],
            [InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu")],
        ]
        await query.message.edit_text("⚙️ **ADMİN PANELİ** ⚙️", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


def main():
    application = ApplicationBuilder().token(TOKEN).build()

    # Handler'lar
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_command))
    
    application.add_handler(CallbackQueryHandler(admin_callbacks, pattern="^(menu_|slot_|adm_|main_menu)"))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text_messages))

    print("@Wexturnuva_bot başarıyla başlatıldı ve çalışıyor! 🚀")
    application.run_polling()


if __name__ == "__main__":
    main()
