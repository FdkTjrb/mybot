import os
import shutil
import instaloader
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import yt_dlp

BOT_TOKEN = os.environ.get("BOT_TOKEN")
IG_USER = os.environ.get("IG_USER")

# إعداد ملفات الكوكيز من المتغيرات البيئية في Railway
cookies_content = os.environ.get("INSTAGRAM_COOKIES")
if cookies_content:
    with open("cookies.txt", "w") as f:
        f.write(cookies_content)

cookie_file = "cookies.txt" if os.path.exists("cookies.txt") else None

yt_cookies_content = os.environ.get("YOUTUBE_COOKIES")
if yt_cookies_content:
    with open("yt_cookies.txt", "w") as f:
        f.write(yt_cookies_content)

yt_cookie_file = "yt_cookies.txt" if os.path.exists("yt_cookies.txt") else None

def is_instagram_stories(url):
    return "instagram.com/stories/" in url

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith("http"):
        return

    context.user_data["url"] = url

    keyboard = [
        [
            InlineKeyboardButton("🎬 فيديو", callback_data="video"),
            InlineKeyboardButton("🎵 صوت MP3", callback_data="audio"),
        ]
    ]
    await update.message.reply_text("شتبي تحمل؟", reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    url = context.user_data.get("url")
    choice = query.data

    # إنشاء مجلد فريد لكل طلب تحميل لمنع تداخل ملفات المستخدمين وحذفها بالخطأ
    req_id = f"{update.effective_user.id}_{query.message.message_id}"
    user_download_dir = os.path.join("downloads", req_id)
    os.makedirs(user_download_dir, exist_ok=True)

    msg = await query.edit_message_text("⏳ جاري التحميل...")
    file_path = None

    try:
        if is_instagram_stories(url):
            username = url.split("/stories/")[1].split("/")[0]

            L = instaloader.Instaloader(
                download_pictures=True,
                download_videos=True,
                download_video_thumbnails=False,
                download_geotags=False,
                download_comments=False,
                save_metadata=False,
                dirname_pattern=user_download_dir,
                filename_pattern="{date_utc:%Y%m%d%H%M%S}",
            )

            try:
                L.load_session_from_file(IG_USER, "session")
            except Exception as e:
                await msg.edit_text(f"❌ فشل تحميل الـ session: {str(e)}")
                return

            profile = instaloader.Profile.from_username(L.context, username)
            stories = L.get_stories(userids=[profile.userid])

            count = 0
            for story in stories:
                for item in story.get_items():
                    L.download_storyitem(item, target=user_download_dir)
                    count += 1

            if count == 0:
                await msg.edit_text("❌ ما في ستوريات أو الحساب خاص")
                return

        else:
            if choice == "video":
                ydl_opts = {
                    # صيغة مرنة تضمن أعلى جودة وتتحول تلقائياً عبر ffmpeg
                    "format": "bestvideo+bestaudio/best",
                    "outtmpl": f"{user_download_dir}/%(autonumber)s_%(id)s.%(ext)s",
                    "merge_output_format": "mp4",
                    "quiet": True,
                    "cookiefile": yt_cookie_file,  # ✅ تم التصحيح لاستخدام كوكيز اليوتيوب بدلاً من الانستا
                }
            else:
                ydl_opts = {
                    "format": "bestaudio/best",
                    "outtmpl": f"{user_download_dir}/%(autonumber)s_%(id)s.%(ext)s",
                    "postprocessors": [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }],
                    "quiet": True,
                    "cookiefile": yt_cookie_file,
                }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(url, download=True)

        files = sorted([
            f for f in os.listdir(user_download_dir)
            if not f.endswith(('.json', '.txt', '.xml'))
            and os.path.isfile(os.path.join(user_download_dir, f))
        ])

        if not files:
            await msg.edit_text("❌ ما قدرت أحمل الملفات")
            return

        await msg.edit_text(f"📤 جاري الإرسال... (0/{len(files)})")

        for i, fname in enumerate(files):
            file_path = os.path.join(user_download_dir, fname)
            file_size = os.path.getsize(file_path)

            if fname.endswith(('.jpg', '.jpeg', '.png', '.webp')):
                with open(file_path, "rb") as f:
                    await query.message.reply_photo(photo=f)
            elif fname.endswith('.mp3'):
                with open(file_path, "rb") as f:
                    await query.message.reply_audio(audio=f)
            else:
                if file_size > 50 * 1024 * 1024:
                    with open(file_path, "rb") as f:
                        await query.message.reply_document(document=f)
                else:
                    with open(file_path, "rb") as f:
                        await query.message.reply_video(video=f, supports_streaming=True)

            os.remove(file_path)
            await msg.edit_text(f"📤 جاري الإرسال... ({i+1}/{len(files)})")

        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"❌ خطأ: {str(e)}")

    finally:
        # تنظيف السيرفر بالكامل وحذف المجلد المؤقت الخاص بهذا الطلب فوراً
        if os.path.exists(user_download_dir):
            shutil.rmtree(user_download_dir)


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    app.add_handler(CallbackQueryHandler(handle_choice))
    print("✅ البوت شغال...")
    app.run_polling()


if __name__ == "__main__":
    main()
