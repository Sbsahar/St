import os
import yt_dlp
import time
import threading
from googleapiclient.discovery import build
from telebot import types

class YoutubeModule:
    def __init__(self, bot, youtube_api_key, bot_username):
        self.bot = bot
        self.YOUTUBE_API_KEY = youtube_api_key
        self.BOT_USERNAME = bot_username
        self.youtube = build('youtube', 'v3', developerKey=self.YOUTUBE_API_KEY)
        self.user_search_data = {}

    def setup_handlers(self):
        @self.bot.message_handler(func=lambda message: message.text.startswith('/ty '))
        def handle_message(message):
            query = message.text[3:].strip()
            search_response = self.youtube.search().list(
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

            markup = types.InlineKeyboardMarkup()
            for video_id, title, _ in results:
                btn_video = types.InlineKeyboardButton(
                    f"📹 {title[:20]}",
                    callback_data=f"youtube_preview|{video_id}"
                )
                btn_audio = types.InlineKeyboardButton(
                    "🎵 MP3",
                    callback_data=f"youtube_download_audio|{video_id}"
                )
                btn_video_download = types.InlineKeyboardButton(
                    "📹 MP4",
                    callback_data=f"youtube_download_video|{video_id}"
                )
                markup.row(btn_video)
                markup.row(btn_audio, btn_video_download)

            msg = self.bot.send_photo(
                message.chat.id,
                thumbnail_url,
                caption=f"<i>نتائج البحث عن:</i> {query}\n\nاختر فيديو لتحميله أو مشاهدته",
                reply_markup=markup,
                parse_mode='HTML'
            )

            def delete_message():
                try:
                    self.bot.delete_message(message.chat.id, msg.message_id)
                except Exception:
                    pass
                if message.chat.id in self.user_search_data:
                    del self.user_search_data[message.chat.id]

            timer = threading.Timer(60, delete_message)
            timer.start()

            self.user_search_data[message.chat.id] = {
                "message_id": msg.message_id,
                "results": results,
                "query": query,
                "delete_timer": timer
            }

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('youtube_'))
        def youtube_buttons(call):
            data = call.data.split('|')
            chat_id = call.message.chat.id

            if chat_id in self.user_search_data:
                timer = self.user_search_data[chat_id].get("delete_timer")
                if timer:
                    timer.cancel()
                    self.user_search_data[chat_id].pop("delete_timer", None)

            if data[0] == "youtube_download_audio":
                self.process_download(call, "audio", data[1])
            elif data[0] == "youtube_download_video":
                self.process_download(call, "video", data[1])

    def process_download(self, call, download_type, video_id):
        chat_id = call.message.chat.id
        loading_msg = self.bot.send_message(chat_id, '<i>جاري التحميل... 🔄</i>', parse_mode='HTML')

        progress_stages = [
            "█▒▒▒▒▒▒▒▒▒10%", "██▒▒▒▒▒▒▒▒20%", "███▒▒▒▒▒▒▒30%",
            "████▒▒▒▒▒▒40%", "█████▒▒▒▒▒▒50%", "████████▒▒80%",
            "██████████100%", "تم التحميل 🎶 جاري الرفع..."
        ]

        for stage in progress_stages:
            time.sleep(1)
            self.bot.edit_message_text(f"<i>{stage}</i>", chat_id=chat_id, message_id=loading_msg.message_id, parse_mode='HTML')

        self.download_media(call, download_type, video_id, loading_msg)

    def download_media(self, call, download_type, url, loading_msg):
        ydl_opts = {
            'outtmpl': '%(title)s.%(ext)s',
            'format': 'bestaudio/best' if download_type == 'audio' else 'bestvideo+bestaudio',
            'timeout': 999999999,
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}] if download_type == 'audio' else [],
            'retries': 3
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = ydl.prepare_filename(info)

                if download_type == 'audio':
                    file_path = file_path.replace('.webm', '.mp3')

                with open(file_path, 'rb') as file:
                    if download_type == 'audio':
                        self.bot.send_audio(call.message.chat.id, file, caption=f"تم التحميل بواسطة {self.BOT_USERNAME} ⋙")
                    else:
                        self.bot.send_video(call.message.chat.id, file, caption=f"تم التحميل بواسطة {self.BOT_USERNAME} ⋙")
                os.remove(file_path)
                time.sleep(2)
                self.bot.delete_message(call.message.chat.id, loading_msg.message_id)
        except Exception as e:
            self.bot.edit_message_text(f'<i>خطأ أثناء التحميل:</i> {e}', chat_id=call.message.chat.id, message_id=loading_msg.message_id, parse_mode='HTML')
                            
