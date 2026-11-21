import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

TOKEN = "9172005481:AAEbc_bAij8pRfdEvcDM9V1egFGzyl9QjaM"
ADMIN_SIFRE = "631363"

t_aktif = True
t_saat = 1200
slotlar = {i: {"durum": "Boş", "takim": "-", "user_id": None} for i in range(1, 26)}
durumlar = {}
kullanicilar = set()
bildirimler = []
kanal = "https://t.me/wexorganizasyon"
oda_id = "-"
oda_sifre = "-"

def saat_yaz(dk):
    s = (dk % 1440) // 60
    d = (dk % 1440) % 60
    return f"{s:02d}:{d:02d}"

def m_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏆 Slot Tablosu & Kayıt Ol", callback_data="s_tablo")],
        [InlineKeyboardButton("👤 Profilim", callback_data="profil")],
        [InlineKeyboardButton("📩 Admine Bildirim Gönder", callback_data="bildir")],
        [InlineKeyboardButton("⚠️ Kayıt İptal Et", callback_data="iptal_et")]
    ])

def s_klavye():
    kb = []
    satir = []
    for no, b in slotlar.items():
        txt = f"Slot {no} 🟢 BOŞ" if b["durum"] == "Boş" else f"Slot {no} 🔴 {b['takim']}"
        satir.append(InlineKeyboardButton(txt, callback_data=f"sl_{no}"))
        if len(satir) == 2:
            kb.append(satir)
            satir = []
    if satir:
        kb.append(satir)
    kb.append([InlineKeyboardButton("🔙 Ana Menü", callback_data="ana")])
    return InlineKeyboardMarkup(kb)

