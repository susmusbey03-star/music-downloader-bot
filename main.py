import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

# Telegram Bot Token'ını buraya tırnaklar arasına yapıştıracaksın
TOKEN = "8655201597:AAG5FIVZWdYcR264HGoS2MvuordCyrcQ5hU"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start komutuna cevap verir."""
    await update.message.reply_text(
        "👋 Merhaba! Ben Termux üzerinde çalışan Müzik İndirme Botuyum.\n\n"
        "Bana bir YouTube veya SoundCloud linki gönder, senin için MP3 yapayım!"
    )

async def download_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gönderilen linki alır, MP3'e dönüştürür ve Telegram üzerinden gönderir."""
    url = update.message.text.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        await update.message.reply_text("⚠️ Lütfen geçerli bir bağlantı adresi (URL) gönderin.")
        return

    status_message = await update.message.reply_text("⏳ İndirme ve MP3 dönüştürme başlatıldı...")

    # yt-dlp ve ffmpeg indirme ayarları
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
    }

    loop = asyncio.get_running_loop()

    try:
        def run_dl():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                base_path, _ = os.path.splitext(filename)
                return f"{base_path}.mp3"

        # İndirme işlemini arka planda çalıştır
        mp3_file = await loop.run_in_executor(None, run_dl)

        await status_message.edit_text("📤 MP3 Telegram'a yükleniyor...")
        
        # MP3 dosyasını sohbet ekranına gönder
        with open(mp3_file, 'rb') as audio:
            await update.message.reply_audio(audio=audio)

        # Temizlik: İndirilen MP3'ü sil
        if os.path.exists(mp3_file):
            os.remove(mp3_file)

        await status_message.delete()

    except Exception as e:
        await status_message.edit_text(f"❌ Bir hata oluştu: {str(e)}")

def main():
    """Botu çalıştırır."""
    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_audio))

    print("🚀 Bot çalışıyor...")
    app.run_polling()

if __name__ == '__main__':
    main()
  
