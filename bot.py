import os
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import yt_dlp

BOT_TOKEN = os.environ.get("BOT_TOKEN")

async def download_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    
    if not url.startswith("http"):
        return

    msg = await update.message.reply_text("⏳ جاري التحميل...")
    os.makedirs("downloads", exist_ok=True)

    ydl_opts = {
        "format": "bestvideo+bestaudio/best",
        "outtmpl": "downloads/%(id)s.%(ext)s",
        "merge_output_format": "mp4",
        "quiet": True,
	"username": "hotspacop@sendnow.win",
	"password": "pop08643",
    }

    file_path = None
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info).replace(f".{info['ext']}", ".mp4")

        await msg.edit_text("📤 جاري الإرسال...")

        file_size = os.path.getsize(file_path)
        
        if file_size > 50 * 1024 * 1024:
            await msg.edit_text("⚠️ الملف أكبر من 50MB، جاري الإرسال كمستند...")
            with open(file_path, "rb") as f:
                await update.message.reply_document(document=f)
        else:
            with open(file_path, "rb") as f:
                await update.message.reply_video(video=f, supports_streaming=True, caption=info.get("title", ""))

        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"❌ خطأ: {str(e)}")

    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_and_send))
    print("✅ البوت شغال...")
    app.run_polling()

if __name__ == "__main__":
    main()
