import sys
import subprocess

# Kütüphane otomatik yükleyici
try:
    import telebot
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyTelegramBotAPI", "flask"])
    import telebot

from telebot import types
import time
from flask import Flask
from threading import Thread

# Render'ın servisi kapatmaması için mini web sunucusu
app = Flask('')

@app.route('/')
def home():
    return "WEX Bot Aktif ve Çalışıyor! 🚀"

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# Token ve Kanal Bilgileri
TOKEN = "9172005481:AAEbc_bAij8pRfdEvcDM9V1egFGzyl9QjaM"
CHANNEL_USERNAME = "@wexorganizasyon"
ADMIN_PASSWORD = "631363"

bot = telebot.TeleBot(TOKEN)

slots = {i: "Boş" for i in range(1, 26)}
user_slots = {}
admin_states = {}
registration_states = {}

def check_sub(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
    except Exception:
        pass
    return False

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    if not check_sub(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Kanala Katıl", url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}"))
        markup.add(types.InlineKeyboardButton("🔄 Kontrol Et", callback_data="check_subscription"))
        bot.send_message(
            message.chat.id,
            "⚠️ **TURNUVAYA KATILIM ŞARTI**\n\nDevam edebilmek için öncelikle aşağıdaki kanala katılman gerekiyor, kanka! 🎮\n\n👉 " + CHANNEL_USERNAME,
            parse_mode="Markdown",
            reply_markup=markup
        )
        return
    show_main_menu(message.chat.id)

