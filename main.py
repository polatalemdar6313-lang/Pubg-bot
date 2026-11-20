import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# --- AYARLANACAK KANAL LİNKİ ---
KANAL_LINKI = "@WEXevent_bot.
https://t.me/wexorganizasyon"

# Bellek verileri
yuvalar = {i: {"durum": "Boş", "takim": "-", "logo": "-"} for i in range(1, 26)}
kullanici_durumlari = {}
bilinen_kullanicilar = set() # Toplu duyuru göndermek için botu kullananlar

async def baslangic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bilinen_kullanicilar.add(user_id)
    
    if user_id in kullanici_durumlari:
        del kullanici_durumlari[user_id]
    
    dolu_sayisi = sum(1 for y in yuvalar.values() if y["durum"] == "Dolu")
    
    metin = (
        f"🏆 **WEXevent PUBG Turnuva Slot Sistemi** 🏆\n\n"
        f"Toplam Slot: 25\n"
        f"🔴 Dolu: {dolu_sayisi} | 🟢 Boş: {25 - dolu_sayisi}\n\n"
        f"Lütfen yapmak istediğiniz işlemi seçin:"
    )
    
    klavye = [
        [InlineKeyboardButton("📋 Turnuva Tablosunu Gör (Slotlar)", callback_data="liste")],
        [InlineKeyboardButton("🎯 Slot Seç / Kayıt Ol", callback_data="kayit_sec")],
        [InlineKeyboardButton("📢 Admin Kanalı ve Oda Bilgileri", url=KANAL_LINKI)],
        [InlineKeyboardButton("🛠️ Yönetici Paneli (Admin)", callback_data="admin_giris")]
    ]
    
    await update.message.reply_text(metin, reply_markup=InlineKeyboardMarkup(klavye), parse_mode="Markdown")

async def dugme_isleyici(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    veri = query.data
    user_id = query.from_user.id

    if veri == "ana_menu":
        if user_id in kullanici_durumlari:
            del kullanici_durumlari[user_id]
        
        dolu_sayisi = sum(1 for y in yuvalar.values() if y["durum"] == "Dolu")
        metin = (
            f"🏆 **WEXevent PUBG Turnuva Slot Sistemi** 🏆\n\n"
            f"Toplam Slot: 25\n"
            f"🔴 Dolu: {dolu_sayisi} | 🟢 Boş: {25 - dolu_sayisi}\n\n"
            f"Lütfen yapmak istediğiniz işlemi seçin:"
        )
        klavye = [
            [InlineKeyboardButton("📋 Turnuva Tablosunu Gör (Slotlar)", callback_data="liste")],
            [InlineKeyboardButton("🎯 Slot Seç / Kayıt Ol", callback_data="kayit_sec")],
            [InlineKeyboardButton("📢 Admin Kanalı ve Oda Bilgileri", url=KANAL_LINKI)],
            [InlineKeyboardButton("🛠️ Yönetici Paneli (Admin)", callback_data="admin_giris")]
        ]
        await query.message.edit_text(metin, reply_markup=InlineKeyboardMarkup(klavye), parse_mode="Markdown")

    elif veri == "liste":
        liste_metni = "📋 **25 Slotluk Turnuva Tablosu**\n\n"
        for i in range(1, 26):
            y = yuvalar[i]
            if y["durum"] == "Boş":
                liste_metni += f"Slot {i}: 🟢 **BOŞ**\n"
            else:
                liste_metni += f"Slot {i}: 🔴 **DOLU** — 🏷️ {y['takim']} | 🎨 {y['logo']}\n"
        
        klavye = [[InlineKeyboardButton("🔙 Ana Menü", callback_data="ana_menu")]]
        await query.message.edit_text(liste_metni, reply_markup=InlineKeyboardMarkup(klavye), parse_mode="Markdown")

    elif veri == "kayit_sec":
        bos_slotlar = [str(i) for i in range(1, 26) if yuvalar[i]["durum"] == "Boş"]
        if not bos_slotlar:
            await query.message.edit_text("⚠️ Üzgünüz, tüm slotlar dolmuş durumda!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Ana Menü", callback_data="ana_menu")]]))
            return
        
        kullanici_durumlari[user_id] = {"durum": "bekleyen_yuva"}
        await query.message.edit_text(
            "🎯 Lütfen 1 ile 25 arasında **boş olan** bir slot numarası yazın (Örn: 5):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 İptal / Ana Menü", callback_data="ana_menu")]])
        )

    elif veri == "admin_giris":
        kullanici_durumlari[user_id] = {"durum": "bekleyen_admin_sifre"}
        await query.message.edit_text(
            "🔐 Yönetici paneline erişmek için lütfen **6 haneli admin şifresini** (`631363`) girin:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 İptal / Ana Menü", callback_data="ana_menu")]])
        )

    elif veri == "admin_panel":
        klavye = [
            [InlineKeyboardButton("📢 Herkese Duyuru / Açıklama Yaz", callback_data="admin_duyuru_yaz")],
            [InlineKeyboardButton("🗑️ Bir Slotu Boşalt", callback_data="admin_slot_bosalt")],
            [InlineKeyboardButton("🔄 Tüm Slotları Sıfırla", callback_data="admin_sifirla")],
            [InlineKeyboardButton("🔙 Ana Menü", callback_data="ana_menu")]
        ]
        await query.message.edit_text("🛠️ **Yönetici Paneli**\n\nYapmak istediğiniz yönetici işlemini seçin:", reply_markup=InlineKeyboardMarkup(klavye), parse_mode="Markdown")

    elif veri == "admin_duyuru_yaz":
        kullanici_durumlari[user_id] = {"durum": "bekleyen_admin_duyuru_metni"}
        await query.message.edit_text(
            "📢 Kullanıcılara göndermek istediğiniz **açıklama / duyuru metnini** yazıp gönderin:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 İptal", callback_data="admin_panel")]])
        )

    elif veri == "admin_sifirla":
        for i in range(1, 26):
            yuvalar[i] = {"durum": "Boş", "takim": "-", "logo": "-"}
        await query.message.edit_text(
            "✅ Tüm 25 slot başarıyla sıfırlandı ve boşaltıldı!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛠️ Admin Panele Dön", callback_data="admin_panel"), InlineKeyboardButton("🔙 Ana Menü", callback_data="ana_menu")]])
        )

    elif veri == "admin_slot_bosalt":
        kullanici_durumlari[user_id] = {"durum": "bekleyen_admin_bosalt"}
        await query.message.edit_text(
            "🗑️ Boşaltmak istediğiniz slot numarasını yazın (Örn: 3):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 İptal", callback_data="admin_panel")]])
        )

