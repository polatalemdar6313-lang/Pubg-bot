import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# --- YAPILANDIRMA VE BİLGİLER ---
TOKEN = "9110504722:AAFQKQ4at0W3Y_IQEyiTNZX1pRytl8o0iJM"
ADMIN_TELEGRAM_ID = 6527413549  # Belirttiğin Telegram ID
IBAN = "TR18 0011 1000 0000 0138 7181 38"
ALICI_ADI = "Polat Karaer"
ADMIN_SIFRE = "631363"

# Bellek içi veriler
slots = {i: None for i in range(1, 26)}  # 25 adet slot (Başlangıçta boş)
pending_payments = {}  # Dekont bekleyen kullanıcılar
user_slots = {}        # Kullanıcının aldığı slotlar
tournament_info = {
    "time": "Henüz ayarlanmadı",
    "room_id": "Henüz ayarlanmadı",
    "room_pass": "Henüz ayarlanmadı"
}
admin_sessions = set()  # Admin paneline giriş yapmış kullanıcılar

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    keyboard = [
        [InlineKeyboardButton("🎮 Turnuvaya Kayıt Ol", callback_data="register")],
        [InlineKeyboardButton("👤 Profilim & Bilgiler", callback_data="profile")],
        [InlineKeyboardButton("⚙️ Admin Paneli", callback_data="admin_login")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("PUBG Mobile Turnuva Botuna Hoş Geldiniz! Lütfen yapmak istediğiniz işlemi seçin:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "register":
        text = (
            f"<b>Turnuva Kayıt İşlemi</b>\n\n"
            f"Kayıt ücretini aşağıdaki IBAN adresine gönderiniz:\n\n"
            f"<b>IBAN:</b> <code>{IBAN}</code>\n"
            f"<b>Alıcı:</b> {ALICI_ADI}\n\n"
            f"Ödemeyi yaptıktan sonra lütfen <b>'Ödemeyi Yaptım / Dekont Gönder'</b> butonuna basarak dekontunuzu (veya işlem görselini/açıklamasını) bu sohbete gönderin."
        )
        keyboard = [[InlineKeyboardButton("💳 Ödemeyi Yaptım / Dekont Gönder", callback_data="send_receipt")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    elif data == "send_receipt":
        pending_payments[user_id] = "waiting_receipt"
        await query.edit_message_text("Lütfen ödemeye ait dekontu veya ekran görüntüsünü (yazı veya fotoğraf olarak) doğrudan bu sohbete gönderin.")

    elif data == "profile":
        slot = user_slots.get(user_id, "Henüz slot almadınız.")
        info = tournament_info
        text = (
            f"<b>Profil Bilgileriniz</b>\n\n"
            f"<b>Alınan Slot:</b> {slot}\n\n"
            f"<b>Turnuva Saati:</b> {info['time']}\n"
            f"<b>Oda ID:</b> {info['room_id']}\n"
            f"<b>Oda Şifresi:</b> {info['room_pass']}"
        )
        keyboard = [[InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    elif data == "admin_login":
        admin_sessions.discard(user_id)
        await query.edit_message_text("Lütfen admin paneline girmek için admin şifresini yazıp gönderin:")
        context.user_data["waiting_admin_password"] = True

    elif data.startswith("approve_"):
        target_user_id = int(data.split("_")[1])
        # Boş bir slot bul ve ata
        assigned_slot = None
        for s_id, occupant in slots.items():
            if occupant is None:
                slots[s_id] = target_user_id
                assigned_slot = s_id
                user_slots[target_user_id] = s_id
                break
        
        if assigned_slot:
            await query.edit_message_text(f"Kullanıcının ödemesi onaylandı ve #{assigned_slot} numaralı slot atandı.")
            try:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=f"Tebrikler! Ödemeniz onaylandı. #{assigned_slot} numaralı slot size tanımlandı. Şimdi takım adınızı göndermek için /takimadi <TakımAdınız> komutunu kullanabilirsiniz."
                )
            except Exception:
                pass
        else:
            await query.edit_message_text("Ödeme onaylandı ancak tüm slotlar dolu!")

    elif data.startswith("reject_"):
        target_user_id = int(data.split("_")[1])
        await query.edit_message_text("Ödeme reddedildi.")
        try:
            await context.bot.send_message(chat_id=target_user_id, text="Üzgünüz, ödemeniz onaylanmadı. Lütfen destek ile iletişime geçin.")
        except Exception:
            pass

    elif data == "main_menu":
        keyboard = [
            [InlineKeyboardButton("🎮 Turnuvaya Kayıt Ol", callback_data="register")],
            [InlineKeyboardButton("👤 Profilim & Bilgiler", callback_data="profile")],
            [InlineKeyboardButton("⚙️ Admin Paneli", callback_data="admin_login")]
        ]
        await query.edit_message_text("Ana Menü:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    # Admin şifre kontrolü
    if context.user_data.get("waiting_admin_password"):
        context.user_data["waiting_admin_password"] = False
        if text == ADMIN_SIFRE:
            admin_sessions.add(user_id)
            keyboard = [
                [InlineKeyboardButton("⏰ Turnuva Saati Ayarla", callback_data="set_time")],
                [InlineKeyboardButton("🔑 Oda Bilgilerini Ayarla", callback_data="set_room")]
            ]
            # Alternatif olarak komutlar üzerinden de yönetilebilir
            await update.message.reply_text(
                "Admin paneline başarıyla giriş yaptınız!\n\n"
                "Komutlar:\n"
                "/saat <00:00> - Turnuva saatini ayarlar ve herkese bildirir.\n"
                "/odabilgi <ID> <Sifre> - Oda bilgilerini ayarlar ve bildirir.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.message.reply_text("Şifre yanlış! İşlem iptal edildi.")
        return

    # Dekont gönderme aşamasındaki kullanıcı
    if pending_payments.get(user_id) == "waiting_receipt":
        pending_payments[user_id] = "sent"
        username = update.effective_user.username or update.effective_user.first_name
        
        # Admine bildirim gönder
        keyboard = [
            [InlineKeyboardButton("Onayla", callback_data=f"approve_{user_id}"),
             InlineKeyboardButton("Reddet", callback_data=f"reject_{user_id}")]
        ]
        try:
            await context.bot.send_message(
                chat_id=ADMIN_TELEGRAM_ID,
                text=f"🔔 <b>Yeni Dekont Bildirimi!</b>\n\nKullanıcı: @{username} (ID: <code>{user_id}</code>)\nGönderilen İçerik: {text}",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )
        except Exception as e:
            logging.error(f"Admin bildirim hatası: {e}")

        await update.message.reply_text("Dekontunuz adminlere iletildi. Onaylandığında size bilgi verilecektir.")
        return

async def set_time_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in admin_sessions and user_id != ADMIN_TELEGRAM_ID:
        await update.message.reply_text("Bu komutu kullanmaya yetkiniz yok.")
        return

    if not context.args:
        await update.message.reply_text("Kullanım: /saat 20:00 şeklinde yazınız.")
        return

    new_time = " ".join(context.args)
    tournament_info["time"] = new_time
    await update.message.reply_text(f"Turnuva saati başarıyla {new_time} olarak ayarlandı.")

    # Tüm kayıtlı kullanıcılara bildirim gönder
    for u_id in user_slots.keys():
        try:
            await context.bot.send_message(chat_id=u_id, text=f"📢 <b>Duyuru:</b> Turnuva saati güncellendi! Yeni saat: <b>{new_time}</b>", parse_mode="HTML")
        except Exception:
            pass

async def set_room_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in admin_sessions and user_id != ADMIN_TELEGRAM_ID:
        await update.message.reply_text("Bu komutu kullanmaya yetkiniz yok.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Kullanım: /odabilgi <OdaID> <OdaSifresi>")
        return

    r_id = context.args[0]
    r_pass = context.args[1]
    tournament_info["room_id"] = r_id
    tournament_info["room_pass"] = r_pass

    await update.message.reply_text(f"Oda bilgileri ayarlandı:\nID: {r_id}\nŞifre: {r_pass}")

    # Tüm kullanıcılara bildirim gönder
    for u_id in user_slots.keys():
        try:
            await context.bot.send_message(
                chat_id=u_id,
                text=f"🔑 <b>Admin Şifresi / Oda Bilgileri Ayarlandı!</b>\nProfilinizden oda detaylarını görebilirsiniz.\nOda ID: {r_id}\nŞifre: {r_pass}",
                parse_mode="HTML"
            )
        except Exception:
            pass

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("saat", set_time_command))
    app.add_handler(CommandHandler("odabilgi", set_room_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    print("Bot çalışıyor...")
    app.run_polling()

if __name__ == '__main__':
    main()
