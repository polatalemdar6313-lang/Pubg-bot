import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# Bot Loglama Ayarları
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# 25 Slotluk Turnuva Veri Tabanı
slots = {i: {"durum": "Boş", "takim": "-", "logo": "-"} for i in range(1, 26)}

# Kullanıcıların geçici durumlarını tutmak için
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
            "🏆 *Ana Menü:*\nİstediğiniz işlemi seçin:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
# Metin Mesajlarını Yönetme
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    if user_id not in user_states:
        return

    state = user_states[user_id]

    if state == "waiting_slot":
        try:
            slot_no = int(text)
            if slot_no < 1 or slot_no > 25:
                await update.message.reply_text("❌ Hata: Lütfen 1 ile 25 arasında geçerli bir slot numarası girin.")
                return

            if slots[slot_no]["durum"] == "Dolu":
                await update.message.reply_text(f"⚠️ Slot {slot_no} maalesef dolu! Lütfen başka bir slot numarası yazın:")
                return

            user_states[user_id] = {"state": "waiting_team_name", "slot": slot_no}
            await update.message.reply_text(f"✅ Slot {slot_no} seçildi.\n\nŞimdi lütfen *Takım Adınızı* yazın (Zorunlu):", parse_mode="Markdown")
        
        except ValueError:
            await update.message.reply_text("❌ Hata: Lütfen geçerli bir sayı girin (Örn: 5).")

    elif isinstance(state, dict) and state.get("state") == "waiting_team_name":
        if not text:
            await update.message.reply_text("❌ Takım adı boş bırakılamaz! Lütfen takım adını yazın:")
            return
        
        slot_no = state["slot"]
        user_states[user_id] = {"state": "waiting_logo", "slot": slot_no, "team_name": text}
        await update.message.reply_text("✨ Takım adı alındı.\n\nİstiyorsorsanız *Logo/Sembol* yazın (Geçmek için `-` yazabilirsiniz):")

    elif isinstance(state, dict) and state.get("state") == "waiting_logo":
        slot_no = state["slot"]
        team_name = state["team_name"]
        logo = text if text != "-" else "-"

        slots[slot_no] = {"durum": "Dolu", "takim": team_name, "logo": logo}
        del user_states[user_id]

        await update.message.reply_text(
            f"🎉 *Tebrikler Başarıyla Kayıt Oldunuz!*\n\n"
            f"📌 Slot: {slot_no}\n"
            f"🛡️ Takım: {team_name}\n"
            f"🎨 Logo: {logo}\n\n"
            f"Tabloyu görmek için /start yazabilirsiniz.",
            parse_mode="Markdown"
        )

# Botu Başlatma Ana Bloğu
if __name__ == '__main__':
    TOKEN = "9172005481:AAEbc_bAij8pRfdEvcDM9V1egFGzyl9QjaM"
    
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message_handler))

    print("Bot aktif ve çalışıyor...")
    app.run_polling()
