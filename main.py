import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# Bot Loglama Ayarları
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# 25 Slotluk Turnuva Veri Tabanı
slots = {i: {"durum": "Boş", "takim": "-", "logo": "-"} for i in range(1, 26)}

# Kullanıcıların geçici durumlarını tutmak için (Hangi slotu seçti vb.)
user_states = {}

# /start Komutu
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📋 Turnuva Tablosunu Gör", callback_data="liste")],
        [InlineKeyboardButton("🎮 Slot Seç / Kayıt Ol", callback_data="kayit_sec")],
        [InlineKeyboardButton("📢 Admin Kanalı ve Şifreler", callback_data="admin_kanal")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🏆 *PUBG Turnuva Kayıt Sistemine Hoş Geldiniz!*\n\n"
        "Aşağıdaki menüyü kullanarak slot seçebilir veya güncel tabloyu inceleyebilirsiniz.",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# Buton Yönlendirmeleri
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "liste":
        text = "📊 *GÜNCEL TURNUVA TABLOSU*\n\n"
        for n, b in slots.items():
            if b["durum"] == "Boş":
                text += f"Slot {n:2d}: [BOŞ]\n"
            else:
                if b["logo"] == "-":
                    text += f"Slot {n:2d}: [DOLU] | {b['takim']}\n"
                else:
                    text += f"Slot {n:2d}: [DOLU] | {b['takim']} | Logo: {b['logo']}\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Ana Menü", callback_data="ana_menu")]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "kayit_sec":
        user_states[user_id] = "waiting_slot"
        await query.edit_message_text(
            "📝 Lütfen kayıt olmak istediğiniz **Slot Numarasını (1-25 arası)** rakam olarak yazıp gönderin:"
        )

    elif data == "admin_kanal":
        text = (
            "📢 *ADMIN KANALI VE ODA BİLGİLERİ*\n\n"
            "Tüm kayıtlar tamamlandıktan sonra oda ID ve şifreler aşağıdaki kanalda paylaşılacaktır:\n\n"
            "🔗 [Admin Duyuru Kanalı Linki](https://t.me/ornek_kanal_linki)"
        )
        keyboard = [[InlineKeyboardButton("🔙 Ana Menü", callback_data="ana_menu")]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown", disable_web_page_preview=True)

    elif data == "ana_menu":
        if user_id in user_states:
            del user_states[user_id]
        keyboard = [
            [InlineKeyboardButton("📋 Turnuva Tablosunu Gör", callback_data="liste")],
            [InlineKeyboardButton("🎮 Slot Seç / Kayıt Ol", callback_data="kayit_sec")],
            [InlineKeyboardButton("📢 Admin Kanalı ve Şifreler", callback_data="admin_kanal")]
        ]
        await query.edit_message_text(
