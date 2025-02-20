import os
import asyncio
import tempfile
from telethon import TelegramClient, events
from ste import bot, check_image_safety, send_violation_report, n2, TOKEN

# إعداد بيانات Telethon – تأكد من إدخال API_ID و API_HASH الصحيحين
API_ID = 21290600
API_HASH = "2bd56b3e7715ec5862d6f856047caa95"

# إنشاء عميل Telethon باستخدام bot_token من ملف ste.py
client = TelegramClient('edited_monitor', API_ID, API_HASH).start(bot_token=TOKEN)

async def run_telethon():
    """
    دالة التشغيل الرئيسية التي تقوم برصد الرسائل الجديدة والمعدلة في القنوات.
    عند اكتشاف رسالة تحتوي على ميديا (صورة أو فيديو أو متحركة) يتم تنزيلها وفحصها،
    وفي حال تم اكتشاف محتوى غير لائق (حسب العتبة) يتم حذف الرسالة وإرسال تقرير عبر TeleBot.
    """

    @client.on(events.NewMessage(chats=lambda e: e.is_channel))
    async def new_message_handler(event):
        message = event.message
        if message.photo or message.video or message.animation:
            print(f"🔹 رسالة جديدة تحتوي على ميديا في القناة {message.chat.title if message.chat else 'Unknown'}، ID: {message.id}")
            await process_media_message(message)

    @client.on(events.MessageEdited(chats=lambda e: e.is_channel))
    async def edited_message_handler(event):
        message = event.message
        if message.photo or message.video or message.animation:
            print(f"🔄 رسالة معدلة تحتوي على ميديا في القناة {message.chat.title if message.chat else 'Unknown'}، ID: {message.id}")
            await process_media_message(message)

    async def process_media_message(message):
        # فحص الصورة
        if message.photo:
            file_path = await message.download_media()
            if not file_path:
                return
            try:
                result = check_image_safety(file_path)
                os.remove(file_path)
                if result == 'nude':
                    try:
                        await client.delete_messages(message.chat_id, [message.id])
                        send_violation_report(message.chat_id, message, "✏️ صورة غير لائقة")
                        print(f"✅ تم حذف رسالة صورة غير لائقة، ID: {message.id}")
                    except Exception as e:
                        print(f"❌ خطأ أثناء حذف رسالة الصورة: {e}")
            except Exception as e:
                print(f"❌ خطأ أثناء فحص رسالة الصورة: {e}")

        # فحص الفيديو
        elif message.video:
            file_path = await message.download_media()
            if not file_path:
                return
            try:
                elapsed, nsfw_probs = n2.predict_video_frames(file_path)
                os.remove(file_path)
                if any(prob >= 0.5 for prob in nsfw_probs):
                    try:
                        await client.delete_messages(message.chat_id, [message.id])
                        send_violation_report(message.chat_id, message, "✏️ فيديو غير لائق")
                        print(f"✅ تم حذف رسالة فيديو غير لائق، ID: {message.id}")
                    except Exception as e:
                        print(f"❌ خطأ أثناء حذف رسالة الفيديو: {e}")
            except Exception as e:
                print(f"❌ خطأ أثناء فحص رسالة الفيديو: {e}")

        # فحص الصورة المتحركة (الأنميشن)
        elif message.animation:
            file_path = await message.download_media()
            if not file_path:
                return
            try:
                elapsed, nsfw_probs = n2.predict_video_frames(file_path)
                os.remove(file_path)
                if any(prob >= 0.5 for prob in nsfw_probs):
                    try:
                        await client.delete_messages(message.chat_id, [message.id])
                        send_violation_report(message.chat_id, message, "✏️ صورة متحركة غير لائقة")
                        print(f"✅ تم حذف رسالة صورة متحركة غير لائقة، ID: {message.id}")
                    except Exception as e:
                        print(f"❌ خطأ أثناء حذف رسالة الصورة المتحركة: {e}")
            except Exception as e:
                print(f"❌ خطأ أثناء فحص رسالة الصورة المتحركة: {e}")

    print("🔹 تشغيل Telethon Handler...")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(run_telethon())
