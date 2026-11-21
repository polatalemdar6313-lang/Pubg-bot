import os
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_PASSWORD = "631363"
DATA_FILE = "tournament_data.json"

DEFAULT_DATA = {
    "payment_info": "IBAN: TR00 0000 0000 0000 0000 0000 00\nAlıcı: Ad Soyad",
    "entry_fee": "100 TL",
    "tournament_time": "22:00",
    "room_id": "Henüz belirlenmedi",
    "room_pass": "Henüz belirlenmedi",
    "slots": {str(i): None for i in range(1, 26)},
    "approved_users": [],
    "pending_receipts": {},
    "admin_messages": [],
    "authenticated_admins": []
}

def load_data():
    if not os.path.exists(DATA_FILE):
        save_data(DEFAULT_DATA)
        return json.loads(json.dumps(DEFAULT_DATA))
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Ödeme Yap & Katıl", callback_data="menu_pay")],
        [InlineKeyboardButton("🏆 Slot Listesi (25 Slot)", callback_data="menu_slots")],
        [InlineKeyboardButton("👤 Profilim & Oda Bilgileri", callback_data="menu_profile")],
        [InlineKeyboardButton("📩 Admine Mesaj Gönder", callback_data="menu_msg_admin")],
    ])

def admin_menu_keyboard(data):
    pending_count = len(data["pending_receipts"])
    msg_count = len(data["admin_messages"])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🧾 Dekontları Kontrol Et ({pending_count})", callback_data="adm_receipts")],
        [InlineKeyboardButton(f"💬 Mesajları Kontrol Et ({msg_count})", callback_data="adm_messages")],
        [InlineKeyboardButton("💰 Ücret & IBAN Ayarla", callback_data="adm_set_payment")],
        [InlineKeyboardButton("🕒 Turnuva Saati Ayarla", callback_data="adm_set_time")],
        [InlineKeyboardButton("🔑 Oda ID & Şifre Gir", callback_data="adm_set_room")],
        [InlineKeyboardButton("❌ Tek Slot Sil", callback_data="adm_del_slot")],
        [InlineKeyboardButton("⚠️ Turnuvayı Sıfırla", callback_data="adm_reset_confirm")],
        [InlineKeyboardButton("🔙 Ana Menü", callback_data="back_main")],
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    data = load_data()
    text = (
        f"🎮 **PUBG Mobile Turnuva Botuna Hoş Geldiniz!**\n\n"
        f"🕒 **Turnuva Saati:** {data['tournament_time']}\n"
        f"💵 **Katılım Ücreti:** {data['entry_fee']}\n\n"
        f"Lütfen yapmak istediğiniz işlemi seçin:"
    )
    if update.message:
        await update.message.reply_text(text, reply_markup=main_menu_keyboard(), parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=main_menu_keyboard(), parse_mode="Markdown")

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = load_data()
    if user_id in data["authenticated_admins"]:
        await update.message.reply_text("🛠 **Admin Paneli**", reply_markup=admin_menu_keyboard(data), parse_mode="Markdown")
    else:
        context.user_data["state"] = "awaiting_admin_pass"
        await update.message.reply_text("🔐 Lütfen Admin Paneli şifresini girin:")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = load_data()
    cb = query.data

    if cb == "back_main":
        context.user_data.clear()
        await start(update, context)

    elif cb == "back_admin":
        context.user_data.clear()
        if user_id in data["authenticated_admins"]:
            await query.edit_message_text("🛠 **Admin Paneli**", reply_markup=admin_menu_keyboard(data), parse_mode="Markdown")

    elif cb == "menu_pay":
        text = (
            f"💳 **Ödeme Bilgileri**\n\n"
            f"💵 **Tutar:** {data['entry_fee']}\n"
            f"🏦 **Hesap Bilgileri:**\n`{data['payment_info']}`\n\n"
            f"Ödemeyi yaptıktan sonra aşağıdaki **'Ödedim'** butonuna basın."
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Ödedim", callback_data="pay_paid")],
            [InlineKeyboardButton("🔙 Geri", callback_data="back_main")]
        ])
        await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")

    elif cb == "pay_paid":
        context.user_data["state"] = "awaiting_receipt"
        text = (
            "📸 Lütfen ödeme dekontunu (fotoğraf veya belge olarak) bu sohbete gönderin.\n"
            "Dekontu yükledikten sonra onay butonuna basmayı unutmayın."
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 İptal", callback_data="back_main")]])
        await query.edit_message_text(text, reply_markup=kb)

    elif cb == "receipt_sent_confirm":
        if "temp_receipt" not in context.user_data:
            await query.answer("Önce dekont fotoğrafı/belgesi göndermelisiniz!", show_alert=True)
            return
        receipt = context.user_data.pop("temp_receipt")
        context.user_data.clear()
        username = query.from_user.username or query.from_user.full_name
        data["pending_receipts"][str(user_id)] = {
            "username": username,
            "file_id": receipt["file_id"],
            "is_photo": receipt["is_photo"]
        }
        save_data(data)
        await query.edit_message_text(
            "✅ Dekontunuz yöneticiye iletildi! Onaylandığında size bildirim gelecek ve slot seçebileceksiniz.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Ana Menü", callback_data="back_main")]])
        )

    elif cb == "menu_slots":
        kb = []
        row = []
        for i in range(1, 26):
            slot_info = data["slots"][str(i)]
            if slot_info:
                label = f"🔒 {i}. {slot_info['team']}"
            else:
                label = f"🟢 {i}. Boş"
            row.append(InlineKeyboardButton(label, callback_data=f"select_slot_{i}"))
            if len(row) == 2:
                kb.append(row)
                row = []
        if row:
            kb.append(row)
        kb.append([InlineKeyboardButton("🔙 Ana Menü", callback_data="back_main")])
        await query.edit_message_text("🏆 **Turnuva Slot Listesi (25 Slot)**\nBoş bir slot seçmek için üzerine tıklayın:", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif cb.startswith("select_slot_"):
        slot_num = cb.split("_")[-1]
        if data["slots"][slot_num] is not None:
            await query.answer("Bu slot zaten dolu!", show_alert=True)
            return
        if user_id not in data["approved_users"]:
            await query.answer("Slot seçmek için önce ödeme yapıp dekont onayı almalısınız!", show_alert=True)
            return
        for s_num, s_val in data["slots"].items():
            if s_val and s_val["user_id"] == user_id:
                await query.answer(f"Zaten {s_num}. slota kayıtlısınız!", show_alert=True)
                return

        context.user_data["state"] = "awaiting_team_name"
        context.user_data["selected_slot"] = slot_num
        await query.edit_message_text(
            f"✍️ **{slot_num}. Slot** seçildi.\nLütfen **Takım Adınızı** yazıp gönderin:",
            parse_mode="Markdown"
        )

    elif cb == "menu_profile":
        user_slot = None
        team_name = "Yok"
        for s_num, s_val in data["slots"].items():
            if s_val and s_val["user_id"] == user_id:
                user_slot = s_num
                team_name = s_val["team"]
                break

        status = "Onaylı (Slot Seçebilir)" if user_id in data["approved_users"] else ("Kayıtlı" if user_slot else "Ödeme Bekleniyor")
        text = (
            f"👤 **Profil Bilgileriniz**\n\n"
            f"🆔 **ID:** `{user_id}`\n"
            f"📌 **Durum:** {status}\n"
            f"🔢 **Slot No:** {user_slot if user_slot else 'Seçilmedi'}\n"
            f"🛡 **Takım Adı:** {team_name}\n\n"
            f"🎮 **Turnuva & Oda Bilgileri**\n"
            f"🕒 **Saat:** {data['tournament_time']}\n"
            f"🔑 **Oda ID:** `{data['room_id'] if user_slot else 'Sadece kayıtlı oyuncular görebilir'}`\n"
            f"🔒 **Oda Şifresi:** `{data['room_pass'] if user_slot else 'Sadece kayıtlı oyuncular görebilir'}`"
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Ana Menü", callback_data="back_main")]]), parse_mode="Markdown")

    elif cb == "menu_msg_admin":
        context.user_data["state"] = "awaiting_admin_msg"
        await query.edit_message_text(
            "📩 Yöneticiye iletmek istediğiniz mesajı yazıp gönderin:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 İptal", callback_data="back_main")]])
        )

    elif cb == "adm_receipts":
        if user_id not in data["authenticated_admins"]:
            return
        if not data["pending_receipts"]:
            await query.answer("Bekleyen dekont yok.", show_alert=True)
            return
        target_uid, r_info = next(iter(data["pending_receipts"].items()))
        caption = f"🧾 **Bekleyen Dekont**\nKullanıcı: @{r_info['username']} (`{target_uid}`)"
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Onayla", callback_data=f"adm_approve_{target_uid}"),
                InlineKeyboardButton("❌ Reddet", callback_data=f"adm_reject_{target_uid}")
            ],
            [InlineKeyboardButton("🔙 Admin Paneli", callback_data="back_admin")]
        ])
        await query.delete_message()
        if r_info["is_photo"]:
            await context.bot.send_photo(chat_id=user_id, photo=r_info["file_id"], caption=caption, reply_markup=kb, parse_mode="Markdown")
        else:
            await context.bot.send_document(chat_id=user_id, document=r_info["file_id"], caption=caption, reply_markup=kb, parse_mode="Markdown")

    elif cb.startswith("adm_approve_"):
        if user_id not in data["authenticated_admins"]:
            return
        target_uid = cb.split("_")[-1]
        if target_uid in data["pending_receipts"]:
            del data["pending_receipts"][target_uid]
            if int(target_uid) not in data["approved_users"]:
                data["approved_users"].append(int(target_uid))
            save_data(data)
            try:
                await context.bot.send_message(
                    chat_id=int(target_uid),
                    text="🎉 **Ödemeniz onaylandı!** Artık 'Slot Listesi' menüsünden istediğiniz boş slotu seçebilirsiniz.",
                    parse_mode="Markdown"
                )
            except Exception:
                pass
        await query.delete_message()
        await context.bot.send_message(chat_id=user_id, text="✅ Dekont onaylandı.", reply_markup=admin_menu_keyboard(data))

    elif cb.startswith("adm_reject_"):
        if user_id not in data["authenticated_admins"]:
            return
        target_uid = cb.split("_")[-1]
        if target_uid in data["pending_receipts"]:
            del data["pending_receipts"][target_uid]
            save_data(data)
            try:
                await context.bot.send_message(
                    chat_id=int(target_uid),
                    text="❌ **Ödeme dekontunuz reddedildi.** Lütfen bilgileri kontrol edip tekrar deneyin.",
                    parse_mode="Markdown"
                )
            except Exception:
                pass
        await query.delete_message()
        await context.bot.send_message(chat_id=user_id, text="❌ Dekont reddedildi.", reply_markup=admin_menu_keyboard(data))

    elif cb == "adm_messages":
        if user_id not in data["authenticated_admins"]:
            return
        if not data["admin_messages"]:
            await query.answer("Gelen mesaj yok.", show_alert=True)
            return
        text = "💬 **Kullanıcı Mesajları:**\n\n"
        for idx, m in enumerate(data["admin_messages"], 1):
            text += f"{idx}. @{m['username']} (`{m['user_id']}`): {m['text']}\n\n"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑 Mesajları Temizle", callback_data="adm_clear_msgs")],
            [InlineKeyboardButton("🔙 Admin Paneli", callback_data="back_admin")]
        ])
        await query.edit_message_text(text[:4000], reply_markup=kb, parse_mode="Markdown")

    elif cb == "adm_clear_msgs":
        if user_id not in data["authenticated_admins"]:
            return
        data["admin_messages"] = []
        save_data(data)
        await query.edit_message_text("🗑 Tüm mesajlar silindi.", reply_markup=admin_menu_keyboard(data))

    elif cb == "adm_set_payment":
        if user_id not in data["authenticated_admins"]:
            return
        context.user_data["state"] = "adm_awaiting_fee"
        await query.edit_message_text(
            f"💰 Mevcut Ücret: **{data['entry_fee']}**\nYeni katılım ücretini yazın (Örn: `150 TL`):",
            parse_mode="Markdown"
        )

    elif cb == "adm_set_time":
        if user_id not in data["authenticated_admins"]:
            return
        context.user_data["state"] = "adm_awaiting_time"
        await query.edit_message_text(
            f"🕒 Mevcut Saat: **{data['tournament_time']}**\nYeni turnuva saatini yazın (Örn: `21:30`):",
            parse_mode="Markdown"
        )

    elif cb == "adm_set_room":
        if user_id not in data["authenticated_admins"]:
            return
        context.user_data["state"] = "adm_awaiting_room_id"
        await query.edit_message_text("🔑 Yeni **Oda ID** bilgisini yazın:", parse_mode="Markdown")

    elif cb == "adm_del_slot":
        if user_id not in data["authenticated_admins"]:
            return
        kb = []
        row = []
        for i in range(1, 26):
            slot_info = data["slots"][str(i)]
            if slot_info:
                row.append(InlineKeyboardButton(f"❌ {i}. {slot_info['team']}", callback_data=f"adm_rmslot_{i}"))
                if len(row) == 2:
                    kb.append(row)
                    row = []
        if row:
            kb.append(row)
        kb.append([InlineKeyboardButton("🔙 Admin Paneli", callback_data="back_admin")])
        await query.edit_message_text("Silmek istediğiniz dolu slotu seçin:", reply_markup=InlineKeyboardMarkup(kb))

    elif cb.startswith("adm_rmslot_"):
        if user_id not in data["authenticated_admins"]:
            return
        s_num = cb.split("_")[-1]
        if data["slots"][s_num]:
            removed_uid = data["slots"][s_num]["user_id"]
            data["slots"][s_num] = None
            if removed_uid in data["approved_users"]:
                data["approved_users"].remove(removed_uid)
            save_data(data)
            await query.answer(f"{s_num}. slot silindi!", show_alert=True)
        await query.edit_message_text("🛠 **Admin Paneli**", reply_markup=admin_menu_keyboard(data), parse_mode="Markdown")

    elif cb == "adm_reset_confirm":
        if user_id not in data["authenticated_admins"]:
            return
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔥 EVET, HER ŞEYİ SIFIRLA", callback_data="adm_reset_execute")],
            [InlineKeyboardButton("🔙 İptal", callback_data="back_admin")]
        ])
        await query.edit_message_text("⚠️ **DİKKAT!** Tüm slotlar, onaylı kullanıcılar ve bekleyen dekontlar silinecek. Emin misiniz?", reply_markup=kb, parse_mode="Markdown")

    elif cb == "adm_reset_execute":
        if user_id not in data["authenticated_admins"]:
            return
        admins = data["authenticated_admins"]
        pay_info = data["payment_info"]
        fee = data["entry_fee"]
        new_data = json.loads(json.dumps(DEFAULT_DATA))
        new_data["authenticated_admins"] = admins
        new_data["payment_info"] = pay_info
        new_data["entry_fee"] = fee
        save_data(new_data)
        await query.edit_message_text("✅ Turnuva tamamen sıfırlandı!", reply_markup=admin_menu_keyboard(new_data))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip() if update.message.text else ""
    state = context.user_data.get("state")
    data = load_data()

    if text.lower() in ["admin", "panel admin", "/admin"]:
        await admin_command(update, context)
        return

    if state == "awaiting_receipt":
        if update.message.photo:
            context.user_data["temp_receipt"] = {"file_id": update.message.photo[-1].file_id, "is_photo": True}
        elif update.message.document:
            context.user_data["temp_receipt"] = {"file_id": update.message.document.file_id, "is_photo": False}
        else:
            await update.message.reply_text("⚠️ Lütfen geçerli bir dekont fotoğrafı veya dosyası gönderin.")
            return

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Dekontu Gönderdim", callback_data="receipt_sent_confirm")],
            [InlineKeyboardButton("🔙 İptal", callback_data="back_main")]
        ])
        await update.message.reply_text("Dekont alındı. Onaya göndermek için aşağıdaki butona basın:", reply_markup=kb)
        return

    if state == "awaiting_team_name":
        slot_num = context.user_data.get("selected_slot")
        if not text:
            await update.message.reply_text("Lütfen geçerli bir takım adı girin:")
            return
        if data["slots"][slot_num] is not None:
            context.user_data.clear()
            await update.message.reply_text("❌ Üzgünüz, siz yazarken bu slot başkası tarafından alındı.", reply_markup=main_menu_keyboard())
            return

        username = update.effective_user.username or update.effective_user.full_name
        data["slots"][slot_num] = {
            "user_id": user_id,
            "username": username,
            "team": text[:25]
        }
        save_data(data)
        context.user_data.clear()
        await update.message.reply_text(
            f"✅ Tebrikler! **{slot_num}. Slot** `{text[:25]}` takımı adına kaydedildi.",
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )
        return

    if state == "awaiting_admin_msg":
        if not text:
            return
        username = update.effective_user.username or update.effective_user.full_name
        data["admin_messages"].append({
            "user_id": user_id,
            "username": username,
            "text": text
        })
        save_data(data)
        context.user_data.clear()
        await update.message.reply_text("✅ Mesajınız admine iletildi.", reply_markup=main_menu_keyboard())
        return

    if state == "awaiting_admin_pass":
        if text == ADMIN_PASSWORD:
            if user_id not in data["authenticated_admins"]:
                data["authenticated_admins"].append(user_id)
                save_data(data)
            context.user_data.clear()
            await update.message.reply_text("🔓 Giriş başarılı! **Admin Paneli:**", reply_markup=admin_menu_keyboard(data), parse_mode="Markdown")
        else:
            context.user_data.clear()
            await update.message.reply_text("❌ Hatalı şifre!", reply_markup=main_menu_keyboard())
        return

    if user_id in data["authenticated_admins"]:
        if state == "adm_awaiting_fee":
            data["entry_fee"] = text
            save_data(data)
            context.user_data["state"] = "adm_awaiting_iban"
            await update.message.reply_text(
                f"✅ Ücret `{text}` olarak güncellendi.\nŞimdi yeni **IBAN / Hesap Bilgilerini** yazın (Değiştirmek istemiyorsanız mevcut bilgiyi tekrar yazın):",
                parse_mode="Markdown"
            )
            return

        elif state == "adm_awaiting_iban":
            data["payment_info"] = text
            save_data(data)
            context.user_data.clear()
            await update.message.reply_text("✅ Ödeme bilgileri güncellendi!", reply_markup=admin_menu_keyboard(data))
            return

        elif state == "adm_awaiting_time":
            data["tournament_time"] = text
            save_data(data)
            context.user_data.clear()
            await update.message.reply_text(f"✅ Turnuva saati `{text}` olarak ayarlandı!", reply_markup=admin_menu_keyboard(data), parse_mode="Markdown")
            return

        elif state == "adm_awaiting_room_id":
            data["room_id"] = text
            save_data(data)
            context.user_data["state"] = "adm_awaiting_room_pass"
            await update.message.reply_text("🔑 Şimdi **Oda Şifresini** yazın:", parse_mode="Markdown")
            return

        elif state == "adm_awaiting_room_pass":
            data["room_pass"] = text
            save_data(data)
            context.user_data.clear()
            await update.message.reply_text("✅ Oda ID ve Şifresi kaydedildi!", reply_markup=admin_menu_keyboard(data))
            return

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
