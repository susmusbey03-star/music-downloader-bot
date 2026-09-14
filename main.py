import os
import asyncio
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.request import HTTPXRequest
import yt_dlp

# Telegram Bot Token
TOKEN = "8655201597:AAG5FIVZWdYcR264HGoS2MvuordCyrcQ5hU"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start komutuna cevap verir."""
    welcome_text = (
        "👋 **Gelişmiş Müzik ve Video İndirme Botuna Hoş Geldiniz!**

"
        "İster şarkı adı yazarak aratın, ister doğrudan YouTube / SoundCloud linki gönderin.

"
        "🛠 **Kullanım Komutları:**
"
        "🎵 `/indir <şarkı adı veya link>` - MP3 Müzik İndir
"
        "🎬 `/video <video adı veya link>` - MP4 Video İndir

"
        "💡 *İpucu:* Komut yazmadan doğrudan şarkı adı veya bağlantı da gönderebilirsiniz!"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def download_audio_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/indir komutu ile arama veya link üzerinden MP3 indirir."""
    if not context.args:
        await update.message.reply_text("⚠️ Lütfen bir şarkı adı veya link girin!
Örnek: `/indir Sezen Aksu Kaç Yıl Geçti Arayadan`", parse_mode="Markdown")
        return

    query = " ".join(context.args).strip()
    await process_download(update, query, mode='audio')

async def download_video_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/video komutu ile arama veya link üzerinden MP4 indirir."""
    if not context.args:
        await update.message.reply_text("⚠️ Lütfen bir video adı veya link girin!
Örnek: `/video https://youtu.be/...`", parse_mode="Markdown")
        return

    query = " ".join(context.args).strip()
    await process_download(update, query, mode='video')

async def handle_direct_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Direkt yazılan metinleri veya linkleri MP3 olarak indirir."""
    text = update.message.text.strip()
    if text.startswith("/"):
        return
    await process_download(update, text, mode='audio')

async def process_download(update: Update, query: str, mode: str = 'audio'):
    """Arama yapma, indirme ve gönderme süreçlerini yönetir."""
    type_icon = "🎵" if mode == 'audio' else "🎬"
    type_str = "MP3 Müzik" if mode == 'audio' else "MP4 Video"
    
    is_url = query.startswith("http://") or query.startswith("https://")
    search_target = query if is_url else f"ytsearch1:{query}"

    status_message = await update.message.reply_text(f"🔍 {type_icon} **'{query}'** aranıyor ve hazırlanıyor...", parse_mode="Markdown")

    # Termux ve yt-dlp optimizasyon ayarları
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
            'default_search': 'ytsearch',
        }
    else:
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'default_search': 'ytsearch',
        }

    loop = asyncio.get_running_loop()

    try:
        def run_dl():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_target, download=True)
                
                # Arama yapıldıysa ilk sonucu al
                if 'entries' in info and len(info['entries']) > 0:
                    info = info['entries'][0]

                filename = ydl.prepare_filename(info)
                title = info.get('title', 'Müzik/Video')
                uploader = info.get('uploader', 'Bilinmiyor')
                duration = info.get('duration', 0)

                if mode == 'audio':
                    base_path, _ = os.path.splitext(filename)
                    final_filename = f"{base_path}.mp3"
                else:
                    final_filename = filename

                return final_filename, title, uploader, duration

        downloaded_file, title, uploader, duration = await loop.run_in_executor(None, run_dl)

        await status_message.edit_text(f"📤 {type_icon} **{title}** Telegram'a yükleniyor...")
        
        caption_text = f"{type_icon} **{title}**
👤 Kanal: {uploader}"

        # Dosyayı kullanıcıya gönder
        with open(downloaded_file, 'rb') as media_file:
            if mode == 'audio':
                await update.message.reply_audio(
                    audio=media_file,
                    title=title,
                    performer=uploader,
                    duration=duration,
                    caption=caption_text,
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_video(
                    video=media_file,
                    caption=caption_text,
                    parse_mode="Markdown"
                )

        # Temizlik: İndirilen geçici dosyayı sil
        if os.path.exists(downloaded_file):
            os.remove(downloaded_file)

        await status_message.delete()

    except Exception as e:
        await status_message.edit_text(f"❌ Bir hata oluştu: {str(e)}")

def main():
    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    # Büyük boyutlu yüklemelerde zaman aşımı olmaması için timeout süreleri artırıldı
    request = HTTPXRequest(read_timeout=90.0, write_timeout=90.0, connect_timeout=90.0, pool_timeout=90.0)
    app = Application.builder().token(TOKEN).request(request).build()

    # Komut ve Mesaj Dinleyicileri
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("indir", download_audio_cmd))
    app.add_handler(CommandHandler("video", download_video_cmd))
    
    # Yazılan şarkı adlarını veya direkt atılan linkleri yakalama
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_direct_text))

    print("🚀 Gelişmiş Müzik & Video Botu Aktif!")
    app.run_polling()

if __name__ == '__main__':
    main()
