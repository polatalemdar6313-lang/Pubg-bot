import sys, subprocess, os
try:
    import telebot
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyTelegramBotAPI", "flask"])
    import telebot
from telebot import types
import time
from flask import Flask
from threading import Thread

app = Flask('')
@app.route('/')
def home():
    return "WEX Bot Aktif!"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

Thread(target=run_web, daemon=True).start()

TOKEN = "9172005481:AAEbc_bAij8pRfdEvcDM9V1egFGzyl9QjaM"
CHANNEL_USERNAME = "@wexorganizasyon"
ADMIN_PASSWORD = "631363"

bot = telebot.TeleBot(TOKEN)
slots = {i: "Boş" for i in range(1, 26)}
user_slots = {}
user_teams = {}
admin_states = {}
registration_states = {}
tournament_room = {"room_id": "Belirlenmedi", "room_pass": "Belirlenmedi"}

def check_sub(user_id):
    try:
        m = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return m.status in ['member', 'administrator', 'creator']
    except:
        return False

def show_main_menu(chat_id):
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(types.InlineKeyboardButton("🏆 Slot Tablosu", callback_data="show_slots"),
          types.InlineKeyboardButton("👤 Profilim", callback_data="show_profile"))
    bot.send_message(chat_id, "🔥 **WEX ESPORTS TURNUVA MERKEZİ** 🔥\n\nAşağıdaki menüden işlem yapabilirsin.", parse_mode="Markdown", reply_markup=m)

