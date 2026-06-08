import os
import shutil
import instaloader
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import yt_dlp

# إعدادات المتغيرات
BOT_TOKEN = os.environ.get("BOT_TOKEN")
IG_USER = os.environ.get("IG_USER")

# تهيئة ملفات الكوكيز
def setup_cookies(env_var, filename):
    content = os.environ.get(env_var)
    if content:
        with open(filename, "w") as f:
            f.write(content)
        return filename
    return None

cookie_file = setup_cookies("INSTAGRAM_COOKIES", "cookies.txt")
yt_cookie_file = setup_cookies("YOUTUBE_COOKIES", "yt_cookies.txt")

def is_instagram_stories(url):
    return "instagram.com/stories/" in url

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith("http"):
        return

    context.user_data["url"] = url
    keyboard = [[InlineKeyboardButton("🎬 فيديو", callback_data="video"), InlineKeyboardButton("🎵 صوت MP3", callback_data="audio")]]
    await update.message.reply_text("شتبي تحمل؟", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    url = context.user_data.get("url")
    choice = query.data

    if not url:
        await query.edit_message_text("❌ حدث خطأ، يرجى إرسال الرابط مرة أخرى.")
        return

    req_id = f"{update.effective_user.id}_{query.message.message_id}"
    user_download_dir = os.path.join("downloads", req_id)
    os.makedirs(user_download_dir, exist_ok=True)
    msg = await query.edit_message_text("⏳ جاري التحميل... انتظر قليلاً.")

    try:
        if is_instagram_stories(url):
            # منطق إنستجرام
            L = instaloader.Instaloader(dirname_pattern=user_download_dir, filename_pattern="{date_utc:%Y%m%d%H%M%S}")
            if os.path.exists("session"): L.load_session_from_file(IG_USER)
            
            username = url.split("/stories/")[1].split("/")[0]
            profile = instaloader.Profile.from_username(L.context, username)
            stories = L.get_stories(userids=[profile.userid])
            for story in stories:
                for item in story.get_items():
                    L.download_storyitem(item, target=user_download_dir)
        else:
            # منطق YouTube / Social Media
            ydl_opts = {
                "outtmpl": f"{user_download_dir}/%(title)s.%(ext)s",
                "quiet": True,
                "cookiefile": yt_cookie_file,
                "format": "bestvideo+bestaudio/best" if choice == "video" else "bestaudio/best"
            }
            if choice == "audio":
                ydl_opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}]
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

        # عملية الإرسال
        files = [os.path.join(user_download_dir, f) for f in os.listdir(user_download_dir) if not f.endswith(".json")]
        if not files:
            await msg.edit_text("❌ لم يتم العثور على ملفات للتحميل.")
            return

        for i, file_path in enumerate(files):
            await msg.edit_text(f"📤 جاري الإرسال ({i+1}/{len(files)})...")
            with open(file_path, "rb") as f:
                if file_path.endswith((".mp3")):
                    await query.message.reply_audio(audio=f)
                else:
                    await query.message.reply_document(document=f)
        
        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"❌ حدث خطأ: {str(e)}")
    finally:
        if os.path.exists(user_download_dir):
            shutil.rmtree(user_download_dir)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    app.add_handler(CallbackQueryHandler(handle_choice))
    print("✅ البوت يعمل الآن...")
    app.run_polling()

if __name__ == "__main__":
    main()import os
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import yt_dlp

BOT_TOKEN = "8963886990:AAFRtN7AXppucUnWAvMWV4hDRtq4QYbzSFo"

async def download_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    
    # التأكد أن الرسالة رابط
    if not url.startswith("http"):
        return

    msg = await update.message.reply_text("⏳ جاري التحميل... يرجى الانتظار.")
    os.makedirs("downloads", exist_ok=True)

    # إعدادات yt-dlp المحسنة لمحاكاة المتصفح
    ydl_opts = {
        "format": "bestvideo+bestaudio/best",
        "outtmpl": "downloads/%(id)s.%(ext)s",
  finally:
        # حذف الملف المؤقت بعد الانتهاء
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    # استخدام فلتر الروابط فقط لتقليل الضغط على البوت
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_and_send))
    
    print("✅ البوت يعمل الآن..")
    app.run_polling()

if __name__ == "__main__":
    main()
