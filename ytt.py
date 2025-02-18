import os
import yt_dlp
from googleapiclient.discovery import build
import telebot
from telebot import types

# إعدادات البوت
TOKEN = '7327783438:AAGmnM5fE1aKO-bEYNfb1dqUHOfLryH3a6g'
CHANNEL_ID = '@SYR_SB'
YOUTUBE_API_KEY = 'AIzaSyBG81yezyxy-SE4cd_-JCK55gEzHkPV9aw'

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
            parse_mode='HTML'  # استخدم HTML لتنسيق النصوص
        )
        return
    bot.send_message(
        message.chat.id,
        'مرحبًا! استخدم /d للبحث أو التحميل من يوتيوب.',
        parse_mode='HTML'  # استخدم HTML لتنسيق النصوص
    )

# التعامل مع الرسائل الواردة
@bot.message_handler(func=lambda message: message.text.startswith('/d '))
def handle_message(message):
    query = message.text[3:].strip()
    if query.startswith('http'):
        show_download_options(message, query)
    else:
        search_response = youtube.search().list(
            q=query, part='snippet', maxResults=1, type='video'
        ).execute()
        
        item = search_response['items'][0]
        video_id = item['id']['videoId']
        thumbnail_url = item['snippet']['thumbnails']['high']['url']
        video_title = item['snippet']['title']

        # الأزرار مع الأسماء واضحة
        markup = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton("تحميل MP3", callback_data=f'audio|{video_id}|mp3')
        markup.add(button)

        bot.send_photo(
            message.chat.id,
            thumbnail_url,
            caption=f'<b>{video_title}</b>',
            reply_markup=markup,
            parse_mode='HTML'  # استخدم HTML لتنسيق النصوص
        )

# التعامل مع الأزرار
@bot.callback_query_handler(func=lambda call: True)
def button(call):
    data = call.data.split('|')
    
    # تحقق من وجود العناصر المطلوبة في الـ data
    if len(data) != 3:
        bot.send_message(call.message.chat.id, "هناك خطأ في البيانات المدخلة. يرجى المحاولة مرة أخرى.", parse_mode='HTML')
        return

    download_type = data[0]  # 'audio'
    video_id = data[1]  # ID الفيديو
    quality = data[2]  # الصيغة (مثل mp3)
    
    video_url = f'https://www.youtube.com/watch?v={video_id}'
    
    # إرسال رسالة مبدئية تفيد بأنه جاري التحميل
    loading_msg = bot.send_message(call.message.chat.id, '<b>جاري التحميل..🔄</b>', parse_mode='HTML')

    # تحميل الوسائط بناءً على الاختيار
    download_media(call, download_type, video_url, quality, loading_msg)

# عرض خيارات التحميل
def show_download_options(message, url):
    markup = types.InlineKeyboardMarkup()
    button = types.InlineKeyboardButton("تحميل MP3", callback_data=f'audio|{url}|mp3')
    markup.add(button)

    bot.send_message(message.chat.id, '<b>اختر نوع التحميل:</b>', reply_markup=markup, parse_mode='HTML')

# تحميل الصوت
def download_media(call, download_type, url, quality, loading_msg):
    # تحميل الكوكيز من الملف النصي
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
        'cookiefile': cookies_file_path,  # استخدام الكوكيز
        'cookies': cookies,  # إضافتها مباشرة في الخيارات
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            
            # إذا كان التحميل صوتي، قم بتغيير الصيغة إلى mp3
            if download_type == 'audio':
                file_path = file_path.replace('.webm', '.mp3')

            # تحديث الرسالة: تم التحميل
            bot.edit_message_text('<b>تم تحميل الصوت 🎶جاري الرفع</b>', chat_id=call.message.chat.id, message_id=loading_msg.message_id, parse_mode='HTML')

            with open(file_path, 'rb') as file:
                # إرسال الملف الصوتي
                bot.send_audio(call.message.chat.id, file)  
                
            os.remove(file_path)  # حذف الملف بعد إرساله

            # تحديث الرسالة: تم رفع الملف
            bot.edit_message_text('<b>تم رفع الملف بنجاح🎧✅</b>', chat_id=call.message.chat.id, message_id=loading_msg.message_id, parse_mode='HTML')
    except Exception as e:
        bot.edit_message_text(f'<b>خطأ أثناء التحميل:</b> {e}', chat_id=call.message.chat.id, message_id=loading_msg.message_id, parse_mode='HTML')

# دالة لتحميل الكوكيز من ملف TXT
def load_cookies_from_file(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            cookies = file.readlines()
            return {line.split('=')[0].strip(): line.split('=')[1].strip() for line in cookies if '=' in line}
    return None

# تشغيل البوت
if __name__ == '__main__':
    bot.polling(none_stop=True)
