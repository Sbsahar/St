import telebot
import yt_dlp
import os
import uuid
import time

# قاموس لتخزين الروابط المرتبطة بمعرف فريد
url_store = {}

# اسم ملف تعريف الارتباط الموحد
cookies_file = 'cookies(2).txt'  # ملف تعريف الارتباط الموحد لفيسبوك وإنستغرام

def register_download_handlers(bot, is_user_admin):
    """ تسجيل الأوامر الخاصة بالتحميل وربطها بالبوت """

    @bot.message_handler(commands=['tf'])
    def handle_tf_command(message):
        chat_id = message.chat.id
        user_id = message.from_user.id

        if not is_user_admin(chat_id, user_id):
            bot.send_message(chat_id, "❌ لاتلعب التحميل فقط للمشرفين.")
            return

        bot.send_message(chat_id, "🔹 أرسـل رابـط مـن Instagram أو Facebook لتحميله.")

    @bot.message_handler(func=lambda message: message.text and ("instagram.com" in message.text or "facebook.com" in message.text))
    def handle_link(message):
        chat_id = message.chat.id
        user_id = message.from_user.id

        if not is_user_admin(chat_id, user_id):
            bot.send_message(chat_id, "❌ هذا الأمر متاح فقط للمشرفين.")
            return

        url = message.text.strip()
        if not url.startswith("http"):
            bot.send_message(chat_id, "❌ الرابط مو شغال تأكد من الرابط .")
            return

        unique_id = str(uuid.uuid4())[:8]
        url_store[unique_id] = url

        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        video_button = telebot.types.InlineKeyboardButton("▶ تحـميل فيديـو", callback_data=f"video_{unique_id}")
        audio_button = telebot.types.InlineKeyboardButton("🎧 تحـميل مقـطع صـوتي", callback_data=f"audio_{unique_id}")
        markup.add(video_button, audio_button)

        message_sent = bot.send_message(chat_id, "⤵ اخـتر نـوع التحـميل:", reply_markup=markup)
        time.sleep(30)
        bot.delete_message(chat_id, message_sent.message_id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("video_") or call.data.startswith("audio_"))
    def handle_download(call):
        chat_id = call.message.chat.id
        format_type = "video" if call.data.startswith("video_") else "audio"
        unique_id = call.data.split("_", 1)[1]

        if unique_id not in url_store:
            bot.send_message(chat_id, "❌ الرابط مالقيته أو انتهت صلاحيته.")
            return

        url = url_store.pop(unique_id)

        progress_msg = bot.send_message(chat_id, "<b>⏳ جاري التحميل، انتظر قليلاً...</b>", parse_mode="HTML")

        for i in range(1, 6):
            time.sleep(2)
            progress = "■" * i + "□" * (5 - i)
            bot.edit_message_text(f"<b>⇄ جـاري التحمـيل أنـطر شـوي...</b>\n{progress} {i * 20}%", chat_id, progress_msg.message_id, parse_mode="HTML")

        bot.edit_message_text("<b>➳ 𝑳𝒐𝒂𝒅𝒊𝒏𝒈..</b>", chat_id, progress_msg.message_id, parse_mode="HTML")

        file_path = download_media(url, format_type)
        if file_path and os.path.exists(file_path):
            with open(file_path, "rb") as media:
                caption = f"<b>تـم التحميل بواسطـة @SY_SBbot</b>\n<b>تـم التحميل مـن ↩</b><a href='{url}'>الرابط هنا</a>"
                if format_type == "video":
                    bot.send_video(chat_id, media, caption=caption, parse_mode="HTML")
                else:
                    bot.send_audio(chat_id, media, caption=caption, parse_mode="HTML")
            os.remove(file_path)
            bot.send_message(chat_id, "<b> تـم التحـميل بنجاح</b> ♡𓏧♡", parse_mode="HTML")
        else:
            bot.send_message(chat_id, "❌ حدث خطأ أثناء التحميل.")
        bot.delete_message(chat_id, progress_msg.message_id)
    
    print("✅ تم تسجيل أوامر التحميل بنجاح.")

def download_media(url, format_type):
    output_dir = "downloads"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "%(title)s.%(ext)s")
    
    ydl_opts = {
        "outtmpl": output_path,
        "format": "bestvideo+bestaudio/best" if format_type == "video" else "bestaudio",
        "merge_output_format": "mp4" if format_type == "video" else "mp3",
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}] if format_type == "audio" else [],
        "cookiefile": cookies_file,
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
        
