import os
import tempfile
import requests
from ste import bot, check_image_safety, send_violation_report, n2

def process_media(message):
    """فحص جميع أنواع الميديا (صور، فيديو، متحركة، ملصقات، ورموز تعبيريّة) سواءً في الرسائل الجديدة أو المعدّلة."""
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
            print(f"❌ خطأ أثناء فحص الصورة: {e}")

    elif message.content_type in ['video', 'animation']:
        # سواء كان فيديو أو صورة متحركة نستخدم نفس المعالجة مع امتداد ".mp4"
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
                violation_text = "🎥 فيديو غير لائق" if message.content_type == 'video' else "🎥 صورة متحركة غير لائقة"
                bot.delete_message(message.chat.id, message.message_id)
                send_violation_report(message.chat.id, message, violation_text)
        except Exception as e:
            print(f"❌ خطأ أثناء فحص الفيديو/الصورة المتحركة: {e}")

    elif message.content_type == 'sticker' and getattr(message.sticker, 'thumb', None):
        file_info = bot.get_file(message.sticker.thumb.file_id)
        file_link = f'https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}'
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                response = requests.get(file_link)
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
            print(f"❌ خطأ أثناء فحص الملصق: {e}")

    elif message.content_type == 'text' and message.entities:
        # فحص الرموز التعبيرية المخصصة
        custom_emoji_ids = [entity.custom_emoji_id for entity in message.entities if entity.type == 'custom_emoji']
        if custom_emoji_ids:
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
                            send_violation_report(message.chat.id, message, "🤬 رمز تعبيري غير لائق")
            except Exception as e:
                print(f"❌ خطأ أثناء فحص الرموز التعبيرية: {e}")
    else:
        print(f"🔄 الرسالة في {message.chat.title} لا تحتوي على ميديا قابلة للفحص.")

def process_edited_channel_media(message):
    """فحص الرسائل المعدّلة باستخدام نفس منطق الفحص للرسائل الجديدة"""
    process_media(message)
