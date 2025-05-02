import os
import json
from yt_dlp import YoutubeDL
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from telegram.request import HTTPXRequest

# Telegram bot token
BOT_TOKEN = 'BOT_TOKEN'
ADMIN_IDS = [id]  # استبدل هذه المعرفات بمعرفات المسؤولين

DOWNLOAD_DIR = 'downloads'
USERS_FILE = 'users.json'
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

MAX_DURATION_SECONDS = 90 * 60  # 1.5 hours

SUPPORTED_SITES = [
    "youtube.com", "youtu.be", "tiktok.com", "instagram.com",
    "twitter.com", "facebook.com", "fb.watch"
]

# Load or initialize user database
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    msg = (
        "👋 أهلاً! أرسل رابط فيديو من YouTube أو TikTok أو Instagram وسأقوم بتحميله لك.\n"
        "اكتب /help لعرض التعليمات."
    )
    if user_id in ADMIN_IDS:
        msg += "\n\n🛠️ أنت مسؤول! اكتب /dashboard لعرض معلومات المستخدمين."
    await update.message.reply_text(msg)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 *تعليمات استخدام البوت:*\n"
        "1. أرسل رابط لفيديو من YouTube أو TikTok أو Instagram أو Twitter أو Facebook.\n"
        "2. سيتم سؤالك إن كنت تريد تحميل الفيديو أو الصوت فقط.\n"
        "⚠️ البوت لا يدعم روابط خاصة أو محمية بكلمة مرور.\n"
        "💬 إن واجهت مشكلة، أعد المحاولة أو تحقق من صحة الرابط."
    )

async def dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in ADMIN_IDS:
        await update.message.reply_text("🚫 هذه الميزة مخصصة للمسؤول فقط.")
        return

    users = load_users()
    count = len(users)
    usernames = '\n'.join([f"{uid}: {uname}" for uid, uname in users.items()])
    await update.message.reply_text(f"👤 عدد المستخدمين: {count}\n\n{usernames}")

def download_media(url, audio_only=False):
    ydl_opts = {
        'outtmpl': f'{DOWNLOAD_DIR}/%(title).70s.%(ext)s',
        'format': 'bestaudio/best' if audio_only else 'best',
        'merge_output_format': 'mp4',
        'quiet': True,
        'noplaylist': True,
        'postprocessors': []
    }
    if audio_only:
        ydl_opts['postprocessors'].append({
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        })
    else:
        ydl_opts['postprocessors'].append({
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        })

    with YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)
        duration = info_dict.get('duration')
        if duration and duration > MAX_DURATION_SECONDS:
            raise Exception("⏱️ الفيديو أطول من ساعة ونصف ولا يمكن تحميله.")

        ydl.download([url])
        filename = ydl.prepare_filename(info_dict)
        if audio_only:
            filename = filename.rsplit('.', 1)[0] + '.mp3'
        elif not filename.endswith('.mp4'):
            filename = filename.rsplit('.', 1)[0] + '.mp4'
        return filename

user_links = {}

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    user_id = str(update.message.from_user.id)
    username = update.message.from_user.username or "بدون اسم مستخدم"
    if user_id not in users:
        users[user_id] = username
        save_users(users)

    url = update.message.text.strip()
    if any(domain in url for domain in SUPPORTED_SITES):
        user_links[user_id] = url
        keyboard = [
            [
                InlineKeyboardButton("🎵 صوت فقط", callback_data='audio'),
                InlineKeyboardButton("🎞️ فيديو", callback_data='video')
            ]
        ]
        await update.message.reply_text("📥 هل تريد تحميل الصوت فقط أم الفيديو؟", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(
            "⚠️ أرسل رابط صحيح من المواقع المدعومة فقط:\n"
            "YouTube, TikTok, Instagram, Twitter, Facebook."
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    url = user_links.get(user_id)
    if not url:
        await query.edit_message_text("❌ لم يتم العثور على الرابط، أرسل الرابط مرة أخرى.")
        return

    await query.edit_message_text("🔄 جارٍ التحميل، يرجى الانتظار...")
    try:
        audio_only = query.data == 'audio'
        filepath = download_media(url, audio_only=audio_only)
        with open(filepath, 'rb') as f:
            if audio_only:
                await query.message.reply_audio(audio=f)
            else:
                await query.message.reply_video(video=f)
        os.remove(filepath)
    except Exception:
        await query.message.reply_text("❌ حدث خطأ أثناء التحميل. تأكد من الرابط أو حاول لاحقاً.")

if __name__ == '__main__':
    request = HTTPXRequest(connect_timeout=10, read_timeout=30)
    app = ApplicationBuilder().token(BOT_TOKEN).request(request).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("dashboard", dashboard))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(CallbackQueryHandler(button_callback))

    print("✅ البوت يعمل الآن...")
    app.run_polling()
