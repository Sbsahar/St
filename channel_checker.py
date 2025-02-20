import os
import time
import tempfile
import requests
from ste import bot, check_image_safety, send_violation_report, n2

def process_channel_media(message):
    """فحص الصور، الفيديوهات، الملصقات، والرسائل في القنوات"""

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

    elif message.content_type == 'video' or message.content_type == 'animation':
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
                    print(f"❌ فشل تحميل الفيديو: {response.status_code}")
                    return

            # تحليل الفيديو باستخدام OpenNSFW2
            elapsed_seconds, nsfw_probabilities = n2.predict_video_frames(temp_path)
            os.remove(temp_path)

            if any(prob >= 0.5 for prob in nsfw_probabilities):
                bot.delete_message(message.chat.id, message.message_id)
                send_violation_report(message.chat.id, message, "🎥 فيديو غير لائق")

        except Exception as e:
            print(f"❌ خطأ أثناء فحص الفيديو في القناة: {e}")

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
                send_violation_report(message.chat.id, message, "🎭 ملصق غير لائق")

        except Exception as e:
            print(f"❌ خطأ أثناء فحص الملصق في القناة: {e}")




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

    elif message.content_type == 'video' or message.content_type == 'animation':
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
                    print(f"❌ فشل تحميل الفيديو: {response.status_code}")
                    return

            # تحليل الفيديو باستخدام OpenNSFW2
            elapsed_seconds, nsfw_probabilities = n2.predict_video_frames(temp_path)
            os.remove(temp_path)

            if any(prob >= 0.5 for prob in nsfw_probabilities):
                bot.delete_message(message.chat.id, message.message_id)
                send_violation_report(message.chat.id, message, "🎥 فيديو غير لائق")

        except Exception as e:
            print(f"❌ خطأ أثناء فحص الفيديو في القناة: {e}")

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
                send_violation_report(message.chat.id, message, "🎭 ملصق غير لائق")

        except Exception as e:
            print(f"❌ خطأ أثناء فحص الملصق في القناة: {e}")

    elif message.content_type == 'text' and message.entities:
        """ فحص الرموز التعبيرية المميزة """
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
                        send_violation_report(message.chat.id, message, "🤬 رمز تعبيري غير لائق")

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
                return

        res = check_image_safety(temp_path)
        os.remove(temp_path)

        if res == 'nude':
            bot.delete_message(message.chat.id, message.message_id)
            send_violation_report(message.chat.id, message, "✏️ صورة معدلة غير لائقة")

    except Exception as e:
        print(f"❌ خطأ أثناء فحص الصورة المعدلة في القناة: {e}")

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
                return

        elapsed_seconds, nsfw_probabilities = n2.predict_video_frames(temp_path)
        os.remove(temp_path)

        if any(prob >= 0.5 for prob in nsfw_probabilities):
            bot.delete_message(message.chat.id, message.message_id)
            send_violation_report(message.chat.id, message, "✏️ فيديو معدل غير لائق")

    except Exception as e:
        print(f"❌ خطأ أثناء فحص الفيديو المعدل في القناة: {e}")

def process_edited_animation(message):
    """فحص الصور المتحركة المعدلة"""
    if not message.animation:
        return

    file_id = message.animation.file_id
    file_info = bot.get_file(file_id)
    file_link = f'https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}'

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".gif") as tmp_file:
            response = requests.get(file_link)
            if response.status_code == 200:
                tmp_file.write(response.content)
                temp_path = tmp_file.name
            else:
                print(f"❌ فشل تحميل الصورة المتحركة المعدلة: {response.status_code}")
                return

        elapsed_seconds, nsfw_probabilities = n2.predict_video_frames(temp_path)
        os.remove(temp_path)

        if any(prob >= 0.5 for prob in nsfw_probabilities):
            bot.delete_message(message.chat.id, message.message_id)
            send_violation_report(message.chat.id, message, "✏️ صورة متحركة معدلة غير لائقة")

    except Exception as e:
        print(f"❌ خطأ أثناء فحص الصورة المتحركة المعدلة في القناة: {e}")


def process_edited_photo(message):
    """تمرير الصورة المعدلة للفحص"""
    process_channel_media(message)

def process_edited_video(message):
    """تمرير الفيديو المعدل للفحص"""
    process_channel_media(message)

def process_edited_animation(message):
    """تمرير الصورة المتحركة المعدلة للفحص"""
    process_channel_media(message)

def process_edited_channel_media(message):
    """فحص جميع الرسائل المعدلة في القناة، بغض النظر عن نوعها"""

    # ننتظر قليلًا حتى يتم تحديث محتوى الرسالة المعدلة بالكامل
    time.sleep(2)

    try:
        # الحصول على الرسالة المعدلة بعد التحديث
        messages = bot.get_chat_history(message.chat.id, limit=5)

        for msg in messages:
            if msg.message_id == message.message_id:
                print(f"🔄 تم العثور على الرسالة المعدلة، جاري الفحص...")

                if msg.content_type == 'photo':
                    process_edited_photo(msg)

                elif msg.content_type == 'video':
                    process_edited_video(msg)

                elif msg.content_type == 'animation':
                    process_edited_animation(msg)

                elif msg.content_type == 'sticker':
                    process_channel_media(msg)

                elif msg.content_type == 'text' and msg.entities:
                    process_channel_media(msg)

                else:
                    print(f"⚠️ تم تعديل الرسالة، لكنها لا تحتوي على ميديا.")
                
                break  # وجدنا الرسالة، لا داعي لمواصلة البحث

    except Exception as e:
        print(f"❌ خطأ أثناء فحص الرسائل المعدلة: {e}")
