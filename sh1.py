import telebot
import yt_dlp
import os
import uuid

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

        bot.send_message(chat_id, "🔹\nأرسل لي الرابط مباشرة مع الأمر /")

    @bot.message_handler(func=lambda message: message.text and (message.text.startswith("/") and ("instagram.com" in message.text or "facebook.com" in message.text)))
    def handle_link(message):
        chat_id = message.chat.id
        user_id = message.from_user.id

        # التحقق من صلاحيات المشرف
        if not is_user_admin(chat_id, user_id):
            bot.send_message(chat_id, "❌ هذا الأمر متاح فقط للمشرفين.")
            return

        url = message.text.split("/", 1)[1]  # استخراج الرابط بعد "/"
        unique_id = str(uuid.uuid4())[:8]

        markup = telebot.types.InlineKeyboardMarkup()
        video_button = telebot.types.InlineKeyboardButton("📹 تحميل فيديو", callback_data=f"video_{unique_id}")
        audio_button = telebot.types.InlineKeyboardButton("🎵 تحميل مقطع صوتي", callback_data=f"audio_{unique_id}")
        markup.add(video_button, audio_button)

        bot.send_message(chat_id, "🔹 اختر نوع التحميل:", reply_markup=markup)

    print("✅ تم تسجيل أوامر التحميل بنجاح في sh1.py")