async def mesaj_isleyici(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bilinen_kullanicilar.add(user_id)
    metin = update.message.text.strip()

    if user_id not in kullanici_durumlari:
        return

    durum_bilgisi = kullanici_durumlari[user_id]
    durum = durum_bilgisi.get("durum")

    # 1. Admin Şifre Kontrolü
    if durum == "bekleyen_admin_sifre":
        if metin == "631363":
            del kullanici_durumlari[user_id]
            klavye = [
                [InlineKeyboardButton("📢 Herkese Duyuru / Açıklama Yaz", callback_data="admin_duyuru_yaz")],
                [InlineKeyboardButton("🗑️ Bir Slotu Boşalt", callback_data="admin_slot_bosalt")],
                [InlineKeyboardButton("🔄 Tüm Slotları Sıfırla", callback_data="admin_sifirla")],
                [InlineKeyboardButton("🔙 Ana Menü", callback_data="ana_menu")]
            ]
            await update.message.reply_text("✅ Şifre Doğru! Yönetici paneline hoş geldiniz.", reply_markup=InlineKeyboardMarkup(klavye))
        else:
            await update.message.reply_text("❌ Hatalı şifre! Lütfen doğru şifreyi girin veya /start yazarak ana menüye dönün.")

    # 2. Toplu Duyuru Gönderme İşlemi
    elif durum == "bekleyen_admin_duyuru_metni":
        del kullanici_durumlari[user_id]
        duyuru_metni = f"📢 **TURNUVA DUYURUSU / AÇIKLAMA** 📢\n\n{metin}"
        
        gonderim_sayisi = 0
        for kid in bilinen_kullanicilar:
            try:
                await context.bot.send_message(chat_id=kid, text=duyuru_metni, parse_mode="Markdown")
                gonderim_sayisi += 1
            except Exception:
                pass
        
        klavye = [
            [InlineKeyboardButton("🛠️ Yönetici Paneli", callback_data="admin_panel")],
            [InlineKeyboardButton("🔙 Ana Menü", callback_data="ana_menu")]
        ]
        await update.message.reply_text(f"✅ Duyuru başarıyla {gonderim_sayisi} kullanıcıya gönderildi!", reply_markup=InlineKeyboardMarkup(klavye))

    # 3. Admin Slot Boşaltma
    elif durum == "bekleyen_admin_bosalt":
        try:
            slot_no = int(metin)
            if 1 <= slot_no <= 25:
                yuvalar[slot_no] = {"durum": "Boş", "takim": "-", "logo": "-"}
                del kullanici_durumlari[user_id]
                await update.message.reply_text(f"✅ Slot {slot_no} başarıyla boşaltıldı!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛠️ Yönetici Paneli", callback_data="admin_panel"), InlineKeyboardButton("🔙 Ana Menü", callback_data="ana_menu")]]))
            else:
                await update.message.reply_text("❌ Lütfen 1 ile 25 arasında geçerli bir slot numarası girin:")
        except ValueError:
            await update.message.reply_text("❌ Hata: Lütfen geçerli bir sayı girin (Örn: 5).")

    # 4. Normal Kullanıcı Slot Seçimi
    elif durum == "bekleyen_yuva":
        try:
            yuva_no = int(metin)
            if not (1 <= yuva_no <= 25):
                await update.message.reply_text("❌ Hata: Lütfen 1 ile 25 arasında geçerli bir slot numarası girin:")
                return
            
            if yuvalar[yuva_no]["durum"] == "Dolu":
                await update.message.reply_text(f"⚠️ Bu slot ({yuva_no}) maalesef dolu! Lütfen başka bir slot seçin:")
                return
            
            kullanici_durumlari[user_id] = {"durum": "bekleyen_takim_adi", "yuva": yuva_no}
            await update.message.reply_text(f"✅ Slot {yuva_no} seçildi.\n\nLütfen **Takım Adınızı** yazın:")
        except ValueError:
            await update.message.reply_text("❌ Hata: Lütfen geçerli bir sayı girin (Örn: 5).")

    # 5. Takım Adı Alma
    elif durum == "bekleyen_takim_adi":
        if not metin:
            await update.message.reply_text("❌ Takım adı boş bırakılamaz! Lütfen takım adınızı yazın:")
            return
        
        yuva_no = durum_bilgisi["yuva"]
        kullanici_durumlari[user_id] = {"durum": "bekleyen_logo", "yuva": yuva_no, "takim_adi": metin}
        await update.message.reply_text("🎨 Takım adı alındı.\n\nİstiyorsanız **Logo/Sembol** yazın (Geçmek istemiyorsanız `-` yazabilirsiniz):")

    # 6. Logo Alma ve Kaydı Tamamlama
    elif durum == "bekleyen_logo":
        yuva_no = durum_bilgisi["yuva"]
        takim_adi = durum_bilgisi["takim_adi"]
        logo = metin if metin != "-" else "Logosuz"

        yuvalar[yuva_no] = {"durum": "Dolu", "takim": takim_adi, "logo": logo}
        del kullanici_durumlari[user_id]

        basari_mesaji = (
            f"🎉 **Tebrikler Başarıyla Kayıt Oldunuz!** 🎉\n\n"
            f"📍 Slot: {yuva_no}\n"
            f"🏷️ Takım: {takim_adi}\n"
            f"🎨 Logo: {logo}\n\n"
            f"Tabloyu görmek için /start yazabilirsiniz."
        )
        klavye = [[InlineKeyboardButton("📢 Admin Kanalına Git", url=KANAL_LINKI)], [InlineKeyboardButton("🔙 Ana Menü", callback_data="ana_menu")]]
        await update.message.reply_text(basari_mesaji, reply_markup=InlineKeyboardMarkup(klavye), parse_mode="Markdown")

if __name__ == '__main__':
    TOKEN = "9172005481:AAEbc_bAij8pRfDeCDM9V1egFGzyl9QjaM" # Kendi token'ını buraya yazabilirsin
    
    uygulama = Application.builder().token(TOKEN).build()
    
    uygulama.add_handler(CommandHandler("start", baslangic))
    uygulama.add_handler(CallbackQueryHandler(dugme_isleyici))
    uygulama.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mesaj_isleyici))
    
    print("Bot aktif ve çalışıyor...")
    uygulama.run_polling()
