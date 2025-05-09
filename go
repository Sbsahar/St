import subprocess
import os
import logging
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
import yt_dlp
from telegram.error import BadRequest

# إعداد التسجيل
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# القيم الأساسية
TOKEN = "7942028086:AAFTxAdkR0xEriPrFZb3rVhC8tTWCFIa_PI"
DOWNLOAD_DIR = "downloads"
LOG_DIR = "logs"

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

user_data = {}

async def start(update, context):
    if not update.message.chat.type == "private":
        return
    user_id = update.effective_user.id
    await safe_reply(update, context, 
        "مرحباً بك في بوت البث المباشر! 🎥\n"
        "يمكنني بث أي مقطع فيديو أو بث مباشر من يوتيوب أو جوجل درايف في قناتك.\n"
        "أرسل لي مفتاح البث (RTMPS URL) ورابط الفيديو أو البث المباشر، وسأقوم ببثه لك! 🌟",
        reply_markup=main_menu_keyboard()
    )

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("إضافة قناة", callback_data="add_channel")],
        [InlineKeyboardButton("إرسال رابط فيديو", callback_data="send_video")],
        [InlineKeyboardButton("بدء البث", callback_data="start_broadcast")],
        [InlineKeyboardButton("إيقاف البث", callback_data="stop_broadcast")],
        [InlineKeyboardButton("القنوات المضافة", callback_data="list_channels")],
        [InlineKeyboardButton("إيقاف كل عمليات البث", callback_data="stop_all_broadcasts")]
    ])

async def safe_reply(update, context, text, reply_markup=None):
    try:
        await update.message.reply_text(text, reply_markup=reply_markup)
    except BadRequest as e:
        logger.warning(f"Failed to send message: {e}")

async def safe_edit(query, text, reply_markup=None):
    try:
        await query.edit_message_text(text[:4096], reply_markup=reply_markup)  # حد أقصى 4096 حرف
    except BadRequest as e:
        logger.warning(f"Failed to edit message: {e}")
        await query.edit_message_text("حدث خطأ، لكن البث قد يكون مستمراً. تحقق من القناة!", reply_markup=reply_markup)

async def button(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    try:
        await query.answer()
    except BadRequest as e:
        logger.warning(f"Failed to answer callback: {e}")

    if query.data == "add_channel":
        await safe_edit(query, 
            "أرسل لي مفتاح البث (RTMPS URL) الخاص بقناتك.\nمثال: rtmps://dc4-1.rtmp.t.me/s/2012804950:bTinKqgjNrYnPy4OF8RH0A",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="back")]])
        )
    elif query.data == "send_video":
        await safe_edit(query, 
            "أرسل لي رابط الفيديو أو البث المباشر من يوتيوب أو جوجل درايف لتحميله وبثه في قناتك.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="back")]])
        )
    elif query.data == "start_broadcast":
        await start_broadcast(user_id, query, context)
    elif query.data == "stop_broadcast":
        await show_stop_broadcast_options(user_id, query)
    elif query.data == "list_channels":
        await list_channels(user_id, query)
    elif query.data == "stop_all_broadcasts":
        await stop_all_broadcasts(user_id, query)
    elif query.data == "back":
        await safe_edit(query, "مرحباً بك في بوت البث المباشر! 🎥", reply_markup=main_menu_keyboard())
    elif query.data.startswith("delete_channel_"):
        channel_id = query.data.split("_")[2]
        await confirm_delete_channel(user_id, channel_id, query)
    elif query.data.startswith("confirm_delete_"):
        channel_id, action = query.data.split("_")[2], query.data.split("_")[3]
        await handle_channel_deletion(user_id, channel_id, action, query)
    elif query.data.startswith("stop_channel_"):
        channel_id = query.data.split("_")[2]
        await stop_broadcast_for_channel(user_id, channel_id, query, context)

