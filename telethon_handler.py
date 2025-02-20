import os
import threading
import tempfile
import requests
from telethon import TelegramClient, events
import asyncio
from ste import bot, check_image_safety, send_violation_report, n2, TOKEN

# بيانات Telethon
API_ID = 21290600
API_HASH = "2bd56b3e7715ec5862d6f856047caa95"

# تعريف العميل Telethon للبوت
client = TelegramClient('edited_monitor', API_ID, API_HASH).start(bot_token=TOKEN)

# معالج الرسائل المعدلة في القنوات
@client.on(events.MessageEdited(chats=lambda e: e.is_channel))
async def edited_handler(event):
    """معالجة الرسائل المعدلة في القنوات"""
    message = event.message
    print(f"🔄 تم تعديل رسالة في القناة {message.chat.title}، ID: {message.id}")

    try:
        # فحص الصور المعدلة
        if message.photo:
            file_path = await message.download_media(file=tempfile.NamedTemporaryFile(delete=False).name)
            result = check_image_safety(file_path)
            os.remove(file_path)
            if result == 'nude':
                await bot.delete_message(message.chat.id, message.id)
                send_violation_report(message.chat.id, message, "✏️ صورة معدلة غير لائقة")
                print("✅ تم حذف صورة معدلة غير لائقة")

        # فحص الفيديوهات والصور المتحركة المعدلة
        elif message.video or message.gif:
            file_path = await message.download_media(file=tempfile.NamedTemporaryFile(delete=False).name)
            elapsed, nsfw_probs = n2.predict_video_frames(file_path)
            os.remove(file_path)
            if any(prob >= 0.5 for prob in nsfw_probs):
                await bot.delete_message(message.chat.id, message.id)
                report_type = "فيديو" if message.video else "صورة متحركة"
                send_violation_report(message.chat.id, message, f"✏️ {report_type} معدل غير لائق")
                print(f"✅ تم حذف {report_type} معدل غير لائق")

    except Exception as e:
        print(f"❌ خطأ أثناء معالجة الرسالة المعدلة: {str(e)}")

# تشغيل Telethon في خيط منفصل
async def run_telethon():
    await client.run_until_disconnected()

def start_telethon():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_telethon())

# بدء تشغيل Telethon عند استيراد الملف
threading.Thread(target=start_telethon, daemon=True).start()
