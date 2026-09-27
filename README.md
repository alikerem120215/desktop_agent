# 🖥️ Desktop Agent — Multimodal Masaüstü Otomasyonu & Telegram Botu

macOS/Linux/Windows işletim sistemlerinde çalışan; **Google Gemini 2.0 / 1.5** yapay zeka modelleriyle ekran görüntüsü alıp analiz eden, dosya/klasör işlemlerini yürüten ve **Telegram Botu** üzerinden uzaktan kontrol edilebilen otonom masaüstü ajanı.

---

## 🌟 Temel Yetenekler
- **Ekran Görsel Zekası:** Anlık ekran görüntüsü alır, ekrandaki pencereleri, butonları ve hata mesajlarını Gemini Vision ile inceler.
- **Telegram Bot Entegrasyonu (`bot.py`):** Dışarıdayken Telegram üzerinden bilgisayarınıza komut gönderebilir, durum sorgulayabilir ve ekran görüntüsü talep edebilirsiniz.
- **Geniş Araç Seti (`tools.py`):** Kullanıcı klasörleri (İndirilenler, Masaüstü, Belgeler vb.) üzerinde akıllı dosya arama, sistem kaynakları izleme ve shell komutu yürütme.
- **Web Yönetim Konsolu (`web_app.py`):** Tarayıcı üzerinden çalışan canlı kontrol ve log izleme paneli.

---

## 🛠️ Yapılandırma & Başlatma

1. **Gerekli paketleri kurun:**
   ```bash
   pip install -r requirements.txt
   ```

2. **`config.json` Ayarları:**
   ```json
   {
     "GEMINI_API_KEY": "AIzaSy...",
     "TELEGRAM_BOT_TOKEN": "123456:ABC...",
     "TELEGRAM_AUTHORIZED_CHAT_IDS": [12345678],
     "TELEGRAM_BOT_ENABLED": true
   }
   ```

3. **Çalıştırma:**
   - Web arayüzü için: `python3 web_app.py`
   - Telegram botu için: `python3 bot.py`
