import os
import sys
import glob
import subprocess
import psutil
from PIL import ImageGrab
import datetime
import urllib.request
import json

# Standart macOS/Linux/Windows kullanıcı klasörleri eşleşmeleri (Türkçe ve İngilizce)
FOLDER_MAPPING = {
    "indirilenler": ["Downloads", "Downloads", "İndirilenler"],
    "downloads": ["Downloads", "Downloads", "İndirilenler"],
    "masaüstü": ["Desktop", "Desktop", "Masaüstü"],
    "desktop": ["Desktop", "Desktop", "Masaüstü"],
    "belgeler": ["Documents", "Documents", "Belgeler"],
    "documents": ["Documents", "Documents", "Belgeler"],
    "resimler": ["Pictures", "Pictures", "Resimler"],
    "pictures": ["Pictures", "Pictures", "Resimler"],
    "müzik": ["Music", "Music", "Müzik"],
    "music": ["Music", "Music", "Müzik"],
    "videolar": ["Movies", "Movies", "Videolar", "Videos"],
    "videos": ["Movies", "Movies", "Videolar", "Videos"],
    "movies": ["Movies", "Movies", "Videolar", "Videos"]
}

def resolve_path(path_str: str) -> str:
    """
    Kullanıcı tarafından verilen dizin veya dosya yolunu akıllıca çözümler.
    Doğal dil esnekliği sağlar (Örn: 'indirilenler' kelimesini ~/Downloads veya ~/İndirilenler olarak eşler).
    """
    if not path_str:
        return os.path.expanduser("~")

    # Yolun başındaki tilde (~) işaretini kullanıcı ana dizinine çevir
    path_str = os.path.expanduser(path_str)
    
    parts = path_str.replace("\\", "/").split("/")
    home_dir = os.path.expanduser("~")

    # Eğer verilen yol doğrudan bir sistem klasörü veya onun altındaysa (Örn: "indirilenler/rapor.txt" gibi)
    first_part = parts[0].lower().strip()
    if first_part in FOLDER_MAPPING:
        possible_dirs = FOLDER_MAPPING[first_part]
        resolved_first_part = None
        
        # Fiziksel olarak mevcut olan ilk klasörü bulmaya çalışalım
        for p_dir in possible_dirs:
            test_path = os.path.join(home_dir, p_dir)
            if os.path.exists(test_path):
                resolved_first_part = test_path
                break
                
        # Eğer fiziksel olarak bulunamadıysa ilk varsayılanı kullanalım
        if not resolved_first_part:
            resolved_first_part = os.path.join(home_dir, possible_dirs[0])
            
        # Alt yolları ekleyelim
        if len(parts) > 1:
            return os.path.join(resolved_first_part, *parts[1:])
        return resolved_first_part

    # Zaten tam yol verilmişse veya tilde çözüldüyse doğrudan döndür
    if os.path.isabs(path_str):
        return path_str

    # Göreceli yolsa, çalışma dizinine göre çözümle
    return os.path.abspath(path_str)


