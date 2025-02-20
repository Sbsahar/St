import os
import threading
import tempfile
import requests
from telethon import TelegramClient, events
import asyncio
from ste import bot, check_image_safety, send_violation_report, n2, TOKEN
    # باقي الكود هنا

# عوّن بيانات Telethon (استبدل API_ID و API_HASH بالقيم الخاصة بك)
API_ID = 21290600     # ضع API_ID الخاص بك هنا
API_HASH = "2bd56b3e7715ec5862d6f856047caa95"  # ضع API_HASH الخاص بك هنا

# إنشاء Telethon client للبوت باستخدام نفس TOKEN
client = TelegramClient('edited_monitor', API_ID, API_HASH).start(bot_token=TOKEN)
def run_telethon():
    loop = asyncio.new_event_loop()  
    asyncio.set_event_loop(loop)

    client = TelegramClient('edited_monitor', API_ID, API_HASH).start(bot_token=TOKEN)

    # استخدم asyncio.run لتشغيل العميل
    asyncio.run(client.run_until_disconnected())
@client.on(events.MessageEdited(chats=lambda e: e.is_channel))
async def edited_handler(event):
    """
    هذا المعالج يستقبل الرسائل المعدلة في القنوات.
    إذا كانت تحتوي على ميديا (صورة، فيديو، أو متحركة) يقوم بتنزيل الملف وفحصه.
    """
    message = event.message  # الرسالة المعدلة (يجب أن تكون محدثة)
    print(f"🔄 تم تعديل رسالة في القناة {message.chat.title}، ID: {message.id}")
    
    # فحص الصور المعدلة
    if message.photo:
        file_path = await message.download_media()
        if not file_path:
            return
        try:
            result = check_image_safety(file_path)
            os.remove(file_path)
            if result == 'nude':
                try:
                    bot.delete_message(message.chat_id, message.id)
                    send_violation_report(message.chat_id, message, "✏️ صورة معدلة غير لائقة")
                    print("✅ تم حذف صورة معدلة غير لائقة")
                except Exception as e:
                    print(f"❌ خطأ أثناء حذف الصورة المعدلة: {e}")
        except Exception as e:
            print(f"❌ خطأ أثناء فحص الصورة المعدلة: {e}")
    
    # فحص الفيديوهات المعدلة
    elif message.video:
        file_path = await message.download_media()
        if not file_path:
            return
        try:
            elapsed, nsfw_probs = n2.predict_video_frames(file_path)
            os.remove(file_path)
            if any(prob >= 0.5 for prob in nsfw_probs):
                try:
                    bot.delete_message(message.chat_id, message.id)
                    send_violation_report(message.chat_id, message, "✏️ فيديو معدل غير لائق")
                    print("✅ تم حذف فيديو معدل غير لائق")
                except Exception as e:
                    print(f"❌ خطأ أثناء حذف الفيديو المعدل: {e}")
        except Exception as e:
            print(f"❌ خطأ أثناء فحص الفيديو المعدل: {e}")
    
    # فحص الصور المتحركة المعدلة
    elif message.animation:
        file_path = await message.download_media()
        if not file_path:
            return
        try:
            elapsed, nsfw_probs = n2.predict_video_frames(file_path)
            os.remove(file_path)
            if any(prob >= 0.5 for prob in nsfw_probs):
                try:
                    bot.delete_message(message.chat_id, message.id)
                    send_violation_report(message.chat_id, message, "✏️ صورة متحركة معدلة غير لائقة")
                    print("✅ تم حذف صورة متحركة معدلة غير لائقة")
                except Exception as e:
                    print(f"❌ خطأ أثناء حذف الصورة المتحركة المعدلة: {e}")
        except Exception as e:
            print(f"❌ خطأ أثناء فحص الصورة المتحركة المعدلة: {e}")

# دالة لتشغيل Telethon في خيط منفصل
def run_telethon():
    client.run_until_disconnected()
