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

    # أول نتيجة لعرضها كصورة مصغرة
    first_video = results[0]
    thumbnail_url = first_video[2]

    # إنشاء الأزرار
    markup = types.InlineKeyboardMarkup()
    for i, (video_id, title, _) in enumerate(results):
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

    # تخزين بيانات البحث للمستخدم
    user_search_data[message.chat.id] = {"message_id": msg.message_id, "results": results}

# تخزين بيانات البحث لكل مستخدم
user_search_data = {}

# التعامل مع الأزرار
@bot.callback_query_handler(func=lambda call: True)
def button(call):
    data = call.data.split('|')
    
    if data[0] == "preview":
        video_id = data[1]
        chat_id = call.message.chat.id
        
        # الحصول على الصورة المصغرة الجديدة
        for vid, title, thumb in user_search_data[chat_id]["results"]:
            if vid == video_id:
                new_thumbnail = thumb
                break
        
        # تعديل الرسالة الحالية بدلاً من إرسال واحدة جديدة
        bot.edit_message_media(
            media=types.InputMediaPhoto(new_thumbnail, caption=call.message.caption),
            chat_id=chat_id,
            message_id=user_search_data[chat_id]["message_id"]
        )

    elif data[0] == "download":
        video_id = data[1]
        chat_id = call.message.chat.id
        
        # إرسال رسالة "جاري التحميل..."
        loading_msg = bot.send_message(chat_id, '<b>جاري التحميل... 🔄</b>', parse_mode='HTML')

        # شريط تقدم التحميل
        progress_stages = [
            "█▒▒▒▒▒▒▒▒▒10%", "██▒▒▒▒▒▒▒▒20%", "███▒▒▒▒▒▒▒30%",
            "████▒▒▒▒▒▒40%", "█████▒▒▒▒▒50%", "████████▒▒80%",
            "██████████100%", "تم التحميل 🎶 جاري الرفع..."
        ]

        for stage in progress_stages:
            time.sleep(1)
            bot.edit_message_text(f"<b>{stage}</b>", chat_id=chat_id, message_id=loading_msg.message_id, parse_mode='HTML')

        # تحميل الفيديو بصيغة MP3
        download_audio(video_id, chat_id, loading_msg.message_id)

# تحميل الصوت
def download_audio(video_id, chat_id, loading_message_id):
    url = f'https://www.youtube.com/watch?v={video_id}'
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': '%(title)s.%(ext)s',
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}]
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info).replace('.webm', '.mp3')

        # إرسال الملف الصوتي
        with open(file_path, 'rb') as file:
            bot.send_audio(chat_id, file, caption=f"تم التحميل بواسطة {BOT_USERNAME} ✅")

        # حذف الملف بعد الإرسال
        os.remove(file_path)

        # حذف رسالة البحث والتحميل
        if chat_id in user_search_data:
            bot.delete_message(chat_id, user_search_data[chat_id]["message_id"])
            del user_search_data[chat_id]
        
        bot.delete_message(chat_id, loading_message_id)

    except Exception as e:
        bot.edit_message_text(f'<b>خطأ أثناء التحميل:</b> {e}', chat_id=chat_id, message_id=loading_message_id, parse_mode='HTML')

# تشغيل البوت
if __name__ == '__main__':
    bot.polling(none_stop=True)
