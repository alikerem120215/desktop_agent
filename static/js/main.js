// =========================================================================
// GLOBAL DEĞİŞKENLER VE AYARLAR
// =========================================================================
const SVG_CIRCUMFERENCE = 201.06; // 2 * PI * r (r=32 için: 201.06)

// Sayfa yüklendiğinde işlemleri başlatıyoruz
document.addEventListener('DOMContentLoaded', () => {
    // Arayüz Elementleri
    const chatTimeline = document.getElementById('chat-timeline');
    const chatInput = document.getElementById('chat-input');
    const btnSendMessage = document.getElementById('btn-send-message');
    const typingIndicator = document.getElementById('typing-indicator');
    
    const btnSettings = document.getElementById('btn-settings');
    const btnCloseSettings = document.getElementById('btn-close-settings');
    const settingsDrawer = document.getElementById('settings-drawer');
    const settingsOverlay = document.getElementById('settings-overlay');
    const btnSaveConfig = document.getElementById('btn-save-config');
    const configForm = document.getElementById('config-form');
    const telegramEnabledCb = document.getElementById('telegram_bot_enabled');
    const telegramConfigFields = document.getElementById('telegram-config-fields');
    
    const logsDrawer = document.getElementById('logs-drawer');
    const btnExpandLogs = document.getElementById('btn-expand-logs');
    const btnToggleLogs = document.getElementById('btn-toggle-logs');
    const logOutput = document.getElementById('log-output');
    const btnClearLogs = document.getElementById('btn-clear-logs');
    const logCountSpan = document.getElementById('log-count');
    
    const btnScreenshot = document.getElementById('btn-screenshot');
    const btnQuickStatus = document.getElementById('btn-quick-status');
    const btnClearChat = document.getElementById('btn-clear-chat');

    let currentLogLines = [];

    // =========================================================================
    // 1. AYARLAR ÇEKMECESİ VE ŞİFRE GÖSTERİCİ
    // =========================================================================
    
    // Ayarlar Çekmecesini Aç
    btnSettings.addEventListener('click', () => {
        loadConfigFromServer();
        settingsDrawer.classList.remove('hidden');
        settingsOverlay.classList.remove('hidden');
    });

    // Ayarlar Çekmecesini Kapat
    const closeSettings = () => {
        settingsDrawer.classList.add('hidden');
        settingsOverlay.classList.add('hidden');
    };
    btnCloseSettings.addEventListener('click', closeSettings);
    settingsOverlay.addEventListener('click', closeSettings);

    // Telegram Alt Ayarlar Alanını Göster/Gizle
    telegramEnabledCb.addEventListener('change', (e) => {
        if (e.target.checked) {
            telegramConfigFields.classList.add('show');
        } else {
            telegramConfigFields.classList.remove('show');
        }
    });

    // Şifre Göster/Gizle Butonları
    document.querySelectorAll('.btn-toggle-pwd').forEach(btn => {
        btn.addEventListener('click', () => {
            const targetId = btn.getAttribute('data-target');
            const targetInput = document.getElementById(targetId);
            const icon = btn.querySelector('i');
            
            if (targetInput.type === 'password') {
                targetInput.type = 'text';
                icon.className = 'fa-solid fa-eye-slash';
            } else {
                targetInput.type = 'password';
                icon.className = 'fa-solid fa-eye';
            }
        });
    });

    // API'den Mevcut Ayarları Çek ve Alanlara Doldur
    const loadConfigFromServer = async () => {
        try {
            const response = await fetch('/api/config');
            if (!response.ok) throw new Error("Ayar yükleme başarısız.");
            const data = await response.json();
            
            document.getElementById('gemini_api_key').value = data.gemini_api_key || '';
            telegramEnabledCb.checked = data.telegram_bot_enabled || false;
            document.getElementById('telegram_bot_token').value = data.telegram_bot_token || '';
            
            // Authorized Chat IDs (Diziyi virgülle ayrılmış string yapıyoruz)
            const chatIds = data.telegram_authorized_chat_ids || [];
            document.getElementById('telegram_authorized_chat_ids').value = chatIds.join(', ');
            
            // Telegram görünürlük tetiklemesi
            if (telegramEnabledCb.checked) {
                telegramConfigFields.classList.add('show');
            } else {
                telegramConfigFields.classList.remove('show');
            }
        } catch (error) {
            console.error("Ayar yükleme hatası:", error);
            showToast("⚠️ Yapılandırma ayarları sunucudan alınamadı.");
        }
    };

    // Sunucuya Ayarları Kaydet
    btnSaveConfig.addEventListener('click', async () => {
        const apiKey = document.getElementById('gemini_api_key').value.trim();
        const botEnabled = telegramEnabledCb.checked;
        const botToken = document.getElementById('telegram_bot_token').value.trim();
        const chatIdsRaw = document.getElementById('telegram_authorized_chat_ids').value.trim();
        
        if (!apiKey) {
            showToast("⚠️ Gemini API Key zorunludur.");
            return;
        }

        if (botEnabled && !botToken) {
            showToast("⚠️ Telegram aktifken Bot Token girilmesi zorunludur.");
            return;
        }

        // Chat ID dizisini ayrıştıralım
        const chatIds = chatIdsRaw.split(',')
            .map(id => id.trim())
            .filter(id => id.length > 0)
            .map(id => {
                const parsed = parseInt(id, 10);
                return isNaN(parsed) ? id : parsed;
            });

        const payload = {
            gemini_api_key: apiKey,
            telegram_bot_enabled: botEnabled,
            telegram_bot_token: botToken,
            telegram_authorized_chat_ids: chatIds
        };

        btnSaveConfig.disabled = true;
        btnSaveConfig.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Kaydediliyor...';

        try {
            const response = await fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            
            const data = await response.json();
            
            if (response.ok && data.status === 'success') {
                showToast("✅ Yapılandırma başarıyla kaydedildi ve uygulandı!");
                closeSettings();
                // Durumu anında tazeleyelim
                fetchSystemStatus();
            } else {
                throw new Error(data.message || "Bilinmeyen kaydetme hatası.");
            }
        } catch (error) {
            showToast(`❌ Hata: ${error.message}`);
        } finally {
            btnSaveConfig.disabled = false;
            btnSaveConfig.innerHTML = '<i class="fa-solid fa-save"></i> Yapılandırmayı Kaydet & Başlat';
        }
    });

    // =========================================================================
    // 2. KONSOL LOG ÇEKMECESİ YÖNETİMİ
    // =========================================================================
    
    const toggleLogs = () => {
        const caret = btnExpandLogs.querySelector('i');
        if (logsDrawer.classList.contains('collapsed')) {
            logsDrawer.classList.remove('collapsed');
            logsDrawer.classList.add('expanded');
            caret.className = 'fa-solid fa-angle-down';
            // Scroll to bottom
            setTimeout(() => { logOutput.scrollTop = logOutput.scrollHeight; }, 100);
        } else {
            logsDrawer.classList.remove('expanded');
            logsDrawer.classList.add('collapsed');
            caret.className = 'fa-solid fa-angle-up';
        }
    };
    
    btnExpandLogs.addEventListener('click', toggleLogs);
    btnToggleLogs.addEventListener('click', toggleLogs);
    
    // Konsol loglarını temizle
    btnClearLogs.addEventListener('click', (e) => {
        e.stopPropagation(); // Drawer'ın açılmasını engeller
        logOutput.textContent = "Konsol temizlendi. Bekleniyor...";
        currentLogLines = [];
        logCountSpan.textContent = "0";
    });

    // Sunucudan Canlı Log Akışını Polling ile Çek
    const fetchLiveLogs = async () => {
        try {
            const response = await fetch('/api/logs');
            if (!response.ok) return;
            const logs = await response.json();
            
            if (logs.length !== currentLogLines.length) {
                currentLogLines = logs;
                logOutput.textContent = logs.join('\n');
                logCountSpan.textContent = logs.length;
                // Eğer konsol açıksa en alta kaydır
                if (logsDrawer.classList.contains('expanded')) {
                    logOutput.scrollTop = logOutput.scrollHeight;
                }
            }
        } catch (err) {
            console.error("Log alma hatası:", err);
        }
    };

    // =========================================================================
    // 3. SİSTEM DONANIM METRİKLERİ VE HALKASI GÜNCELLEMESİ
    // =========================================================================
    
    // SVG Halka Yüzdesini Set Eden Fonksiyon
    const setRingProgress = (ringId, valId, percent) => {
        const ring = document.getElementById(ringId);
        const valSpan = document.getElementById(valId);
        
        if (!ring || !valSpan) return;

        // Yüzdeyi ekrana yazdır
        valSpan.textContent = Math.round(percent);

        // Halka doluluk seviyesini ayarla
        const offset = SVG_CIRCUMFERENCE - (percent / 100) * SVG_CIRCUMFERENCE;
        ring.style.strokeDashoffset = offset;
    };

    // Sunucudan Canlı Sistem Durumunu Çek
    const fetchSystemStatus = async () => {
        try {
            const response = await fetch('/api/status');
            if (!response.ok) return;
            const data = await response.json();

            // Progress halkalarını güncelle
            setRingProgress('cpu-ring', 'cpu-val', data.cpu);
            setRingProgress('ram-ring', 'ram-val', data.ram);
            setRingProgress('disk-ring', 'disk-val', data.disk);
            setRingProgress('battery-ring', 'battery-val', data.battery);

            // Detaylı RAM verisi
            document.getElementById('ram-details').textContent = `${data.ram_used} / ${data.ram_total}`;

            // Priz/Şarj durum simgesi
            const chargeIcon = document.getElementById('battery-charging-icon');
            if (data.battery_plugged) {
                chargeIcon.classList.remove('hidden');
            } else {
                chargeIcon.classList.add('hidden');
            }

            // Ajan / Model Durum Rozeti
            const geminiDot = document.getElementById('gemini-status-dot');
            const geminiText = document.getElementById('gemini-status-text');
            if (data.gemini_active) {
                geminiDot.className = 'dot green-pulse';
                geminiText.textContent = "Gemini Aktif";
            } else {
                geminiDot.className = 'dot red-pulse';
                geminiText.textContent = "Gemini Ayarlanmamış";
            }

            // Telegram Durum Rozeti
            const botDot = document.getElementById('bot-status-dot');
            const botText = document.getElementById('bot-status-text');
            if (data.telegram_active) {
                botDot.className = 'dot green-pulse';
                botText.textContent = "Telegram: Aktif (Dinliyor)";
            } else {
                botDot.className = 'dot red-pulse';
                botText.textContent = "Telegram: Devre Dışı";
            }

        } catch (error) {
            console.error("Donanım metrikleri okunamadı:", error);
        }
    };

    // =========================================================================
    // 4. MESAJLAŞMA VE CHAT YÖNETİMİ
    // =========================================================================
    
    // Mesaj Giriş Alanı Enter Tetiklemesi
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            sendMessageToAgent();
        }
    });

    btnSendMessage.addEventListener('click', sendMessageToAgent);

    // Canlı Chat Mesaj Gönderme
    async function sendMessageToAgent() {
        const messageText = chatInput.value.trim();
        if (!messageText) return;

        // Girdiyi temizle
        chatInput.value = '';

        // Kullanıcı mesajını arayüze ekle
        appendChatMessage("Siz", messageText, true);

        // Yazıyor göstergesini aktif et, alta kaydır
        typingIndicator.classList.remove('hidden');
        chatTimeline.scrollTop = chatTimeline.scrollHeight;

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: messageText })
            });

            const data = await response.json();
            
            // Yazıyor simgesini gizle
            typingIndicator.classList.add('hidden');

            if (response.ok) {
                appendChatMessage("Antigravity OS Ajanı", data.response, false);
            } else {
                appendChatMessage("Sistem Uyarısı", `⚠️ Hata: ${data.response || "Yapay zeka yanıt üretemedi."}`, false, true);
            }
        } catch (error) {
            typingIndicator.classList.add('hidden');
            appendChatMessage("Sistem Uyarısı", `❌ Bağlantı Hatası: Sunucu ile iletişim kurulamadı.`, false, true);
        }
    }

    // Sohbet Arayüzüne Mesaj Ekleme ve Markdown Biçimlendirme
    function appendChatMessage(sender, text, isUser = true, isAlert = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user-message' : 'assistant-message'} glassmorphic`;
        
        if (isAlert) {
            messageDiv.style.borderColor = 'var(--red)';
        }

        // Gönderici Başlığı
        const senderDiv = document.createElement('div');
        senderDiv.className = 'message-sender';
        senderDiv.innerHTML = isUser ? '<i class="fa-solid fa-user"></i> <span>Siz</span>' : '<i class="fa-solid fa-robot"></i> <span>Asistan</span>';
        if (isAlert) senderDiv.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> <span>Sistem Uyarısı</span>';
        
        // Mesaj İçeriği (Basit Markdown Çözümleyici)
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.innerHTML = parseSimpleMarkdown(text);
        
        // Zaman Etiketi
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        const now = new Date();
        timeDiv.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        messageDiv.appendChild(senderDiv);
        messageDiv.appendChild(contentDiv);
        messageDiv.appendChild(timeDiv);

        chatTimeline.appendChild(messageDiv);
        
        // Ekranı otomatik olarak en alta kaydır
        chatTimeline.scrollTop = chatTimeline.scrollHeight;
    }

    // Basit ve Güvenli HTML / Markdown Parser (WOW faktörü için)
    function parseSimpleMarkdown(text) {
        let html = text;

        // HTML injection engellemek için tag'leri escape edelim (kendi eklediğimiz tagler hariç)
        html = html
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");

        // Kod blokları (```kod```) -> yeşil retro terminal stili
        html = html.replace(/```([\s\S]+?)```/g, (match, code) => {
            return `<pre><code>${code.trim()}</code></pre>`;
        });

        // Kalın Metinler (**metin**)
        html = html.replace(/\*\*([\s\S]+?)\*\*/g, '<strong>$1</strong>');

        // İtalik Metinler (*metin*)
        html = html.replace(/\*([\s\S]+?)\*/g, '<em>$1</em>');

        // Tek Satır Kodlar (`kod`)
        html = html.replace(/`([^`]+)`/g, '<code class="inline-code" style="background:rgba(255,255,255,0.06); padding:2px 6px; border-radius:4px; font-family:var(--font-mono); font-size:90%; color:#06b6d4;">$1</code>');

        // Satır sonları (<br>)
        html = html.replace(/\n/g, '<br>');

        // Eğer assistsan yanıtında bir resim yolu varsa, otomatik olarak web arayüzünde o resmin altına bir resim kutusu ekleyelim!
        // Örn: "Dosya Yolu: /Users/.../screenshot_XXX.png"
        const pathRegex = /Dosya Yolu:\s*([^\s<>\n]+.png)/i;
        const match = html.match(pathRegex);
        if (match) {
            // Arayüze gömülü resim ekliyoruz (yerel dosyayı Flask static gibi servis edemez ama
            // yerelde ekran görüntüsünün alındığını şık bir placeholder resimle veya basit bir logla gösterelim)
            // Aslında yerel dosyaları doğrudan browser güvenlik politikaları yüzünden yükleyemeyiz (file:// yasak).
            // Ama asistanın bunu yaptığını görselleştirmek adına güzel bir visual kart ekleyebiliriz!
            html += `<br><div style="margin-top: 10px; padding: 12px; background: rgba(16, 185, 129, 0.08); border: 1px solid var(--green); border-radius: 10px; display: flex; align-items: center; gap: 10px;">
                        <i class="fa-solid fa-circle-check text-green" style="font-size: 20px;"></i>
                        <div>
                            <strong style="color:#ffffff;">Ekran Görüntüsü Yerelde Kaydedildi</strong>
                            <div style="font-size:11px; color:var(--fg-muted); margin-top:2px;">Yol: ${match[1]}</div>
                        </div>
                     </div>`;
        }

        return html;
    }

    // =========================================================================
    // 5. HIZLI İŞLEMLER VE MAKET BUTONLAR
    // =========================================================================
    
    // Ekran Görüntüsü Al
    btnScreenshot.addEventListener('click', async () => {
        btnScreenshot.disabled = true;
        btnScreenshot.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Fotoğraflanıyor...';
        
        try {
            const response = await fetch('/api/screenshot', { method: 'POST' });
            const data = await response.json();
            if (response.ok && data.status === 'success') {
                showToast("📸 Ekran görüntüsü başarıyla alındı ve kaydedildi!");
            } else {
                throw new Error(data.message);
            }
        } catch (err) {
            showToast(`❌ Hata: ${err.message}`);
        } finally {
            btnScreenshot.disabled = false;
            btnScreenshot.innerHTML = '<i class="fa-solid fa-camera"></i> Ekran Görüntüsü Al';
        }
    });

    // Sistem Raporu İste
    btnQuickStatus.addEventListener('click', () => {
        chatInput.value = "Sistem durumunu kontrol et";
        sendMessageToAgent();
    });

    // Sohbet Geçmişini Sıfırla
    btnClearChat.addEventListener('click', async () => {
        if (!confirm("Sohbet geçmişini sıfırlamak istediğinize emin misiniz?")) return;
        
        try {
            const response = await fetch('/api/chat/clear', { method: 'POST' });
            if (response.ok) {
                // Timeline temizle
                chatTimeline.innerHTML = '';
                // Hoşgeldin mesajını geri ekle
                appendWelcomeBack();
                showToast("🗑️ Sohbet geçmişi sıfırlandı.");
            }
        } catch (err) {
            showToast("❌ Sohbet sıfırlanamadı.");
        }
    });

    function appendWelcomeBack() {
        const welcomeHtml = `
            <div class="message-sender">
                <i class="fa-solid fa-robot"></i>
                <span>Antigravity OS Ajanı</span>
            </div>
            <div class="message-content">
                <p>Sohbet geçmişi başarıyla temizlendi. Sistem üzerinde yeni sorgular gönderebilirsiniz.</p>
            </div>
            <div class="message-time">Sıfırlandı</div>
        `;
        const div = document.createElement('div');
        div.className = "message assistant-message glassmorphic";
        div.innerHTML = welcomeHtml;
        chatTimeline.appendChild(div);
    }

    // =========================================================================
    // 6. TOAST BİLDİRİM SİSTEMİ (NOTIFICATION TOAST)
    // =========================================================================
    function showToast(message) {
        const toast = document.getElementById('notification-toast');
        const msgSpan = document.getElementById('notification-message');
        
        msgSpan.textContent = message;
        toast.classList.remove('hidden');
        
        // 4 saniye sonra otomatik gizle
        setTimeout(() => {
            toast.classList.add('hidden');
        }, 4000);
    }

    // =========================================================================
    // PERİYODİK POLING DÖNGÜLERİ (POLLING RUNNERS)
    // =========================================================================
    
    // İlk tazelemeleri yapalım
    fetchSystemStatus();
    loadConfigFromServer();

    // Periyodik polingler (3 Saniyede bir)
    setInterval(fetchSystemStatus, 3000);
    setInterval(fetchLiveLogs, 3000);
});
