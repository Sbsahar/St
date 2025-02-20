import os
import time
import tempfile
import requests
from ste import bot, check_image_safety, send_violation_report, n2

def get_message_link(message):
    """
    يُنشئ رابط للرسالة بناءً على وجود اسم مستخدم للقناة أو باستخدام تنسيق المعرف.
    """
    if hasattr(message.chat, 'username') and message.chat.username:
        return f"https://t.me/{message.chat.username}/{message.message_id}"
    elif str(message.chat.id).startswith("-100"):
        # إزالة بادئة -100 للحصول على الرابط الصحيح
        return f"https://t.me/c/{str(message.chat.id)[4:]}/{message.message_id}"
    else:
        return "رابط غير متاح"

def process_channel_media(message):
    """فحص الصور، الفيديوهات، الملصقات، والرموز التعبيرية في القنوات"""
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
        file_obj = message.video if message.content_type == 'video' else message.animation
        file_id = file_obj.file_id
        file_info = bot.get_file(file_id)
        file_link = f'https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}'
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
                response = requests.get(file_link)
                if response.status_code == 200:
                    tmp_file.write(response.content)
                    temp_path = tmp_file.name
                else:
                    print(f"❌ فشل تحميل الفيديو/الصورة المتحركة: {response.status_code}")
                    return
            elapsed_seconds, nsfw_probabilities = n2.predict_video_frames(temp_path)
            os.remove(temp_path)
            if any(prob >= 0.5 for prob in nsfw_probabilities):
                bot.delete_message(message.chat.id, message.message_id)
                violation_text = "🎥 فيديو غير لائقة" if message.content_type == 'video' else "🎥 صورة متحركة غير لائقة"
                send_violation_report(message.chat.id, message, violation_text)
        except Exception as e:
            print(f"❌ خطأ أثناء فحص الفيديو/الصورة المتحركة في القناة: {e}")

    elif message.content_type == 'sticker' and getattr(message.sticker, 'thumb', None):
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
                send_violation_report(message.chat.id, message, "🎭 ملصق غير لائقة")
        except Exception as e:
            print(f"❌ خطأ أثناء فحص الملصق في القناة: {e}")

    elif message.content_type == 'text' and message.entities:
        custom_emoji_ids = [entity.custom_emoji_id for entity in message.entities if entity.type == 'custom_emoji']
        if not custom_emoji_ids:
            return
        try:
            stickers = bot.get_custom_emoji_stickers(custom_emoji_ids)
            for sticker in stickers:
                if getattr(sticker, 'thumb', None):
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
                        send_violation_report(message.chat.id, message, "🤬 رمز تعبيري غير لائقة")
        except Exception as e:
            print(f"❌ خطأ أثناء فحص الرموز التعبيرية في القناة: {e}")

def process_edited_photo(message):
    """فحص الصور المعدلة"""
    if not message.photo:
        return
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
                print(f"❌ فشل تحميل الصورة المعدلة: {response.status_code}")
                message_link = get_message_link(message)
                bot.send_message(
                    message.chat.id,
                    f"⚠️ هناك تعديل لرسالة جديدة في القناة.\nرابط الرسالة: {message_link}\nلم أتمكن من فحصها بسبب سياسة تلغرام."
                )
                return
        res = check_image_safety(temp_path)
        os.remove(temp_path)
        if res == 'nude':
            bot.delete_message(message.chat.id, message.message_id)
            send_violation_report(message.chat.id, message, "✏️ صورة معدلة غير لائقة")
    except Exception as e:
        print(f"❌ خطأ أثناء فحص الصورة المعدلة في القناة: {e}")
        message_link = get_message_link(message)
        bot.send_message(
            message.chat.id,
            f"⚠️ هناك تعديل لرسالة جديدة في القناة.\nرابط الرسالة: {message_link}\nلم أتمكن من فحصها بسبب سياسة تلغرام."
        )

def process_edited_video(message):
    """فحص الفيديوهات المعدلة"""
    if not message.video:
        return
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
                print(f"❌ فشل تحميل الفيديو المعدل: {response.status_code}")
                message_link = get_message_link(message)
                bot.send_message(
                    message.chat.id,
                    f"⚠️ هناك تعديل لرسالة جديدة في القناة.\nرابط الرسالة: {message_link}\nلم أتمكن من فحصها بسبب سياسة تلغرام."
                )
                return
        elapsed_seconds, nsfw_probabilities = n2.predict_video_frames(temp_path)
        os.remove(temp_path)
        if any(prob >= 0.5 for prob in nsfw_probabilities):
            bot.delete_message(message.chat.id, message.message_id)
            send_violation_report(message.chat.id, message, "✏️ فيديو معدل غير لائقة")
    except Exception as e:
        print(f"❌ خطأ أثناء فحص الفيديو المعدل في القناة: {e}")
        message_link = get_message_link(message)
        bot.send_message(
            message.chat.id,
            f"⚠️ هناك تعديل لرسالة جديدة في القناة.\nرابط الرسالة: {message_link}\nلم أتمكن من فحصها بسبب سياسة تلغرام."
        )

def process_edited_animation(message):
    """فحص الصور المتحركة المعدلة"""
    if not message.animation:
        return
    file_id = message.animation.file_id
    file_info = bot.get_file(file_id)
    file_link = f'https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}'
    try:
        # استخدام امتداد .mp4 لتخزين الصورة المتحركة مؤقتًا
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
            response = requests.get(file_link)
            if response.status_code == 200:
                tmp_file.write(response.content)
                temp_path = tmp_file.name
            else:
                print(f"❌ فشل تحميل الصورة المتحركة المعدلة: {response.status_code}")
                message_link = get_message_link(message)
                bot.send_message(
                    message.chat.id,
                    f"⚠️ هناك تعديل لرسالة جديدة في القناة.\nرابط الرسالة: {message_link}\nلم أتمكن من فحصها بسبب سياسة تلغرام."
                )
                return
        elapsed_seconds, nsfw_probabilities = n2.predict_video_frames(temp_path)
        os.remove(temp_path)
        if any(prob >= 0.5 for prob in nsfw_probabilities):
            bot.delete_message(message.chat.id, message.message_id)
            send_violation_report(message.chat.id, message, "✏️ صورة متحركة معدلة غير لائقة")
    except Exception as e:
        print(f"❌ خطأ أثناء فحص الصورة المتحركة المعدلة في القناة: {e}")
        message_link = get_message_link(message)
        bot.send_message(
            message.chat.id,
            f"⚠️ هناك تعديل لرسالة جديدة في القناة.\nرابط الرسالة: {message_link}\nلم أتمكن من فحصها بسبب سياسة تلغرام."
        )

def process_edited_channel_media(message):
    """فحص جميع الرسائل المعدلة في القناة، بغض النظر عن نوعها"""
    if message.content_type == 'photo' and message.photo:
        process_edited_photo(message)
    elif message.content_type == 'video' and message.video:
        process_edited_video(message)
    elif message.content_type == 'animation' and message.animation:
        process_edited_animation(message)
    elif message.content_type == 'sticker' and message.sticker:
        process_channel_media(message)
    elif message.content_type == 'text' and message.entities:
        process_channel_media(message)
    else:
        print(f"🔄 تم تعديل رسالة في القناة {message.chat.title} ولكنها لا تحتوي على ميديا.")
        message_link = get_message_link(message)
        bot.send_message(
            message.chat.id,
            f"⚠️ هناك تعديل لرسالة جديدة في القناة.\nرابط الرسالة: {message_link}\nلم أتمكن من فحصها بسبب سياسة تلغرام."
        )
