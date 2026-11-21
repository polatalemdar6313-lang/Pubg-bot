import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

TOKEN = "9172005481:AAEbc_bAij8pRfdEvcDM9V1egFGzyl9QjaM"
ADMIN_SIFRE = "631363"

turnuva_aktif = True
toplam_slot = 25
yuvalar = {i: {"durum": "Boş", "takim": "-", "user_id": None} for i in range(1, toplam_slot + 1)}
kullanici_durumlari = {}
bilinen_kullanicilar = set()
admin_bildirimleri = []

ayar_kanal_linki = "https://t.me/wexorganizasyon"
ayar_oda_id = "-"
ayar_oda_sifre = "-"
ayar_geri_sayim = "Ayarlanmadı"

def ana_menu_klavyesi():
    keyboard = [
        [InlineKeyboardButton("📋 Slot Tablosu", callback_data="menu_slot_tablosu")],
        [InlineKeyboardButton("🎮 Turnuvaya Kayıt Ol / Slot Seç", callback_data="menu_slot_sec")],
        [InlineKeyboardButton("👤 Profilim (Kayıt & Şifre)", callback_data="menu_profil")],
        [InlineKeyboardButton("📩 Admine Bildirim Gönder", callback_data="menu_bildirim_gonder")],
        [InlineKeyboardButton("⚠️ Kayıt İptal Et (İptal yaz)", callback_data="menu_iptal")]
    ]
    return InlineKeyboardMarkup(keyboard)

def slot_klavyesi_olustur():
    keyboard = []
    satir = []
    for slot_no, bilgi in yuvalar.items():
        if bilgi["durum"] == "Boş":
            buton_metni = f"Slot {slot_no} 🟢 BOŞ"
        else:
            buton_metni = f"Slot {slot_no} 🔴 {bilgi['takim']}"
            
        satir.append(InlineKeyboardButton(buton_metni, callback_data=f"slot_{slot_no}"))
        if len(satir) == 2:
            keyboard.append(satir)
            satir = []
    if satir:
        keyboard.append(satir)
    keyboard.append([InlineKeyboardButton("🔙 Ana Menü", callback_data="menu_ana_sayfa")])
    return InlineKeyboardMarkup(keyboard)

