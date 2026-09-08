import os
import shutil
import instaloader
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import yt_dlp

BOT_TOKEN = os.environ.get("BOT_TOKEN")
IG_USER = "usrhumn"
TEMP_DIR = "downloads"
COOKIE_FILE = "cookies.txt"

if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

def is_instagram_stories(url):
    return "instagram.com/stories/" in url

def is_youtube(url):
    return "youtube.com" in url or "youtu.be" in url

def get_video_info(url):
    opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'cookiefile': COOKIE_FILE, 
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        formats = []
        seen_qualities = set()
        
        for f in info.get('formats', []):
            if f.get('ext') == 'mp4' and f.get('vcodec') != 'none':
                quality = f.get('format_note', 'N/A')
                if quality not in seen_qualities and quality != 'N/A':
                    seen_qualities.add(quality)
                    formats.append({'id': f['format_id'], 'type': 'video', 'quality': quality, 'size': f.get('filesize_approx', 0) or f.get('filesize', 0)})
            
            elif f.get('ext') == 'm4a' and f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                if 'Audio' not in seen_qualities:
                    seen_qualities.add('Audio')
                    formats.append({'id': f['format_id'], 'type': 'audio', 'quality': 'Audio', 'size': f.get('filesize_approx', 0) or f.get('filesize', 0)})
                    
        return {'title': info['title'], 'duration': info.get('duration'), 'formats': formats}

