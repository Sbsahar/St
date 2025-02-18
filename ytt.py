import os
import yt_dlp
from googleapiclient.discovery import build
import telebot
from telebot import types
import time

# إعدادات البوت
TOKEN = '7327783438:AAGmnM5fE1aKO-bEYNfb1dqUHOfLryH3a6g'
CHANNEL_ID = '@SYR_SB'
YOUTUBE_API_KEY = 'AIzaSyBG81yezyxy-SE4cd_-JCK55gEzHkPV9aw'
BOT_USERNAME = '@SY_SBbot'

youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
bot = telebot.TeleBot(TOKEN)

# التحقق من الاشتراك في القناة
def check_subscription(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ('member', 'administrator', 'creator')
    except Exception:
        return False

# دالة start لبدء التفاعل مع البوت
@bot.message_handler(commands=['start'])
def start(message):
    if not check_subscription(message.from_user.id):
        bot.send_message(
            message.chat.id,
            f'يجب الاشتراك في القناة أولًا: {CHANNEL_ID}',
            parse_mode='HTML'
        )
        return
    bot.send_message(
        message.chat.id,
        'مرحبًا! استخدم /d للبحث أو التحميل من يوتيوب.',
        parse_mode='HTML'
    )

# التعامل مع الرسائل الواردة
@bot.message_handler(func=lambda message: message.text.startswith('/d '))
def handle_message(message):
    query = message.text[3:].strip()
    if query.startswith('http'):
        show_download_options(message, query)
    else:
        search_response = youtube.search().list(
            q=query, part='snippet', maxResults=5, type='video'
        ).execute()
        
        search_results = []
        for item in search_response['items']:
            video_id = item['id']['videoId']
            thumbnail_url = item['snippet']['thumbnails']['high']['url']
            video_title = item['snippet']['title']
            search_results.append((video_id, thumbnail_url, video_title))
        
        markup = types.InlineKeyboardMarkup()
        # إضافة الأزرار لأربعة نتائج
        for idx, (video_id, thumbnail_url, video_title) in enumerate(search_results):
            button_online = types.InlineKeyboardButton(f"أون لاين {video_title}", callback_data=f'change_thumbnail|{idx}')
            button_download = types.InlineKeyboardButton("تحميل MP3", callback_data=f'download|{video_id}|mp3')

            markup.add(button_online, button_download)

        # حفظ نتائج البحث في الذاكرة (سنستخدم dictionary لتخزين النتائج)
        bot_data = {'results': search_results, 'message_id': message.message_id}
        bot.set_chat_data(message.chat.id, bot_data)

        # إرسال الرسالة الأولى
        bot.send_message(
            message.chat.id,
            "اختر من بين هذه النتائج:",
            reply_markup=markup,
        )

# التعامل مع الأزرار
@bot.callback_query_handler(func=lambda call: True)
def button(call):
    data = call.data.split('|')

    if data[0] == 'change_thumbnail':
        idx = int(data[1])
        bot_data = bot.get_chat_data(call.message.chat.id)
        search_results = bot_data['results']
        video_id, thumbnail_url, video_title = search_results[idx]
        
        # تحديث الصورة المصغرة
        bot.edit_message_media(
            media=types.InputMediaPhoto(thumbnail_url, caption=f'<b>{video_title}</b>', parse_mode='HTML'),
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
        )

        # إضافة رسالة منبثقة لتأكيد التغيير
        bot.answer_callback_query(call.id, text="تم تغيير الصورة المصغرة!")

    elif data[0] == 'download':
        video_id = data[1]
        video_url = f'https://www.youtube.com/watch?v={video_id}'
        
        # إرسال رسالة التحميل الأولية
        loading_msg = bot.send_message(call.message.chat.id, '<b>جاري التحميل... 🔄</b>', parse_mode='HTML')

        # تحميل الوسائط
        download_media(call, 'audio', video_url, 'mp3', loading_msg)

# تحميل الصوت
def download_media(call, download_type, url, quality, loading_msg):
    ydl_opts = {
        'outtmpl': '%(title)s.%(ext)s',
        'format': 'bestaudio/best',
        'timeout': 999999999,
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}] if download_type == 'audio' else [],
        'retries': 3,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            
            if download_type == 'audio':
                file_path = file_path.replace('.webm', '.mp3')

            # إرسال نسبة التحميل
            total_size = os.path.getsize(file_path)
            bot.edit_message_text(f"<b>تحميل: {0}%...</b>", chat_id=call.message.chat.id, message_id=loading_msg.message_id, parse_mode="HTML")

            with open(file_path, 'rb') as file:
                bot.send_audio(call.message.chat.id, file, caption=f"تم التحميل بواسطة {BOT_USERNAME} ⋙")

            os.remove(file_path)

            # حذف رسالة التحميل بعد الرفع
            bot.delete_message(call.message.chat.id, loading_msg.message_id)

            # حذف نتائج البحث بعد التحميل
            bot.delete_message(call.message.chat.id, call.message.message_id)

    except Exception as e:
        bot.edit_message_text(f'<b>خطأ أثناء التحميل:</b> {e}', chat_id=call.message.chat.id, message_id=loading_msg.message_id, parse_mode='HTML')

# تشغيل البوت
if __name__ == '__main__':
    bot.polling(none_stop=True)
