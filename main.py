import telebot

# Bot tokenin ve Admin ID'n eklendi:
TOKEN = "9110504722:AAGddP_BnHguYkzLnC5X3-YC4i9l6SES1oI"
bot = telebot.TeleBot(TOKEN)

ADMIN_ID = 6527413549

IBAN_BILGISI = """
🏦 **PUBG Mobile Turnuva Ödeme Bilgileri**

* **IBAN:** `TR00 0000 0000 0000 0000 0000 00`
* **Alıcı Adı:** Adınız Soyadınız
* **Katılım Ücreti:** 50 TL

⚠️ Ödemeyi yaptıktan sonra dekontu veya onay kodunu doğrudan buraya gönder!
"""

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = telebot.types.KeyboardButton("💳 IBAN ve Ödeme Bilgisi")
    btn2 = telebot.types.KeyboardButton("🎟️ Kod / Dekont Gönder")
    markup.add(btn1, btn2)
    
    bot.reply_to(message, "🎮 **PUBG Mobile Turnuva Botuna Hoş Geldin!**", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "💳 IBAN ve Ödeme Bilgisi")
def send_iban(message):
    bot.send_message(message.chat.id, IBAN_BILGISI, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "🎟️ Kod / Dekont Gönder")
def ask_for_code(message):
    bot.send_message(message.chat.id, "Lütfen ödemeyi yaptıktan sonra dekontu veya kodunu buraya yaz.", parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_user_message(message):
    user = message.from_user
    user_text = message.text
    
    bot.reply_to(message, "✅ Bildirimin alındı! İncelendikten sonra onaylanacak.")
    
    try:
        bot.send_message(
            ADMIN_ID,
            f"🔔 **Yeni Bildirim!**\n\n"
            f"👤 Kullanıcı: @{user.username} ({user.first_name})\n"
            f"💬 Mesaj: {user_text}",
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Hata: {e}")

print("Bot çalışıyor...")
bot.infinity_polling()
