from flask import Flask, render_template, jsonify, request
import os
import time
import collections
import psutil
import threading
import datetime
from config import ConfigManager
from agent import GeminiAgent
import tools

# Flask uygulamasını başlatıyoruz
# Arayüz dosyalarını 'templates' ve 'static' klasörlerinden servis edecek
base_dir = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, 
            template_folder=os.path.join(base_dir, "templates"),
            static_folder=os.path.join(base_dir, "static"))

# Global Değişkenler ve Paylaşılan Referanslar
agent = None
config_manager = None
bot_runner_class = None
bot_runner_instance = None

# Thread-safe log kuyruğu (Web arayüzünde canlı göstermek için)
MAX_LOGS = 150
app_logs = collections.deque(maxlen=MAX_LOGS)
logs_lock = threading.Lock()

def add_log(message: str):
    """Sistem çapında log ekleyen thread-safe yardımcı fonksiyon."""
    timestamp = datetime.datetime.now().strftime("[%H:%M:%S]")
    log_line = f"{timestamp} {message}"
    print(log_line)
    with logs_lock:
        app_logs.append(log_line)

def init_web_app(cfg: ConfigManager, agnt: GeminiAgent, runner_class):
    """
    Ana script (main.py) tarafından çağrılarak, Flask içindeki 
    servis referanslarını ilklendirir.
    """
    global config_manager, agent, bot_runner_class
    config_manager = cfg
    agent = agnt
    bot_runner_class = runner_class
    
    add_log("Flask Web Arayüzü servisleri ilklendirildi.")


# =========================================================================
# WEB URL ROTALARI (ROUTES)
# =========================================================================

@app.route('/')
def index():
    """Ana paneli (dashboard) yükler."""
    return render_template('index.html')


@app.route('/api/chat', methods=['POST'])
def api_chat():
    """Yapay Zeka asistanı ile konuşmayı sağlayan POST API."""
    if not agent:
        return jsonify({"response": "Hata: Gemini Yapay Zeka Ajanı hazır değil."}), 500
        
    data = request.json or {}
    user_message = data.get("message", "").strip()
    
    if not user_message:
        return jsonify({"response": "Lütfen geçerli bir mesaj yazın."}), 400
        
    add_log(f"[Web Chat] Kullanıcı: '{user_message}'")
    
    # Gemini Ajanına mesajı gönderiyoruz (web arayüzü sohbeti için 'web_gui' session_id kullanıyoruz)
    try:
        response_text = agent.send_message(user_message, session_id="web_gui")
        return jsonify({"response": response_text})
    except Exception as e:
        err_msg = f"Asistan mesaj üretirken hata oluştu: {e}"
        add_log(f"[Web Chat] {err_msg}")
        return jsonify({"response": err_msg}), 500


@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    """Yapılandırma ayarlarını yükleyen veya güncelleyen API."""
    global bot_runner_instance
    
    if not config_manager:
        return jsonify({"error": "Config Manager ilklendirilmedi."}), 500

    if request.method == 'GET':
        # Hassas şifreleri maskelemeden, yerel (local-only) çalıştığımız için 
        # düzenlemeyi kolaylaştırmak amacıyla doğrudan gönderelim.
        return jsonify({
            "gemini_api_key": config_manager.gemini_api_key,
            "telegram_bot_token": config_manager.telegram_bot_token,
            "telegram_authorized_chat_ids": config_manager.authorized_chat_ids,
            "telegram_bot_enabled": config_manager.telegram_bot_enabled
        })

    else:
        # POST: Ayarları kaydet
        data = request.json or {}
        key = data.get("gemini_api_key", "").strip()
        token = data.get("telegram_bot_token", "").strip()
        enabled = bool(data.get("telegram_bot_enabled", False))
        chat_ids_raw = data.get("telegram_authorized_chat_ids", [])
        
        # ID listesini temizleyelim
        cleaned_ids = []
        for cid in chat_ids_raw:
            if isinstance(cid, int):
                cleaned_ids.append(cid)
            elif str(cid).strip():
                try:
                    cleaned_ids.append(int(cid))
                except ValueError:
                    cleaned_ids.append(str(cid).strip())

        # Config'e kaydet
        config_manager.gemini_api_key = key
        config_manager.telegram_bot_token = token
        config_manager.telegram_bot_enabled = enabled
        config_manager.authorized_chat_ids = cleaned_ids

        if config_manager.save():
            add_log("Yerel yapılandırma başarıyla güncellendi.")
            
            # Gemini Agent'ı yeni anahtarla yeniden başlat
            if agent:
                if agent.initialize_agent():
                    add_log("Gemini API Ajanı yeni anahtarla başarıyla başlatıldı.")
                else:
                    add_log("HATA: Gemini API Ajanı yeni anahtarla başlatılamadı.")

            # Telegram Botunu yeni ayarlara göre yönet
            manage_telegram_bot()
            
            return jsonify({"status": "success", "message": "Ayarlar başarıyla kaydedildi!"})
        else:
            add_log("HATA: Yapılandırma kaydedilemedi.")
            return jsonify({"status": "error", "message": "Dosya yazma hatası oluştu."}), 500


