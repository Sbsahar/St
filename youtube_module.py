import os
import yt_dlp
import time
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
        # معالجة رسائل البحث عن فيديوهات
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
                btn_video = types.InlineKeyboardButton(f"🎶 {title[:25]}", callback_data=f"youtube_preview|{video_id}")
                btn_download = types.InlineKeyboardButton("MP3🎵", callback_data=f"youtube_download|{video_id}")
                markup.row(btn_video, btn_download)

            msg = self.bot.send_photo(
                message.chat.id,
                thumbnail_url,
                caption=f"<i>نتائج البحث عن:</i> {query}\n\nاختر فيديو لتحميله أو مشاهدته",
                reply_markup=markup,
                parse_mode='HTML'
            )

            self.user_search_data[message.chat.id] = {"message_id": msg.message_id, "results": results, "query": query}

        # معالجة الأزرار الخاصة بالفيديوهات
        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('youtube_'))
        def youtube_buttons(call):
            data = call.data.split('|')
            chat_id = call.message.chat.id

            if data[0] == "youtube_preview":
                video_id = data[1]
                if chat_id not in self.user_search_data:
                    return

                results = self.user_search_data[chat_id]["results"]
                query = self.user_search_data[chat_id]["query"]

                for vid, title, thumb in results:
                    if vid == video_id:
                        new_thumbnail = thumb
                        break

                markup = types.InlineKeyboardMarkup()
                for vid, title, _ in results:
                    btn_video = types.InlineKeyboardButton(f"MP3🎵 {title[:25]}", callback_data=f"youtube_preview|{vid}")
                    btn_download = types.InlineKeyboardButton("🎶⬇️", callback_data=f"youtube_download|{vid}")
                    markup.row(btn_video, btn_download)

                self.bot.edit_message_media(
                    media=types.InputMediaPhoto(new_thumbnail, caption=f"<i>نتائج البحث عن:</i> {query}\n\nاختر فيديو لمشاهدته أو تحميله"),
                    chat_id=chat_id,
                    message_id=self.user_search_data[chat_id]["message_id"],
                    reply_markup=markup
                )

            elif data[0] == "youtube_download":
                video_id = data[1]
                loading_msg = self.bot.send_message(chat_id, '<i>جاري التحميل... 🔄</i>', parse_mode='HTML')

                progress_stages = [
                    "█▒▒▒▒▒▒▒▒▒10%", "██▒▒▒▒▒▒▒▒20%", "███▒▒▒▒▒▒▒30%",
                    "████▒▒▒▒▒▒40%", "█████▒▒▒▒▒▒50%", "████████▒▒80%",
                    "██████████100%", "تم التحميل 🎶 جاري الرفع..."
                ]

                for stage in progress_stages:
                    time.sleep(1)
                    self.bot.edit_message_text(f"<i>{stage}</i>", chat_id=chat_id, message_id=loading_msg.message_id, parse_mode='HTML')

                self.download_media(call, 'audio', video_id, 'bestaudio', loading_msg)

    def download_media(self, call, download_type, url, quality, loading_msg):
        cookies_file_path = 'cookies.txt'
        cookies = self.load_cookies_from_file(cookies_file_path)

        if not cookies:
            self.bot.edit_message_text('<i>فشل تحميل الكوكيز! يرجى التأكد من الملف.</i>', chat_id=call.message.chat.id, message_id=loading_msg.message_id, parse_mode='HTML')
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

                with open(file_path, 'rb') as file:
                    self.bot.send_audio(call.message.chat.id, file, caption=f"تم التحميل بواسطة {self.BOT_USERNAME} ⋙")

                os.remove(file_path)

                time.sleep(2)
                self.bot.delete_message(call.message.chat.id, loading_msg.message_id)

                time.sleep(5)
                try:
                    self.bot.delete_message(call.message.chat.id, call.message.message_id)
                except Exception:
                    pass

        except Exception as e:
            self.bot.edit_message_text(f'<i>خطأ أثناء التحميل:</i> {e}', chat_id=call.message.chat.id, message_id=loading_msg.message_id, parse_mode='HTML')

    def load_cookies_from_file(self, file_path):
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
