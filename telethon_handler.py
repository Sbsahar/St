import os
import asyncio
import tempfile
from telethon import TelegramClient, events
from ste import bot, check_image_safety, send_violation_report, n2, TOKEN

# إعداد بيانات Telethon
API_ID = 21290600            # ضع API_ID الخاص بك هنا
API_HASH = "2bd56b3e7715ec5862d6f856047caa95"  # ضع API_HASH الخاص بك هنا

# تعريف عميل Telethon مع تشغيل البوت باستخدام bot_token الخاص بـ TeleBot
client = TelegramClient('edited_monitor', API_ID, API_HASH).start(bot_token=TOKEN)

@client.on(events.MessageEdited(chats=lambda e: e.is_channel))
async def edited_handler(event):
    """
    هذا المعالج يستقبل الرسائل المعدلة في القنوات.
    إذا كانت الرسالة تحتوي على ميديا (صورة، فيديو، أو متحركة) يتم تنزيل الملف وفحصه.
    في حال اكتشاف محتوى غير لائق، يتم حذف الرسالة باستخدام Telethon وإرسال تقرير عبر TeleBot.
    """
    message = event.message
    chat_title = message.chat.title if message.chat else "Unknown Channel"
    print(f"🔄 تم تعديل رسالة في القناة {chat_title}، ID: {message.id}")

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
                    # حذف الرسالة باستخدام Telethon
                    await client.delete_messages(message.chat_id, [message.id])
                    # إرسال تقرير إلى TeleBot
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
                    await client.delete_messages(message.chat_id, [message.id])
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
                    await client.delete_messages(message.chat_id, [message.id])
                    send_violation_report(message.chat_id, message, "✏️ صورة متحركة معدلة غير لائقة")
                    print("✅ تم حذف صورة متحركة معدلة غير لائقة")
                except Exception as e:
                    print(f"❌ خطأ أثناء حذف الصورة المتحركة المعدلة: {e}")
        except Exception as e:
            print(f"❌ خطأ أثناء فحص الصورة المتحركة المعدلة: {e}")

async def run_telethon():
    print("🔹 بدء تشغيل Telethon...")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(run_telethon())
