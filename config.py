import os
import json

class ConfigManager:
    """
    Yerel yapılandırma verilerini (API Key, Telegram Token vb.) yöneten sınıf.
    Verileri 'config.json' dosyasında güvenli bir şekilde saklar ve okur.
    """
    def __init__(self, filename="config.json"):
        # Çalıştırılan dosyanın dizininde config.json konumlandırılır
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.filepath = os.path.join(self.base_dir, filename)
        self.config = self._load_defaults()
        self.load()

    def _load_defaults(self):
        """Varsayılan boş yapılandırma şablonu."""
        return {
            "GEMINI_API_KEY": "",
            "TELEGRAM_BOT_TOKEN": "",
            "TELEGRAM_AUTHORIZED_CHAT_IDS": [],
            "TELEGRAM_BOT_ENABLED": False
        }

    def load(self):
        """Yapılandırma dosyasını yükler, dosya yoksa varsayılanları oluşturur."""
        if not os.path.exists(self.filepath):
            self.save()
            return
        
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Yeni eklenen anahtarlar varsa varsayılanlardan tamamlayalım
                for key, val in self._load_defaults().items():
                    if key not in data:
                        data[key] = val
                self.config = data
        except (json.JSONDecodeError, IOError) as e:
            print(f"Yapılandırma dosyası okunurken hata oluştu: {e}. Varsayılanlar yüklendi.")
            self.config = self._load_defaults()

    def save(self):
        """Mevcut yapılandırmayı yerel diskteki json dosyasına yazar."""
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            return True
        except IOError as e:
            print(f"Yapılandırma dosyası kaydedilirken hata oluştu: {e}")
            return False

    # Gemini API Key Getter/Setter
    @property
    def gemini_api_key(self) -> str:
        return self.config.get("GEMINI_API_KEY", "")

    @gemini_api_key.setter
    def gemini_api_key(self, value: str):
        self.config["GEMINI_API_KEY"] = value.strip()

    # Telegram Bot Token Getter/Setter
    @property
    def telegram_bot_token(self) -> str:
        return self.config.get("TELEGRAM_BOT_TOKEN", "")

    @telegram_bot_token.setter
    def telegram_bot_token(self, value: str):
        self.config["TELEGRAM_BOT_TOKEN"] = value.strip()

    # Yetkili Telegram Sohbet Kimlikleri (Chat IDs)
    @property
    def authorized_chat_ids(self) -> list:
        return self.config.get("TELEGRAM_AUTHORIZED_CHAT_IDS", [])

    @authorized_chat_ids.setter
    def authorized_chat_ids(self, value: list):
        # Tüm ID'leri integer veya düzgün string olarak saklayalım
        cleaned = []
        for item in value:
            try:
                cleaned.append(int(item))
            except (ValueError, TypeError):
                if item:
                    cleaned.append(str(item).strip())
        self.config["TELEGRAM_AUTHORIZED_CHAT_IDS"] = cleaned

    # Telegram Botunun aktif olup olmadığı
    @property
    def telegram_bot_enabled(self) -> bool:
        return self.config.get("TELEGRAM_BOT_ENABLED", False)

    @telegram_bot_enabled.setter
    def telegram_bot_enabled(self, value: bool):
        self.config["TELEGRAM_BOT_ENABLED"] = bool(value)

    def is_configured(self) -> bool:
        """Kritik ayarların yapılıp yapılmadığını kontrol eder (Gemini API Key)."""
        return len(self.gemini_api_key) > 10