@bot.message_handler(commands=['start'])
def start(m):
    if not check_sub(m.from_user.id):
        mup = types.InlineKeyboardMarkup()
        mup.add(types.InlineKeyboardButton("📢 Kanala Katıl", url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}"))
        mup.add(types.InlineKeyboardButton("🔄 Kontrol Et", callback_data="check_subscription"))
        bot.send_message(m.chat.id, f"⚠️ Devam etmek için kanala katılmalısın:\n👉 {CHANNEL_USERNAME}", reply_markup=mup)
        return
    show_main_menu(m.chat.id)

@bot.callback_query_handler(func=lambda c: c.data == "check_subscription")
def sub_check(c):
    if check_sub(c.from_user.id):
        bot.answer_callback_query(c.id, "Kanal onaylandı! 🎉")
        try: bot.delete_message(c.message.chat.id, c.message.message_id)
        except: pass
        show_main_menu(c.message.chat.id)
    else:
        bot.answer_callback_query(c.id, "Henüz kanala katılmadın!", show_alert=True)

@bot.message_handler(commands=['admin'])
def admin(m):
    admin_states[m.from_user.id] = "waiting_password"
    bot.send_message(m.chat.id, "🔐 **ADMİN GİRİŞİ**\n\nŞifreyi gir:")

@bot.callback_query_handler(func=lambda c: c.data == "show_profile")
def profile(c):
    uid = c.from_user.id
    if uid not in user_slots:
        txt = "👤 **PROFİL**\n\n❌ Aktif kaydın yok.\n🔑 Oda ID: Belirlenmedi\n🔒 Şifre: Belirlenmedi"
    else:
        txt = f"👤 **PROFİL**\n\n🏆 Takım: `{user_teams.get(uid)}`\n📍 Slot: `{user_slots[uid]}. Slot`\n\n🔑 Oda ID: `{tournament_room['room_id']}`\n🔒 Şifre: `{tournament_room['room_pass']}`"
    mup = types.InlineKeyboardMarkup()
    mup.add(types.InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu"))
    try: bot.edit_message_text(txt, c.message.chat.id, c.message.message_id, parse_mode="Markdown", reply_markup=mup)
    except: bot.send_message(c.message.chat.id, txt, parse_mode="Markdown", reply_markup=mup)

@bot.callback_query_handler(func=lambda c: c.data == "show_slots")
def slots_menu(c):
    mup = types.InlineKeyboardMarkup(row_width=5)
    btns = [types.InlineKeyboardButton(f"{i} {'🟢' if slots[i]=='Boş' else '🔴'}", callback_data=f"slot_{i}") for i in range(1, 26)]
    mup.add(*btns)
    mup.add(types.InlineKeyboardButton("❌ Slotumu İptal Et", callback_data="cancel_my_slot"))
    mup.add(types.InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu"))
    txt = "🎯 **SLOT LİSTESİ**\n\n" + "\n".join([f"{'🟩' if slots[i]=='Boş' else '🟥'} Slot {i}: `{slots[i]}`" for i in range(1, 26)])
    try: bot.edit_message_text(txt, c.message.chat.id, c.message.message_id, parse_mode="Markdown", reply_markup=mup)
    except: bot.send_message(c.message.chat.id, txt, parse_mode="Markdown", reply_markup=mup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("slot_"))
def select_slot(c):
    s = int(c.data.split("_")[1])
    uid = c.from_user.id
    if uid in user_slots:
        bot.answer_callback_query(c.id, "Zaten bir slotun var!", show_alert=True)
        return
    if slots[s] != "Boş":
        bot.answer_callback_query(c.id, "Bu slot dolu!", show_alert=True)
        return
    registration_states[uid] = s
    mup = types.InlineKeyboardMarkup()
    mup.add(types.InlineKeyboardButton("İptal", callback_data="show_slots"))
    bot.send_message(c.message.chat.id, f"🎯 {s}. Slot seçildi. Takım adını yaz:", reply_markup=mup)
    bot.answer_callback_query(c.id)

@bot.message_handler(func=lambda m: True)
def msg_handler(m):
    uid = m.from_user.id
    txt = m.text.strip() if m.text else ""
    if uid in admin_states and admin_states[uid] == "waiting_password":
        if txt == ADMIN_PASSWORD:
            admin_states[uid] = "logged_in"
            mup = types.InlineKeyboardMarkup()
            mup.add(types.InlineKeyboardButton("🔑 Oda Bilgisi Gir", callback_data="admin_set_room"),
                    types.InlineKeyboardButton("🔄 Sıfırla", callback_data="admin_reset"),
                    types.InlineKeyboardButton("⏳ Sayaç", callback_data="admin_countdown"),
                    types.InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu"))
            bot.send_message(m.chat.id, "👑 **ADMİN PANELİ**", reply_markup=mup)
        else:
            bot.send_message(m.chat.id, "❌ Hatalı şifre!")
            admin_states.pop(uid, None)
        return

    if uid in admin_states and admin_states[uid] == "waiting_room_info":
        parts = txt.split()
        if len(parts) < 2:
            bot.send_message(m.chat.id, "⚠️ Örnek format: `123456 şifre123`", parse_mode="Markdown")
            return
        tournament_room["room_id"], tournament_room["room_pass"] = parts[0], parts[1]
        admin_states[uid] = "logged_in"
        bot.send_message(m.chat.id, "✅ Oda bilgileri güncellendi ve kullanıcılara bildiriliyor...")
        for u in user_slots:
            try: bot.send_message(u, f"🚨 **Oda Bilgisi Yayınlandı!**\n🔑 ID: `{parts[0]}`\n🔒 Şifre: `{parts[1]}`", parse_mode="Markdown")
            except: pass
        show_main_menu(m.chat.id)
        return

    if uid in registration_states:
        s = registration_states[uid]
        if slots[s] != "Boş":
            del registration_states[uid]
            bot.send_message(m.chat.id, "❌ Bu slot başkası tarafından alındı!")
            show_main_menu(m.chat.id)
            return
        slots[s] = txt
        user_slots[uid] = s
        user_teams[uid] = txt
        del registration_states[uid]
        bot.send_message(m.chat.id, f"✅ Kayıt başarılı! Takım: {txt}, Slot: {s}")
        show_main_menu(m.chat.id)
        return

@bot.callback_query_handler(func=lambda c: c.data == "cancel_my_slot")
def cancel(c):
    uid = c.from_user.id
    if uid not in user_slots:
        bot.answer_callback_query(c.id, "Kayıtlı slotun yok!", show_alert=True)
        return
    s = user_slots[uid]
    slots[s] = "Boş"
    user_slots.pop(uid, None)
    user_teams.pop(uid, None)
    bot.answer_callback_query(c.id, "Slot iptal edildi.")
    slots_menu(c)

@bot.callback_query_handler(func=lambda c: c.data == "main_menu")
def menu_cb(c):
    try: bot.delete_message(c.message.chat.id, c.message.message_id)
    except: pass
    show_main_menu(c.message.chat.id)

@bot.callback_query_handler(func=lambda c: c.data == "admin_set_room")
def set_room_cb(c):
    if admin_states.get(c.from_user.id) != "logged_in": return
    admin_states[c.from_user.id] = "waiting_room_info"
    bot.answer_callback_query(c.id)
    bot.send_message(c.message.chat.id, "🔑 Oda ID ve Şifreyi araya boşluk koyarak yaz:")

@bot.callback_query_handler(func=lambda c: c.data == "admin_reset")
def reset_cb(c):
    if admin_states.get(c.from_user.id) != "logged_in": return
    global slots, user_slots, user_teams, tournament_room
    slots = {i: "Boş" for i in range(1, 26)}
    user_slots.clear()
    user_teams.clear()
    tournament_room = {"room_id": "Belirlenmedi", "room_pass": "Belirlenmedi"}
    bot.answer_callback_query(c.id, "Sıfırlandı!")
    bot.send_message(c.message.chat.id, "🔄 Turnuva sıfırlandı.")

@bot.callback_query_handler(func=lambda c: c.data == "admin_countdown")
def count_cb(c):
    if admin_states.get(c.from_user.id) != "logged_in": return
    bot.answer_callback_query(c.id, "Başladı!")
    msg = bot.send_message(c.message.chat.id, "⏳ Geri sayım: **10 saniye**", parse_mode="Markdown")
    for i in range(9, 0, -1):
        time.sleep(1)
        try: bot.edit_message_text(f"⏳ Geri sayım: **{i} saniye**", c.message.chat.id, msg.message_id, parse_mode="Markdown")
        except: pass
    time.sleep(1)
    try: bot.edit_message_text("🚨 **START! START! START!**", c.message.chat.id, msg.message_id, parse_mode="Markdown")
    except: pass

if __name__ == "__main__":
    print("Bot aktif...")
    bot.infinity_polling()
