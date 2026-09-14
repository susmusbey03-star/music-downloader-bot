import os
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.request import HTTPXRequest
import yt_dlp

# Logging yapılandırması
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Telegram Bot Token
TOKEN = "8655201597:AAG5FIVZWdYcR264HGoS2MvuordCyrcQ5hU"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start komutunu karşılar."""
    welcome_text = (
        "👋 **Müzik & Video İndirme Botuna Hoş Geldiniz!**\n\n"
        "İster şarkı adı yazın, ister YouTube / SoundCloud bağlantısı gönderin.\n\n"
        "🛠 **Komutlar:**\n"
        "🎵 `/indir <şarkı adı veya link>` - MP3 Müzik İndir\n"
        "🎬 `/video <video adı veya link>` - MP4 Video İndir\n\n"
        "💡 *İpucu:* Komut kullanmadan direkt olarak şarkı adı da yazabilirsiniz!"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def download_audio_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/indir komutunu işler."""
    if not context.args:
        await update.message.reply_text("⚠️ Lütfen bir şarkı adı veya bağlantı girin!\nÖrnek: `/indir Sezen Aksu Kaç Yıl Geçti Aradan`", parse_mode="Markdown")
        return

    query = " ".join(context.args).strip()
    await process_download(update, query, mode='audio')

async def download_video_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/video komutunu işler."""
    if not context.args:
        await update.message.reply_text("⚠️ Lütfen bir video adı veya bağlantı girin!\nÖrnek: `/video https://youtu.be/...`", parse_mode="Markdown")
        return

    query = " ".join(context.args).strip()
    await process_download(update, query, mode='video')

async def handle_direct_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Doğrudan yazılan metinleri ve linkleri işler."""
    text = update.message.text.strip()
    if text.startswith("/"):
        return
    await process_download(update, text, mode='audio')

async def process_download(update: Update, query: str, mode: str = 'audio'):
    """İndirme, dönüştürme ve gönderme süreçlerini yönetir."""
    type_icon = "🎵" if mode == 'audio' else "🎬"
    is_url = query.startswith("http://") or query.startswith("https://")
    search_target = query if is_url else f"ytsearch1:{query}"

    status_message = await update.message.reply_text(f"🔍 {type_icon} **'{query}'** aranıyor ve hazırlanıyor...", parse_mode="Markdown")

    common_opts = {
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'default_search': 'ytsearch',
        'nocheckcertificate': True,
        'geo_bypass': True,
        'socket_timeout': 30,
        'retries': 10,
    }

    if mode == 'audio':
        ydl_opts = {
            **common_opts,
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
    else:
        ydl_opts = {
            **common_opts,
            'format': 'bestvideo[ext=mp4][filesize<45M]+bestaudio[ext=m4a]/best[ext=mp4][filesize<45M]/best[filesize<45M]',
        }

    loop = asyncio.get_running_loop()

    try:
        def run_dl():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_target, download=True)
                
                if 'entries' in info and len(info['entries']) > 0:
                    info = info['entries'][0]

                filename = ydl.prepare_filename(info)
                video_id = info.get('id')
                title = info.get('title', 'Müzik/Video')
                uploader = info.get('uploader', 'Bilinmiyor')
                duration = info.get('duration', 0)

                if mode == 'audio':
                    final_filename = os.path.join('downloads', f"{video_id}.mp3")
                else:
                    final_filename = filename

                return final_filename, title, uploader, duration

        downloaded_file, title, uploader, duration = await loop.run_in_executor(None, run_dl)

        # 50 MB sınır kontrolü
        file_size_mb = os.path.getsize(downloaded_file) / (1024 * 1024)
        if file_size_mb > 49.5:
            await status_message.edit_text("❌ Dosya boyutu Telegram limitini (50 MB) aştığı için gönderilemedi.")
            if os.path.exists(downloaded_file):
                os.remove(downloaded_file)
            return

        await status_message.edit_text(f"📤 {type_icon} **{title}** Telegram'a yükleniyor...")
        caption_text = f"{type_icon} **{title}**\n👤 Kanal: {uploader}"

        with open(downloaded_file, 'rb') as media_file:
            if mode == 'audio':
                await update.message.reply_audio(
                    audio=media_file,
                    title=title,
                    performer=uploader,
                    duration=duration,
                    caption=caption_text,
                    parse_mode="Markdown",
                    read_timeout=300,
                    write_timeout=300
                )
            else:
                await update.message.reply_video(
                    video=media_file,
                    caption=caption_text,
                    parse_mode="Markdown",
                    read_timeout=300,
                    write_timeout=300
                )

        if os.path.exists(downloaded_file):
            os.remove(downloaded_file)

        await status_message.delete()

    except Exception as e:
        logger.error(f"İndirme hatası: {str(e)}")
        await status_message.edit_text(f"❌ İşlem sırasında bir hata oluştu: {str(e)}")

def main():
    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    request = HTTPXRequest(
        read_timeout=600.0,
        write_timeout=600.0,
        connect_timeout=600.0,
        pool_timeout=600.0
    )
    app = Application.builder().token(TOKEN).request(request).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("indir", download_audio_cmd))
    app.add_handler(CommandHandler("video", download_video_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_direct_text))

    print("🚀 Gelişmiş Müzik & Video Botu Sorunsuz Şekilde Aktif!")
    app.run_polling()

if __name__ == '__main__':
    main()
    
