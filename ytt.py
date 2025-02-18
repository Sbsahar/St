import os
import yt_dlp
import time
from googleapiclient.discovery import build
import telebot
from telebot import types

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
        
        for item in search_response['items']:
            video_id = item['id']['videoId']
            thumbnail_url = item['snippet']['thumbnails']['high']['url']
            video_title = item['snippet']['title']

            markup = types.InlineKeyboardMarkup()
            button_online = types.InlineKeyboardButton("أون لاين", callback_data=f'online|{video_id}')
            button_download = types.InlineKeyboardButton("تحميل MP3", callback_data=f'audio|{video_id}|mp3')
            markup.add(button_online, button_download)

            bot.send_photo(
                message.chat.id,
                thumbnail_url,
                caption=f'<b>{video_title}</b>',
                reply_markup=markup,
                parse_mode='HTML'
            )

# التعامل مع الأزرار
@bot.callback_query_handler(func=lambda call: True)
def button(call):
    data = call.data.split('|')
    
    if len(data) != 3:
        bot.send_message(call.message.chat.id, "هناك خطأ في البيانات المدخلة. يرجى المحاولة مرة أخرى.", parse_mode='HTML')
        return

    action = data[0]
    video_id = data[1]
    quality = data[2]
    
    video_url = f'https://www.youtube.com/watch?v={video_id}'

    if action == 'online':
        # تغيير الصورة المصغرة
        thumbnail_url = f'https://img.youtube.com/vi/{video_id}/hqdefault.jpg'
        bot.edit_message_media(
            media=types.InputMediaPhoto(thumbnail_url, caption=f'جاري تشغيل {video_id}'),
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
    elif action == 'audio':
        # إرسال رسالة التحميل الأولية
        loading_msg = bot.send_message(call.message.chat.id, '<b>جاري التحميل... 🔄</b>', parse_mode='HTML')

        # تحميل الوسائط
        download_media(call, action, video_url, quality, loading_msg)

# عرض خيارات التحميل
def show_download_options(message, url):
    markup = types.InlineKeyboardMarkup()
    button = types.InlineKeyboardButton("تحميل MP3", callback_data=f'audio|{url}|mp3')
    markup.add(button)

    bot.send_message(message.chat.id, '<b>اختر نوع التحميل:</b>', reply_markup=markup, parse_mode='HTML')

# تحميل الصوت
def download_media(call, download_type, url, quality, loading_msg):
    cookies_file_path = 'cookies.txt'
    cookies = load_cookies_from_file(cookies_file_path)
    
    if not cookies:
        bot.edit_message_text('<b>فشل تحميل الكوكيز! يرجى التأكد من الملف.</b>', chat_id=call.message.chat.id, message_id=loading_msg.message_id, parse_mode='HTML')
        return

    ydl_opts = {
        'outtmpl': '%(title)s.%(ext)s',
        'format': 'bestaudio/best',
        'timeout': 999999999,
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}] if download_type == 'audio' else [],
        'retries': 3,
        'cookiefile': cookies_file_path,
        'cookies': cookies,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            
            if download_type == 'audio':
                file_path = file_path.replace('.webm', '.mp3')

            # رفع الملف الصوتي
            with open(file_path, 'rb') as file:
                bot.send_audio(call.message.chat.id, file, caption=f"تم التحميل بواسطة {BOT_USERNAME} ⋙")  

            os.remove(file_path)

            # حذف رسالة "تم التحميل 🎶 جاري الرفع..." بعد الرفع
            bot.delete_message(call.message.chat.id, loading_msg.message_id)

            # حذف نتائج البحث بعد التحميل
            bot.delete_message(call.message.chat.id, call.message.message_id)

    except Exception as e:
        bot.edit_message_text(f'<b>خطأ أثناء التحميل:</b> {e}', chat_id=call.message.chat.id, message_id=loading_msg.message_id, parse_mode='HTML')

# تحميل الكوكيز من ملف
def load_cookies_from_file(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            cookies = file.readlines()
            cookies_dict = {}
            for line in cookies:
                if line.startswith('#') or line.strip() == '':
                    continue
                parts = line.strip().split('\t')
                if len(parts) > 6:
                    cookie_name = parts[5].strip()
                    cookie_value = parts[6].strip()
                    cookies_dict[cookie_name] = cookie_value
            return cookies_dict
    return None

# تشغيل البوت
if __name__ == '__main__':
    bot.polling(none_stop=True)