@app.route('/api/status', methods=['GET'])
def api_status():
    """Anlık CPU, RAM, Disk ve Pil durumunu döndüren API."""
    try:
        # CPU
        cpu = psutil.cpu_percent(interval=None)
        
        # RAM
        ram = psutil.virtual_memory()
        
        # Disk
        disk = psutil.disk_usage('/')
        
        # Pil
        battery = psutil.sensors_battery()
        battery_pct = 100
        battery_plugged = True
        if battery:
            battery_pct = battery.percent
            battery_plugged = battery.power_plugged

        # Gemini API ve Telegram bot çalışma durumları
        gemini_active = agent is not None and agent.model is not None
        telegram_active = bot_runner_instance is not None and bot_runner_instance.is_running

        return jsonify({
            "cpu": cpu,
            "ram": ram.percent,
            "ram_used": f"{ram.used / (1024**3):.1f} GB",
            "ram_total": f"{ram.total / (1024**3):.1f} GB",
            "disk": disk.percent,
            "battery": battery_pct,
            "battery_plugged": battery_plugged,
            "gemini_active": gemini_active,
            "telegram_active": telegram_active
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/logs', methods=['GET'])
def api_logs():
    """Sistem log akışını JSON olarak döndürür."""
    with logs_lock:
        return jsonify(list(app_logs))


@app.route('/api/screenshot', methods=['POST'])
def api_screenshot():
    """Web arayüzünden tetiklenen ekran görüntüsü alma API."""
    add_log("[Sistem] Ekran görüntüsü alınıyor...")
    try:
        result = tools.take_screenshot()
        add_log(f"[Sistem] {result}")
        return jsonify({"status": "success", "message": result})
    except Exception as e:
        err = f"Ekran görüntüsü hatası: {e}"
        add_log(f"[Sistem] {err}")
        return jsonify({"status": "error", "message": err}), 500


@app.route('/api/chat/clear', methods=['POST'])
def api_clear_chat():
    """Sohbet geçmişini sıfırlayan API."""
    if agent:
        agent.reset_session("web_gui")
        add_log("[Sistem] Web sohbet geçmişi sıfırlandı.")
        return jsonify({"status": "success", "message": "Geçmiş sıfırlandı."})
    return jsonify({"status": "error"}), 500


# =========================================================================
# TELEGRAM BOT DİŞLİ YÖNETİMİ
# =========================================================================

def manage_telegram_bot():
    """Telegram botunu config ayarlarına göre başlatır veya durdurur."""
    global bot_runner_instance
    
    # Mevcut aktif botu durdur
    if bot_runner_instance:
        add_log("Mevcut Telegram botu durduruluyor...")
        bot_runner_instance.stop()
        bot_runner_instance = None

    if not config_manager or not bot_runner_class or not agent:
        return

    # Eğer bot aktif edilmişse başlat
    if config_manager.telegram_bot_enabled:
        add_log("Telegram botu başlatılıyor...")
        bot_runner_instance = bot_runner_class(
            config_manager,
            agent,
            on_log_callback=add_log
        )
        started = bot_runner_instance.start()
        if started:
            add_log("Telegram botu arka planda dinlemede.")
        else:
            add_log("HATA: Telegram botu başlatılamadı.")
    else:
        add_log("Telegram botu devre dışı bırakıldı.")
