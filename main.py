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

# Slot klavyesi
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
    return InlineKeyboardMarkup(keyboard)

# Admin Paneli Butonları
def admin_klavyesi_olustur():
    keyboard = [
        [InlineKeyboardButton("🗑️ Tüm Slotları Boşalt (Hepsini Sil)", callback_data="adm_hepsinisil")],
        [InlineKeyboardButton("🚪 Admin Panelinden Çık", callback_data="adm_cikis")]
    ]
    return InlineKeyboardMarkup(keyboard)

# /start komutu
async def baslangic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bilinen_kullanicilar.add(user_id)
    
    reply_markup = slot_klavyesi_olustur()
    await update.message.reply_text(
        "🎮 **PUBG Mobile Turnuvasına Hoş Geldiniz!**\n\n"
        "Kayıt olmak istediğiniz boş bir slotu seçin:\n"
        "*(Not: Kaydınızı iptal etmek için istediğiniz zaman `/iptal` yazabilirsiniz)*",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# /iptal komutu
async def iptal_komutu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bulunan_slot = None
    
    for s_no, bilgi in yuvalar.items():
        if bilgi.get("user_id") == user_id:
            bulunan_slot = s_no
            break
            
    if bulunan_slot:
        yuvalar[bulunan_slot] = {"durum": "Boş", "takim": "-", "user_id": None}
        if user_id in kullanici_durumlari:
            del kullanici_durumlari[user_id]
        await update.message.reply_text(f"✅ Slot {bulunan_slot üzerindeki kaydınız başarıyla iptal edildi!")
    else:
        await update.message.reply_text("⚠️ Aktif bir slot kaydınız bulunmuyor.")

# Buton tıklama yönetimi
async def dugme_isleyici(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    
    # Admin Butonları
    if data.startswith("adm_"):
        if data == "adm_hepsinisil":
            for s_no in yuvalar:
                yuvalar[s_no] = {"durum": "Boş", "takim": "-", "user_id": None}
            await query.message.edit_text("✅ Tüm slotlar başarıyla sıfırlandı!", reply_markup=admin_klavyesi_olustur())
        elif data == "adm_cikis":
            if user_id in kullanici_durumlari:
                del kullanici_durumlari[user_id]
            await query.
