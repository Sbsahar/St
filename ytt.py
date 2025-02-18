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

# قاموس لتتبع الرسائل المرسلة لكل مستخدم
user_sessions = {}

def check_subscription(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ('member', 'administrator', 'creator')
    except Exception:
        return False

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

def create_search_results_markup(video_id):
    markup = types.InlineKeyboardMarkup()
    online_btn = types.InlineKeyboardButton("▶️ اون لاين", callback_data=f'preview|{video_id}')
    download_btn = types.InlineKeyboardButton("⬇️ تحميل MP3", callback_data=f'download|{video_id}')
    markup.row(online_btn, download_btn)
    return markup

@bot.message_handler(func=lambda message: message.text.startswith('/d '))
def handle_message(message):
    if not check_subscription(message.from_user.id):
        bot.send_message(message.chat.id, f'يجب الاشتراك في القناة أولًا: {CHANNEL_ID}', parse_mode='HTML')
        return

    query = message.text[3:].strip()
    
    if query.startswith('http'):
        show_download_options(message, query)
        return

    search_response = youtube.search().list(
        q=query,
        part='snippet',
        maxResults=5,
        type='video'
    ).execute()

    items = search_response.get('items', [])
    if not items:
        bot.send_message(message.chat.id, "⚠️ لم يتم العثور على نتائج!")
        return

    user_sessions[message.chat.id] = []
    progress_msg = bot.send_message(message.chat.id, "🔍 جاري البحث عن النتائج...")
    
    try:
        for item in items:
            video_id = item['id']['videoId']
            thumbnail = item['snippet']['thumbnails']['high']['url']
            title = item['snippet']['title']
            
            markup = create_search_results_markup(video_id)
            sent_msg = bot.send_photo(
                message.chat.id,
                thumbnail,
                caption=f"<b>{title}</b>",
                reply_markup=markup,
                parse_mode='HTML'
            )
            user_sessions[message.chat.id].append(sent_msg.message_id)
            
        bot.delete_message(message.chat.id, progress_msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"حدث خطأ: {e}", message.chat.id, progress_msg.message_id)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    data = call.data.split('|')
    
    if data[0] == 'preview':
        video_id = data[1]
        item = youtube.videos().list(part='snippet', id=video_id).execute()['items'][0]
        thumbnail = item['snippet']['thumbnails']['maxres']['url']
        title = item['snippet']['title']
        
        bot.edit_message_media(
            types.InputMediaPhoto(thumbnail),
            chat_id=chat_id,
            message_id=call.message.message_id
        )
        bot.edit_message_caption(
            chat_id=chat_id,
            message_id=call.message.message_id,
            caption=f"<b>▶️ {title}</b>",
            reply_markup=create_search_results_markup(video_id),
            parse_mode='HTML'
        )
        
    elif data[0] == 'download':
        video_id = data[1]
        url = f'https://www.youtube.com/watch?v={video_id}'
        
        loading_msg = bot.send_message(chat_id, "<b>⏳ جاري التحميل...</b>", parse_mode='HTML')
        
        # محاكاة شريط التقدم
        progress = [
            "█▒▒▒▒▒▒▒▒▒ 10%",
            "███▒▒▒▒▒▒▒ 30%",
            "██████▒▒▒▒ 60%",
            "██████████ 100%",
            "✅ تم التحميل! جاري الرفع..."
        ]
        
        for stage in progress:
            time.sleep(1.5)
            bot.edit_message_text(
                f"<b>{stage}</b>",
                chat_id=chat_id,
                message_id=loading_msg.message_id,
                parse_mode='HTML'
            )
            
        try:
            file_path = download_audio(url)
            with open(file_path, 'rb') as audio_file:
                bot.send_audio(chat_id, audio_file, caption=f"🎧 تم التحميل بواسطة {BOT_USERNAME}")
            os.remove(file_path)
            
            # حذف جميع رسائل البحث والتحميل
            if chat_id in user_sessions:
                for msg_id in user_sessions[chat_id]:
                    try:
                        bot.delete_message(chat_id, msg_id)
                    except:
                        pass
                del user_sessions[chat_id]
            bot.delete_message(chat_id, loading_msg.message_id)
            
        except Exception as e:
            bot.edit_message_text(f"❌ خطأ في التحميل: {e}", chat_id, loading_msg.message_id)

def download_audio(url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': '%(title)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
        }],
        'cookiefile': 'cookies.txt'
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info).replace('.webm', '.mp3')

def show_download_options(message, url):
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("⬇️ تحميل MP3", callback_data=f'direct|{url}')
    markup.add(btn)
    bot.send_message(message.chat.id, "⚙️ اختر نوع التحميل:", reply_markup=markup)

if __name__ == '__main__':
    bot.polling(none_stop=True)
