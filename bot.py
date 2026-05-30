import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import yt_dlp

BOT_TOKEN = os.environ.get("BOT_TOKEN")

cookies_content = os.environ.get("INSTAGRAM_COOKIES")
if cookies_content:
    with open("cookies.txt", "w") as f:
        f.write(cookies_content)

cookie_file = "cookies.txt" if os.path.exists("cookies.txt") else None

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

    os.makedirs("downloads", exist_ok=True)

    for f in os.listdir("downloads"):
        os.remove(os.path.join("downloads", f))

    if choice == "video":
        ydl_opts = {
            "format": "bestvideo+bestaudio/best",
            "outtmpl": "downloads/%(autonumber)s_%(id)s.%(ext)s",
            "merge_output_format": "mp4",
            "quiet": True,
            "cookiefile": cookie_file,
        }
    else:
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": "downloads/%(autonumber)s_%(id)s.%(ext)s",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "quiet": True,
            "cookiefile": cookie_file,
        }

    msg = await query.edit_message_text("⏳ جاري التحميل...")
    file_path = None

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)

        files = sorted([
            f for f in os.listdir("downloads")
            if not f.endswith(('.json', '.txt', '.xml'))
            and os.path.isfile(os.path.join("downloads", f))
        ])

        if not files:
            all_files = os.listdir("downloads")
            await msg.edit_text(f"❌ الملفات الموجودة: {str(all_files)}")
            return

        await msg.edit_text(f"📤 جاري الإرسال... (0/{len(files)})")

        for i, fname in enumerate(files):
            file_path = os.path.join("downloads", fname)
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
        if file_path and os.path.exists(file_path):
            os.remove(file_path)


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    app.add_handler(CallbackQueryHandler(handle_choice))
    print("✅ البوت شغال...")
    app.run_polling()


if __name__ == "__main__":
    main()