def download_yt_media(url, format_id, media_type, user_download_dir):
    file_path = os.path.join(user_download_dir, '%(title)s.%(ext)s')
    if media_type == 'video':
        opts = {
            'format': f'{format_id}+bestaudio[ext=m4a]/best',
            'merge_output_format': 'mp4',
            'outtmpl': file_path,
            'quiet': True,
            'no_warnings': True,
            'cookiefile': COOKIE_FILE,
            'writethumbnail': True,
        }
    else:
        opts = {
            'format': format_id,
            'outtmpl': file_path,
            'quiet': True,
            'no_warnings': True,
            'cookiefile': COOKIE_FILE,
            'writethumbnail': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        final_file = ydl.prepare_filename(info)
        if media_type == 'audio':
            final_file = final_file.rsplit('.', 1)[0] + '.mp3'
        return final_file

# ----- دوال البوت الأساسية -----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        f" اللَّهُمَّ صَلِّ عَلَى مُحَمَّــدٍ وَآلِ مُحَمَّــد!\n\n"
        "أرسل رابط فيديو من اي منصة وبنزله لك إن شاء الله 🎬\n\n"
    )
    await update.message.reply_text(text)

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith("http"):
        return

    context.user_data["url"] = url

    if is_youtube(url):
        status_msg = await update.message.reply_text("🔍 تحليل الرابط ...")
        try:
            info = get_video_info(url)
            if not info['formats']:
                await status_msg.edit_text("❌ لم يتم العثور على صيغ متاحة.")
                return

            context.user_data['formats'] = info['formats']
            keyboard = []
            for fmt in info['formats']:
                if fmt['type'] == 'video':
                    text = f"🎥 فيديو - الجودة: {fmt['quality']}"
                else:
                    text = "🎵 صوت - MP3"
                size_mb = f" ({fmt['size']/1024/1024:.1f}MB)" if fmt['size'] else ""
                keyboard.append([InlineKeyboardButton(text + size_mb, callback_data=f"yt:{fmt['id']}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await status_msg.edit_text(
                f"✅ *{info['title']}*\n⏱ المدة: {info['duration']} ثانية\nاختار الصيغة الي تبي:",
                reply_markup=reply_markup, parse_mode='Markdown'
            )
        except Exception as e:
            await status_msg.edit_text(f"❌ خطأ في تحليل اليوتيوب: {str(e)[:200]}")
    else:
        keyboard = [[InlineKeyboardButton("🎬 فيديو", callback_data="video"), InlineKeyboardButton("🎵 صوت MP3", callback_data="audio")]]
        await update.message.reply_text("شودك؟", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    url = context.user_data.get("url")
    choice = query.data

    if not url:
        await query.edit_message_text("❌ صار خطأ، إرسل الرابط مرة لخ.")
        return

    req_id = f"{update.effective_user.id}_{query.message.message_id}"
    user_download_dir = os.path.join(TEMP_DIR, req_id)
    os.makedirs(user_download_dir, exist_ok=True)

    # معالجة طلبات يوتيوب
    if choice.startswith("yt:"):
        format_id = choice.split(":")[1]
        formats = context.user_data.get('formats', [])
        media_type = 'video'
        for f in formats:
            if f['id'] == format_id:
                media_type = f['type']
                break

        msg = await query.edit_message_text("⏳ جاري التحميل... استنى شوي.")
        try:
            file_path = download_yt_media(url, format_id, media_type, user_download_dir)
            file_size = os.path.getsize(file_path)

            if file_size > 50 * 1024 * 1024:
                await msg.edit_text("❌ حجم الملف أكبر من 50 ميقا. التلقرام ما يسمح للبوتات بإرسال ملفات أكبر من هالحجم.")
                return

            # استخراج عنوان الفيديو والصورة
            video_title = os.path.splitext(os.path.basename(file_path))[0]
            thumb_path = None
            for item in os.listdir(user_download_dir):
                if item.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                    thumb_path = os.path.join(user_download_dir, item)
                    break

            await msg.edit_text("📤 جاري الإرسال...")
            with open(file_path, "rb") as f:
                thumb_file = open(thumb_path, "rb") if thumb_path else None
                
                if media_type == 'video':
                    await query.message.reply_video(video=f, caption=video_title, thumbnail=thumb_file, read_timeout=120, write_timeout=120, supports_streaming=True)
                else:
                    await query.message.reply_audio(audio=f, caption=video_title, title=video_title, thumbnail=thumb_file, read_timeout=120, write_timeout=120)
                
                if thumb_file:
                    thumb_file.close()
            await msg.delete()
        except Exception as e:
            await msg.edit_text(f"❌ صار خطأ أثناء التحميل من اليوتيوب: {str(e)}")
        finally:
            if os.path.exists(user_download_dir):
                shutil.rmtree(user_download_dir)
        return

    # معالجة طلبات المنصات الأخرى 
    msg = await query.edit_message_text("⏳ جاري التحميل... استنى شوي.")
    try:
        if is_instagram_stories(url):
            L = instaloader.Instaloader(dirname_pattern=user_download_dir, filename_pattern="{date_utc:%Y%m%d%H%M%S}")
            session_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "session")
            if os.path.exists(session_path) and IG_USER:
                L.load_session_from_file(IG_USER, filename=session_path)

            username = url.split("/stories/")[1].split("/")[0]
            profile = instaloader.Profile.from_username(L.context, username)
            stories = L.get_stories(userids=[profile.userid])
            for story in stories:
                for item in story.get_items():
                    L.download_storyitem(item, target=user_download_dir)
        else:
            ydl_opts = {
                "outtmpl": f"{user_download_dir}/%(title)s.%(ext)s",
                "quiet": True,
                "cookiefile": COOKIE_FILE,
                "writethumbnail": True,
                "format": "bestvideo+bestaudio/best" if choice == "video" else "bestaudio/best"
            }
            if choice == "audio":
                ydl_opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}]

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

        VIDEO_EXT = (".mp4", ".mov", ".avi", ".mkv", ".webm")
        AUDIO_EXT = (".mp3", ".m4a")
        IMAGE_EXT = (".jpg", ".jpeg", ".png", ".gif", ".webp")
        ALLOWED_EXT = VIDEO_EXT + AUDIO_EXT + IMAGE_EXT

        all_files = [f for f in os.listdir(user_download_dir) if f.lower().endswith(ALLOWED_EXT)]
        all_files.sort()

        media_stems = {os.path.splitext(f)[0] for f in all_files if f.lower().endswith(VIDEO_EXT + AUDIO_EXT)}
        filtered = [f for f in all_files if not (f.lower().endswith(IMAGE_EXT) and os.path.splitext(f)[0] in media_stems)]
        files = [os.path.join(user_download_dir, f) for f in filtered]

        if not files:
            await msg.edit_text("❌ ما لقيت ملفات للتحميل.")
            return

        for i, file_path in enumerate(files):
            await msg.edit_text(f"📤 جاري الإرسال ({i+1}/{len(files)})...")
            try:
                # استخراج العنوان ليكون الوصف أسفل الفيديو/الصوت
                video_title = os.path.splitext(os.path.basename(file_path))[0]
                
                # البحث عن صورة مناسبة لتعيينها كغلاف
                thumb_path = None
                if not is_instagram_stories(url):
                    for item in all_files:
                        if item.lower().endswith(IMAGE_EXT) and os.path.splitext(item)[0] == video_title:
                            thumb_path = os.path.join(user_download_dir, item)
                            break

                with open(file_path, "rb") as f:
                    thumb_file = open(thumb_path, "rb") if thumb_path else None
                    
                    if file_path.lower().endswith(AUDIO_EXT):
                        await query.message.reply_audio(audio=f, caption=video_title, title=video_title, thumbnail=thumb_file, read_timeout=120, write_timeout=120)
                    elif file_path.lower().endswith(IMAGE_EXT):
                        await query.message.reply_photo(photo=f, caption=video_title, read_timeout=120, write_timeout=120)
                    else:
                        await query.message.reply_video(video=f, caption=video_title, thumbnail=thumb_file, read_timeout=120, write_timeout=120)
                        
                    if thumb_file:
                        thumb_file.close()
            except Exception as send_error:
                print(f"تجاهل خطأ في ملف: {send_error}")
                
        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"❌ حدث خطأ: {str(e)}")
    finally:
        if os.path.exists(user_download_dir):
            shutil.rmtree(user_download_dir)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    app.add_handler(CallbackQueryHandler(handle_choice))
    print("✅")
    app.run_polling()

if __name__ == "__main__":
    main()
