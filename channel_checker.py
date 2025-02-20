import os
import threading
import tempfile
import requests
from telethon import TelegramClient, events
from ste import bot, check_image_safety, send_violation_report, n2, TOKEN  # تأكد من استيراد المتغيرات والدوال من ملف ste.py

API_ID = 21290600    # ضع API_ID الخاص بك هنا
API_HASH = "2bd56b3e7715ec5862d6f856047caa95"  # ضع API_HASH الخاص بك هنا


client = TelegramClient('edited_monitor', API_ID, API_HASH).start(bot_token=TOKEN)

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
                    print("تم حذف صورة معدلة غير لائقة")
                except Exception as e:
                    print(f"Error deleting edited photo message: {e}")
        except Exception as e:
            print(f"Error processing edited photo: {e}")
    
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
                    print("تم حذف فيديو معدل غير لائق")
                except Exception as e:
                    print(f"Error deleting edited video message: {e}")
        except Exception as e:
            print(f"Error processing edited video: {e}")
    
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
                    print("تم حذف صورة متحركة معدلة غير لائقة")
                except Exception as e:
                    print(f"Error deleting edited animation message: {e}")
        except Exception as e:
            print(f"Error processing edited animation: {e}")

# دالة لتشغيل Telethon في خيط منفصل
def run_telethon():
    client.run_until_disconnected()

# تشغيل Telethon في خيط منفصل
threading.Thread(target=run_telethon, daemon=True).start()


def process_channel_media(message):
    """فحص الميديا في الرسائل الجديدة في القنوات (صور، فيديو، متحركات، ملصقات، ورموز تعبيرية)"""
    if message.content_type == 'photo':
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        file_link = f'https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}'
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                response = requests.get(file_link)
                if response.status_code == 200:
                    tmp_file.write(response.content)
                    temp_path = tmp_file.name
                else:
                    print(f"❌ فشل تحميل الصورة: {response.status_code}")
                    return
            res = check_image_safety(temp_path)
            os.remove(temp_path)
            if res == 'nude':
                bot.delete_message(message.chat.id, message.message_id)
                send_violation_report(message.chat.id, message, "📸 صورة غير لائقة")
        except Exception as e:
            print(f"❌ خطأ أثناء فحص الصورة في القناة: {e}")

    elif message.content_type in ['video', 'animation']:
        # نستخدم ملحق .mp4 للفيديو و .mp4 أيضاً للفتح نظرًا لأن النموذج يعمل مع ملفات الفيديو (حتى لو كانت GIF)
        file_id = message.video.file_id if message.content_type == 'video' else message.animation.file_id
        file_info = bot.get_file(file_id)
        file_link = f'https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}'
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
                response = requests.get(file_link)
                if response.status_code == 200:
                    tmp_file.write(response.content)
                    temp_path = tmp_file.name
                else:
                    print(f"❌ فشل تحميل الفيديو/المتحركة: {response.status_code}")
                    return
            elapsed_seconds, nsfw_probabilities = n2.predict_video_frames(temp_path)
            os.remove(temp_path)
            if any(prob >= 0.5 for prob in nsfw_probabilities):
                bot.delete_message(message.chat.id, message.message_id)
                send_violation_report(message.chat.id, message, "🎥 فيديو/متحركة غير لائقة")
        except Exception as e:
            print(f"❌ خطأ أثناء فحص الفيديو/المتحركة في القناة: {e}")

    elif message.content_type == 'sticker' and message.sticker.thumb:
        file_info = bot.get_file(message.sticker.thumb.file_id)
        sticker_url = f'https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}'
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                response = requests.get(sticker_url)
                if response.status_code == 200:
                    tmp_file.write(response.content)
                    temp_path = tmp_file.name
                else:
                    print(f"❌ فشل تحميل الملصق: {response.status_code}")
                    return
            res = check_image_safety(temp_path)
            os.remove(temp_path)
            if res == 'nude':
                bot.delete_message(message.chat.id, message.message_id)
                send_violation_report(message.chat.id, message, "🎭 ملصق غير لائقي")
        except Exception as e:
            print(f"❌ خطأ أثناء فحص الملصق في القناة: {e}")

    elif message.content_type == 'text' and message.entities:
        # فحص الرموز التعبيرية المميزة
        custom_emoji_ids = [entity.custom_emoji_id for entity in message.entities if entity.type == 'custom_emoji']
        if not custom_emoji_ids:
            return
        try:
            stickers = bot.get_custom_emoji_stickers(custom_emoji_ids)
            for sticker in stickers:
                if sticker.thumb:
                    file_info = bot.get_file(sticker.thumb.file_id)
                    file_link = f'https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}'
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                        response = requests.get(file_link)
                        if response.status_code == 200:
                            tmp_file.write(response.content)
                            temp_path = tmp_file.name
                        else:
                            print(f"❌ فشل تحميل الرمز التعبيري: {response.status_code}")
                            return
                    res = check_image_safety(temp_path)
                    os.remove(temp_path)
                    if res == 'nude':
                        bot.delete_message(message.chat.id, message.message_id)
                        send_violation_report(message.chat.id, message, "🤬 رمز تعبيري غير لائقي")
        except Exception as e:
            print(f"❌ خطأ أثناء فحص الرموز التعبيرية في القناة: {e}")

#######################
# دوال الفحص للرسائل المعدلة
#######################

# نقوم بإعادة تمرير الرسالة المعدلة إلى نفس دوال الفحص الجديدة؛
# حيث إن الرسالة المعدلة قد لا تُحدّث بيانات الميديا تلقائيًا،
# سنحاول الحصول على النسخة المُحدّثة باستخدام get_chat_history إذا لزم الأمر.

def process_edited_channel_media(message):
    """فحص جميع الرسائل المعدلة في القناة، بغض النظر عن نوعها.
       نحاول إعادة جلب الرسالة المُحدّثة من السجل لضمان تحديث بيانات الميديا."""
    try:
        # نحاول جلب الرسالة المحدثة؛ إذا فشل ذلك نستخدم الرسالة الحالية
        messages = bot.get_chat_history(message.chat.id, limit=1, offset_id=message.message_id-1)
        if messages:
            updated_msg = messages[0]
        else:
            updated_msg = message
    except Exception as e:
        print(f"❌ خطأ أثناء جلب الرسالة المحدثة: {e}")
        updated_msg = message

    # الآن نمرر النسخة المحدثة إلى دوال الفحص بناءً على نوع المحتوى
    if updated_msg.content_type == 'photo' and updated_msg.photo:
        process_edited_photo(updated_msg)
    elif updated_msg.content_type == 'video' and updated_msg.video:
        process_edited_video(updated_msg)
    elif updated_msg.content_type == 'animation' and updated_msg.animation:
        process_edited_animation(updated_msg)
    elif updated_msg.content_type == 'sticker' and updated_msg.sticker:
        process_channel_media(updated_msg)
    elif updated_msg.content_type == 'text' and updated_msg.entities:
        process_channel_media(updated_msg)
    else:
        print(f"🔄 تم تعديل رسالة في القناة {updated_msg.chat.title} ولكنها لا تحتوي على ميديا.")

def process_edited_photo(message):
    """فحص الصور المعدلة"""
    process_channel_media(message)  # إعادة استخدام نفس منطق الفحص للصور

def process_edited_video(message):
    """فحص الفيديوهات المعدلة"""
    process_channel_media(message)  # إعادة استخدام نفس منطق الفحص للفيديوهات

def process_edited_animation(message):
    """فحص الصور المتحركة المعدلة"""
    process_channel_media(message)  # إعادة استخدام نفس منطق الفحص للصورة المتحركة