def search_file_in_common_dirs(filename: str) -> str:
    """
    Kullanıcı sadece dosya adı verdiğinde (Örn: 'aptal_sey.png'),
    bu dosyayı Masaüstü, İndirilenler, Belgeler gibi sık kullanılan klasörlerde arar.
    Bulursa tam yolunu döner, bulamazsa hata/uyarı mesajı içeren bir hata fırlatır.
    """
    home_dir = os.path.expanduser("~")
    search_dirs = ["Desktop", "Downloads", "Documents", "Pictures", "Masaüstü", "İndirilenler", "Belgeler", "Resimler"]
    
    # Eşsiz arama yolları listesi oluşturalım
    unique_search_paths = []
    for d in search_dirs:
        full_path = os.path.join(home_dir, d)
        if os.path.exists(full_path) and full_path not in unique_search_paths:
            unique_search_paths.append(full_path)

    found_files = []
    
    # Dizinleri tarayalım (Case-insensitive arama için glob veya walk kullanalım)
    for base_dir in unique_search_paths:
        try:
            for root, dirs, files in os.walk(base_dir):
                # Sadece ilk seviyede (veya çok derine inmeden) arayalım ki performans düşmesin
                for f in files:
                    if f.lower() == filename.lower() or filename.lower() in f.lower():
                        found_files.append(os.path.join(root, f))
                # Derin aramayı engellemek için sadece en üst seviye alt klasörlere bakalım
                break
        except Exception:
            continue

    if len(found_files) == 1:
        return found_files[0]
    elif len(found_files) > 1:
        # Birden fazla eşleşme bulunduysa listeyi raporlayalım
        paths_str = "\n".join([f"- {p}" for p in found_files])
        raise FileNotFoundError(
            f"'{filename}' adında birden fazla dosya bulundu, lütfen tam konumunu belirtir misiniz?\n{paths_str}"
        )
    else:
        # Hiç bulunamadıysa kullanıcıya aradığımız yerleri söyleyelim
        dirs_str = ", ".join([os.path.basename(d) for d in unique_search_paths])
        raise FileNotFoundError(
            f"'{filename}' dosyasını şu klasörlerde aradım ama bulamadım: ({dirs_str}).\n"
            "Dosyanın tam konumunu veya tam adını söyleyebilir misiniz?"
        )


# --- 1. Sistem Terminal Komutları ---
def execute_system_command(command: str) -> str:
    """
    Güvenli bir şekilde terminal/cmd komutları çalıştırır ve çıktısını (stdout/stderr) döndürür.
    Süre aşımı (timeout) 30 saniyedir.
    """
    try:
        # shell=True kullanarak macOS'te standart komutları çalıştırıyoruz
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        output = ""
        if result.stdout:
            output += f"--- STDOUT ---\n{result.stdout}\n"
        if result.stderr:
            output += f"--- STDERR ---\n{result.stderr}\n"
        
        if not output:
            output = "Komut çalıştırıldı fakat herhangi bir çıktı üretmedi."
            
        return f"Çalıştırılan Komut: {command}\nKod: {result.returncode}\n{output}"
    except subprocess.TimeoutExpired:
        return f"Hata: Komut 30 saniyelik zaman aşımı süresini aştı ve durduruldu: {command}"
    except Exception as e:
        return f"Komut çalıştırılırken bir hata oluştu: {str(e)}"


# --- 2. Dosya Yönetim Fonksiyonları ---
def file_list_directory(directory_path: str = ".") -> str:
    """
    Verilen dizindeki dosya ve klasörleri listeler.
    """
    try:
        resolved = resolve_path(directory_path)
        if not os.path.exists(resolved):
            return f"Hata: '{directory_path}' dizini mevcut değil. (Çözümlenen yol: {resolved})"
        
        if not os.path.isdir(resolved):
            return f"Hata: '{directory_path}' bir klasör değil, dosya."

        items = os.listdir(resolved)
        if not items:
            return f"'{directory_path}' klasörü boş."

        # Klasörler ve dosyaları ayıralım
        folders = []
        files = []
        for item in items:
            item_path = os.path.join(resolved, item)
            if os.path.isdir(item_path):
                folders.append(f"[KLASÖR] {item}/")
            else:
                size = os.path.getsize(item_path)
                # KB veya MB cinsinden boyut gösterelim
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size/1024:.1f} KB"
                else:
                    size_str = f"{size/(1024*1024):.1f} MB"
                files.append(f"[DOSYA]  {item} ({size_str})")

        folders.sort()
        files.sort()
        
        result = f"Dizin İçeriği ({directory_path}):\n"
        result += "\n".join(folders + files)
        return result
    except Exception as e:
        return f"Dizin listelenirken hata oluştu: {str(e)}"


