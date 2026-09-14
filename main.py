import os
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.request import HTTPXRequest
import yt_dlp

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = "8655201597:AAG5FIVZWdYcR264HGoS2MvuordCyrcQ5hU"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👋 **Müzik & Video İndirme Botuna Hoş Geldiniz!**\n\n"
        "💬 **Özel Mesajlarda:** Direkt şarkı adı veya link göndermeniz yeterlidir.\n"
        "👥 **Grup Sohbetlerinde:** Normal sohbetinizi etkilemez! İndirme yapmak için:\n"
        "• `/indir <şarkı adı>` veya `/video <link>` komutlarını kullanın.\n"
        "• Doğrudan bir YouTube / SoundCloud linki gönderin.\n"
        "• Bota yanıt vererek (reply) şarkı adı yazın."
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def download_audio_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Lütfen bir şarkı adı veya bağlantı girin!\nÖrnek: `/indir Sezen Aksu`", parse_mode="Markdown")
        return
    query = " ".join(context.args).strip()
    await process_download(update, query, mode='audio')

async def download_video_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Lütfen bir video adı veya bağlantı girin!\nÖrnek: `/video https://youtu.be/...`", parse_mode="Markdown")
        return
    query = " ".join(context.args).strip()
    await process_download(update, query, mode='video')

async def handle_direct_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    chat_type = update.effective_chat.type

    if text.startswith("/"):
        return

    # Grup sohbeti kontrolü
    if chat_type in ['group', 'supergroup']:
        is_url = text.startswith("http://") or text.startswith("https://")
        bot_username = context.bot.username
        is_mentioned = bot_username and f"@{bot_username}" in text
        is_reply_to_bot = (
            update.message.reply_to_message and 
            update.message.reply_to_message.from_user.id == context.bot.id
        )

        # Grup içindeyse sadece URL, mention veya yanıt durumunda çalışır
        if is_url or is_mentioned or is_reply_to_bot:
            clean_query = text.replace(f"@{bot_username}", "").strip() if is_mentioned else text
            await process_download(update, clean_query, mode='audio')
        else:
            # Normal sohbet mesajı, bota işlem yaptırma
            return
    else:
        # Özel sohbet (DM) - Her metni indirme araması yap
        await process_download(update, text, mode='audio')

async def process_download(update: Update, query: str, mode: str = 'audio'):
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

    print("🚀 Grup Destekli Bot Aktif!")
    app.run_polling()

if __name__ == '__main__':
    main()
    
