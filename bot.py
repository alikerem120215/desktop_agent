import os
import re
import threading
import telebot
from config import ConfigManager
from agent import GeminiAgent

class TelegramBotRunner:
    """
    Telegram botunu arka planda (threading kullanarak) çalıştıran sınıf.
    GUI'yi dondurmamak için ana döngüden bağımsız çalışır.
    """
    def __init__(self, config_manager: ConfigManager, agent: GeminiAgent, on_log_callback=None):
        self.config_manager = config_manager
        self.agent = agent
        self.on_log_callback = on_log_callback  # GUI'ye log yazdırmak için callback fonksiyonu
        
        self.bot = None
        self.thread = None
        self.is_running = False

    def log(self, message: str):
        """Log kayıtlarını konsola ve eğer tanımlanmışsa GUI log ekranına yansıtır."""
        text = f"[Telegram Bot] {message}"
        print(text)
        if self.on_log_callback:
            self.on_log_callback(text)

    def start(self) -> bool:
        """Telegram botunu arka plan thread'inde başlatır."""
        if self.is_running:
            return True

        token = self.config_manager.telegram_bot_token
        enabled = self.config_manager.telegram_bot_enabled

        if not enabled:
            self.log("Bot devre dışı bırakılmış (Config üzerinden).")
            return False

        if not token or len(token) < 20:
            self.log("Hata: Telegram Bot Token bulunamadı veya geçersiz.")
            return False

        try:
            self.bot = telebot.TeleBot(token)
            self.is_running = True
            
            # Handler'ları tanımlayalım
            self._register_handlers()
            
            # Thread oluşturup başlatalım
            self.thread = threading.Thread(target=self._run_polling, daemon=True)
            self.thread.start()
            self.log("Bot arka planda başarıyla başlatıldı, mesajlar dinleniyor...")
            return True
        except Exception as e:
            self.log(f"Bot başlatılamadı: {e}")
            self.is_running = False
            return False

    def stop(self):
        """Poller'ı ve arka plan thread'ini güvenli bir şekilde sonlandırır."""
        if not self.is_running:
            return

        self.log("Bot durduruluyor...")
        self.is_running = False
        if self.bot:
            try:
                self.bot.stop_polling()
            except Exception:
                pass
        
        if self.thread and self.thread.is_alive():
            # Thread daemon olduğu için uygulama kapanınca zaten kapanır ama 
            # stop_polling ile polling loop'u hemen kırılır.
            self.thread.join(timeout=1.0)
            
        self.log("Bot durduruldu.")

    def _run_polling(self):
        """Arka planda çalışan polling döngüsü."""
        while self.is_running:
            try:
                # infinity_polling bot.stop_polling() çağrıldığında döngüden çıkar
                self.bot.infinity_polling(timeout=10, long_polling_timeout=5)
            except Exception as e:
                self.log(f"Polling sırasında hata oluştu, 5 sn sonra yeniden denenecek: {e}")
                # Hata durumunda hemen tekrar sarmamak için kısa bir bekleme
                import time
                time.sleep(5)

    def _is_authorized(self, chat_id: int) -> bool:
        """Kullanıcının yetkili olup olmadığını kontrol eder."""
        authorized_ids = self.config_manager.authorized_chat_ids
        # Eğer henüz hiçbir yetkili ID tanımlanmamışsa, güvenlik için kimse erişemez
        # ama ilk kullanıcının kendini ekleyebilmesi için ID'sini görmesini sağlayacağız
        return chat_id in authorized_ids

    def _register_handlers(self):
        """Telegram API olay dinleyicilerini (handlers) tanımlar."""
        
        @self.bot.message_handler(commands=['start', 'help'])
        def send_welcome(message):
            chat_id = message.chat.id
            self.log(f"Kullanıcı bağlantı kurdu. Chat ID: {chat_id}")
            
            if not self._is_authorized(chat_id):
                welcome_msg = (
                    f"🔒 **Erişim Reddedildi!**\n\n"
                    f"Bu bilgisayar uzaktan kontrole kapalıdır.\n"
                    f"Bu Telegram hesabına izin vermek istiyorsanız, bilgisayar üzerindeki Ayarlar menüsünden "
                    f"aşağıdaki Chat ID'yi yetkililer listesine eklemelisiniz:\n\n"
                    f"👉 **Senin Chat ID'n:** `{chat_id}`"
                )
                self.bot.reply_to(message, welcome_msg, parse_mode="Markdown")
                return

            welcome_msg = (
                "🤖 **Antigravity OS Ajanına Hoş Geldiniz!**\n\n"
                "Artık bilgisayarınızı uzaktan kontrol edebilirsiniz. Yapabileceklerinizden bazıları:\n"
                "- 📊 'Sistem durumunu rapor et'\n"
                "- 📸 'Ekran görüntüsü al' (Alınan ekran doğrudan buraya yüklenecektir)\n"
                "- 📂 'İndirilenler klasöründeki dosyaları listele'\n"
                "- 📝 'Masaüstüne rapor.txt yaz ve içeriğine test yaz'\n"
                "- ⛅ 'İstanbul hava durumunu söyle'\n"
                "- 🖥️ 'Terminalde ls -la komutunu çalıştır'\n\n"
                "Sadece doğal dilde ne yapmak istediğinizi yazın!"
            )
            self.bot.reply_to(message, welcome_msg, parse_mode="Markdown")

        @self.bot.message_handler(func=lambda message: True)
        def handle_message(message):
            chat_id = message.chat.id
            user_text = message.text
            
            if not self._is_authorized(chat_id):
                self.bot.reply_to(
                    message, 
                    f"❌ Bu hesaptan komut göndermeye yetkiniz yoktur.\nChat ID'niz: `{chat_id}`",
                    parse_mode="Markdown"
                )
                return

            self.log(f"Komut Alındı ({chat_id}): '{user_text}'")
            
            # Telegram için "Yazıyor..." animasyonu gönderelim
            try:
                self.bot.send_chat_action(chat_id, 'typing')
            except Exception:
                pass

            # Gemini Ajanına soruyu yönlendir (Telegram için ayrı bir chat session kullanıyoruz)
            session_id = f"telegram_{chat_id}"
            response_text = self.agent.send_message(user_text, session_id=session_id)
            
            # Gelen yanıtta ekran görüntüsü yolu var mı kontrol et (Örn: "Dosya Yolu: /path/to/screenshot.png")
            # re.IGNORECASE ile arama yapalım
            screenshot_match = re.search(r"Dosya Yolu:\s*([^\n]+)", response_text, re.IGNORECASE)
            
            # Yanıtı kullanıcıya gönder
            self.bot.reply_to(message, response_text)
            
            if screenshot_match:
                filepath = screenshot_match.group(1).strip()
                # Markdown veya tırnak işaretlerini temizleyelim
                filepath = filepath.strip("`'\"* ")
                
                if os.path.exists(filepath):
                    self.log(f"Ekran görüntüsü algılandı, Telegram'a yükleniyor: {filepath}")
                    try:
                        self.bot.send_chat_action(chat_id, 'upload_photo')
                        with open(filepath, 'rb') as photo:
                            self.bot.send_photo(chat_id, photo, caption="📸 Alınan Ekran Görüntüsü")
                        self.log("Ekran görüntüsü başarıyla yüklendi.")
                    except Exception as upload_err:
                        self.log(f"Ekran görüntüsü yüklenirken hata: {upload_err}")
                        self.bot.send_message(chat_id, f"⚠️ Ekran görüntüsü dosyası yüklenemedi: {upload_err}")
                else:
                    self.log(f"Ekran görüntüsü dosyası bulunamadı: {filepath}")
