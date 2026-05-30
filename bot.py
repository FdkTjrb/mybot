import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import yt_dlp

BOT_TOKEN = os.environ.get("BOT_TOKEN")

# حفظ كوكيز انستا
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

    if choice == "video":
        ydl_opts = {
            "format": "bestvideo+bestaudio/best",
            "outtmpl": "downloads/%(id)s.%(ext)s",
            "merge_output_format": "mp4",
            "quiet": True,
            "cookiefile": cookie_file,
        }
    else:
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": "downloads/%(id)s.%(ext)s",
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
            info = ydl.extract_info(url, download=True)
            if choice == "video":
                ext = info.get('ext', 'mp4')
                file_path = ydl.prepare_filename(info).replace(f".{ext}", ".mp4")
            else:
                ext = info.get('ext', 'mp3')
                file_path = ydl.prepare_filename(info).replace(f".{ext}", ".mp3")

        await msg.edit_text("📤 جاري الإرسال...")
        file_size = os.path.getsize(file_path)

        if choice == "video":
            if file_size > 50 * 1024 * 1024:
                await msg.edit_text("⚠️ الملف أكبر من 50MB، جاري الإرسال كمستند...")
                with open(file_path, "rb") as f:
                    await query.message.reply_document(document=f)
            else:
                with open(file_path, "rb") as f:
                    await query.message.reply_video(video=f, supports_streaming=True, caption=info.get("title", ""))
        else:
            with open(file_path, "rb") as f:
                await query.message.reply_audio(audio=f, title=info.get("title", ""), caption=info.get("title", ""))

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