def file_read_content(file_path: str) -> str:
    """
    Verilen dosyanın içeriğini okur ve metin olarak geri döndürür.
    Eğer sadece dosya adı verilmişse akıllı arama yapar.
    """
    try:
        # Eğer dosya yolu değil de sadece dosya adı ise arama yapalım
        if not os.path.isabs(file_path) and "/" not in file_path and "\\" not in file_path:
            try:
                resolved = search_file_in_common_dirs(file_path)
            except FileNotFoundError as fnf:
                return str(fnf)
        else:
            resolved = resolve_path(file_path)

        if not os.path.exists(resolved):
            return f"Hata: '{file_path}' dosyası bulunamadı. (Çözümlenen yol: {resolved})"

        if os.path.isdir(resolved):
            return f"Hata: '{file_path}' bir dosya değil, klasör. Klasör içeriğini görmek için 'file_list_directory' kullanın."

        # Dosya boyut kontrolü (Çok büyük dosyaları okuyup Gemini bağlamını doldurmayalım)
        size = os.path.getsize(resolved)
        if size > 1024 * 1024: # 1 MB limit
            return f"Hata: Dosya boyutu ({size/(1024*1024):.2f} MB) çok büyük. Okuma limiti 1 MB'dır."

        with open(resolved, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        
        return f"--- DOSYA: {resolved} ---\n{content}"
    except Exception as e:
        return f"Dosya okunurken hata oluştu: {str(e)}"


def file_write_content(file_path: str, content: str) -> str:
    """
    Belirtilen dosyayı oluşturur ve içine metin yazar. Klasörler yoksa otomatik oluşturur.
    """
    try:
        resolved = resolve_path(file_path)
        
        # Üst klasörleri otomatik oluştur
        parent_dir = os.path.dirname(resolved)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
            
        with open(resolved, "w", encoding="utf-8") as f:
            f.write(content)
            
        return f"Dosya başarıyla yazıldı/güncellendi: {resolved}"
    except Exception as e:
        return f"Dosya yazılırken hata oluştu: {str(e)}"


def file_delete(path: str) -> str:
    """
    Verilen dosya veya klasörü siler.
    Klasör doluysa veya sadece dosya adı verilip bulunamazsa akıllı çözümler.
    """
    try:
        # Sadece dosya adı verilmişse
        if not os.path.isabs(path) and "/" not in path and "\\" not in path:
            try:
                resolved = search_file_in_common_dirs(path)
            except FileNotFoundError as fnf:
                return str(fnf)
        else:
            resolved = resolve_path(path)

        if not os.path.exists(resolved):
            return f"Hata: '{path}' silinmek istendi ancak bulunamadı. (Çözümlenen yol: {resolved})"

        if os.path.isdir(resolved):
            # Dizin silme işlemi
            try:
                os.rmdir(resolved)
                return f"Klasör başarıyla silindi: {resolved}"
            except OSError:
                # Klasör doluysa shutil veya terminal üzerinden silinebilir ancak güvenlik için
                # şimdilik Gemini'ın onayını veya açıkça silmesini isteyebiliriz.
                return f"Hata: Klasör içi boş değil, silinemedi: {resolved}. İçindekileri silip tekrar deneyin veya terminal komutu kullanın."
        else:
            # Dosya silme işlemi
            os.remove(resolved)
            return f"Dosya başarıyla silindi: {resolved}"
    except Exception as e:
        return f"Silme işlemi sırasında hata oluştu: {str(e)}"


# --- 3. Ekran Görüntüsü ---
def take_screenshot() -> str:
    """
    Anlık ekran görüntüsü alır, local projedeki 'screenshots' klasörüne kaydeder.
    Geriye kaydedilen dosyanın yerel absolute yolunu döner.
    """
    try:
        # Proje altında screenshots klasörünü belirleyelim
        base_dir = os.path.dirname(os.path.abspath(__file__))
        screenshot_dir = os.path.join(base_dir, "screenshots")
        os.makedirs(screenshot_dir, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        filepath = os.path.join(screenshot_dir, filename)

        # PIL ImageGrab kullanarak ekran görüntüsünü alalım (Cross-platform & macOS dostu)
        screenshot = ImageGrab.grab()
        screenshot.save(filepath, "PNG")

        return f"SUCCESS: Ekran görüntüsü başarıyla alındı ve kaydedildi.\nDosya Yolu: {filepath}"
    except Exception as e:
        return f"ERROR: Ekran görüntüsü alınamadı. Hata: {str(e)}"


# --- 4. Sistem Durumu (CPU / RAM) ---
def get_system_status() -> str:
    """
    psutil kütüphanesini kullanarak CPU, RAM, disk kullanımı ve pil durumunu raporlar.
    """
    try:
        # CPU
        cpu_percent = psutil.cpu_percent(interval=0.5)
        cpu_count = psutil.cpu_count(logical=True)
        
        # RAM
        ram = psutil.virtual_memory()
        ram_total = ram.total / (1024**3)
        ram_used = ram.used / (1024**3)
        ram_percent = ram.percent
        
        # Disk
        disk = psutil.disk_usage('/')
        disk_total = disk.total / (1024**3)
        disk_used = disk.used / (1024**3)
        disk_percent = disk.percent
        
        # Pil (Pil yoksa None dönecektir)
        battery = psutil.sensors_battery()
        battery_status = "Bilinmiyor (Masaüstü/Şebeke)"
        if battery:
            plugged = "Prizde" if battery.power_plugged else "Pil Gücünde"
            battery_status = f"%{battery.percent} ({plugged}), Kalan Süre: {datetime.timedelta(seconds=battery.secsleft) if battery.secsleft != -1 else 'Hesaplanıyor'}"

        status_report = (
            f"=== SİSTEM DURUM RAPORU ===\n"
            f"💻 CPU Kullanımı: %{cpu_percent} (Çekirdek Sayısı: {cpu_count})\n"
            f"🧠 Bellek (RAM): %{ram_percent} (Kullanılan: {ram_used:.1f} GB / Toplam: {ram_total:.1f} GB)\n"
            f"💽 Disk Kullanımı (/): %{disk_percent} (Kullanılan: {disk_used:.1f} GB / Toplam: {disk_total:.1f} GB)\n"
            f"🔋 Pil Durumu: {battery_status}"
        )
        return status_report
    except Exception as e:
        return f"Sistem durumu alınırken hata oluştu: {str(e)}"


# --- 5. Hava Durumu & Genel Bilgi ---
def get_weather(city: str) -> str:
    """
    Belirtilen şehir için wttr.in servisini kullanarak güncel hava durumunu çeker.
    Eğer hata oluşursa open-meteo API'sine düşer.
    """
    try:
        # wttr.in servisi için Türkçe dil desteği ve sadeleştirilmiş format (?format=3)
        city_clean = city.strip().replace(" ", "+")
        # wttr.in/<city>?lang=tr&format=3 (Örn: "Istanbul: 🌦️  +18°C ↙️ 19km/h")
        url = f"https://wttr.in/{city_clean}?lang=tr&format=3"
        
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
        )
        
        with urllib.request.urlopen(req, timeout=5) as response:
            weather_data = response.read().decode('utf-8').strip()
            if "Unknown location" in weather_data or "404" in weather_data:
                raise ValueError("Bilinmeyen konum")
            return f"🌦️ {city.capitalize()} Hava Durumu: {weather_data}"
            
    except Exception as e:
        # wttr.in başarısız olursa Open-Meteo ile basit bir geo-koordinat fallback yapabiliriz
        # Ancak Gemini kendi bilgisiyle veya internet aramasıyla da cevap verebileceğinden,
        # en azından basit bir hata raporu verip asistanın kendi kapasitesini kullanmasını sağlayabiliriz.
        return f"Hava durumu servisine (wttr.in) erişilemedi. Şehir: {city}. Hata: {str(e)}. " \
               f"Lütfen kendi bilgi birikiminiz veya internet araması yetenekleriniz ile tahmin yapın."
