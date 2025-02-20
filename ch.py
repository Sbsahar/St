import telebot
from PIL import Image
import opennsfw2 as n2
import os
import tempfile
import requests
import json

# بيانات تسجيل الدخول
API_TOKEN = "7067951946:AAEEW6mX9JVqwExL0CLVoawGptEKjDCjR3E"  # توكن البوت

bot = telebot.TeleBot(API_TOKEN)

# تحميل مجموعات التقارير المخزنة
REPORT_GROUPS_FILE = "report_groups.json"
report_groups = {}

try:
    with open(REPORT_GROUPS_FILE, "r", encoding="utf-8") as f:
        report_groups = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    report_groups = {}

def save_report_groups():
    with open(REPORT_GROUPS_FILE, "w", encoding="utf-8") as f:
        json.dump(report_groups, f, ensure_ascii=False, indent=4)

# أوامر البوت لتحديد مجموعة التقارير
@bot.message_handler(commands=['setreportgroup'])
def set_report_group(message):
    """تحديد مجموعة التقارير للقناة"""
    if not message.chat.type == 'supergroup':
        bot.reply_to(message, "❌ يجب استخدام هذا الأمر في مجموعة التقارير.")
        return

    if not message.reply_to_message or not message.reply_to_message.forward_from:
        bot.reply_to(message, "❌ يرجى إعادة توجيه رسالة من القناة ثم استخدام الأمر.")
        return

    channel_id = str(message.reply_to_message.forward_from.id)
    report_groups[channel_id] = message.chat.id
    save_report_groups()
    bot.reply_to(message, f"✅ تم تعيين مجموعة التقارير للقناة.")

def check_image_safety(image_path):
    """فحص الصورة باستخدام OpenNSFW2 بشكل غير متزامن"""
    try:
        # فتح الصورة
        image = Image.open(image_path)
        
        # تحليل الصورة باستخدام النموذج
        nsfw_probability = n2.predict_image(image)
        
        # إذا كانت نسبة NSFW > 0.5، نعتبرها غير لائقة
        return 'nude' if nsfw_probability > 0.5 else 'ok'
    
    except Exception as e:
        print(f"❌ خطأ أثناء تحليل الصورة: {e}")
        return 'error'

def send_violation_report(channel_id, message, violation_type):
    """إرسال تقرير عند كشف مخالفة"""
    report_group_id = report_groups.get(str(channel_id))
    if not report_group_id:
        return

    report_text = f"🚨 **تقرير مخالفة** 🚨\n📢 **القناة:** {message.chat.title}\n⚠️ **المخالفة:** {violation_type}"

    bot.send_message(report_group_id, report_text)

@bot.message_handler(content_types=['photo', 'video', 'sticker', 'animation'])
def handle_media(message):
    """فحص الصور، الفيديوهات، المتحركات، الملصقات في القنوات"""
    media_type = ""
    file_path = ""

    if message.photo:
        media_type = "📸 صورة غير لائقة"
        file_path = bot.download_file(message.photo[-1].file_id)

    elif message.video:
        media_type = "🎥 فيديو غير لائق"
        file_path = bot.download_file(message.video.file_id)

    elif message.animation:
        media_type = "🎞 صورة متحركة غير لائقة"
        file_path = bot.download_file(message.animation.file_id)

    elif message.sticker:
        media_type = "🎭 ملصق غير لائق"
        file_path = bot.download_file(message.sticker.file_id)

    if file_path:
        result = check_image_safety(file_path)

        # حذف المخالفات وإرسال تقرير
        if result == 'nude':
            bot.delete_message(message.chat.id, message.message_id)
            send_violation_report(message.chat.id, message, media_type)

# بدء البوت
bot.polling()
