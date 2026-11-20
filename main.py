import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

TOKEN = "9172005481:AAEbc_bAij8pRfdEvcDM9V1egFGzyl9QjaM"
ADMIN_SIFRE = "631363"

toplam_slot = 25
yuvalar = {i: {"durum": "Boş", "takim": "-", "user_id": None} for i in range(1, toplam_slot + 1)}
kullanici_durumlari = {}
bilinen_kullanicilar = set()

ayar_kanal_linki = "https://t.me/wexorganizasyon"
ayar_oda_bilgisi = "Oda bilgisi henüz girilmedi."
ayar_geri_sayim = "Yarın Akşam 20:00"

# Ana Menü (Start Menüsü)
def ana_menu_klavyesi():
    keyboard = [
        [InlineKeyboardButton("📋 Slot Tablosu (Durum Göster)", callback_data="menu_slot_tablosu")],
        [InlineKeyboardButton("🎮 Turnuvaya Kayıt Ol / Slot Seç", callback_data="menu_slot_sec")],
        [InlineKeyboardButton("⚠️ Kayıt İptal Et", callback_data="menu_iptal")],
        [InlineKeyboardButton("👑 Admin Paneli", callback_data="menu_admin_giris")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Slot Tablosu / Seçim Klavyesi
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

# Tamamen Butonlu Admin Paneli Klavyesi
def admin_paneli_klavyesi():
    keyboard = [
        [InlineKeyboardButton("🗑️ Tek Slot Sil (Numara Seç)", callback_data="adm_sil_sec")],
        [InlineKeyboardButton("🚨 Tüm Slotları Boşalt (Hepsini Sil)", callback_data="adm_hepsinisil")],
        [InlineKeyboardButton("📢 Herkese Duyuru Gönder", callback_data="adm_duyuru_iste")],
        [InlineKeyboardButton("🔑 Oda Bilgisini Değiştir", callback_data="adm_odalink_iste")],
        [InlineKeyboardButton("⏳ Geri Sayım Süresini Ayarla", callback_data="adm_sure_iste")],
        [InlineKeyboardButton("🚪 Admin Panelinden Çık", callback_data="adm_cikis")]
    ]
    return InlineKeyboardMarkup(keyboard)

# /start komutu
async def baslangic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bilinen_kullanicilar.add(user_id)
    
    mesaj = (
        f"🎮 **PUBG Mobile Turnuvasına Hoş Geldiniz!**\n\n"
        f"⏳ **Turnuva / Geri Sayım:** {ayar_geri_sayim}\n"
        f"📢 **Kanal:** {ayar_kanal_linki}\n\n"
        f"Lütfen yapmak istediğiniz işlemi aşağıdaki butonlardan seçin:"
    )
    
    if update.callback_query:
        await update.callback_query.message.edit_text(mesaj, reply_markup=ana_menu_klavyesi(), parse_mode="Markdown")
    else:
        await update.message.reply_text(mesaj, reply_markup=ana_menu_klavyesi(), parse_mode="Markdown")

# Buton Tıklama Yöneticisi
async def dugme_isleyici(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    
    # Ana Menü Yönlendirmeleri
    if data == "menu_ana_sayfa":
        await baslangic(update, context)
        return
        
    elif data == "menu_slot_tablosu":
        await query.message.edit_text(
            f"📋 **Güncel Slot Tablosu:**\n⏳ Başlangıç: {ayar_geri_sayim}\nKırmızı dolu slotlarda takım adları yazar.",
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
        
    elif data == "menu_admin_giris":
        kullanici_durumlari[user_id] = {"durum": "admin_giris"}
        await query.message.reply_text("🔐 Lütfen admin şifresini (`631363`) sohbet kısmına yazarak gönderin:")
        return

    # Admin Buton İşlemleri
    if data.startswith("adm_"):
        if data == "adm_hepsinisil":
            for s_no in yuvalar:
                yuvalar[s_no] = {"durum": "Boş", "takim": "-", "user_id": None}
            await query.message.edit_text("✅ Tüm slotlar başarıyla sıfırlandı!", reply_markup=admin_paneli_klavyesi())
            
        elif data == "adm_cikis":
            if user_id in kullanici_durumlari:
                del kullanici_durumlari[user_id]
            await query.message.edit_text("🚪 Admin panelinden çıkış yapıldı.", reply_markup=ana_menu_klavyesi())
            
        elif data == "adm_sil_sec":
            kullanici_durumlari[user_id] = {"durum": "admin_sil_bekliyor"}
            await query.message.reply_text("🗑️ Hangi slotu silmek istiyorsanız numarasını yazın (Örn: `5`):")
            
        elif data == "adm_duyuru_iste":
            kullanici_durumlari[user_id] = {"durum": "admin_duyuru_bekliyor"}
            await query.message.reply_text("📢 Herkese göndermek istediğiniz duyuru mesajını yazın:")
            
        elif data == "adm_odalink_iste":
            kullanici_durumlari[user_id] = {"durum": "admin_odalink_bekliyor"}
            await query.message.reply_text("🔑 Yeni oda şifresini / bilgisini yazın:")
            
        elif data == "adm_sure_iste":
            kullanici_durumlari[user_id] = {"durum": "admin_sure_bekliyor"}
            await query.message.reply_text("⏳ Yeni turnuva süresini / geri sayımı yazın (Örn: `Yarın 21:00`):")
        return

    # Slot Seçim İşlemi
    if data.startswith("slot_"):
        slot_no = int(data.split("_")[1])
        if yuvalar[slot_no]["durum"] == "Dolu":
            await query.message.reply_text(f"⚠️ Slot {slot_no} dolu! Bu slotta '{yuvalar[slot_no]['takim']}' takımı var.")
            return
            
        kullanici_durumlari[user_id] = {"durum": "bekleyen_takim_adi", "yuva": slot_no}
        await query.message.reply_text(f"✅ Slot {slot_no} seçildi.\n\nLütfen **takım adınızı** yazıp gönderin:")

# Mesaj ve Admin Panel Durum Yönetimi
async def mesaj_isleyici(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    metin = update.message.text
    if not metin:
        return
    metin = metin.strip()

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

    # Admin Özel Durum Girişleri (Silme, Duyuru, Süre vb.)
    if user_id in kullanici_durumlari and kullanici_durumlari[user_id].get("durum") == "admin_paneli":
        durum_tipi = kullanici_durumlari[user_id].get("alt_durum")
        
        if durum_tipi == "sil":
            try:
                s_no = int(metin)
                if s_no in yuvalar:
                    yuvalar[s_no] = {"durum": "Boş", "takim": "-", "user_id": None}
                    await update.message.reply_text(f"✅ Slot {s_no} boşaltıldı.", reply_markup=admin_paneli_klavyesi())
                else:
                    await update.message.reply_text("❌ Geçersiz slot numarası.", reply_markup=admin_paneli_klavyesi())
            except ValueError:
                await update.message.reply_text("❌ Lütfen sadece sayı girin (Örn: 3)", reply_markup=admin_paneli_klavyesi())
            kullanici_durumlari[user_id]["alt_durum"] = None
            return

    # Admin Alt Komut Beklemeleri
    if user_id in kullanici_durumlari:
        durum = kullanici_durumlari[user_id].get("durum")
        
        if durum == "admin_sil_bekliyor":
            try:
                s_no = int(metin)
                if s_no in yuvalar:
                    yuvalar[s_no] = {"durum": "Boş", "takim": "-", "user_id": None}
                    await update.message.reply_text(f"✅ Slot {s_no} başarıyla silindi ve boşaltıldı!", reply_markup=admin_paneli_klavyesi())
                else:
                    await update.message.reply_text("❌ Böyle bir slot bulunmuyor.", reply_markup=admin_paneli_klavyesi())
            except ValueError:
                await update.message.reply_text("❌ Geçerli bir sayı giriniz.", reply_markup=admin_paneli_klavyesi())
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
            
        elif durum == "admin_odalink_bekliyor":
            global ayar_oda_bilgisi
            ayar_oda_bilgisi = metin
            await update.message.reply_text(f"✅ Oda bilgisi güncellendi:\n{ayar_oda_bilgisi}", reply_markup=admin_paneli_klavyesi())
            kullanici_durumlari[user_id]["durum"] = "admin_paneli"
            return
            
        elif durum == "admin_sure_bekliyor":
            global ayar_geri_sayim
            ayar_geri_sayim = metin
            await update.message.reply_text(f"✅ Turnuva geri sayım süresi güncellendi:\n{ayar_geri_sayim}", reply_markup=admin_paneli_klavyesi())
            kullanici_durumlari[user_id]["durum"] = "admin_paneli"
            return

    # Normal Kullanıcı Takım Kaydı
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
            f"⏳ Geri Sayım: {ayar_geri_sayim}\n\n"
            f"🔑 **Oda & Maç Bilgisi:**\n{ayar_oda_bilgisi}"
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
