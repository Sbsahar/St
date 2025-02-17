import telebot
import yt_dlp
import os
import uuid

# قاموس لتخزين الروابط المرتبطة بمعرف فريد
url_store = {}

def register_download_handlers(bot, is_user_admin):
    """ تسجيل الأوامر الخاصة بالتحميل وربطها بالبوت """

    @bot.message_handler(commands=['tf'])
    def handle_tf_command(message):
        chat_id = message.chat.id
        user_id = message.from_user.id

        # التحقق مما إذا كان المستخدم مشرفًا
        if not is_user_admin(chat_id, user_id):
            bot.send_message(chat_id, "❌ هذا الأمر متاح فقط للمشرفين.")
            return

        bot.send_message(chat_id, "🔹 أهلاً بك في بوت تحميل الفيديو والصوت!\nأرسل الرابط مباشرة.")

    @bot.message_handler(func=lambda message: message.text and ("instagram.com" in message.text or "facebook.com" in message.text))
    def handle_link(message):
        chat_id = message.chat.id
        user_id = message.from_user.id

        # التحقق من صلاحيات المشرف
        if not is_user_admin(chat_id, user_id):
            bot.send_message(chat_id, "❌ هذا الأمر متاح فقط للمشرفين.")
            return

        url = message.text.strip()  # استخراج الرابط بالكامل
        unique_id = str(uuid.uuid4())[:8]  # إنشاء معرف فريد
        url_store[unique_id] = url  # تخزين الرابط

        markup = telebot.types.InlineKeyboardMarkup()
        video_button = telebot.types.InlineKeyboardButton("📹 تحميل فيديو", callback_data=f"video_{unique_id}")
        audio_button = telebot.types.InlineKeyboardButton("🎵 تحميل مقطع صوتي", callback_data=f"audio_{unique_id}")
        markup.add(video_button, audio_button)

        bot.send_message(chat_id, "🔹 اختر نوع التحميل:", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("video_") or call.data.startswith("audio_"))
    def handle_download(call):
        chat_id = call.message.chat.id
        format_type = "video" if call.data.startswith("video_") else "audio"
        unique_id = call.data.split("_", 1)[1]

        if unique_id not in url_store:
            bot.send_message(chat_id, "❌ الرابط غير متاح أو انتهت صلاحيته.")
            return

        url = url_store.pop(unique_id)  # استرجاع الرابط وحذفه من التخزين
        bot.send_message(chat_id, "⏳ جاري التحميل، انتظر قليلاً...")

        file_path = download_media(url, format_type)
        if file_path and os.path.exists(file_path):
            with open(file_path, "rb") as media:
                if format_type == "video":
                    bot.send_video(chat_id, media)
                else:
                    bot.send_audio(chat_id, media)

            os.remove(file_path)  # حذف الملف بعد الإرسال
            bot.send_message(chat_id, "✅ تم التحميل بنجاح!")
        else:
            bot.send_message(chat_id, "❌ حدث خطأ أثناء التحميل.")

    print("✅ تم تسجيل أوامر التحميل بنجاح في sh1.py")

# دالة تحميل الفيديو أو الصوت
def download_media(url, format_type):
    output_dir = "downloads"
    os.makedirs(output_dir, exist_ok=True)  # التأكد من وجود المجلد

    output_path = os.path.join(output_dir, "%(title)s.%(ext)s")
    
    ydl_opts = {
        "outtmpl": output_path,
        "format": "bestaudio/best" if format_type == "audio" else "bestvideo[height<=480]+bestaudio/best[height<=480]",
        "merge_output_format": "mp4" if format_type == "video" else "mp3",
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}] if format_type == "audio" else []
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_name = ydl.prepare_filename(info)
            if format_type == "audio":
                file_name = file_name.rsplit(".", 1)[0] + ".mp3"
            return file_name
    except Exception as e:
        print(f"Error: {e}")
        return None