async def handle_rtmps_url(update, context):
    if not update.message.chat.type == "private":
        return
    user_id = update.effective_user.id
    rtmps_url = update.message.text.strip()
    if rtmps_url.startswith("rtmps://"):
        channel_id = rtmps_url.split("/")[-1].split(":")[0]
        user_data.setdefault(user_id, {"channels": {}, "videos": {}, "processes": {}})["channels"][channel_id] = rtmps_url
        await safe_reply(update, context, 
            "تم حفظ مفتاح البث بنجاح! ✅\nالآن أرسل رابط الفيديو أو البث المباشر.",
            reply_markup=main_menu_keyboard()
        )
    else:
        await safe_reply(update, context, "المفتاح غير صحيح! يجب أن يبدأ بـ 'rtmps://'. أعد المحاولة.")

async def handle_video_url(update, context):
    if not update.message.chat.type == "private":
        return
    user_id = update.effective_user.id
    video_url = update.message.text.strip()

    if not video_url.startswith("https://"):
        logger.info(f"Ignoring invalid URL: {video_url}")
        return

    await safe_reply(update, context, "جاري التحقق من الرابط... ⏳")

    is_live, video_info = check_video_status(video_url)
    if video_info:
        if user_id not in user_data or not user_data[user_id]["channels"]:
            await safe_reply(update, context, "لم تقم بإضافة أي قناة بعد! أضف قناة أولاً باستخدام 'إضافة قناة'.")
            return

        channel_id = list(user_data[user_id]["channels"].keys())[0]
        if is_live:
            stream_url = get_stream_url(video_url)
            if stream_url:
                user_data[user_id]["videos"][channel_id] = {"path": stream_url, "is_live": True}
                await safe_reply(update, context, 
                    "تم التعرف على البث المباشر! ✅\nاضغط 'بدء البث' لبثه في قناتك مباشرة.",
                    reply_markup=main_menu_keyboard()
                )
            else:
                await safe_reply(update, context, "فشل استخراج تيار البث المباشر! تأكد من الرابط.")
        else:
            video_path = download_video(video_url)
            expected_path = os.path.join(DOWNLOAD_DIR, f"video_{video_info.get('title', 'unknown')}.mp4")
            if os.path.exists(expected_path):
                user_data[user_id]["videos"][channel_id] = {"path": expected_path, "is_live": False}
                await safe_reply(update, context, 
                    "الفيديو موجود بالفعل وجاهز للبث! ✅\nاضغط 'بدء البث' لبثه.",
                    reply_markup=main_menu_keyboard()
                )
            elif video_path and os.path.exists(video_path):
                user_data[user_id]["videos"][channel_id] = {"path": video_path, "is_live": False}
                await safe_reply(update, context, 
                    "نجح تحميل الفيديو إلى الخادم! ✅\nالفيديو جاهز للبث. اضغط 'بدء البث' لبثه.",
                    reply_markup=main_menu_keyboard()
                )
            else:
                await safe_reply(update, context, "فشل تحميل الفيديو! تأكد من الرابط وحاول مرة أخرى.")
    else:
        await safe_reply(update, context, "فشل التحقق من الرابط! تأكد من أنه رابط يوتيوب أو جوجل درايف صالح.")

def check_video_status(url):
    ydl_opts = {"cookiefile": "cookies.txt"}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get("is_live", False), info
    except Exception as e:
        logger.error(f"Error checking video status: {e}")
        return False, None

