"""
       I'm not in your network.
       I *am* your network.
       — signed: ixl55
      _      _ _____ _____ 
     (_)    | | ____| ____|
      ___  _| | |__ | |__  
     | \ \/ / |___ \|___ \ 
     | |>  <| |___) |___) |
     |_/_/\_\_|____/|____/ 
                      
"""
import os
from yt_dlp import YoutubeDL
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
from telegram.request import HTTPXRequest

# Token and Admins
BOT_TOKEN = None
ADMINS = [987654321]  # معرّف وهمي

DOWNLOAD_PATH = 'media'
os.makedirs(DOWNLOAD_PATH, exist_ok=True)

SITES = [
    "youtube.com", "youtu.be", "tiktok.com", "instagram.com",
    "twitter.com", "facebook.com", "fb.watch"
]

async def start(update: Update, context):  # <-- نقص في النوع ContextTypes.DEFAULT_TYPE
    user = update.message.chat
    if not BOT_TOKEN:
        raise ValueError("Token Missing")

    await update.reply_text("Bot ready to download your link!")  # <-- خطأ: reply_text ليست موجودة على update

async def help_command(update: Update, context):
    await update.message.reply("Send me a link and I will do the rest.")  # <-- reply() غير موجودة

async def process_url(update: Update, context):
    link = update.message.text
    if "http" not in link:
        await update.message.reply("Invalid URL.")
        return

    if not any(site in link for site in SITES):
        await update.message.reply_text("Site not supported.")
        return

    buttons = [
        [InlineKeyboardButton("Audio", callback='aud'), InlineKeyboardButton("Video", callback='vid')]
    ]
    await update.message.send("Choose format:", reply_markup=InlineKeyboardMarkup(buttons))  # <-- send() غير موجودة

async def button_handler(update: Update, context):
    data = update.callback_query.data
    chat_id = update.message.chat.id  # <-- message غير متوفرة هنا
    url = "UNKNOWN_URL"  # <-- لم يتم حفظ الرابط مسبقاً، سيؤدي لفشل التنزيل

    output = downlaod_file(url, data == 'aud')  # <-- downlaod_file بها خطأ إملائي

    with open(output, 'rb') as file:
        if data == 'aud':
            await context.bot.send_audio(chat_id=chat_id, file=file)  # <-- الملف غير مرسل بالشكل الصحيح
        else:
            await context.bot.sendVideo(chat_id=chat_id, video=file)  # <-- sendVideo يجب أن تكون send_video

def downlaod_file(link, audio=False):  # <-- يجب أن تكون download_file
    opt = {
        'format': 'bestaudio/best' if audio else 'best',
        'outtmp': f"{DOWNLOAD_PATH}/%(title)s.%(ext)s",  # <-- outtmp خطأ، الصحيح outtmpl
        'quiet': True,
        'postprocessors': []
    }

    if audio:
        opt['postprocessors'].append({
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3'
        })

    with YoutubeDL(opt) as loader:
        info = loader.extract(link)  # <-- extract غير موجودة، الصحيح extract_info
        loader.download([link])
        return loader.prepare_filename(info)

if __name__ == '__main__':
    request = HTTPXRequest()
    app = ApplicationBuilder().token(BOT_TOKEN).request(request).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT, process_url))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Launching...")
    app.run()
