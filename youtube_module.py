import os
import yt_dlp
import time
import threading
from googleapiclient.discovery import build
from telebot import types
import ffmpeg
import logging

# إعداد التسجيل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
                    f"🎶 {title[:25]}",
                    callback_data=f"youtube_preview|{video_id}"
                )
                btn_download_audio = types.InlineKeyboardButton(
                    "MP3🎵",
                    callback_data=f"youtube_download|{video_id}"
                )
                btn_download_video = types.InlineKeyboardButton(
                    "Video📹",
                    callback_data=f"youtube_download_video|{video_id}"
                )
                markup.row(btn_video, btn_download_audio, btn_download_video)

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

            if data[0] == "youtube_preview":
                video_id = data[1]
                if chat_id not in self.user_search_data:
                    return

                results = self.user_search_data[chat_id]["results"]
                query = self.user_search_data[chat_id]["query"]

                new_thumbnail = None
                for vid, title, thumb in results:
                    if vid == video_id:
                        new_thumbnail = thumb
                        break
                if new_thumbnail is None:
                    new_thumbnail = results[0][2]

                markup = types.InlineKeyboardMarkup()
                for vid, title, _ in results:
                    btn_video = types.InlineKeyboardButton(
                        f"🔸 {title[:25]}",
                        callback_data=f"youtube_preview|{vid}"
                    )
                    btn_download = types.InlineKeyboardButton(
                        "MP3🎶",
                        callback_data=f"youtube_download|{vid}"
                    )
                    btn_download_video = types.InlineKeyboardButton(
                        "video📹",
                        callback_data=f"youtube_download_video|{vid}"
                    )
                    markup.row(btn_video, btn_download, btn_download_video)

                try:
                    self.bot.edit_message_media(
                        media=types.InputMediaPhoto(
                            new_thumbnail,
                            caption=f"<i>نتائج البحث عن:</i> {query}\n\nاختر فيديو لمشاهدته أو تحميله"
                        ),
                        chat_id=chat_id,
                        message_id=self.user_search_data[chat_id]["message_id"],
                        reply_markup=markup
                    )
                except Exception as e:
                    pass

            elif data[0] == "youtube_download":
                video_id = data[1]
                loading_msg = self.bot.send_message(
                    chat_id, '<i>جاري التحميل... 🔄</i>', parse_mode='HTML'
                )
                self.download_media(call, 'audio', video_id, 'bestaudio', loading_msg)

            elif data[0] == "youtube_download_video":
                video_id = data[1]
                loading_msg = self.bot.send_message(
                    chat_id, '<i>جاري التحميل... 🔄</i>', parse_mode='HTML'
                )
                self.download_media(call, 'video', video_id, 'hd', loading_msg)

    def split_file(self, file_path, max_size_mb, output_prefix):
        """تقسيم الملف إلى أجزاء بحجم أقصى محدد (بالميغابايت)."""
        max_size_bytes = max_size_mb * 1024 * 1024
        file_size = os.path.getsize(file_path)
        
        if file_size <= max_size_bytes:
            return [file_path]

        probe = ffmpeg.probe(file_path)
        duration = float(probe['format']['duration'])
        
        num_parts = int((file_size + max_size_bytes - 1) // max_size_bytes)
        part_duration = duration / num_parts
        
        output_files = []
        for i in range(num_parts):
            output_file = f"{output_prefix}_part{i+1}{os.path.splitext(file_path)[1]}"
            start_time = i * part_duration
            (
                ffmpeg
                .input(file_path, ss=start_time, t=part_duration)
                .output(output_file, c='copy', f='mp4' if file_path.endswith('.mp4') else 'mp3')
                .run(overwrite_output=True, quiet=True)
            )
            output_files.append(output_file)
        
        os.remove(file_path)
        return output_files

    def download_media(self, call, download_type, url, quality, loading_msg):
        cookies_file_path = 'cookies.txt'
        cookies = self.load_cookies_from_file(cookies_file_path)

        if not cookies:
            self.bot.edit_message_text(
                '<i>فشل تحميل الكوكيز! يرجى التأكد من الملف.</i>',
                chat_id=call.message.chat.id,
                message_id=loading_msg.message_id,
                parse_mode='HTML'
            )
            return

        base_ydl_opts = {
            'outtmpl': '%(title)s.%(ext)s',
            'timeout': 999999999,
            'retries': 10,
            'cookiefile': cookies_file_path,
            'cookies': cookies,
            'noplaylist': True,
            'quiet': False,
            'no_warnings': False,
            'ignoreerrors': False,
            'extractor_retries': 10,
            'fragment_retries': 10,
            'force_generic_extractor': True,
            'simulate': False,
            'skip_unavailable_fragments': True,
            'youtube_include_dash': True,  # محاولة استخدام تنسيقات DASH
        }

        if download_type == 'audio':
            ydl_opts = {
                **base_ydl_opts,
                'format': 'bestaudio/best[ext=mp3]/best[ext=m4a]/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            }
            max_size_mb = 24
        elif download_type == 'video':
            ydl_opts = {
                **base_ydl_opts,
                'format': 'bestvideo[height<=720]+bestaudio/best[height<=720]/best[ext=mp4]/best',
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4'
                }],
                'merge_output_format': 'mp4',
            }
            max_size_mb = 30

        try:
            video_url = f"https://www.youtube.com/watch?v={url}"
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # التحقق من التنسيقات المتاحة
                info = ydl.extract_info(video_url, download=False)
                logging.info(f"Available formats for {url}: {len(info.get('formats', []))} formats found")
                available_formats = [f.get('format_id') for f in info.get('formats', [])]
                logging.info(f"Format IDs: {available_formats}")

                if not info.get('formats') or all('acodec' not in f or f['acodec'] == 'none' for f in info['formats']):
                    logging.warning(f"No valid audio/video formats for {url}, falling back to 'best'")
                    self.bot.edit_message_text(
                        '<i>التنسيقات المطلوبة غير متاحة، جاري المحاولة بأي تنسيق متاح...</i>',
                        chat_id=call.message.chat.id,
                        message_id=loading_msg.message_id,
                        parse_mode='HTML'
                    )
                    time.sleep(2)
                    ydl_opts['format'] = 'best'
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(video_url, download=True)
                else:
                    self.bot.edit_message_text(
                        '<i>جاري التحميل...</i>',
                        chat_id=call.message.chat.id,
                        message_id=loading_msg.message_id,
                        parse_mode='HTML'
                    )
                    time.sleep(2)
                    info = ydl.extract_info(video_url, download=True)

                file_path = ydl.prepare_filename(info)
                logging.info(f"File path prepared: {file_path}")

                if download_type == 'audio':
                    file_path = file_path.rsplit('.', 1)[0] + '.mp3'
                    output_prefix = file_path.replace('.mp3', '')
                    files_to_send = self.split_file(file_path, max_size_mb, output_prefix)
                    for file in files_to_send:
                        with open(file, 'rb') as f:
                            self.bot.send_audio(
                                call.message.chat.id, f,
                                caption=f"تم التحميل بواسطة {self.BOT_USERNAME} ⋙"
                            )
                        os.remove(file)
                elif download_type == 'video':
                    output_prefix = file_path.replace('.mp4', '')
                    files_to_send = self.split_file(file_path, max_size_mb, output_prefix)
                    for file in files_to_send:
                        with open(file, 'rb') as f:
                            self.bot.send_video(
                                call.message.chat.id, f,
                                caption=f"تم التحميل بواسطة {self.BOT_USERNAME} ⋙"
                            )
                        os.remove(file)

                time.sleep(2)
                self.bot.delete_message(call.message.chat.id, loading_msg.message_id)

                time.sleep(5)
                try:
                    self.bot.delete_message(call.message.chat.id, call.message.message_id)
                except Exception:
                    pass

        except Exception as e:
            logging.error(f"Download error for {url}: {str(e)}")
            self.bot.edit_message_text(
                f'<i>خطأ أثناء التحميل: {str(e)}</i>\n<i>الفيديو قد يكون محميًا أو هناك مشكلة في YouTube، جرب لاحقًا أو استخدم فيديو آخر</i>',
                chat_id=call.message.chat.id,
                message_id=loading_msg.message_id,
                parse_mode='HTML'
            )

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
                logging.info(f"Loaded {len(cookies_dict)} cookies from {file_path}")
                return cookies_dict
        logging.warning(f"Cookies file {file_path} not found")
        return None
