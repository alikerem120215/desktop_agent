import sys
import os
import threading
import time
import webbrowser

# Mevcut dizini sys.path'e ekleyelim ki modül importları problemsiz çalışsın
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from config import ConfigManager
from agent import GeminiAgent
from bot import TelegramBotRunner
from web_app import app, init_web_app, manage_telegram_bot, add_log

def open_browser():
    """Flask sunucusu ayaklandıktan hemen sonra tarayıcıyı otomatik açan thread fonksiyonu."""
    time.sleep(1.2) # Sunucunun dinlemeye başlaması için ufak bir bekleme payı
    url = "http://127.0.0.1:5050"
    add_log(f"[Sistem] Varsayılan tarayıcı otomatik açılıyor: {url}")
    webbrowser.open(url)

def main():
    """
    Uygulama Giriş Noktası (Entry Point).
    Yerel Flask sunucusunu ve arka plan Telegram iş parçacıklarını orkestre eder.
    """
    add_log("=== Aquarius Ajanı Web Uygulaması Başlatılıyor ===")
    
    # 1. Yerel Yapılandırma Dosyasını Yükle
    config_manager = ConfigManager()
    
    # 2. Gemini Yapay Zeka Ajanını Hazırla
    agent = GeminiAgent(config_manager)
    
    # 3. Flask Web Sunucusu İçindeki Servisleri İlklendir
    init_web_app(config_manager, agent, TelegramBotRunner)
    
    # 4. Yapılandırma ayarına göre Telegram Botunu arka planda başlat
    manage_telegram_bot()
    
    # 5. Tarayıcıyı Ayrı Thread'de Aç
    threading.Thread(target=open_browser, daemon=True).start()
    
    # 6. Flask Web Sunucusunu Başlat (Geliştirici modu kapalı ki thread'ler çiftlemesin)
    add_log("[Sistem] Yerel Flask sunucusu 127.0.0.1:5050 portunda başlatılıyor...")
    try:
        app.run(host="127.0.0.1", port=5050, debug=False)
    except KeyboardInterrupt:
        add_log("[Sistem] Uygulama sonlandırılıyor...")
    finally:
        # Kapatılırken bot iş parçacığını da durduralım
        from web_app import bot_runner_instance
        if bot_runner_instance:
            bot_runner_instance.stop()

if __name__ == "__main__":
    main()
