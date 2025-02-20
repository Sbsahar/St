import os
import asyncio
import tempfile
from telethon import TelegramClient, events
from ste import bot, check_image_safety, send_violation_report, n2, TOKEN

# إعداد بيانات Telethon – تأكد من إدخال API_ID و API_HASH الصحيحين
API_ID = 21290600
API_HASH = "2bd56b3e7715ec5862d6f856047caa95"

# تشغيل عميل Telethon
client = TelegramClient('edited_monitor', API_ID, API_HASH).start(bot_token=TOKEN)

async def process_media_message(message):
    """فحص الميديا وحذف المحتوى غير اللائق"""
    print(f"🔍 فحص الميديا في رسالة {message.id} من القناة {message.chat.title}")

    if message.photo:
        print("📸 تم اكتشاف صورة، يتم الفحص الآن...")
        file_path = await message.download_media()
        if not file_path:
            return
        try:
            result = check_image_safety(file_path)
            os.remove(file_path)
            if result == 'nude':
                await client.delete_messages(message.chat_id, [message.id])
                send_violation_report(message.chat_id, message, "🚨 صورة غير لائقة تم تعديلها")
                print("✅ تم حذف صورة غير لائقة")
        except Exception as e:
            print(f"❌ خطأ أثناء فحص الصورة: {e}")

    elif message.video:
        print("🎥 تم اكتشاف فيديو، يتم الفحص الآن...")
        file_path = await message.download_media()
        if not file_path:
            return
        try:
            elapsed, nsfw_probs = n2.predict_video_frames(file_path)
            os.remove(file_path)
            if any(prob >= 0.5 for prob in nsfw_probs):
                await client.delete_messages(message.chat_id, [message.id])
                send_violation_report(message.chat_id, message, "🚨 فيديو غير لائق تم تعديله")
                print("✅ تم حذف فيديو غير لائق")
        except Exception as e:
            print(f"❌ خطأ أثناء فحص الفيديو: {e}")

    elif message.animation:
        print("🎞️ تم اكتشاف صورة متحركة، يتم الفحص الآن...")
        file_path = await message.download_media()
        if not file_path:
            return
        try:
            elapsed, nsfw_probs = n2.predict_video_frames(file_path)
            os.remove(file_path)
            if any(prob >= 0.5 for prob in nsfw_probs):
                await client.delete_messages(message.chat_id, [message.id])
                send_violation_report(message.chat_id, message, "🚨 صورة متحركة غير لائقة تم تعديلها")
                print("✅ تم حذف صورة متحركة غير لائقة")
        except Exception as e:
            print(f"❌ خطأ أثناء فحص الصورة المتحركة: {e}")

@client.on(events.NewMessage(chats=lambda e: e.is_channel))
async def new_message_handler(event):
    """التقاط الرسائل الجديدة في القنوات"""
    message = event.message
    print(f"📥 رسالة جديدة في القناة {message.chat.title}, ID: {message.id}")

    if message.photo or message.video or message.animation:
        await process_media_message(message)

@client.on(events.MessageEdited(chats=lambda e: e.is_channel))
async def edited_message_handler(event):
    """التقاط الرسائل المعدلة في القنوات"""
    message = event.message
    print(f"✏️ تم تعديل رسالة في القناة {message.chat.title}, ID: {message.id}")

    if message.photo or message.video or message.animation:
        await process_media_message(message)

async def run_telethon():
    """تشغيل Telethon"""
    print("✅ Telethon متصل وينتظر الرسائل...")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(run_telethon())
