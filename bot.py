import os
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
        "merge_output_format": "mp4",
        "quiet": True,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    file_path = None
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # استخراج المعلومات والتحميل
            info = ydl.extract_info(url, download=True)
            # تحديد مسار الملف بدقة بعد التحميل
            file_path = ydl.prepare_filename(info)
            if not file_path.endswith('.mp4'):
                file_path = file_path.rsplit('.', 1)[0] + '.mp4'

        await msg.edit_text("📤 جاري الإرسال إلى تليجرام...")

        # التحقق من حجم الملف للإرسال
        file_size = os.path.getsize(file_path)
        
        with open(file_path, "rb") as f:
            if file_size > 50 * 1024 * 1024:
                # إرسال كمستند إذا كان كبيراً
                await update.message.reply_document(document=f, caption=info.get("title", ""))
            else:
                # إرسال كفيديو
                await update.message.reply_video(video=f, supports_streaming=True, caption=info.get("title", ""))

        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"❌ حدث خطأ أثناء التحميل:\n{str(e)}")

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
