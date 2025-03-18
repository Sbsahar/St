import subprocess
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
import yt_dlp

# القيم الأساسية
TOKEN = "7942028086:AAFTxAdkR0xEriPrFZb3rVhC8tTWCFIa_PI"  # ضع توكن البوت هنا
DOWNLOAD_DIR = "downloads"  # مجلد لتخزين الفيديوهات المحملة

# إنشاء مجلد التحميل إذا لم يكن موجوداً
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# متغيرات لتخزين بيانات المستخدمين
user_data = {}  # {user_id: {"channels": {channel_id: rtmps_url}, "videos": {channel_id: {"path": video_path, "is_live": bool}}, "processes": {channel_id: process}}}

async def start(update, context):
    user_id = update.effective_user.id
    await update.message.reply_text(
        "مرحباً بك في بوت البث المباشر! 🎥\n"
        "يمكنني بث أي مقطع فيديو أو بث مباشر من يوتيوب أو جوجل درايف في قناتك.\n"
        "أرسل لي مفتاح البث (RTMPS URL) ورابط الفيديو أو البث المباشر، وسأقوم ببثه لك! 🌟",
        reply_markup=main_menu_keyboard()
    )

def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("إضافة قناة", callback_data="add_channel")],
        [InlineKeyboardButton("إرسال رابط فيديو", callback_data="send_video")],
        [InlineKeyboardButton("بدء البث", callback_data="start_broadcast")],
        [InlineKeyboardButton("إيقاف البث", callback_data="stop_broadcast")],
        [InlineKeyboardButton("القنوات المضافة", callback_data="list_channels")],
        [InlineKeyboardButton("إيقاف كل عمليات البث", callback_data="stop_all_broadcasts")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def button(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == "add_channel":
        await query.edit_message_text(
            "أرسل لي مفتاح البث (RTMPS URL) الخاص بقناتك.\n"
            "مثال: rtmps://dc4-1.rtmp.t.me/s/2012804950:bTinKqgjNrYnPy4OF8RH0A",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="back")]])
        )
    elif query.data == "send_video":
        await query.edit_message_text(
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
        await query.edit_message_text(
            "مرحباً بك في بوت البث المباشر! 🎥",
            reply_markup=main_menu_keyboard()
        )
    elif query.data.startswith("delete_channel_"):
        channel_id = query.data.split("_")[2]
        await confirm_delete_channel(user_id, channel_id, query)
    elif query.data.startswith("confirm_delete_"):
        channel_id = query.data.split("_")[2]
        action = query.data.split("_")[3]
        await handle_channel_deletion(user_id, channel_id, action, query)
    elif query.data.startswith("stop_channel_"):
        channel_id = query.data.split("_")[2]
        await stop_broadcast_for_channel(user_id, channel_id, query, context)

async def handle_rtmps_url(update, context):
    user_id = update.effective_user.id
    rtmps_url = update.message.text.strip()
    if rtmps_url.startswith("rtmps://"):
        channel_id = rtmps_url.split("/")[-1].split(":")[0]
        user_data.setdefault(user_id, {"channels": {}, "videos": {}, "processes": {}})["channels"][channel_id] = rtmps_url
        await update.message.reply_text(
            "تم حفظ مفتاح البث بنجاح! ✅\n"
            "الآن أرسل رابط الفيديو أو البث المباشر.",
            reply_markup=main_menu_keyboard()
        )
    else:
        await update.message.reply_text("المفتاح غير صحيح! يجب أن يبدأ بـ 'rtmps://'. أعد المحاولة.")

async def handle_video_url(update, context):
    user_id = update.effective_user.id
    video_url = update.message.text.strip()
    await update.message.reply_text("جاري التحقق من الرابط... ⏳")

    # التحقق مما إذا كان بثاً مباشراً أو فيديو عادي
    is_live, video_info = check_video_status(video_url)
    if video_info:
        if user_id not in user_data or not user_data[user_id]["channels"]:
            await update.message.reply_text(
                "لم تقم بإضافة أي قناة بعد! أضف قناة أولاً باستخدام 'إضافة قناة'."
            )
            return

        channel_id = list(user_data[user_id]["channels"].keys())[0]  # القناة الأولى افتراضياً
        if is_live:
            user_data[user_id]["videos"][channel_id] = {"path": video_url, "is_live": True}
            await update.message.reply_text(
                "تم التعرف على البث المباشر! ✅\nاضغط 'بدء البث' لبثه في قناتك مباشرة.",
                reply_markup=main_menu_keyboard()
            )
        else:
            video_path = download_video(video_url)
            if video_path:
                user_data[user_id]["videos"][channel_id] = {"path": video_path, "is_live": False}
                await update.message.reply_text(
                    "نجح تحميل الفيديو إلى الخادم! ✅\nالفيديو جاهز للبث. اضغط 'بدء البث' لبثه.",
                    reply_markup=main_menu_keyboard()
                )
            else:
                await update.message.reply_text("فشل تحميل الفيديو! تأكد من الرابط وحاول مرة أخرى.")
    else:
        await update.message.reply_text("فشل التحقق من الرابط! تأكد منه وحاول مرة أخرى.")

def check_video_status(url):
    ydl_opts = {"cookiefile": "cookies.txt"}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get("is_live", False), info
    except Exception as e:
        print(f"Error checking video status: {e}")
        return False, None

def download_video(url):
    output_path = os.path.join(DOWNLOAD_DIR, "video_%(title)s.%(ext)s")
    ydl_opts = {
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "outtmpl": output_path,
        "cookiefile": "cookies.txt"
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            info = ydl.extract_info(url, download=False)
            return ydl.prepare_filename(info)
    except Exception as e:
        print(f"Error downloading video: {e}")
        return None

async def start_broadcast(user_id, query, context):
    if user_id not in user_data or not user_data[user_id]["channels"] or not user_data[user_id]["videos"]:
        await query.edit_message_text(
            "يجب عليك إضافة قناة وتحميل فيديو أو بث مباشر أولاً!",
            reply_markup=main_menu_keyboard()
        )
        return

    channel_id = list(user_data[user_id]["channels"].keys())[0]
    rtmps_url = user_data[user_id]["channels"][channel_id]
    video_data = user_data[user_id]["videos"][channel_id]
    input_source = video_data["path"]
    is_live = video_data["is_live"]

    ffmpeg_command = [
        "ffmpeg",
        "-re",
        "-i", input_source,
        "-c:v", "libx264" if not is_live else "copy",  # نسخ الفيديو مباشرة إذا كان بثاً مباشراً
        "-c:a", "aac",
        "-b:v", "2M" if not is_live else None,
        "-f", "flv",
        rtmps_url
    ]
    if is_live:
        ffmpeg_command = [x for x in ffmpeg_command if x is not None]  # إزالة القيم None للبث المباشر

    process = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    user_data[user_id]["processes"][channel_id] = process

    # مراقبة انتهاء البث
    context.job_queue.run_once(check_broadcast_end, 1, data={"user_id": user_id, "channel_id": channel_id})

    await query.edit_message_text(
        f"🎥 بدأ البث المباشر لقناتك!\nالقناة: {channel_id}\n{'بث مباشر' if is_live else 'فيديو'}",
        reply_markup=main_menu_keyboard()
    )

async def check_broadcast_end(context):
    job = context.job
    user_id = job.data["user_id"]
    channel_id = job.data["channel_id"]
    process = user_data[user_id]["processes"].get(channel_id)

    if process and process.poll() is not None:  # انتهى البث
        # حذف الفيديو إذا لم يكن بثاً مباشراً
        video_data = user_data[user_id]["videos"].get(channel_id, {})
        if not video_data.get("is_live") and os.path.exists(video_data["path"]):
            os.remove(video_data["path"])
            print(f"Deleted video: {video_data['path']}")

        del user_data[user_id]["processes"][channel_id]
        del user_data[user_id]["videos"][channel_id]
        await context.bot.send_message(
            user_id,
            "مرحباً عزيزي، الفيديو أو البث الخاص بك انتهى! 🎬\nيمكنك مشاركة رابط آخر لبثه.",
            reply_markup=main_menu_keyboard()
        )
    elif process:  # البث مستمر
        context.job_queue.run_once(check_broadcast_end, 1, data=job.data)

async def show_stop_broadcast_options(user_id, query):
    if user_id not in user_data or not user_data[user_id]["processes"]:
        await query.edit_message_text(
            "لا يوجد بث يعمل حالياً!",
            reply_markup=main_menu_keyboard()
        )
        return

    keyboard = [
        [InlineKeyboardButton(f"القناة: {channel_id}", callback_data=f"stop_channel_{channel_id}")]
        for channel_id in user_data[user_id]["processes"].keys()
    ] + [[InlineKeyboardButton("رجوع", callback_data="back")]]
    await query.edit_message_text(
        "اضغط على القناة التي تريد إيقاف البث فيها:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def stop_broadcast_for_channel(user_id, channel_id, query, context):
    if channel_id in user_data[user_id]["processes"]:
        user_data[user_id]["processes"][channel_id].terminate()
        # حذف الفيديو إذا لم يكن بثاً مباشراً
        video_data = user_data[user_id]["videos"].get(channel_id, {})
        if not video_data.get("is_live") and os.path.exists(video_data["path"]):
            os.remove(video_data["path"])
            print(f"Deleted video: {video_data['path']}")
        del user_data[user_id]["processes"][channel_id]
        del user_data[user_id]["videos"][channel_id]
        await query.edit_message_text(
            f"تم إيقاف البث للقناة: {channel_id} 🛑",
            reply_markup=main_menu_keyboard()
        )

async def stop_all_broadcasts(user_id, query):
    if user_id not in user_data or not user_data[user_id]["processes"]:
        await query.edit_message_text(
            "لا يوجد بث يعمل حالياً!",
            reply_markup=main_menu_keyboard()
        )
        return

    for channel_id, process in user_data[user_id]["processes"].items():
        process.terminate()
        video_data = user_data[user_id]["videos"].get(channel_id, {})
        if not video_data.get("is_live") and os.path.exists(video_data["path"]):
            os.remove(video_data["path"])
            print(f"Deleted video: {video_data['path']}")
    user_data[user_id]["processes"].clear()
    user_data[user_id]["videos"].clear()
    await query.edit_message_text(
        "تم إيقاف كل عمليات البث بنجاح! 🛑",
        reply_markup=main_menu_keyboard()
    )

async def list_channels(user_id, query):
    if user_id not in user_data or not user_data[user_id]["channels"]:
        await query.edit_message_text(
            "لم تقم بإضافة أي قنوات بعد!",
            reply_markup=main_menu_keyboard()
        )
        return

    keyboard = [
        [InlineKeyboardButton(f"القناة: {channel_id}", callback_data=f"delete_channel_{channel_id}")]
        for channel_id in user_data[user_id]["channels"].keys()
    ] + [[InlineKeyboardButton("رجوع", callback_data="back")]]
    await query.edit_message_text(
        "القنوات المضافة:\nاختر قناة لحذفها إذا أردت:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def confirm_delete_channel(user_id, channel_id, query):
    keyboard = [
        [InlineKeyboardButton("نعم", callback_data=f"confirm_delete_{channel_id}_yes")],
        [InlineKeyboardButton("لا", callback_data=f"confirm_delete_{channel_id}_no")],
        [InlineKeyboardButton("رجوع", callback_data="back")]
    ]
    await query.edit_message_text(
        f"هل ترغب في حذف القناة: {channel_id} من البث المباشر؟",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

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
                print(f"Deleted video: {video_data['path']}")
            del user_data[user_id]["videos"][channel_id]
        await query.edit_message_text(
            f"تم حذف القناة: {channel_id} بنجاح!",
            reply_markup=main_menu_keyboard()
        )
    else:
        await query.edit_message_text(
            "تم الإلغاء.",
            reply_markup=main_menu_keyboard()
        )

def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, lambda update, context: handle_rtmps_url(update, context) if "rtmps://" in update.message.text else handle_video_url(update, context)))
    application.run_polling()

if __name__ == "__main__":
    main()
