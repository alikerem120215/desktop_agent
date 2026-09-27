import google.generativeai as genai
from config import ConfigManager
import tools  # Araçları import ediyoruz

class GeminiAgent:
    """
    Gemini API entegrasyonunu ve Function Calling (Araç Kullanımı) mekanizmasını yöneten sınıf.
    Hem GUI hem de Telegram Bot bu sınıf üzerinden konuşur.
    """
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.model_name = "gemini-2.5-flash"  # Hızlı ve yeni nesil gemini-2.5-flash modeli
        self.model = None
        self.sessions = {}  # Farklı arayüzler (gui, telegram vb.) için ayrı sohbet oturumları tutar
        self.initialize_agent()

    def initialize_agent(self) -> bool:
        """Gemini API'yi yerel yapılandırma anahtarı ile başlatır."""
        api_key = self.config_manager.gemini_api_key
        if not api_key or len(api_key) < 10:
            print("Hata: Geçerli bir Gemini API Key yapılandırılmamış.")
            self.model = None
            return False

        try:
            genai.configure(api_key=api_key)
            
            # Gemini Ajanının işletim sistemine hükmederken uyması gereken kurallar
            system_instruction = (
                "Sen 'Aquarius' adında gelişmiş, akıllı bir Masaüstü Asistanı ve İşletim Sistemi Ajanısın. "
                "Kullanıcıya hem grafiksel bir arayüzden (GUI) hem de Telegram üzerinden yardımcı oluyorsun.\n\n"
                "SAHİP OLDUĞUN YETENEKLER VE ARAÇLAR:\n"
                "Sistem komutları çalıştırabilir, dosya oluşturabilir, okuyabilir, silebilir, dizin listeleyebilir, "
                "anlık ekran görüntüsü alabilir, sistem durumunu (CPU, RAM, Disk vb.) raporlayabilir ve anlık hava durumunu söyleyebilirsin.\n\n"
                "KURALLAR VE DAVRANIŞ BİÇİMİ:\n"
                "1. Dosya yolları konusunda esneksin. Kullanıcı 'indirilenler' veya 'downloads' dediğinde, "
                "sistem araçlarını kullanarak ~/Downloads veya ~/İndirilenler klasörünü bulmalısın.\n"
                "2. Eğer kullanıcı sadece dosya adı verdiyse (Örn: 'rapor.pdf') ve bu dosyanın tam yolunu belirtmediyse, "
                "arama ve okuma araçlarını kullanarak bu dosyayı otomatik olarak bulmaya çalış. Bulamazsan, körü körüne hata vermek yerine "
                "nerelerde aradığını söyleyip kullanıcıdan tam konumunu rica et.\n"
                "3. Terminal komutlarını çalıştırırken dikkatli ve güvenli ol. Zararlı olabilecek komutlarda uyarı yapabilir veya onay alabilirsin.\n"
                "4. Her zaman kibar, profesyonel ve çözüm odaklı konuş. Türkçe dilinde yanıt ver.\n"
                "5. Ekran görüntüsü alman istendiğinde 'take_screenshot' aracını çağır. Aldığın ekran görüntüsünün tam dosya yolunu yanıtta belirt."
            )

            # Gemini modeline Python araçlarımızı tool olarak tanımlıyoruz
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=system_instruction,
                tools=[
                    tools.execute_system_command,
                    tools.file_list_directory,
                    tools.file_read_content,
                    tools.file_write_content,
                    tools.file_delete,
                    tools.take_screenshot,
                    tools.get_system_status,
                    tools.get_weather
                ]
            )
            
            # Başarılı başlatma sonrasında oturumları sıfırla
            self.sessions = {}
            print(f"Gemini Ajanı başarıyla başlatıldı. Model: {self.model_name}")
            return True
        except Exception as e:
            print(f"Gemini Ajanı başlatılırken hata oluştu: {e}")
            self.model = None
            return False

    def get_chat_session(self, session_id: str):
        """Belirtilen session_id için aktif bir sohbet oturumu döndürür veya yeni bir tane oluşturur."""
        if not self.model:
            # API Key henüz girilmemiş veya geçersizse
            raise ValueError("Gemini Ajanı henüz başlatılmamış. Lütfen Ayarlar'dan API Key girin.")

        if session_id not in self.sessions:
            # enable_automatic_function_calling=True ile Gemini, tool call taleplerini 
            # doğrudan python tarafındaki fonksiyonları çalıştırarak otomatik çözer.
            self.sessions[session_id] = self.model.start_chat(enable_automatic_function_calling=True)
            print(f"Yeni sohbet oturumu oluşturuldu: {session_id}")
            
        return self.sessions[session_id]

    def send_message(self, message: str, session_id: str = "gui") -> str:
        """
        Belirli bir oturum üzerinden Gemini'a mesaj gönderir ve yanıtını döner.
        Function calling adımlarını otomatik tamamlar.
        """
        try:
            chat = self.get_chat_session(session_id)
            response = chat.send_message(message)
            return response.text
        except ValueError as ve:
            return str(ve)
        except Exception as e:
            return f"Mesaj gönderilirken asistan tarafında bir hata oluştu: {str(e)}"

    def reset_session(self, session_id: str = "gui"):
        """Belirtilen oturumun sohbet geçmişini temizler."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            print(f"Sohbet oturumu sıfırlandı: {session_id}")
