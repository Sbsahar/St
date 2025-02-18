import os
import yt_dlp
import time
import telebot

# تعريف دالة تحميل الصوت
def download_audio(bot: telebot.TeleBot, chat_id, video_url, message):
    loading_msg = bot.send_message(chat_id, '<b>جاري التحميل... 🔄</b>', parse_mode='HTML')

    progress_stages = [
        "█▒▒▒▒▒▒▒▒▒10%", "██▒▒▒▒▒▒▒▒20%", "███▒▒▒▒▒▒▒30%",
        "████▒▒▒▒▒▒40%", "█████▒▒▒▒▒50%", "████████▒▒80%",
        "██████████100%", "تم التحميل 🎶 جاري الرفع..."
    ]

    for stage in progress_stages:
        time.sleep(1)
        bot.edit_message_text(f"<b>{stage}</b>", chat_id=chat_id, message_id=loading_msg.message_id, parse_mode='HTML')

    ydl_opts = {
        'outtmpl': '%(title)s.%(ext)s',
        'format': 'bestaudio/best',
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}],
        'retries': 3,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            file_path = ydl.prepare_filename(info).replace('.webm', '.mp3')

        with open(file_path, 'rb') as file:
            bot.send_audio(chat_id, file, caption="🎵 تم التحميل بنجاح!")

        os.remove(file_path)
        time.sleep(2)
        bot.delete_message(chat_id, loading_msg.message_id)

    except Exception as e:
        bot.send_message(chat_id, f'<b>حدث خطأ أثناء التحميل:</b> {str(e)}', parse_mode='HTML')
