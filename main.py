import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.request import HTTPXRequest
import yt_dlp

# Telegram Bot Token'ını buraya tırnaklar arasına yapıştırın
TOKEN = "8655201597:AAG5FIVZWdYcR264HGoS2MvuordCyrcQ5hU"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start komutuna cevap verir."""
    await update.message.reply_text(
        "👋 Merhaba! Müzik ve Video İndirme Botuna Hoş Geldiniz.\n\n"
        "🎵 **Müzik (MP3) İndirmek İçin:**\n"
        "`/indir <youtube_linki>`\n\n"
        "🎬 **Video (MP4) İndirmek İçin:**\n"
        "`/video <youtube_linki>`\n\n"
        "Eşleşen bağlantıyı göndererek hızlıca indirebilirsiniz!",
        parse_mode="Markdown"
    )

async def download_audio_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/indir komutu ile MP3 indirir."""
    if not context.args:
        await update.message.reply_text("⚠️ Lütfen komuttan sonra bir link girin!\nÖrnek: `/indir https://youtu.be/...`", parse_mode="Markdown")
        return

    url = context.args[0].strip()
    await process_download(update, url, mode='audio')

async def download_video_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/video komutu ile MP4 indirir."""
    if not context.args:
        await update.message.reply_text("⚠️ Lütfen komuttan sonra bir link girin!\nÖrnek: `/video https://youtu.be/...`", parse_mode="Markdown")
        return

    url = context.args[0].strip()
    await process_download(update, url, mode='video')

async def handle_direct_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Direkt atılan linkleri varsayılan olarak MP3 olarak indirir."""
    url = update.message.text.strip()
    if url.startswith("http://") or url.startswith("https://"):
        await process_download(update, url, mode='audio')

async def process_download(update: Update, url: str, mode: str = 'audio'):
    """İndirme ve gönderme işlemlerini yürütür."""
    if not (url.startswith("http://") or url.startswith("https://")):
        await update.message.reply_text("⚠️ Lütfen geçerli bir bağlantı adresi (URL) gönderin.")
        return

    type_str = "🎵 MP3 Müzik" if mode == 'audio' else "🎬 MP4 Video"
    status_message = await update.message.reply_text(f"⏳ {type_str} indirme ve dönüştürme başlatıldı...")

    if mode == 'audio':
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
    else: # video
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
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
                if mode == 'audio':
                    base_path, _ = os.path.splitext(filename)
                    return f"{base_path}.mp3"
                return filename

        downloaded_file = await loop.run_in_executor(None, run_dl)

        await status_message.edit_text(f"📤 {type_str} Telegram'a yükleniyor...")
        
        # Dosyayı kullanıcıya gönder
        with open(downloaded_file, 'rb') as media_file:
            if mode == 'audio':
                await update.message.reply_audio(audio=media_file)
            else:
                await update.message.reply_video(video=media_file)

        # Temizlik: İndirilen dosyayı sil
        if os.path.exists(downloaded_file):
            os.remove(downloaded_file)

        await status_message.delete()

    except Exception as e:
        await status_message.edit_text(f"❌ Bir hata oluştu: {str(e)}")

def main():
    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    # TimeOut hatasının önüne geçmek için HTTP istek sürelerini artırıyoruz
    request = HTTPXRequest(read_timeout=60.0, write_timeout=60.0, connect_timeout=60.0, pool_timeout=60.0)
    app = Application.builder().token(TOKEN).request(request).build()

    # Komut tanımlamaları
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("indir", download_audio_cmd))
    app.add_handler(CommandHandler("video", download_video_cmd))
    
    # Direkt atılan linkleri yakalama
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_direct_link))

    print("🚀 Bot çalışıyor...")
    app.run_polling()

if __name__ == '__main__':
    main()
    
