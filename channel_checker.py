from sahen_v1 import bot, check_image_safety, send_violation_report
import os
import tempfile
import requests

def process_channel_custom_emoji(message):
    """فحص الرموز التعبيرية الخاصة في القنوات"""
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

            # إذا كان الرمز غير لائق، نحذفه ونرسل تقريراً
            if res == 'nude':
                bot.delete_message(message.chat.id, message.message_id)
                send_violation_report(message.chat.id, message, "🤬 رمز تعبيري غير لائق")

        except Exception as e:
            print(f"❌ خطأ أثناء فحص الرمز التعبيري في القناة: {e}")

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