def get_stream_url(url):
    ydl_opts = {
        "cookiefile": "cookies.txt",
        "format": "best",
        "geturl": True
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info["url"]
    except Exception as e:
        logger.error(f"Error extracting stream URL: {e}")
        return None

def download_video(url):
    output_path = os.path.join(DOWNLOAD_DIR, "video_%(title)s.mp4")
    ydl_opts = {
        "format": "bestvideo+bestaudio/best",
        "outtmpl": output_path,
        "cookiefile": "cookies.txt",
        "merge_output_format": "mp4",
        "postprocessors": [{
            "key": "FFmpegVideoConvertor",
            "preferedformat": "mp4"
        }]
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            return output_path
    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        return None

async def start_broadcast(user_id, query, context):
    if user_id not in user_data or not user_data[user_id]["channels"] or not user_data[user_id]["videos"]:
        await safe_edit(query, "يجب عليك إضافة قناة وتحميل فيديو أو بث مباشر أولاً!", reply_markup=main_menu_keyboard())
        return

    channel_id = list(user_data[user_id]["channels"].keys())[0]
    rtmps_url = user_data[user_id]["channels"][channel_id]
    video_data = user_data[user_id]["videos"][channel_id]
    input_source = video_data["path"]
    is_live = video_data["is_live"]

    log_file = os.path.join(LOG_DIR, f"ffmpeg_{channel_id}.log")
    max_retries = 3
    retry_delay = 5  # ثوانٍ

    for attempt in range(max_retries):
        try:
            ffmpeg_command = [
                "ffmpeg",
                "-re",
                "-i", input_source,
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-b:v", "2500k",
                "-maxrate", "3000k",
                "-bufsize", "6000k",
                "-r", "30",
                "-g", "30",             # Keyframe interval صغير لتوافق تلغرام
                "-profile:v", "baseline",  # توافق أوسع
                "-pix_fmt", "yuv420p",   # تنسيق ألوان مدعوم
                "-c:a", "aac",
                "-b:a", "128k",
                "-ar", "44100",
                "-f", "flv",
                "-flvflags", "no_duration_filesize"
            ]
            if is_live:
                ffmpeg_command.extend([
                    "-reconnect", "1",
                    "-reconnect_streamed", "1",
                    "-reconnect_delay_max", "10",
                    "-hls_playlist_size", "5",  # تخزين 5 مقاطع (كل مقطع 2 ثانية تقريباً = 10 ثوانٍ تأخير)
                    "-hls_time", "2"           # مدة كل مقطع 2 ثانية
                ])
            ffmpeg_command.append(rtmps_url)

            logger.info(f"Attempt {attempt + 1}/{max_retries} - Starting ffmpeg with command: {' '.join(ffmpeg_command)}")
            with open(log_file, "w") as log:
                process = subprocess.Popen(ffmpeg_command, stdout=log, stderr=log)
            user_data[user_id]["processes"][channel_id] = process

            await asyncio.sleep(20)  # الانتظار 20 ثانية للتأكد من الاستقرار
            if process.poll() is not None:
                with open(log_file, "r") as log:
                    error_log = log.read()
                raise Exception(f"ffmpeg failed early: {error_log}")

            if context.job_queue:
                context.job_queue.run_once(check_broadcast_end, 1, data={"user_id": user_id, "channel_id": channel_id})
            else:
                logger.warning("Job queue unavailable, broadcast end check will not run.")

            await safe_edit(query, 
                f"🎥 بدأ البث المباشر لقناتك!\nالقناة: {channel_id}\n{'بث مباشر' if is_live else 'فيديو'}",
                reply_markup=main_menu_keyboard()
            )
            return  # نجاح البث، خروج من الحلقة

        except Exception as e:
            logger.error(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
            with open(log_file, "r") as log:
                error_log = log.read()
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                continue
            else:
                await safe_edit(query, 
                    f"حدث خطأ بعد {max_retries} محاولات: {str(e)}\nتفاصيل: {error_log[:500]}",
                    reply_markup=main_menu_keyboard()
                )

async def check_broadcast_end(context):
    job = context.job
    user_id = job.data["user_id"]
    channel_id = job.data["channel_id"]
    process = user_data[user_id]["processes"].get(channel_id)

    if process and process.poll() is not None:
        video_data = user_data[user_id]["videos"].get(channel_id, {})
        if not video_data.get("is_live") and os.path.exists(video_data["path"]):
            os.remove(video_data["path"])
            logger.info(f"Deleted video: {video_data['path']}")
        del user_data[user_id]["processes"][channel_id]
        del user_data[user_id]["videos"][channel_id]
        try:
            await context.bot.send_message(
                user_id,
                "مرحباً، البث انتهى! 🎬\nأرسل رابطاً آخر لبثه.",
                reply_markup=main_menu_keyboard()
            )
        except BadRequest as e:
            logger.warning(f"Failed to notify user: {e}")
    elif process:
        if context.job_queue:
            context.job_queue.run_once(check_broadcast_end, 1, data=job.data)

async def show_stop_broadcast_options(user_id, query):
    if user_id not in user_data or not user_data[user_id]["processes"]:
        await safe_edit(query, "لا يوجد بث يعمل حالياً!", reply_markup=main_menu_keyboard())
        return
    keyboard = [
        [InlineKeyboardButton(f"القناة: {channel_id}", callback_data=f"stop_channel_{channel_id}")]
        for channel_id in user_data[user_id]["processes"].keys()
    ] + [[InlineKeyboardButton("رجوع", callback_data="back")]]
    await safe_edit(query, "اختر القناة لإيقاف البث:", reply_markup=InlineKeyboardMarkup(keyboard))

async def stop_broadcast_for_channel(user_id, channel_id, query, context):
    if channel_id in user_data[user_id]["processes"]:
        user_data[user_id]["processes"][channel_id].terminate()
        video_data = user_data[user_id]["videos"].get(channel_id, {})
        if not video_data.get("is_live") and os.path.exists(video_data["path"]):
            os.remove(video_data["path"])
            logger.info(f"Deleted video: {video_data['path']}")
        del user_data[user_id]["processes"][channel_id]
        del user_data[user_id]["videos"][channel_id]
        await safe_edit(query, f"تم إيقاف البث للقناة: {channel_id} 🛑", reply_markup=main_menu_keyboard())

async def stop_all_broadcasts(user_id, query):
    if user_id not in user_data or not user_data[user_id]["processes"]:
        await safe_edit(query, "لا يوجد بث يعمل حالياً!", reply_markup=main_menu_keyboard())
        return
    for channel_id, process in user_data[user_id]["processes"].items():
        process.terminate()
        video_data = user_data[user_id]["videos"].get(channel_id, {})
        if not video_data.get("is_live") and os.path.exists(video_data["path"]):
            os.remove(video_data["path"])
            logger.info(f"Deleted video: {video_data['path']}")
    user_data[user_id]["processes"].clear()
    user_data[user_id]["videos"].clear()
    await safe_edit(query, "تم إيقاف كل البث بنجاح! 🛑", reply_markup=main_menu_keyboard())

async def list_channels(user_id, query):
    if user_id not in user_data or not user_data[user_id]["channels"]:
        await safe_edit(query, "لم تقم بإضافة قنوات بعد!", reply_markup=main_menu_keyboard())
        return
    keyboard = [
        [InlineKeyboardButton(f"القناة: {channel_id}", callback_data=f"delete_channel_{channel_id}")]
        for channel_id in user_data[user_id]["channels"].keys()
    ] + [[InlineKeyboardButton("رجوع", callback_data="back")]]
    await safe_edit(query, "القنوات المضافة:\nاختر قناة لحذفها:", reply_markup=InlineKeyboardMarkup(keyboard))

async def confirm_delete_channel(user_id, channel_id, query):
    keyboard = [
        [InlineKeyboardButton("نعم", callback_data=f"confirm_delete_{channel_id}_yes")],
        [InlineKeyboardButton("لا", callback_data=f"confirm_delete_{channel_id}_no")],
        [InlineKeyboardButton("رجوع", callback_data="back")]
    ]
    await safe_edit(query, f"هل تريد حذف القناة: {channel_id}؟", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_channel_deletion(user_id, channel_id, action, query):
    if action == "yes":
        del user_data[user_id]["channels"][channel_id]
        if channel_id in user_data[user_id]["processes"]:
            user_data[user_id]["processes"][channel_id].terminate()
            del user_data[user_id]["processes"][channel_id]
        if channel_id in user_data[user_id]["videos"]:
            video_data = user_data[user_id]["videos"][channel_id]
            if not video_data["is_live"] and os.path.exists(video_data["path"]):
                os.remove(video_data["path"])
                logger.info(f"Deleted video: {video_data['path']}")
            del user_data[user_id]["videos"][channel_id]
        await safe_edit(query, f"تم حذف القناة: {channel_id} بنجاح!", reply_markup=main_menu_keyboard())
    else:
        await safe_edit(query, "تم الإلغاء.", reply_markup=main_menu_keyboard())

def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, lambda update, context: handle_rtmps_url(update, context) if "rtmps://" in update.message.text else handle_video_url(update, context)))
    application.run_polling()

if __name__ == "__main__":
    main()
