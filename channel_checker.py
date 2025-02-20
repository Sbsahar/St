import os
import time
import tempfile
import requests
from ste import bot, check_image_safety, send_violation_report, n2

def send_unchecked_media_alert(message):
    """إرسال إشعار عند تعديل رسالة لم يتمكن البوت من فحصها"""
    message_link = f"https://t.me/c/{str(message.chat.id).replace('-100', '')}/{message.message_id}"
    alert_text = f"⚠️ تم تعديل رسالة في القناة ولكن لم أتمكن من فحصها بسبب سياسة تيليجرام.
🔗 رابط الرسالة: {message_link}"
    bot.send_message(message.chat.id, alert_text)

def process_channel_media(message):
    """فحص الصور، الفيديوهات، الملصقات، والرموز التعبيرية في القنوات"""
    try:
        if message.content_type == 'photo':
            file_id = message.photo[-1].file_id
            file_info = bot.get_file(file_id)
            file_link = f'https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}'
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                response = requests.get(file_link)
                if response.status_code == 200:
                    tmp_file.write(response.content)
                    temp_path = tmp_file.name
                else:
                    send_unchecked_media_alert(message)
                    return
            res = check_image_safety(temp_path)
            os.remove(temp_path)
            if res == 'nude':
                bot.delete_message(message.chat.id, message.message_id)
                send_violation_report(message.chat.id, message, "📸 صورة غير لائقة")
        
        elif message.content_type in ['video', 'animation']:
            file_obj = message.video if message.content_type == 'video' else message.animation
            file_id = file_obj.file_id
            file_info = bot.get_file(file_id)
            file_link = f'https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}'
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
                response = requests.get(file_link)
                if response.status_code == 200:
                    tmp_file.write(response.content)
                    temp_path = tmp_file.name
                else:
                    send_unchecked_media_alert(message)
                    return
            elapsed_seconds, nsfw_probabilities = n2.predict_video_frames(temp_path)
            os.remove(temp_path)
            if any(prob >= 0.5 for prob in nsfw_probabilities):
                bot.delete_message(message.chat.id, message.message_id)
                violation_text = "🎥 فيديو غير لائق" if message.content_type == 'video' else "🎥 صورة متحركة غير لائقة"
                send_violation_report(message.chat.id, message, violation_text)
    except Exception as e:
        print(f"❌ خطأ أثناء فحص الوسائط: {e}")
        send_unchecked_media_alert(message)

def process_edited_channel_media(message):
    """فحص جميع الرسائل المعدلة في القناة، مع إرسال إشعار إذا تعذر الفحص"""
    try:
        if message.content_type == 'photo' and message.photo:
            process_channel_media(message)
        elif message.content_type == 'video' and message.video:
            process_channel_media(message)
        elif message.content_type == 'animation' and message.animation:
            process_channel_media(message)
        elif message.content_type == 'sticker' and message.sticker:
            process_channel_media(message)
        elif message.content_type == 'text' and message.entities:
            process_channel_media(message)
        else:
            send_unchecked_media_alert(message)
    except Exception as e:
        print(f"❌ خطأ أثناء فحص الرسالة المعدلة: {e}")
        send_unchecked_media_alert(message)
