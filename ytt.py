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

# تخزين بيانات البحث لكل مستخدم
user_search_data = {}

@bot.message_handler(commands=['start'])
def start(message):
    if not check_subscription(message.from_user.id):
        bot.send_message(message.chat.id, f'يجب الاشتراك في القناة أولًا: {CHANNEL_ID}', parse_mode='HTML')
        return
    bot.send_message(message.chat.id, 'مرحبًا! استخدم /d للبحث أو التحميل من يوتيوب.', parse_mode='HTML')

# البحث عن فيديوهات يوتيوب
@bot.message_handler(func=lambda message: message.text.startswith('/d '))
def handle_message(message):
    query = message.text[3:].strip()
    search_response = youtube.search().list(
        q=query,
        part='snippet',
        maxResults=5,
        type='video'
    ).execute()

    results = []
    for item in search_response['items']:
        video_id = item['id']['videoId']
        title = item['snippet']['title']
        thumbnail = item['snippet']['thumbnails']['high']['url']
        results.append((video_id, title, thumbnail))

    first_video = results[0]
    thumbnail_url = first_video[2]

    # إنشاء الأزرار
    markup = types.InlineKeyboardMarkup()
    for video_id, title, _ in results:
        btn_video = types.InlineKeyboardButton(f"🎥 {title[:25]}", callback_data=f"preview|{video_id}")
        btn_download = types.InlineKeyboardButton("⬇️", callback_data=f"download|{video_id}")
        markup.row(btn_video, btn_download)

    # إرسال الرسالة مع الصورة المصغرة
    msg = bot.send_photo(
        message.chat.id,
        thumbnail_url,
        caption=f"<b>نتائج البحث عن:</b> {query}\n\nاختر فيديو لمشاهدته أو تحميله",
        reply_markup=markup,
        parse_mode='HTML'
    )

    # تخزين بيانات البحث
    user_search_data[message.chat.id] = {"message_id": msg.message_id, "results": results, "query": query}

@bot.callback_query_handler(func=lambda call: True)
def button(call):
    data = call.data.split('|')
    chat_id = call.message.chat.id

    if data[0] == "preview":
        video_id = data[1]
        if chat_id not in user_search_data:
            return

        results = user_search_data[chat_id]["results"]
        query = user_search_data[chat_id]["query"]

        for vid, title, thumb in results:
            if vid == video_id:
                new_thumbnail = thumb
                break

        # تعديل الرسالة بدون حذف المحتوى
        markup = types.InlineKeyboardMarkup()
        for vid, title, _ in results:
            btn_video = types.InlineKeyboardButton(f"🎥 {title[:25]}", callback_data=f"preview|{vid}")
            btn_download = types.InlineKeyboardButton("⬇️", callback_data=f"download|{vid}")
            markup.row(btn_video, btn_download)

        bot.edit_message_media(
            media=types.InputMediaPhoto(new_thumbnail, caption=f"<b>نتائج البحث عن:</b> {query}\n\nاختر فيديو لمشاهدته أو تحميله"),
            chat_id=chat_id,
            message_id=user_search_data[chat_id]["message_id"],
            reply_markup=markup
        )

    elif data[0] == "download":
        video_id = data[1]
        loading_msg = bot.send_message(chat_id, '<b>جاري التحميل... 🔄</b>', parse_mode='HTML')

        progress_stages = [
            "█▒▒▒▒▒▒▒▒▒10%", "██▒▒▒▒▒▒▒▒20%", "███▒▒▒▒▒▒▒30%",
            "████▒▒▒▒▒▒40%", "█████▒▒▒▒▒50%", "████████▒▒80%",
            "██████████100%", "تم التحميل 🎶 جاري الرفع..."
        ]

        for stage in progress_stages:
            time.sleep(1)
            bot.edit_message_text(f"<b>{stage}</b>", chat_id=chat_id, message_id=loading_msg.message_id, parse_mode='HTML')

        # استدعاء الدالة الخاصة بالتحميل الصوت فقط
        download_media(call, 'audio', video_id, 'bestaudio', loading_msg)

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

            # حذف رسالة الأزرار بعد 2 ثانية من إرسال الملف الصوتي
            time.sleep(2)
            bot.delete_message(call.message.chat.id, loading_msg.message_id)

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
