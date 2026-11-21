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

# Slot Klavyesi
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

# Admin Paneli Klavyesi
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
        await query.message.edit_text(profil_mesaji, reply_markup=klavye, parse_mode="Markdown
