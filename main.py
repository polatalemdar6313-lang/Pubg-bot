import sys
import subprocess
import os

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

# Render port uyumlu mini web sunucusu
app = Flask('')

@app.route('/')
def home():
    return "WEX Bot Aktif ve Çalışıyor! 🚀"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.daemon = True
    t.start()

# Token ve Kanal Bilgileri
TOKEN = "9172005481:AAEbc_bAij8pRfdEvcDM9V1egFGzyl9QjaM"
CHANNEL_USERNAME = "@wexorganizasyon"
ADMIN_PASSWORD = "631363"

bot = telebot.TeleBot(TOKEN)

# Veri Yapıları
slots = {i: "Boş" for i in range(1, 26)}  # 25 Slot
user_slots = {}  # user_id -> slot_num
user_teams = {}  # user_id -> team_name
admin_states = {}  # user_id -> state
registration_states = {}  # user_id -> slot_num

# Turnuva Oda Bilgileri (Admin belirleyecek)
tournament_room = {
    "room_id": "Henüz belirlenmedi",
    "room_pass": "Henüz belirlenmedi"
}


# Kanal Abonelik Kontrolü
def check_sub(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
    except Exception:
        pass
    return False


# --- ANA MENÜ ---
def show_main_menu(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🏆 Slot Tablosu", callback_data="show_slots"),
        types.InlineKeyboardButton("👤 Profilim", callback_data="show_profile")
    )
    
    bot.send_message(
        chat_id,
        "🔥 **WEX ESPORTS TURNUVA MERKEZİ** 🔥\n\n"
        "🏆 *Mücadele başlasın, kazanan inatçı savaşçı olsun!*\n"
        "Aşağıdaki menüden işlem yapabilirsin. 🚀",
        parse_mode="Markdown",
        reply_markup=markup
    )


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


# --- 2. /admin KOMUTU ---
@bot.message_handler(commands=['admin'])
def admin_login(message):
    admin_states[message.from_user.id] = "waiting_password"
    bot.send_message(
        message.chat.id,
        "🔐 **ADMİN GİRİŞİ**\n\nLütfen admin şifresini gir:",
        parse_mode="Markdown"
    )


# --- 3. PROFİL GÖRÜNTÜLEME ---
@bot.callback_query_handler(func=lambda call: call.data == "show_profile")
def callback_show_profile(call):
    user_id = call.from_user.id
    
    if user_id not in user_slots:
        profile_text = (
            "👤 **OYUNCU PROFİLİ**\n\n"
            "❌ Aktif bir slot kaydın bulunmuyor.\n\n"
            "🔑 **Oda ID:** Belirlenmedi\n"
            "🔒 **Oda Şifresi:** Belirlenmedi"
        )
    else:
        slot_num = user_slots[user_id]
        team_name = user_teams.get(user_id, "Bilinmeyen Takım")
        profile_text = (
            "👤 **OYUNCU PROFİLİ**\n\n"
            f"🏆 **Takım Adı:** `{team_name}`\n"
            f"📍 **Kayıtlı Slot:** `{slot_num}. Slot`\n\n"
            f"🔑 **Oda ID:** `{tournament_room['room_id']}`\n"
            f"🔒 **Oda Şifresi:** `{tournament_room['room_pass']}`"
        )

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu"))

    try:
        bot.edit_message_text(profile_text, call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)
    except:
        bot.send_message(call.message.chat.id, profile_text, parse_mode="Markdown", reply_markup=markup)


# --- 4. SLOT TABLOSU ---
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
        bot.edit_message_text(table_text, call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)
    except:
        bot.send_message(call.message.chat.id, table_text, parse_mode="Markdown", reply_markup=markup)


# Slot Seçme
@bot.callback_query_handler(func=lambda call: call.data.startswith("slot_"))
def callback_select_slot(call):
    slot_num = int(call.data.split("_")[1])
    user_id = call.from_user.id

    if user_id in user_slots:
        bot.answer_callback_query(call.id, f"Zaten {user_slots[user_id]}. slotta kaydın var!", show_alert=True)
        return

    if slots[slot_num] != "Boş":
        bot.answer_callback_query(call.id, "Bu slot maalesef dolu!", show_alert=True)
        return

    registration_states[user_id] = slot_num
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ İptal Et", callback_data="show_slots"))

    bot.send_message(
        call.message.chat.id,
        f"🎯 **{slot_num}. Slot** seçildi.\n\n"
        "Lütfen katılacak **Takım Adını** mesaj olarak yaz:",
        parse_mode="Markdown",
        reply_markup=markup
    )
    bot.answer_callback_query(call.id)


# --- 5. MESAJ YÖNETİCİSİ (Şifre, Takım Adı, Admin Oda Bilgisi) ---
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    text = message.text.strip() if message.text else ""

    # A) Admin Şifre Kontrolü
    if user_id in admin_states and admin_states[user_id] == "waiting_password":
        if text == ADMIN_PASSWORD:
            admin_states[user_id] = "logged_in"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔑 Oda ID & Şifre Belirle", callback_data="admin_set_room"))
            markup.add(types.InlineKeyboardButton("🔄 Turnuvayı Sıfırla", callback_data="admin_reset"))
            markup.add(types.InlineKeyboardButton("⏳ Geri Sayım Başlat", callback_data="admin_countdown"))
            markup.add(types.InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu"))
            
            bot.send_message(
                message.chat.id,
                "👑 **ADMİN PANELİNE HOŞ GELDİNİZ**\n\nYönetmek istediğiniz işlemi seçin:",
                parse_mode="Markdown",
                reply_markup=markup
            )
        else:
            bot.send_message(message.chat.id, "❌ Hatalı şifre! Tekrar /admin yazarak deneyebilirsin.")
            admin_states.pop(user_id, None)
        return

    # B) Admin Oda Bilgisi Girişi (ID ve Şifre)
    if user_id in admin_states and admin_states[user_id] == "waiting_room_info":
        parts = text.split()
        if len(parts) < 2:
            bot.send_message(message.chat.id, "⚠️ Lütfen hem Oda ID hem de Şifre girin!\nÖrnek format: `1234567 şifre123`", parse_mode="Markdown")
            return
        
        room_id = parts[0]
        room_pass = parts[1]
        
        tournament_room["room_id"] = room_id
        tournament_room["room_pass"] = room_pass
        admin_states[user_id] = "logged_in"

        bot.send_message(
            message.chat.id,
            f"✅ **Oda Bilgileri Güncellendi!**\n🔑 ID: `{room_id}`\n🔒 Şifre: `{room_pass}`\n\n*Slot alan tüm kullanıcılara bildirim gönderiliyor...*",
            parse_mode="Markdown"
        )

        # Slot alan herkese toplu bildirim gönder
        for uid in list(user_slots.keys()):
            try:
                bot.send_message(
                    uid,
                    "🚨 **TURNUVA ODA BİLGİLERİ YAYINLANDI!** 🚨\n\n"
                    f"🔑 **Oda ID:** `{room_id}`\n"
                    f"🔒 **Oda Şifresi:** `{room_pass}`\n\n"
                    "Hadi savaş alanına! 🏆",
                    parse_mode="Markdown"
                )
            except:
                pass
        
        show_main_menu(message.chat.id)
        return

    # C) Takım Adı Kayıt Kontrolü
    if user_id in registration_states:
        slot_num = registration_states[user_id]
        team_name = text if text else "Bilinmeyen Takım"

        if slots[slot_num] != "Boş":
            del registration_states[user_id]
            bot.send_message(message.chat.id, "❌ Üzgünüm, bu slot siz yazana kadar başkası tarafından alındı!")
            show_main_menu(message.chat
