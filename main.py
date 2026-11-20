import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

TOKEN = "9172005481:AAEbc_bAij8pRfdEvcDM9V1egFGzyl9QjaM"
ADMIN_SIFRE = "631363"

# Turnuva Durumu ve Veriler
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

# Ana Menü
def ana_menu_klavyesi():
    keyboard = [
        [InlineKeyboardButton("📋 Slot Tablosu", callback_data="menu_slot_tablosu")],
        [InlineKeyboardButton("🎮 Turnuvaya Kayıt Ol / Slot Seç", callback_data="menu_slot_sec")],
        [InlineKeyboardButton("👤 Profilim (Slotum & Oda Şifresi)", callback_data="menu_profil")],
        [InlineKeyboardButton("📩 Admine Bildirim Gönder", callback_data="menu_bildirim_gonder")],
        [InlineKeyboardButton("⚠️ Kayıt İptal Et", callback_data="menu_iptal")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Slot Klavyesi (Herkes güncel görür)
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
    keyboard.append([InlineKeyboardButton("🔙 Ana Menüye Dön", callback_data="menu_ana_sayfa")])
    return InlineKeyboardMarkup(keyboard)

# Butonlu Admin Paneli
def admin_paneli_klavyesi():
    keyboard = [
        [InlineKeyboardButton("🛠️ Turnuva Oluştur / Ayarla", callback_data="adm_turnuva_olustur")],
        [InlineKeyboardButton("🔑 Oda ID & Şifre Gir ve Bildir", callback_data="adm_odalink_iste")],
        [InlineKeyboardButton("🗑️ Tek Slot Sil", callback_data="adm_sil_sec")],
        [InlineKeyboardButton("🔄 Her Şeyi Sıfırla (Sıfırla)", callback_data="adm_hepsinisil")],
        [InlineKeyboardButton("📥 Gelen Bildirimleri Oku", callback_data="adm_bildirimleri_oku")],
        [InlineKeyboardButton("📢 Herkese Duyuru Gönder", callback_data="adm_duyuru_iste")],
        [InlineKeyboardButton("🚪 Admin Panelinden Çık", callback_data="menu_ana_sayfa")]
    ]
    return InlineKeyboardMarkup(keyboard)

# /start komutu
async def baslangic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bilinen_kullanicilar.add(user_id)
    
    if user_id in kullanici_durumlari:
        del kullanici_durumlari[user_id]
        
    if not turnuva_aktif:
        mesaj = "❌ **Şu anda aktif bir turnuva bulunmamaktadır.** Lütfen daha sonra tekrar deneyin."
        if update.callback_query:
            await update.callback_query.message.edit_text(mesaj, parse_mode="Markdown")
        else:
            await update.message.reply_text(mesaj, parse_mode="Markdown")
        return
    
    mesaj = (
        f"🎮 **PUBG Mobile Turnuvasına Hoş Geldiniz!**\n\n"
        f"⏳ **Turnuva Saati:** {ayar_geri_sayim}\n"
        f"📢 **Kanal:** {ayar_kanal_linki}\n\n"
        f"Lütfen yapmak istediğiniz işlemi seçin:"
    )
    
    if update.callback_query:
        await update.callback_query.message.edit_text(mesaj, reply_markup=ana_menu_klavyesi(), parse_mode="Markdown")
    else:
        await update.message.reply_text(mesaj, reply_markup=ana_menu_klavyesi(), parse_mode="Markdown")

# Buton Yöneticisi
async def dugme_isleyici(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        await query.message.edit_text(
            f"📋 **Güncel Slot Tablosu:**\nKırmızı dolu slotlarda takımların adları anlık olarak yazar.",
            reply_markup=slot_klavyesi_olustur(),
            parse_mode="Markdown"
        )
        return
        
    elif data == "menu_slot_sec":
        await query.message.edit_text(
            "🎮 Kayıt olmak istediğiniz boş bir slotu seçin:",
            reply_markup=slot_klavyesi_olustur(),
            parse_mode="Markdown"
        )
        return
        
    elif data == "menu_profil":
        # Kullanıcının aldığı slotu bul
        kullanici_slotu = None
        takim_adi = "-"
        for s_no, bilgi in yuvalar.items():
            if bilgi.get("user_id") == user_id:
                kullanici_slotu = s_no
                takim_adi = bilgi["takim"]
                break
                
        if kullanici_slotu:
            profil_mesaji = (
                f"👤 **Profil Bilgileriniz:**\n\n"
                f"📌 Slot Numaranız: {kullanici_slotu}\n"
                f"🏆 Takım Adınız: {takim_adi}\n"
                f"⏳ Turnuva Saati: {ayar_geri_sayim}\n\n"
                f"🔑 **Oda ID & Şifre:** {ayar_oda_id} / {ayar_oda_sifre}\n"
                f"ℹ️ *Şifreler turnuvadan 5 dk önce paylaşılacaktır.*\n"
                f"⚠️ *İptal etmek için sohbete `iptal` yazabilirsiniz.*"
            )
        else:
            profil_mesaji = "⚠️ Aktif bir slot kaydınız bulunmuyor. Önce 'Turnuvaya Kayıt Ol' butonundan slot seçiniz."
            
        klavye = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Ana Menüye Dön", callback_data="menu_ana_sayfa")]])
        await query.message.edit_text(profil_mesaji, reply_markup=klavye, parse_mode="Markdown")
        return
        
    elif data == "menu_bildirim_gonder":
        kullanici_durumlari[user_id] = {"durum": "kullanici_bildirim_bekliyor"}
        await query.message.reply_text("📩 Admine göndermek istediğiniz mesajı yazıp gönderin:")
        return
        
    elif data == "menu_iptal":
        bulunan_slot = None
        for s_no, bilgi in yuvalar.items():
            if bilgi.get("user_id") == user_id:
                bulunan_slot = s_no
                break
        if bulunan_slot:
            yuvalar[bulunan_slot] = {"durum": "Boş", "takim": "-", "user_id": None}
            await query.message.edit_text(f"✅ Slot {bulunan_slot} üzerindeki kaydınız iptal edildi!", reply_markup=ana_menu_klavyesi())
        else:
            await query.message.edit_text("⚠️ Aktif bir slot kaydınız bulunmuyor.", reply_markup=ana_menu_klavyesi())
        return

    # Admin Buton İşlemleri
    if data.startswith("adm_"):
        if data == "adm_hepsinisil":
            global turnuva_aktif, ayar_oda_id, ayar_oda_sifre, ayar_geri_sayim
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
            await query.message.reply_text("⏳ Adım 1/2: Turnuva saatini yazın (Örn: `Yarın Akşam 21:00`):")
            
        elif data == "adm_odalink_iste":
            kullanici_durumlari[user_id] = {"durum": "admin_oda_id_bekliyor"}
            await query.message.reply_text("🔑 Adım 1/2: Oda ID'sini yazın:")
            
        elif data == "adm_sil_sec":
            kullanici_durumlari[user_id] = {"durum": "admin_sil_bekliyor"}
            await query.message.reply_text("🗑️ Silmek istediğiniz slot numarasını yazın (Örn: `5`):")
            
        elif data == "adm_bildirimleri_oku":
            if not admin_bildirimleri:
                await query.message.edit_text("📥 Henüz gelen yeni bir bildirim yok.", reply_markup=admin_paneli_klavyesi())
            else:
                liste = "📥 **Gelen Bildirimler:**\n\n" + "\n".join([f"• {b}" for b in admin_bildirimleri])
                await query.message.edit_text(liste, reply_markup=admin_paneli_klavyesi(), parse_mode="Markdown")
            
        elif data == "adm_duyuru_iste":
            kullanici_durumlari[user_id] = {"durum": "admin_duyuru_bekliyor"}
            await query.message.reply_text("📢 Herkese göndermek istediğiniz duyuru mesajını yazın:")
        return

    # Slot Seçim İşlemi
    if data.startswith("slot_"):
        slot_no = int(data.split("_")[1])
        if yuvalar[slot_no]["durum"] == "Dolu":
            await query.message.reply_text(f"⚠️ Slot {slot_no} dolu! Bu slotta '{yuvalar[slot_no]['takim']}' takımı var.")
            return
            
        kullanici_durumlari[user_id] = {"durum": "bekleyen_takim_adi", "yuva": slot_no}
        await query.message.reply_text(f"✅ Slot {slot_no} seçildi.\n\nLütfen **takım adınızı** yazıp gönderin:")

# Mesaj ve Durum Yönetimi
async def mesaj_isleyici(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    metin = update.message.text
    if not metin:
        return
    metin = metin.strip()

    # Kullanıcıların "iptal" yazarak slot silmesi
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

    # Gizli Admin Giriş Komutu
    if metin.lower() in ["admin", "/admin"]:
        kullanici_durumlari[user_id] = {"durum": "admin_giris"}
        await update.message.reply_text("🔐 Lütfen admin şifresini girin:")
        return

    if user_id in kullanici_durumlari and kullanici_durumlari[user_id].get("durum") == "kullanici_bildirim_bekliyor":
        admin_bildirimleri.append(f"Kullanıcı ID {user_id}: {metin}")
        del kullanici_durumlari[user_id]
        await update.message.reply_text("✅ Mesajınız başarıyla admine iletildi!", reply_markup=ana_menu_klavyesi())
        return

    # Admin Şifre Kontrolü
    if user_id in kullanici_durumlari and kullanici_durumlari[user_id].get("durum") == "admin_giris":
        if metin == ADMIN_SIFRE:
            kullanici_durumlari[user_id]["durum"] = "admin_paneli"
            await update.message.reply_text(
                "👑 **Admin Paneline Başarıyla Giriş Yaptınız!**\n\nAşağıdaki butonlardan dilediğiniz işlemi seçebilirsiniz:",
                reply_markup=admin_paneli_klavyesi()
            )
        else:
            del kullanici_durumlari[user_id]
            await update.message.reply_text("❌ Hatalı şifre!")
        return

    # Admin Adım Adım Turnuva Oluşturma & Oda Girişi
    if user_id in kullanici_durumlari:
        durum = kullanici_durumlari[user_id].get("durum")
        
        if durum == "admin_turnuva_saat":
            global ayar_geri_sayim, turnuva_aktif
            ayar_geri_sayim = metin
            turnuva_aktif = True
            kullanici_durumlari[user_id]["durum"] = "admin_paneli"
            await update.message.reply_text(f"✅ Turnuva başarıyla oluşturuldu!\n⏳ Saat: {ayar_geri_sayim}\nTurnuva aktif hale getirildi.", reply_markup=admin_paneli_klavyesi())
            return
            
        elif durum == "admin_oda_id_bekliyor":
            kullanici_durumlari[user_id]["gecici_oda_id"] = metin
            kullanici_durumlari[user_id]["durum"] = "admin_oda_sifre_bekliyor"
            await update.message.reply_text("🔑 Adım 2/2: Oda şifresini yazın:")
            return
            
        elif durum == "admin_oda_sifre_bekliyor":
            global ayar_oda_id, ayar_oda_sifre
            oda_id = kullanici_durumlari[user_id].get("gecici_oda_id")
            oda_sifre = metin
            
            ayar_oda_id = oda_id
            ayar_oda_sifre = oda_sifre
            kullanici_durumlari[user_id]["durum"] = "admin_paneli"
            
            # Slot alan kullanıcılara otomatik bildirim gönder
            bilgilendirilenler = 0
            for s_no, bilgi in yuvalar.items():
                if bilgi.get("user_id") is not None:
                    try:
                        await context.bot.send_message(
                            chat_id=bilgi["user_id"],
                            text=f"🚨 **Oda Bilgileri Paylaşıldı!** 🚨\n\n📌 Slotunuz: {s_no}\n🔑 Oda ID: {ayar_oda_id}\n🔑 Oda Şifre: {ayar_oda_sifre}\n\n*Hadi oyuna!*",
                            parse_mode="Markdown"
                        )
                        bilgilendirilenler += 1
                    except Exception:
                        pass
                        
            await update.message.reply_text(f"✅ Oda bilgileri kaydedildi ve slot alan {bilgilendirilenler} kullanıcıya otomatik bildirildi!", reply_markup=admin_paneli_klavyesi())
            return
            
        elif durum == "admin_sil_bekliyor":
            try:
                s_no = int(metin)
                if s_no in yuvalar:
                    yuvalar[s_no] = {"durum": "Boş", "takim": "-", "user_id": None}
                    await update.message.reply_text(f"✅ Slot {s_no} başarıyla silindi ve boşaltıldı!", reply_markup=admin_paneli_klavyesi())
                else:
                    await update.message.reply_text("❌ Geçersiz slot numarası.", reply_markup=admin_paneli_klavyesi())
            except ValueError:
                await update.message.reply_text("❌ Lütfen geçerli bir sayı girin.", reply_markup=admin_paneli_klavyesi())
            kullanici_durumlari[user_id]["durum"] = "admin_paneli"
            return
            
        elif durum == "admin_duyuru_bekliyor":
            basarili = 0
            for uid in bilinen_kullanicilar:
                try:
                    await context.bot.send_message(chat_id=uid, text=f"📢 **DUYURU:**\n\n{metin}", parse_mode="Markdown")
                    basarili += 1
                except Exception:
                    pass
            await update.message.reply_text(f"✅ Duyuru {basarili} kullanıcıya iletildi.", reply_markup=admin_paneli_klavyesi())
            kullanici_durumlari[user_id]["durum"] = "admin_paneli"
            return

    # Normal Kullanıcı Takım Kaydı
    if not turnuva_aktif:
        await update.message.reply_text("❌ Şu anda aktif bir turnuva yok.")
        return

    if user_id in kullanici_durumlari and kullanici_durumlari[user_id].get("durum") == "bekleyen_takim_adi":
        if metin.startswith("/"):
            await update.message.reply_text("❌ Takım adı komut olamaz!")
            return
            
        yuva_no = kullanici_durumlari[user_id]["yuva"]
        yuvalar[yuva_no] = {"durum": "Dolu", "takim": metin, "user_id": user_id}
        del kullanici_durumlari[user_id]
        
        basari_mesaji = (
            f"🎉 **Tebrikler Başarıyla Kayıt Oldunuz!** 🎉\n\n"
            f"📌 Slot: {yuva_no}\n"
            f"🏆 Takım: {metin}\n"
            f"⏳ Turnuva Saati: {ayar_geri_sayim}\n\n"
            f"👤 *Profil butonundan slotunuza ve oda şifrenize her zaman bakabilirsiniz.*\n"
            f"⚠️ *İptal etmek için sohbete `iptal` yazabilirsiniz.*"
        )
        klavye = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Kanalımıza Git", url=ayar_kanal_linki)],
            [InlineKeyboardButton("🔙 Ana Menüye Dön", callback_data="menu_ana_sayfa")]
        ])
        await update.message.reply_text(basari_mesaji, reply_markup=klavye, parse_mode="Markdown")

def main():
    uygulama = Application.builder().token(TOKEN).build()

    uygulama.add_handler(CommandHandler("start", baslangic))
    uygulama.add_handler(CallbackQueryHandler(dugme_isleyici))
    uygulama.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mesaj_isleyici))

    print("Bot aktif ve çalışıyor...")
    uygulama.run_polling()

if __name__ == "__main__":
    main()
