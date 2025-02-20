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

def process_edited_channel_custom_emoji(message):
    """فحص الرموز التعبيرية المميزة في الرسائل المعدلة داخل القنوات"""
    if not message.entities:
        return

    custom_emoji_ids = [entity.custom_emoji_id for entity in message.entities if entity.type == 'custom_emoji']
    if not custom_emoji_ids:
        return

    sticker_links = get_premium_sticker_info(custom_emoji_ids)
    if not sticker_links:
        return

    for link in sticker_links:
        try:
            # تنزيل الصورة المصغرة مؤقتًا
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                response = requests.get(link)
                if response.status_code == 200:
                    tmp_file.write(response.content)
                    temp_path = tmp_file.name
                else:
                    print(f"❌ فشل تحميل الرمز التعبيري، رمز الحالة: {response.status_code}")
                    continue

            # فحص الرمز التعبيري
            res = check_image_safety(temp_path)

            # حذف الملف المؤقت بعد الفحص
            os.remove(temp_path)

            # إذا كان الرمز غير لائق، نحذف الرسالة ونرسل تقريراً
            if res == 'nude':
                bot.delete_message(message.chat.id, message.message_id)
                send_violation_report(message.chat.id, message, "✏️ رسالة معدلة تحتوي على رمز تعبيري غير لائق")

        except Exception as e:
            print(f"❌ خطأ أثناء فحص الرموز التعبيرية في الرسائل المعدلة بالقناة: {e}")

def get_premium_sticker_info(custom_emoji_ids):
    """استخراج الروابط الخاصة بالرموز التعبيرية"""
    try:
        sticker_set = bot.get_custom_emoji_stickers(custom_emoji_ids)
        sticker_links = []
        for sticker in sticker_set:
            if sticker.thumb:
                file_info = bot.get_file(sticker.thumb.file_id)
                file_link = f'https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}'
                sticker_links.append(file_link)
        return sticker_links
    except Exception as e:
        print(f"❌ خطأ أثناء استخراج بيانات الرمز التعبيري: {e}")
        return []

def process_edited_channel_media(message):
    """فحص الصور والملصقات المعدلة في القنوات"""

    # فحص الصور المعدلة
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
                send_violation_report(message.chat.id, message, "✏️ صورة معدلة غير لائقة")

        except Exception as e:
            print(f"❌ خطأ أثناء فحص الصورة المعدلة في القناة: {e}")

    # فحص الملصقات المعدلة
    elif message.content_type == 'sticker':
        if not message.sticker.thumb:  # بعض الملصقات ليس لها صورة مصغرة
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
                    print(f"❌ فشل تحميل الملصق: {response.status_code}")
                    return

            res = check_image_safety(temp_path)
            os.remove(temp_path)

            if res == 'nude':
                bot.delete_message(message.chat.id, message.message_id)
                send_violation_report(message.chat.id, message, "✏️ ملصق معدل غير لائق")

        except Exception as e:
            print(f"❌ خطأ أثناء فحص الملصق المعدل في القناة: {e}")



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

def process_channel_gif(message):
    """فحص الصور المتحركة في القنوات"""
    try:
        file_info = bot.get_file(message.animation.file_id)
        file_url = f'https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}'
        response = requests.get(file_url)
        
        if response.status_code == 200:
            process_channel_media(response.content, '.gif', message, 'صورة متحركة')
    except Exception as e:
        print(f"❌ خطأ في معالجة GIF في القناة: {e}")

def process_channel_video(message):
    """فحص الفيديوهات في القنوات"""
    try:
        file_info = bot.get_file(message.video.file_id)
        file_url = f'https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}'
        response = requests.get(file_url)
        
        if response.status_code == 200:
            process_channel_media(response.content, '.mp4', message, 'فيديو')
    except Exception as e:
        print(f"❌ خطأ في معالجة الفيديو في القناة: {e}")

def process_edited_channel_media(message):
    """فحص الميديا المعدلة في القنوات"""
    if message.animation:
        process_channel_gif(message)
    elif message.video:
        process_channel_video(message) 









def process_channel_media(message):
    """فحص جميع أنواع الميديا في القنوات"""

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

    elif message.content_type == 'sticker':
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
                    print(f"❌ فشل تحميل الملصق: {response.status_code}")
                    return

            res = check_image_safety(temp_path)
            os.remove(temp_path)

            if res == 'nude':
                bot.delete_message(message.chat.id, message.message_id)
                send_violation_report(message.chat.id, message, "🎭 ملصق غير لائق")

        except Exception as e:
            print(f"❌ خطأ أثناء فحص الملصق في القناة: {e}")




