# 🎵 Termux Telegram Music Downloader

Android cihazınızda **Termux** kullanarak çalıştırabileceğiniz, `yt-dlp` tabanlı Telegram MP3 indirme botu.

## 🚀 Özellikler

- 🎧 YouTube ve SoundCloud bağlantılarını yüksek kalitede MP3'e dönüştürür.
- ⚡ Fast & Lightweight (Hızlı ve hafif altyapı).
- 🧹 Gönderilen geçici ses dosyalarını otomatik temizler.

## 📱 Termux Kurulumu

```bash
# 1. Depoları güncelle ve paketleri yükle
pkg update && pkg upgrade -y
pkg install python ffmpeg git tmux -y

# 2. Projeyi klonla
git clone [https://github.com/KULLANICI_ADI/music-downloader-bot.git](https://github.com/KULLANICI_ADI/music-downloader-bot.git)
cd music-downloader-bot

# 3. Bağımlılıkları yükle
pip install -r requirements.txt

# 4. Botu çalıştır
python main.py
