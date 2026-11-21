import sys
import subprocess

# --- OTOMATİK KÜTÜPHANE YÜKLEYİCİ (Render hatasını kökten çözer) ---
try:
    import telebot
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyTelegramBotAPI"])
    import telebot

from telebot import types
import time

# Token ve Kanal Bilgileri
TOKEN = "9172005481:AAEbc_bAij8pRfdEvcDM9V1egFGzyl9QjaM"
CHANNEL_USERNAME = "@wexorganizasyon"  # Zorunlu katılınacak kanal
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


# Ana Menü (Start Komutu)
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    
    # Kanal kontrolü
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
    markup.add(types.InlineKeyboardButton("🏆 Slot Tablosu & Kayıt Ol", callback_data="show_slots"))
    
    bot.send_message(
        chat_id,
        "🔥 **WEX ESPORTS TURNUVA MERKEZİNE HOŞ GELDİN!** 🔥\n\n"
        "🏆 *Mücadele başlasın, kazanan inatçı savaşçı olsun!*\n"
        "Aşağıdaki butonu kullanarak slot seçebilir ve heyecana ortak olabilirsin. 🚀",
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


# Slot Tablosu ve Kayıt Paneli
@bot.callback_query_handler(func=lambda call: call.data == "show_slots")
def callback_show_slots(call):
    markup = types.InlineKeyboardMarkup(row_width=5)
    
    # 25 Slotun butonları (Dolu olanlar işaretli)
    buttons = []
    for i in range(1, 26):
        status = "🟢" if slots[i] == "Boş" else "🔴"
        buttons.append(types.InlineKeyboardButton(f"{i}. Slot {status}", callback_data=f"slot_{i}"))
    
    markup.add(*buttons)
    markup.add(types.InlineKeyboardButton("❌ Slotumu İptal Et", callback_data="cancel_my_slot"))
    markup.add(types.InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu"))

    # Tablo metni oluşturma
    table_text = "🎯 **CANLI SLOT TABLOSU** 🎯\n\n"
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


# Slot Seçme ve Takım Adı İsteme
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

    bot.send_message(
        call.message.chat.id,
        f"🎯 **{slot_num}. Slot** için işlem yapıyorsun.\n\n"
        "Lütfen katılacak **Takım Adını** mesaj olarak yaz gönder:",
        parse_mode="Markdown",
        reply_markup=markup
    )
    bot.answer_callback_query(call.id)


# Takım Adı Mesajını Yakalama
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

    bot.send_message(
        message.chat.id,
        f"✅ **BAŞARILI!**\n\n"
        f"🏆 **Takım:** `{team_name}`\n"
        f"📍 **Seçilen Slot:** `{slot_num}. Slot`\n\n"
        "Bol şans dileriz! Savaş alanında görüşmek üzere. 🔥",
        parse_mode="Markdown"
    )
    show_main_menu(message.chat.id)


# Slot İptal Etme
@bot.callback_query_handler(func=lambda call: call.data == "cancel_my_slot")
def callback_cancel_slot(call):
    user_id = call.from_user.id
    if user_id not in user_slots:
        bot.answer_callback_query(call.id, "Aktif bir slot kaydın bulunmuyor!", show_alert=True)
        return

    slot_num = user_slots[user_id]
    slots[slot_num] = "Boş"
    del user_slots[user_id]

    bot.answer_callback_
