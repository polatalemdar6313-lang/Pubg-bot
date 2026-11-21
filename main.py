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

# Veri Yapıları
slots = {i: "Boş" for i in range(1, 26)}  # 25 Slot
user_slots = {}  # Hangi kullanıcı hangi slotu almış
admin_states = {}  # Admin şifre giriş aşamaları
registration_states = {}  # Takım adı kayıt aşamaları


# Kanal Abonelik Kontrolü
def check_sub(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
    except Exception:
        pass
    return False


# --- 1. /start KOMUTU ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    
    if not check_sub(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Kanala Katıl", url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}"))
        markup.add(types.InlineKeyboardButton("🔄 Kontrol Et", callback_data="check_subscription"))
        
        bot.send_message(
            message.chat.id,
            "⚠️ **TURNUVAYA KATILIM ŞARTI**\n\n"
            "Devam edebilmek için öncelikle aşağıdaki kanala katılman gerekiyor, kanka! 🎮\n\n"
            f"👉 {CHANNEL_USERNAME}",
            parse_mode="Markdown",
            reply_markup=markup
        )
        return

    show_main_menu(message.chat.id)


def show_main_menu(chat_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🏆 Canlı Slot Tablosu & Kayıt", callback_data="show_slots"))
    
    bot.send_message(
        chat_id,
        "🔥 **WEX ESPORTS TURNUVA MERKEZİ** 🔥\n\n"
        "🏆 *Mücadele başlasın, kazanan inatçı savaşçı olsun!*\n"
        "Aşağıdaki butona tıklayarak slot seçebilirsin. 🚀",
        parse_mode="Markdown",
        reply_markup=markup
    )


# Abonelik Kontrol Butonu
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


# --- 2. /admin KOMUTU (Kesinlikle şifre ister) ---
@bot.message_handler(commands=['admin'])
def admin_login(message):
    admin_states[message.from_user.id] = "waiting_password"
    bot.send_message(
        message.chat.id,
        "🔐 **ADMİN GİRİŞİ**\n\nLütfen admin şifresini gir:",
        parse_mode="Markdown"
    )


# --- 3. SLOT TABLOSU GÖRÜNÜMÜ (Temiz Arayüz) ---
@bot.callback_query_handler(func=lambda call: call.data == "show_slots")
def callback_show_slots(call):
    markup = types.InlineKeyboardMarkup(row_width=5)
    
    buttons = []
    for i in range(1, 26):
        status = "🟢" if slots[i] == "Boş" else "🔴"
        buttons.append(types.InlineKeyboardButton(f"{i} {status}", callback_data=f"slot_{i}"))
    
    markup.add(*buttons)
    markup.add(types.InlineKeyboardButton("❌ Slotumu İptal Et", callback_data="cancel_my_slot"))
    markup.add(types.InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu"))

    table_text = "🎯 **WEX ESPORTS - 25 KİŞİLİK SLOT LİSTESİ** 🎯\n\n"
    for i in range(1, 26):
        team_name = slots[i]
        icon = "🟩" if team_name == "Boş" else "🟥"
        table_text += f"{icon} **Slot {i}:** `{team_name}`\n"

    table_text += "\n*(Kayıt olmak için boş bir slota tıklayabilirsin!)*"

    try:
        bot.edit_message_text(
            table_text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    except:
        bot.send_message(call.message.chat.id, table_text, parse_mode="Markdown", reply_markup=markup)


# Slot Seçme
@bot.callback_query_handler(func=lambda call: call.data.startswith("slot_"))
def callback_select_slot(call):
    slot_num = int(call.data.split("_")[1])
    user_