def admin_paneli_klavyesi():
    keyboard = [
        [InlineKeyboardButton("🛠️ Turnuva Oluştur", callback_data="adm_turnuva_olustur")],
        [InlineKeyboardButton("🔑 Oda ID & Şifre Gir", callback_data="adm_odalink_iste")],
        [InlineKeyboardButton("🗑️ Tek Slot Sil", callback_data="adm_sil_sec")],
        [InlineKeyboardButton("🔄 Sıfırla", callback_data="adm_hepsinisil")],
        [InlineKeyboardButton("📥 Bildirimleri Oku", callback_data="adm_bildirimleri_oku")],
        [InlineKeyboardButton("📢 Duyuru Gönder", callback_data="adm_duyuru_iste")],
        [InlineKeyboardButton("🚪 Çıkış", callback_data="menu_ana_sayfa")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def baslangic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bilinen_kullanicilar.add(user_id)
    
    if user_id in kullanici_durumlari:
        del kullanici_durumlari[user_id]
        
    if not turnuva_aktif:
        mesaj = "❌ Şu anda aktif bir turnuva bulunmamaktadır."
        if update.callback_query:
            await update.callback_query.message.edit_text(mesaj)
        else:
            await update.message.reply_text(mesaj)
        return
    
    mesaj = f"🎮 PUBG Mobile Turnuvasına Hoş Geldiniz!\n\n⏳ Turnuva Saati: {ayar_geri_sayim}\n📢 Kanal: {ayar_kanal_linki}\n\nİşlem seçin:\n*(İptal etmek için sohbete `iptal` yazabilirsiniz)*"
    
    if update.callback_query:
        await update.callback_query.message.edit_text(mesaj, reply_markup=ana_menu_klavyesi())
    else:
        await update.message.reply_text(mesaj, reply_markup=ana_menu_klavyesi())

async def dugme_isleyici(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global turnuva_aktif, ayar_oda_id, ayar_oda_sifre, ayar_geri_sayim
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    
    if data == "menu_ana_sayfa":
        if user_id in kullanici_durumlari:
            del kullanici_durumlari[user_id]
        await baslangic(update, context)
        return
        
    if not turnuva_aktif and not data.startswith("adm_"):
        await query.message.edit_text("❌ Şu anda aktif bir turnuva bulunmuyor.")
        return
        
    if data == "menu_slot_tablosu":
        await query.message.edit_text("📋 Güncel Slot Tablosu:\n(Dolu slotlar kırmızı görünür)", reply_markup=slot_klavyesi_olustur())
        return
        
    elif data == "menu_slot_sec":
        await query.message.edit_text("🎮 Kayıt olmak istediğiniz boş slotu seçin:", reply_markup=slot_klavyesi_olustur())
        return
        
    elif data == "menu_profil":
        kullanici_slotu = None
        takim_adi = "-"
        for s_no, bilgi in yuvalar.items():
            if bilgi.get("user_id") == user_id:
                kullanici_slotu = s_no
                takim_adi = bilgi["takim"]
                break
                
        if kullanici_slotu:
            profil_mesaji = f"👤 Profiliniz:\n\n📌 Slot: {kullanici_slotu}\n🏆 Takım: {takim_adi}\n⏳ Saat: {ayar_geri_sayim}\n\n🔑 Oda ID & Şifre: {ayar_oda_id} / {ayar_oda_sifre}\n(Şifreler turnuvadan 5 dk önce paylaşılır)\n⚠️ İptal etmek için sohbete `iptal` yazın."
        else:
            profil_mesaji = "⚠️ Aktif slot kaydınız yok. Önce slot seçiniz."
            
        klavye = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Ana Menü", callback_data="menu_ana_sayfa")]])
        await query.message.edit_text(profil_mesaji, reply_markup=klavye)
        return
        
    elif data == "menu_bildirim_gonder":
        kullanici_durumlari[user_id] = {"durum": "kullanici_bildirim_bekliyor"}
        await query.message.reply_text("📩 Admine göndermek istediğiniz mesajı yazın:")
        return
        
    elif data == "menu_iptal":
        bulunan_slot = None
        for s_no, bilgi in yuvalar.items():
            if bilgi.get("user_id") == user_id:
                bulunan_slot = s_no
                break
        if bulunan_slot:
            yuvalar[bulunan_slot] = {"durum": "Boş", "takim": "-", "user_id": None}
            await query.message.edit_text(f"✅ Slot {bulunan_slot} iptal edildi!", reply_markup=ana_menu_klavyesi())
        else:
            await query.message.edit_text("⚠️ Aktif kaydınız yok.", reply_markup=ana_menu_klavyesi())
        return

    if data.startswith("adm_"):
        if data == "adm_hepsinisil":
            for s_no in yuvalar:
                yuvalar[s_no] = {"durum": "Boş", "takim": "-", "user_id": None}
            ayar_oda_id = "-"
            ayar_oda_sifre = "-"
            ayar_geri_sayim = "Ayarlanmadı"
            turnuva_aktif = False
            admin_bildirimleri.clear()
            await query.message.edit_text("🔄 Her şey sıfırlandı ve turnuva kapatıldı!", reply_markup=admin_paneli_klavyesi())
            
        elif data == "adm_turnuva_olustur":
            kullanici_durumlari[user_id] = {"durum": "admin_turnuva_saat"}
            await query.message.reply_text("⏳ Turnuva saatini yazın (Örn: 21:00):")
            
        elif data == "adm_odalink_iste":
            kullanici_durumlari[user_id] = {"durum": "admin_oda_id_bekliyor"}
            await query.message.reply_text("🔑 Oda ID'sini yazın:")
            
        elif data == "adm_sil_sec":
            kullanici_durumlari[user_id] = {"durum": "admin_sil_bekliyor"}
            await query.message.reply_text("🗑️ Silinecek slot numarasını yazın:")
            
        elif data == "adm_bildirimleri_oku":
            if not admin_bildirimleri:
                await query.message.edit_text("📥 Bildirim yok.", reply_markup=admin_paneli_klavyesi())
            else:
                liste = "📥 Bildirimler:\n\n" + "\n".join(admin_bildirimleri)
                await query.message.edit_text(liste, reply_markup=admin_paneli_klavyesi())
            
        elif data == "adm_duyuru_iste":
            kullanici_durumlari[user_id] = {"durum": "admin_duyuru_bekliyor"}
            await query.message.reply_text("📢 Duyuru metnini yazın:")
        return

    # Dolu slot kontrolü
    if data.startswith("slot_"):
        slot_no = int(data.split("_")[1])
        if yuvalar[slot_no]["durum"] == "Dolu":
            await query.message.reply_text(f"⚠️ Bu slot ({slot_no}) dolu! Lütfen başka bir boş slot seçin.")
            return
            
        kullanici_durumlari[user_id] = {"durum": "bekleyen_takim_adi", "yuva": slot_no}
        await query.message.reply_text(f"✅ Slot {slot_no} seçildi. Takım adını yazın:\n*(İptal için sohbete `iptal` yazabilirsiniz)*")

async def mesaj_isleyici(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global turnuva_aktif, ayar_oda_id, ayar_oda_sifre, ayar_geri_sayim
    user_id = update.effective_user.id
    metin = update.message.text
    if not metin:
        return
    metin = metin.strip()

    if metin.lower() == "iptal":
        bulunan_slot = None
        for s_no, bilgi in yuvalar.items():
            if bilgi.get("user_id") == user_id:
                bulunan_slot = s_no
                break
        if bulunan_slot:
            yuvalar[bulunan_slot] = {"durum": "Boş", "takim": "-", "user_id": None}
            if user_id in kullanici_durumlari:
                del kullanici_durumlari[user_id]
            await update.message.reply_text(f"✅ Slot {bulunan_slot} üzerindeki kaydınız iptal edildi!", reply_markup=ana_menu_klavyesi())
        else:
            await update.message.reply_text("⚠️ Aktif bir slot kaydınız bulunmuyor.", reply_markup=ana_menu_klavyesi())
        return

    if metin.lower() in ["admin", "/admin"]:
        kullanici_durumlari[user_id] = {"durum": "admin_giris"}
        await update.message.reply_text("🔐 Şifreyi girin:")
        return

    if user_id in kullanici_durumlari and kullanici_durumlari[user_id].get("durum") == "kullanici_bildirim_bekliyor":
        admin_bildirimleri.append(f"ID {user_id}: {metin}")
        del kullanici_durumlari[user_id]
        await update.message.reply_text("✅ Mesajınız admine iletildi!", reply_markup=ana_menu_klavyesi())
        return

    if user_id in kullanici_durumlari and kullanici_durumlari[user_id].get("durum") == "admin_giris":
        # Admin şifresi ne yazılırsa yazılsın kabul edilsin istendiği için direkt panele alıyoruz
        kullanici_durumlari[user_id]["durum"] = "admin_paneli"
        await update.message.reply_text("👑 Admin Paneli:", reply_markup=admin_paneli_klavyesi())
        return

    if user_id in kullanici_durumlari:
        durum = kullanici_durumlari[user_id].get("durum")
        
        if durum == "admin_turnuva_saat":
            ayar_geri_sayim = metin
            turnuva_aktif = True
            kullanici_durumlari[user_id]["durum"] = "admin_paneli"
            await update.message.reply_text(f"✅ Turnuva açıldı! Saat: {ayar_geri_sayim}", reply_markup=admin_paneli_klavyesi())
            return
            
        elif durum == "admin_oda_id_bekliyor":
            kullanici_durumlari[user_id]["gecici_oda_id"] = metin
            kullanici_durumlari[user_id]["durum"] = "admin_oda_sifre_bekliyor"
            await update.message.reply_text("🔑 Oda şifresini yazın:")
            return
            
        elif durum == "admin_oda_sifre_bekliyor":
            oda_id = kullanici_durumlari[user_id].get("gecici_oda_id")
            ayar_oda_id = oda_id
            ayar_oda_sifre = metin
            kullanici_durumlari[user_id]["durum"] = "admin_paneli"
            
            for s_no, bilgi in yuvalar.items():
                if bilgi.get("user_id") is not None:
                    try:
                        await context.bot.send_message(chat_id=bilgi["user_id"], text=f"🚨 Oda Bilgisi Paylaşıldı!\nSlot: {s_no}\nID: {ayar_oda_id}\nŞifre: {ayar_oda_sifre}")
                    except Exception:
                        pass
                        
            await update.message.reply_text("✅ Oda bilgileri kaydedildi ve kullanıcılara bildirildi!", reply_markup=admin_paneli_klavyesi())
            return
            
        elif durum == "admin_sil_bekliyor":
            try:
                s_no = int(metin)
                if s_no in yuvalar:
                    yuvalar[s_no] = {"durum": "Boş", "takim": "-", "user_id": None}
                    await update.message.reply_text(f"✅ Slot {s_no} silindi!", reply_markup=admin_paneli_klavyesi())
                else:
                    await update.message.reply_text("❌ Geçersiz slot.", reply_markup=admin_paneli_klavyesi())
            except ValueError:
                await update.message.reply_text("❌ Sayı girin.", reply_markup=admin_paneli_klavyesi())
            kullanici_durumlari[user_id]["durum"] = "admin_paneli"
            return
            
        elif durum == "admin_duyuru_bekliyor":
            for uid in bilinen_kullanicilar:
                try:
                    await context.bot.send_message(chat_id=uid, text=f"📢 DUYURU:\n\n{metin}")
                except Exception:
                    pass
            await update.message.reply_text("✅ Duyuru gönderildi!", reply_markup=admin_paneli_klavyesi())
            kullanici_durumlari[user_id]["durum"] = "admin_paneli"
            return

    if not turnuva_aktif:
        await update.message.reply_text("❌ Şu anda aktif bir turnuva yok.")
        return

    if user_id in kullanici_durumlari and kullanici_durumlari[user_id].get("durum") == "bekleyen_takim_adi":
        if metin.startswith("/"):
            await update.message.reply_text("❌ Komut olamaz!")
            return
            
        yuva_no = kullanici_durumlari[user_id]["yuva"]
        yuvalar[yuva_no] = {"durum": "Dolu", "takim": metin, "user_id": user_id}
        del kullanici_durumlari[user_id]
        
        basari_mesaji = f"🎉 Kayıt Oldunuz!\n\n📌 Slot: {yuva_no}\n🏆 Takım: {metin}\n⏳ Saat: {ayar_geri_sayim}\n\nProfil butonundan şifreye bakabilirsiniz.\n⚠️ İptal etmek için `iptal` yazın."
        klavye = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Ana Menü", callback_data="menu_ana_sayfa")]])
        await update.message.reply_text(basari_mesaji, reply_markup=klavye)

def main():
    uygulama = Application.builder().token(TOKEN).build()

    uygulama.add_handler(CommandHandler("start", baslangic))
    uygulama.add_handler(CallbackQueryHandler(dugme_isleyici))
    uygulama.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mesaj_isleyici))

    print("Bot aktif ve çalışıyor...")
    uygulama.run_polling()

if __name__ == "__main__":
    main()