def show_main_menu(chat_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🏆 Slot Tablosu & Kayıt Ol", callback_data="show_slots"))
    bot.send_message(
        chat_id,
        "🔥 **WEX ESPORTS TURNUVA MERKEZİNE HOŞ GELDİN!** 🔥\n\n🏆 *Mücadele başlasın, kazanan inatçı savaşçı olsun!*\nAşağıdaki butonu kullanarak slot seçebilirsin. 🚀",
        parse_mode="Markdown",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "check_subscription")
def callback_check_sub(call):
    if check_sub(call.from_user.id):
        bot.answer_callback_query(call.id, "Tebrikler! Kanal doğrulandı. 🎉")
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        show_main_menu(call.message.chat.id)
    else:
        bot.answer_callback_query(call.id, "Henüz kanala katılmamışsın!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "show_slots")
def callback_show_slots(call):
    markup = types.InlineKeyboardMarkup(row_width=5)
    buttons = []
    for i in range(1, 26):
        status = "🟢" if slots[i] == "Boş" else "🔴"
        buttons.append(types.InlineKeyboardButton(f"{i}. Slot {status}", callback_data=f"slot_{i}"))
    markup.add(*buttons)
    markup.add(types.InlineKeyboardButton("❌ Slotumu İptal Et", callback_data="cancel_my_slot"))
    markup.add(types.InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu"))

    table_text = "🎯 **CANLI SLOT TABLOSU** 🎯\n\n"
    for i in range(1, 26):
        team_name = slots[i]
        icon = "🟩" if team_name == "Boş" else "🟥"
        table_text += f"{icon} **Slot {i}:** `{team_name}`\n"
    table_text += "\n*(Kayıt olmak için boş bir slota tıklayabilirsin!)*"

    try:
        bot.edit_message_text(table_text, call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)
    except:
        bot.send_message(call.message.chat.id, table_text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("slot_"))
def callback_select_slot(call):
    slot_num = int(call.data.split("_")[1])
    user_id = call.from_user.id
    if user_id in user_slots:
        bot.answer_callback_query(call.id, f"Zaten {user_slots[user_id]}. slotta kaydın var!", show_alert=True)
        return
    if slots[slot_num] != "Boş":
        bot.answer_callback_query(call.id, "Bu slot maalesef dolu, başka bir tane seç!", show_alert=True)
        return
    registration_states[user_id] = slot_num
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ İptal Et", callback_data="show_slots"))
    bot.send_message(call.message.chat.id, f"🎯 **{slot_num}. Slot** için işlem yapıyorsun.\n\nLütfen katılacak **Takım Adını** mesaj olarak yaz gönder:", parse_mode="Markdown", reply_markup=markup)
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: message.from_user.id in registration_states)
def get_team_name(message):
    user_id = message.from_user.id
    slot_num = registration_states[user_id]
    team_name = message.text.strip()
    if len(team_name) > 30:
        bot.send_message(message.chat.id, "⚠️ Takım adı çok uzun! Lütfen en fazla 30 karakter gir.")
        return
    slots[slot_num] = team_name
    user_slots[user_id] = slot_num
    del registration_states[user_id]
    bot.send_message(message.chat.id, f"✅ **BAŞARILI!**\n\n🏆 **Takım:** `{team_name}`\n📍 **Seçilen Slot:** `{slot_num}. Slot`\n\nBol şans dileriz! 🔥", parse_mode="Markdown")
    show_main_menu(message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data == "cancel_my_slot")
def callback_cancel_slot(call):
    user_id = call.from_user.id
    if user_id not in user_slots:
        bot.answer_callback_query(call.id, "Aktif bir slot kaydın bulunmuyor!", show_alert=True)
        return
    slot_num = user_slots[user_id]
    slots[slot_num] = "Boş"
    del user_slots[user_id]
    bot.answer_callback_query(call.id, f"{slot_num}. slot üzerindeki kaydın iptal edildi.")
    callback_show_slots(call)

@bot.callback_query_handler(func=lambda call: call.data == "main_menu")
def callback_main_menu(call):
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
    show_main_menu(call.message.chat.id)

@bot.message_handler(commands=['admin'])
def admin_login(message):
    admin_states[message.from_user.id] = "waiting_password"
    bot.send_message(message.chat.id, "🔐 **ADMİN GİRİŞİ**\n\nLütfen admin şifresini gir:", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.from_user.id in admin_states)
def admin_panel_handler(message):
    user_id = message.from_user.id
    state = admin_states.get(user_id)
    if state == "waiting_password":
        if message.text.strip() == ADMIN_PASSWORD:
            admin_states[user_id] = "logged_in"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔄 Turnuvayı Sıfırla", callback_data="admin_reset"))
            markup.add(types.InlineKeyboardButton("⏳ Geri Sayım Başlat", callback_data="admin_countdown"))
            bot.send_message(message.chat.id, "👑 **ADMİN PANELİNE HOŞ GELDİNİZ**\n\nYönetmek istediğiniz işlemi seçin:", parse_mode="Markdown", reply_markup=markup)
        else:
            bot.send_message(message.chat.id, "❌ Hatalı şifre!")
            admin_states.pop(user_id, None)

@bot.callback_query_handler(func=lambda call: call.data == "admin_reset")
def admin_reset_tournament(call):
    if admin_states.get(call.from_user.id) != "logged_in":
        return
    global slots, user_slots
    slots = {i: "Boş" for i in range(1, 26)}
    user_slots.clear()
    bot.answer_callback_query(call.id, "Turnuva başarıyla sıfırlandı!")
    bot.send_message(call.message.chat.id, "🔄 Tüm slotlar temizlendi!")

@bot.callback_query_handler(func=lambda call: call.data == "admin_countdown")
def admin_start_countdown(call):
    if admin_states.get(call.from_user.id) != "logged_in":
        return
    bot.answer_callback_query(call.id, "Geri sayım başlatıldı!")
    msg = bot.send_message(call.message.chat.id, "⏳ **TURNUVAYA KALAN SÜRE**\n\nBaşlangıç: **10 saniye** kaldı! 🚀", parse_mode="Markdown")
    for i in range(9, 0, -1):
        time.sleep(1)
        try:
            bot.edit_message_text(f"⏳ **TURNUVAYA KALAN SÜRE**\n\nBaşlangıç: **{i} saniye** kaldı! 🚀", call.message.chat.id, msg.message_id, parse_mode="Markdown")
        except:
            pass
    time.sleep(1)
    try:
        bot.edit_message_text("🚨 **START! START! START!**\n\n🔥 Turnuva başlamıştır!", call.message.chat.id, msg.message_id, parse_mode="Markdown")
    except:
        pass

if __name__ == "__main__":
    keep_alive()  # Web sunucusunu başlat (Render kapanmasın diye)
    print("WEX Event Bot aktif ve çalışıyor...")
    bot.infinity_polling()