def a_klavye():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"⏳ Saat: {saat_yaz(t_saat)}", callback_data="bos")],
        [InlineKeyboardButton("➖ 30dk", callback_data="a_eksi"), InlineKeyboardButton("➕ 30dk", callback_data="a_arti")],
        [InlineKeyboardButton("🔑 Oda ID & Şifre Gir", callback_data="a_oda")],
        [InlineKeyboardButton("🗑️ Slot Sil", callback_data="a_sil")],
        [InlineKeyboardButton("🔄 Sıfırla", callback_data="a_sifirla")],
        [InlineKeyboardButton("📥 Bildirimler", callback_data="a_oku")],
        [InlineKeyboardButton("📢 Duyuru", callback_data="a_duyuru")],
        [InlineKeyboardButton("🚪 Çıkış", callback_data="ana")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    kullanicilar.add(uid)
    durumlar.pop(uid, None)
    
    msg = (
        "🔥 WEX ESPORTS TURNUVA MERKEZİNE HOŞ GELDİN! 🔥\n\n"
        "🏆 Mücadele başlasın, kazanan inatçı savaşçı olsun!\n"
        f"⏳ Turnuva Saati: {saat_yaz(t_saat)}\n"
        f"📢 Kanal: {kanal}\n\n"
        "Aşağıdaki butonu kullanarak slot seçebilirsin. 🚀"
    )
    if update.callback_query:
        await update.callback_query.message.edit_text(msg, reply_markup=m_menu())
    else:
        await update.message.reply_text(msg, reply_markup=m_menu())

async def buton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global t_aktif, t_saat, oda_id, oda_sifre
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    data = q.data
    
    if data == "ana":
        durumlar.pop(uid, None)
        await start(update, context)
        return
    if data == "bos":
        return
        
    if not t_aktif and not data.startswith("a_"):
        await q.message.edit_text("❌ Aktif turnuva yok.")
        return
        
    if data == "s_tablo":
        await q.message.edit_text("📋 Güncel Slot Tablosu:", reply_markup=s_klavye())
    elif data == "profil":
        slotum = next((no for no, b in slotlar.items() if b.get("user_id") == uid), None)
        if slotum:
            txt = f"👤 Profiliniz:\n\n📌 Slot: {slotum}\n🏆 Takım: {slotlar[slotum]['takim']}\n⏳ Saat: {saat_yaz(t_saat)}\n\n🔑 Oda ID & Şifre: {oda_id} / {oda_sifre}\n⚠️ İptal için `iptal` yazın."
        else:
            txt = "⚠️ Aktif slot kaydınız yok."
        await q.message.edit_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Ana Menü", callback_data="ana")]]))
    elif data == "bildir":
        durumlar[uid] = "bekle_bildirim"
        await q.message.reply_text("📩 Admine göndereceğiniz mesajı yazın:")
    elif data == "iptal_et":
        for no, b in slotlar.items():
            if b.get("user_id") == uid:
                slotlar[no] = {"durum": "Boş", "takim": "-", "user_id": None}
                await q.message.edit_text(f"✅ Slot {no} iptal edildi!", reply_markup=m_menu())
                return
        await q.message.edit_text("⚠️ Aktif kaydınız yok.", reply_markup=m_menu())
        
    elif data.startswith("a_"):
        if data == "a_sifirla":
            for no in slotlar: slotlar[no] = {"durum": "Boş", "takim": "-", "user_id": None}
            oda_id, oda_sifre, t_aktif, t_saat = "-", "-", False, 1200
            bildirimler.clear()
            await q.message.edit_text("🔄 Sıfırlandı!", reply_markup=a_klavye())
        elif data == "a_arti":
            t_saat = (t_saat + 30) % 1440
            await q.message.edit_text("👑 Admin Paneli:", reply_markup=a_klavye())
        elif data == "a_eksi":
            t_saat = (t_saat - 30) % 1440
            await q.message.edit_text("👑 Admin Paneli:", reply_markup=a_klavye())
        elif data == "a_oda":
            durumlar[uid] = "adm_oda_id"
            await q.message.reply_text("🔑 Oda ID'sini yazın:")
        elif data == "a_sil":
            durumlar[uid] = "adm_sil"
            await q.message.reply_text("🗑️ Silinecek slot no yazın:")
        elif data == "a_oku":
            lst = "📥 Bildirim yok." if not bildirimler else "📥 Bildirimler:\n\n" + "\n".join(bildirimler)
            await q.message.edit_text(lst, reply_markup=a_klavye())
        elif data == "a_duyuru":
            durumlar[uid] = "adm_duyuru"
            await q.message.reply_text("📢 Duyuru metnini yazın:")
            
    elif data.startswith("sl_"):
        no = int(data.split("_")[1])
        mevcut_slot = next((n for n, b in slotlar.items() if b.get("user_id") == uid), None)
        if mevcut_slot:
            await q.answer(f"⚠️ Zaten Slot {mevcut_slot}'te kaydınız var!", show_alert=True)
            return

        if slotlar[no]["durum"] == "Dolu":
            await q.answer(f"⚠️ Bu slot başkası tarafından alındı!", show_alert=True)
            return
            
        durumlar[uid] = {"durum": "takim_adi", "slot": no}
        await q.message.reply_text(f"✅ Slot {no} seçildi. Takım adını yazın:")

async def mesaj(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global t_aktif, oda_id, oda_sifre
    uid = update.effective_user.id
    txt = update.message.text
    if not txt: return
    txt = txt.strip()

    # 1. Admin komutu en başta kontrol edilir
    if txt.lower() in ["admin", "/admin"]:
        durumlar[uid] = "admin_sifre_bekleniyor"
        await update.message.reply_text("🔒 Şifreyi girin:")
        return

    # 2. Şifre kontrolü (Eğer kullanıcı şifre beklenen aşamadaysa)
    if durumlar.get(uid) == "admin_sifre_bekleniyor":
        if txt == ADMIN_SIFRE:
            durumlar[uid] = "admin_panel"
            await update.message.reply_text("👑 Admin Paneli Başarıyla Açıldı:", reply_markup=a_klavye())
        else:
            durumlar.pop(uid, None)
            await update.message.reply_text("❌ Yanlış şifre!")
        return

    # 3. İptal komutu
    if txt.lower() == "iptal":
        for no, b in slotlar.items():
            if b.get("user_id") == uid:
                slotlar[no] = {"durum": "Boş", "takim": "-", "user_id": None}
                durumlar.pop(uid, None)
                await update.message.reply_text(f"✅ Slot {no} üzerindeki kaydınız iptal edildi!", reply_markup=m_menu())
                return
        await update.message.reply_text("⚠️ Aktif bir slot kaydınız bulunmuyor.", reply_markup=m_menu())
        return

    # 4. Diğer akışlar
    if uid in durumlar:
        d = durumlar[uid]
        if d == "bekle_bildirim":
            bildirimler.append(f"ID {uid}: {txt}")
            durumlar.pop(uid, None)
            await update.message.reply_text("✅ Mesajınız admine iletildi!", reply_markup=m_menu())
            return
        if d == "admin_panel":
            await update.message.reply_text("👑 Admin Paneli:", reply_markup=a_klavye())
            return
        if d == "adm_oda_id":
            durumlar[uid] = {"durum": "adm_oda_sifre", "id": txt}
            await update.message.reply_text("🔑 Oda şifresini yazın:")
            return
        if isinstance(d, dict) and d.get("durum") == "adm_oda_sifre":
            oda_id = d["id"]
            oda_sifre = txt
            durumlar[uid] = "admin_panel"
            for no, b in slotlar.items():
                if b.get("user_id"):
                    try: await context.bot.send_message(b["user_id"], f"🚨 Oda Bilgisi Paylaşıldı!\nSlot: {no}\nID: {oda_id}\nŞifre: {oda_sifre}")
                    except: pass
            await update.message.reply_text("✅ Oda bilgileri kaydedildi ve kullanıcılara bildirildi!", reply_markup=a_klav
