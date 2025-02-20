from ste import bot, check_image_safety, send_violation_report
import os
import tempfile
import requests

def process_channel_photo(message):
    """فحص الصور في القنوات"""
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
                print(f"❌ فشل تحميل الصورة، رمز الحالة: {response.status_code}")
                return

        res = check_image_safety(temp_path)
        os.remove(temp_path)

        if res == 'nude':
            bot.delete_message(message.chat.id, message.message_id)
            send_violation_report(message.chat.id, message, "📸 صورة غير لائقة")

    except Exception as e:
        print(f"❌ خطأ في فحص الصورة في القناة: {e}")

def process_channel_video(message):
    """فحص الفيديوهات في القنوات"""
    file_id = message.video.file_id
    file_info = bot.get_file(file_id)
    file_link = f'https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}'

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
            response = requests.get(file_link)
            if response.status_code == 200:
                tmp_file.write(response.content)
                temp_path = tmp_file.name
            else:
                print(f"❌ فشل تحميل الفيديو، رمز الحالة: {response.status_code}")
                return

        res = check_image_safety(temp_path)
        os.remove(temp_path)

        if res == 'nude':
            bot.delete_message(message.chat.id, message.message_id)
            send_violation_report(message.chat.id, message, "🎥 فيديو غير لائق")

    except Exception as e:
        print(f"❌ خطأ في فحص الفيديو في القناة: {e}")

def process_channel_sticker(message):
    """فحص الملصقات في القنوات"""
    if not message.sticker.thumb:
        return

    file_info = bot.get_file(message.sticker.thumb.file_id)
    sticker_url = f'https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}'

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
            response = requests.get(sticker_url)
            if response.status_code == 200:
                tmp_file.write(response.content)
                temp_path = tmp_file.name
            else:
                print(f"❌ فشل تحميل الملصق، رمز الحالة: {response.status_code}")
                return

        res = check_image_safety(temp_path)
        os.remove(temp_path)

        if res == 'nude':
            bot.delete_message(message.chat.id, message.message_id)
            send_violation_report(message.chat.id, message, "🎭 ملصق غير لائق")

    except Exception as e:
        print(f"❌ خطأ في فحص الملصق في القناة: {e}")

def process_channel_custom_emoji(message):
    """فحص الرموز التعبيرية الخاصة في القنوات"""
    custom_emoji_ids = [entity.custom_emoji_id for entity in message.entities if entity.type == 'custom_emoji']
    
    if not custom_emoji_ids:
        return

    try:
        sticker_set = bot.get_custom_emoji_stickers(custom_emoji_ids)
        for sticker in sticker_set:
            if sticker.thumb:
                file_info = bot.get_file(sticker.thumb.file_id)
                file_link = f'https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}'

                response = requests.get(file_link)
                if response.status_code == 200:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                        tmp_file.write(response.content)
                        temp_path = tmp_file.name

                    res = check_image_safety(temp_path)
                    os.remove(temp_path)

                    if res == 'nude':
                        bot.delete_message(message.chat.id, message.message_id)
                        send_violation_report(message.chat.id, message, "🤬 رمز تعبيري غير لائق")

    except Exception as e:
        print(f"❌ خطأ أثناء فحص الرموز التعبيرية في القناة: {e}")




def process_channel_media(content, file_extension, message, media_type):
    """
    معالجة الميديا (الفيديو والملفات المتحركة) باستخدام OpenNSFW2.
    يتم حفظ المحتوى مؤقتًا، ثم تحليل الفيديو باستخدام predict_video_frames.
    إذا كان أي إطار بنسبة NSFW >= 0.5، يتم اعتبار المحتوى غير لائق.
    """
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            temp_file.write(content)
            temp_file.close()
            
            # استخدام دالة predict_video_frames لتحليل الفيديو
            elapsed_seconds, nsfw_probabilities = n2.predict_video_frames(temp_file.name)
            
            # إذا كان هناك أي إطار بنسبة NSFW >= 0.5، يعتبر المحتوى غير لائق
            if any(prob >= 0.5 for prob in nsfw_probabilities):
                bot.delete_message(message.chat.id, message.message_id)
                send_violation_report(message.chat.id, message, f"🎥 {media_type} غير لائق")

            os.unlink(temp_file.name)
    except Exception as e:
        print(f"❌ خطأ في معالجة الميديا في القناة: {e}")

def process_channel_media(message, media_type):
    """فحص الفيديوهات والصور المتحركة في القنوات"""

    file_id = message.video.file_id if media_type == "فيديو" else message.animation.file_id
    file_info = bot.get_file(file_id)
    file_url = f'https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}'

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4" if media_type == "فيديو" else ".gif") as temp_file:
            response = requests.get(file_url)
            if response.status_code == 200:
                temp_file.write(response.content)
                temp_file.close()

                # فحص الفيديو باستخدام OpenNSFW2
                elapsed_seconds, nsfw_probabilities = n2.predict_video_frames(temp_file.name)

                # إذا كان هناك أي إطار بنسبة NSFW >= 0.5، نحذف الفيديو
                if any(prob >= 0.5 for prob in nsfw_probabilities):
                    bot.delete_message(message.chat.id, message.message_id)
                    send_violation_report(message.chat.id, message, f"🎥 {media_type} غير لائق")

            os.unlink(temp_file.name)

    except Exception as e:
        print(f"❌ خطأ في معالجة {media_type} في القناة: {e}")
