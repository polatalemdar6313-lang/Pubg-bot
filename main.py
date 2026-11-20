import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Loglama ayarları
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# --- AYARLAR ---
TOKEN = "9172005481:AAEbc_bAij8pRfdEvcDM9V1egFGzyl9QjaM"
ADMIN_SIFRE = "631363"

# Bellek Verileri (25 Slot ve Admin/Oda Ayarları)
toplam_slot = 25
yuvalar = {i: {"durum": "Boş", "takim": "-", "user_id": None} for i in range(1, toplam_slot + 1)}
kullanici_durumlari = {}
bilinen_kullanicilar = set()

# Dinamik Ayarlar (Admin panelinden değiştirilebilir)
ayar_kanal_linki = "https://t.me/wexorganizasyon"
ayar_oda_bilgisi = "Oda bilgisi henüz girilmedi."

# /start komutu
async def baslangic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bilinen_kullanicilar.add(user_id)
    
    keyboard = []
    # 2'li sütunlar halinde butonlar oluşturalım
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
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🎮 **PUBG Mobile Turnuvasına Hoş Geldiniz!**\n\nKayıt olmak istediğiniz boş bir slotu seçin:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# Buton tıklama yönetimi
async def dugme_isleyici(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    
    if data.startswith("slot_"):
        slot_no = int(data.split("_")[1])
        
        if yuvalar[slot_no]["durum"] == "Dolu":
            await query.message.reply_text(f"⚠️ Slot {slot_no} maalesef dolu! Başka bir slot seçiniz.")
            return
            
        kullanici_durumlari[user_id] = {"durum": "bekleyen_takim_adi", "yuva": slot_no}
        await query.message.reply_text(f"✅ Slot {slot_no} seçildi.\n\nLütfen **takım adınızı** yazıp gönderin (Zorunludur):")

# Metin mesajı ve Admin Paneli yönetimi
async def mesaj_isleyici(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    metin = update.message.text
    
    # 1. Admin Girişi / Komutları Kontrolü
    if user_id in kullanici_durumlari and kullanici_durumlari[user_id].get("durum") == "admin_giris":
        if metin == ADMIN_SIFRE:
            kullanici_durumlari[user_id]["durum"] = "admin_paneli"
            await admin_paneli_goster(update)
        else:
            del kullanici_durumlari[user_id]
            await update.message.reply_text("❌ Hatalı şifre! Admin paneline giriş başarısız.")
        return

    # Admin Paneli İşlemleri İçindeyse
    if user_id in kullanici_durumlari and kullanici_durumlari[user_id].get("durum") == "admin_paneli":
        komutlar = metin.split(" ", 1)
        islem = komutlar[0].lower()
        
        if islem == "sil" and len(komutlar) > 1:
            try:
                s_no = int(komutlar[1])
                if s_no in yuvalar:
                    yuvalar[s_no] = {"durum": "Boş", "takim": "-", "user_id": None}
                    await update.message.reply_text(f"✅ Slot {s_no} başarıyla boşaltıldı.")
                else:
                    await update.message.reply_text("❌ Geçersiz slot numarası.")
            except ValueError:
                await update.message.reply_text("❌ Lütfen geçerli bir sayı girin. Örn: `sil 5`", parse_mode="Markdown")
                
        elif islem == "hepsinisil":
            for s_no in yuvalar:
                yuvalar[s_no] = {"durum": "Boş", "takim": "-", "user_id": None}
            await update.message.reply_text("✅ Tüm slotlar sıfırlandı ve boşaltıldı!")
            
        elif islem == "duyuru" and len(komutlar) > 1:
            duyuru_metni = komutlar[1]
            basarili = 0
            for uid in bilinen_kullanicilar:
                try:
                    await context.bot.send_message(chat_id=uid, text=f"📢 **DUYURU:**\n\n{duyuru_metni}", parse_mode="Markdown")
                    basarili += 1
                except Exception:
                    pass
            await update.message.reply_text(f"✅ Duyuru {basarili} kullanıcıya gönderildi.")
            
        elif islem == "odalink" and len(komutlar) > 1:
            global ayar_oda_bilgisi
            ayar_oda_bilgisi = komutlar[1]
            await update.message.reply_text(f"✅ Oda bilgisi/linki güncellendi:\n{ayar_oda_bilgisi}")
            
        elif islem == "kanallink" and len(komutlar) > 1:
            global ayar_kanal_linki
            ayar_kanal_linki = komutlar[1]
            await update.message.reply_text(f"✅ Kanal linki güncellendi:\n{ayar_kanal_linki}")
            
        elif islem == "cikis":
            del kullanici_durumlari[user_id]
            await update.message.reply_text("🚪 Admin panelinden çıkış yapıldı.")
        else:
            await admin_paneli_goster(update)
        return

    # 2. Normal Kullanıcı Takım Adı Kaydı
    if user_id in kullanici_durumlari and kullanici_durumlari[user_id].get("durum") == "bekleyen_takim_adi":
        if not metin or metin.startswith("/"):
            await update.message.reply_text("❌ Takım adı boş bırakılamaz! Lütfen geçerli bir takım adı yazın.")
            return
            
        yuva_no = kullanici_durumlari[user_id]["yuva"]
        yuvalar[yuva_no] = {"durum": "Dolu", "takim": metin, "user_id": user_id}
        del kullanici_durumlari[user_id]
        
        basari_mesaji = (
            f"🎉 **Tebrikler Başarıyla Kayıt Oldunuz!** 🎉\n\n"
            f"📌 Slot Numarası: {yuva_no}\n"
            f"🏆 Takım Adınız: {metin}\n\n"
            f"🔑 **Oda & Maç Bilgisi:**\n{ayar_oda_bilgisi}\n\n"
            f"📢 Kanalımıza göz atmayı unutmayın."
        )
        klavye = InlineKeyboardMarkup([[InlineKeyboardButton("📢 Turnuva Kanalına Git", url=ayar_kanal_linki)]])
        await update.message.reply_text(basari_mesaji, reply_markup=klavye, parse_mode="Markdown")

# /admin komutu
async def admin_giris_komutu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    kullanici_durumlari[user_id] = {"durum": "admin_giris"}
    await update.message.reply_text("🔐 Lütfen admin şifresini girin:")

async def admin_paneli_goster(update: Update):
    panel_mesaji = (
        "👑 **ADMİN PANELİNE HOŞ GELDİNİZ** 👑\n\n"
        "İşlem yapmak için aşağıdaki komutları yazabilirsiniz:\n\n"
        "• `sil [slot_no]` -> Belirli bir slotu boşaltır (Örn: `sil 3`)\n"
        "• `hepsinisil` -> Tüm slotları tamamen sıfırlar\n"
        "• `duyuru [mesaj]` -> Botu kullanan herkese bildirim yollar\n"
        "• `odalink [link/sifre]` -> Oda şifresini/linkini değiştirir\n"
        "• `kanallink [url]` -> Kanal linkini değiştirir\n"
        "• `cikis` -> Admin panelinden çıkar"
    )
    await update.message.reply_text(panel_mesaji, parse_mode="Markdown")

def main():
    uygulama = Application.builder().token(TOKEN).build()

    uygulama.add_handler(CommandHandler("start", baslangic))
    uygulama.add_handler(CommandHandler("admin", admin_giris_komutu))
    uygulama.add_handler(CallbackQueryHandler(dugme_isleyici))
    uygulama.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mesaj_isleyici))

    print("Bot aktif ve çalışıyor...")
    uygulama.run_polling()

if __name__ == "__main__":
    main()
