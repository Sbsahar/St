import telebot
import opennsfw2 as n2
from PIL import Image
import requests
import tempfile
import os
import time
import json
import threading
from datetime import datetime, date, timedelta
from queue import Queue
import re
import subprocess
from transformers import pipeline, CLIPProcessor, CLIPModel
import logging
import torch
import sys

# إعداد التسجيل
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
telebot.logger.setLevel(logging.DEBUG)

# إعدادات البوت
TOKEN = '7882394358:AAGQx9QbwgodZm7-mzBp1J6kJKt2QFIDh9I'
CHANNEL_USERNAME = 'F_U_2'
CHANNEL_URL = 'https://t.me/S_Y_K'
PROGRAMMER_URL = 'https://t.me/S_Y_K'
DEVELOPER_ID = '6305419238'
DEVELOPER_CHAT_ID = "6789179634"
NSFW_THRESHOLD = 0.7
VIOLENCE_THRESHOLD = 0.6
bot = telebot.TeleBot(TOKEN)
BOT_ID = bot.get_me().id

# ملفات التخزين
DATA_FILE = "restart_data.json"
VIOLATIONS_FILE = "user_violations.json"
REPORTS_FILE = "daily_reports.json"
ACTIVATIONS_FILE = "activations.json"
BANNED_WORDS_FILE = "banned_words.json"
# ملف لتخزين المجموعات المحظورة
BANNED_GROUPS_FILE = "banned_groups.json"
banned_groups = set()        
user_violations = {}
daily_reports = {}
activations = {}
banned_words = {}
current_date = date.today().isoformat()
media_queue = Queue()

# تحميل نموذج كاشف الإباحية (opennsfw2)
print("📦 جاري تحميل نموذج الكشف عن الإباحية...")

# تحميل نموذج كاشف العنف (CLIP)
print("📦 جاري تحميل نموذج CLIP للكشف عن العنف...")
clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
print("✅ تم تحميل النموذج بنجاح!")

VIOLENT_LABELS = [
    "violent scene",
    "blood or gore",
    "weapon or gun",
    "horror or scary content",
    "fighting or combat"
]
SAFE_LABEL = "safe content"

def load_banned_groups():
    global banned_groups
    try:
        with open(BANNED_GROUPS_FILE, 'r', encoding='utf-8') as f:
            banned_groups = set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        banned_groups = set()

# حفظ المجموعات المحظورة
def save_banned_groups():
    with open(BANNED_GROUPS_FILE, 'w', encoding='utf-8') as f:
        json.dump(list(banned_groups), f, ensure_ascii=False, indent=4)
        

# تحميل بيانات المخالفات
def load_violations():
    global user_violations
    try:
        with open(VIOLATIONS_FILE, 'r', encoding='utf-8') as f:
            user_violations = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        user_violations = {}

# حفظ بيانات المخالفات
def save_violations():
    with open(VIOLATIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(user_violations, f, ensure_ascii=False, indent=4)

# تحميل التقارير اليومية
def load_reports():
    global daily_reports
    try:
        with open(REPORTS_FILE, 'r', encoding='utf-8') as f:
            daily_reports = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        daily_reports = {}

# حفظ التقارير اليومية
def save_reports():
    with open(REPORTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(daily_reports, f, ensure_ascii=False, indent=4)

# تحميل التفعيلات
def load_activations():
    global activations
    try:
        with open(ACTIVATIONS_FILE, 'r', encoding='utf-8') as f:
            activations = json.load(f)
        for chat_id in activations:
            if 'violence_enabled' not in activations[chat_id]:
                activations[chat_id]['violence_enabled'] = False
    except (FileNotFoundError, json.JSONDecodeError):
        activations = {}

# حفظ التفعيلات
def save_activations():
    with open(ACTIVATIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(activations, f, ensure_ascii=False, indent=4)

# تحميل الكلمات المحظورة
def load_banned_words():
    global banned_words
    try:
        with open(BANNED_WORDS_FILE, 'r', encoding='utf-8') as f:
            banned_words = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        banned_words = {}

# حفظ الكلمات المحظورة
def save_banned_words():
    with open(BANNED_WORDS_FILE, 'w', encoding='utf-8') as f:
        json.dump(banned_words, f, ensure_ascii=False, indent=4)

# التحقق إذا كانت المجموعة مفعلة
def is_group_activated(chat_id):
    chat_id_str = str(chat_id)
    if chat_id_str in activations:
        expiry = activations[chat_id_str]['expiry_date']
        if expiry == 'permanent':
            return True
        expiry_date = datetime.strptime(expiry, '%Y-%m-%d').date()
        if date.today() <= expiry_date:
            return True
        else:
            del activations[chat_id_str]
            save_activations()
    return False

# التحقق إذا كان كاشف العنف مفعل
def is_violence_enabled(chat_id):
    chat_id_str = str(chat_id)
    return activations.get(chat_id_str, {}).get('violence_enabled', False)

# حساب الوقت المتبقي
def get_remaining_time(chat_id):
    chat_id_str = str(chat_id)
    if chat_id_str in activations:
        expiry = activations[chat_id_str]['expiry_date']
        if expiry == 'permanent':
            return "للأبد"
        expiry_date = datetime.strptime(expiry, '%Y-%m-%d').date()
        remaining_days = (expiry_date - date.today()).days
        if remaining_days > 0:
            return f"{remaining_days} أيام"
        else:
            return "منتهي"
    return "غير مفعل"

# فحص الصور باستخدام OpenNSFW2 (إباحية)
def check_image_safety(image_path):
    try:
        image = Image.open(image_path)
        nsfw_probability = n2.predict_image(image)
        print(f"NSFW Probability for image: {nsfw_probability}")
        return 'nude' if nsfw_probability > NSFW_THRESHOLD else 'ok'
    except Exception as e:
        print(f"حدث خطأ أثناء تحليل الصورة: {e}")
        return 'error'

# فحص الصور للعنف باستخدام CLIP
def check_violence_safety(image_path):
    try:
        image = Image.open(image_path).convert("RGB")
        inputs = clip_processor(
            text=VIOLENT_LABELS + [SAFE_LABEL],
            images=image,
            return_tensors="pt",
            padding=True
        )
        with torch.no_grad():
            outputs = clip_model(**inputs)
        logits_per_image = outputs.logits_per_image
        probs = logits_per_image.softmax(dim=1).cpu().numpy()[0]
        
        for i, label in enumerate(VIOLENT_LABELS):
            if probs[i] >= VIOLENCE_THRESHOLD:
                print(f"[VIOLENCE DETECTED] {label} ({probs[i]:.4f}) في {image_path}")
                return True
        return False
    except Exception as e:
        print(f"⚠️ خطأ في فحص العنف: {e}")
        return False

# استخراج إطارات الفيديو لفحص العنف
def extract_frames(video_path, output_folder):
    os.makedirs(output_folder, exist_ok=True)
    cmd = [
        'ffmpeg', '-i', video_path,
        '-vf', 'fps=1',
        f'{output_folder}/frame_%03d.jpg',
        '-hide_banner', '-loglevel', 'error'
    ]
    subprocess.run(cmd, check=True)

# فحص الفيديو للعنف
def check_video(video_path):
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            extract_frames(video_path, temp_dir)
            for frame in sorted(os.listdir(temp_dir)):
                frame_path = os.path.join(temp_dir, frame)
                if check_violence_safety(frame_path):
                    return True
        return False
    except Exception as e:
        print(f"⚠️ خطأ أثناء فحص الفيديو: {e}")
        return False

# فحص GIF للعنف
def check_gif(gif_path):
    try:
        with tempfile.NamedTemporaryFile(delete=True, suffix=".jpg") as frame:
            cmd = [
                'ffmpeg', '-y',  # خيار -y للكتابة التلقائية دون تأكيد
                '-i', gif_path, '-vframes', '1',
                '-q:v', '2', frame.name,
                '-hide_banner', '-loglevel', 'error'
            ]
            subprocess.run(cmd, check=True)
            result = check_violence_safety(frame.name)
        return result
    except Exception as e:
        print(f"⚠️ خطأ في فحص GIF: {e}")
        return False

# تطبيع النص للكلمات المحظورة
def normalize_text(text):
    text = re.sub(r'[\u0617-\u061A\u064B-\u065F]', '', text)
    text = re.sub(r'[-\s\u0640]+', '', text)
    return text.lower()

# فحص الكلمات المحظورة
def check_banned_words(message):
    chat_id_str = str(message.chat.id)
    if chat_id_str not in banned_words:
        return False
    text = normalize_text(message.text or message.caption or "")
    for word in banned_words[chat_id_str]:
        if normalize_text(word) in text:
            return True
    return False

# معالجة الفيديوهات والصور المتحركة في خيط منفصل (للإباحية)
def process_media_worker():
    while True:
        content, file_extension, message, media_type = media_queue.get()
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name
            
            elapsed_seconds, nsfw_probabilities = n2.predict_video_frames(temp_file_path)
            print(f"NSFW Probabilities for video {message.message_id}: {nsfw_probabilities}")
            os.unlink(temp_file_path)
            
            if any(prob >= NSFW_THRESHOLD for prob in nsfw_probabilities):
                handle_violation(message, media_type, 'إباحية')
        except Exception as e:
            print(f"خطأ في معالجة الميديا للرسالة {message.message_id}: {e}")
        finally:
            media_queue.task_done()

# معالجة المخالفات مع تسجيل التقرير
# معالجة المخالفات مع تسجيل التقرير
def handle_violation(message, content_type, violation_type='إباحية'):
    global current_date
    try:
        bot.delete_message(message.chat.id, message.message_id)
        user_id = str(message.from_user.id)
        chat_id = str(message.chat.id)
        
        user_violations[user_id] = user_violations.get(user_id, 0) + 1
        violation_count = user_violations[user_id]
        
        reason = violation_type if violation_type != 'كلمة محظورة' else 'كلمة محظورة'
        warning_msg = (
            f"⚠️ <b>تنبيه فوري!</b>\n"
            f"👤 <b>العضو:</b> <a href='tg://user?id={user_id}'>{message.from_user.first_name}</a>\n"
            f"🚫 <b>نوع المخالفة:</b> {content_type} {reason}\n"
            f"🔢 <b>عدد المخالفات:</b> {violation_count}/10\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        if is_user_admin(chat_id, user_id):
            warning_msg += (
                "🛡️ <b>ملاحظة:</b> المستخدم مشرف لايمكن تقيده تجاوز الحد المسموح!\n"
                "📢 <b>يرجى التعامل معه من قبل مالك المجموعة.</b>"
            )
        else:
            warning_msg += (
                "⚠️ <b>تحذير:</b> إذا تجاوزت 10 مخالفات، سيتم تقييدك تلقائيًا لمدة 24 ساعة!"
            )
        bot.send_message(chat_id, warning_msg, parse_mode="HTML")
        
        today = date.today().isoformat()
        if today != current_date:
            reset_daily_reports()
            current_date = today
        
        if chat_id not in daily_reports:
            daily_reports[chat_id] = []
        
        violation_entry = {
            "user_name": message.from_user.first_name,
            "username": f"@{message.from_user.username}" if message.from_user.username else "غير متوفر",
            "user_id": user_id,
            "violation_type": f"{content_type} {violation_type}",
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_violations": violation_count
        }
        daily_reports[chat_id].append(violation_entry)
        save_reports()
        
        if violation_count >= 10 and not is_user_admin(chat_id, user_id):
            bot.restrict_chat_member(chat_id, user_id, until_date=int(time.time()) + 86400, can_send_messages=False)
            markup = telebot.types.InlineKeyboardMarkup()
            unban_button = telebot.types.InlineKeyboardButton("رفع القيود", callback_data=f"unban_{user_id}")
            markup.add(unban_button)
            bot.send_message(chat_id, (
                f"🚫 <b>تم تقييد العضو!</b>\n"
                f"👤 <b>العضو:</b> <a href='tg://user?id={user_id}'>{message.from_user.first_name}</a>\n"
                f"⏳ <b>المدة:</b> 24 ساعة\n"
                f"📢 <b>السبب:</b> تجاوز 10 مخالفات!"
            ), parse_mode="HTML", reply_markup=markup)
            user_violations[user_id] = 0
        
        save_violations()
    except Exception as e:
        print(f"خطأ في معالجة المخالفة: {e}")

# التحقق من صلاحيات المشرف
def is_user_admin(chat_id, user_id):
    try:
        admins = bot.get_chat_administrators(chat_id)
        return any(str(admin.user.id) == str(user_id) for admin in admins)
    except Exception as e:
        print(f"خطأ في التحقق من الصلاحيات: {e}")
        return False

# التحقق من صلاحيات البوت
def is_bot_admin_with_permissions(chat_id):
    try:
        bot_member = bot.get_chat_member(chat_id, BOT_ID)
        if bot_member.status == 'administrator':
            return bot_member.can_delete_messages and bot_member.can_restrict_members
        return False
    except Exception as e:
        print(f"خطأ في التحقق من صلاحيات البوت: {e}")
        return False

# التحقق من الاشتراك في القناة
def is_user_subscribed(user_id):
    try:
        if str(user_id) == DEVELOPER_ID:
            print(f"[DEBUG] User {user_id} is the developer, bypassing subscription check.")
            return True
        
        print(f"[DEBUG] التحقق من اشتراك المستخدم {user_id} في القناة @{CHANNEL_USERNAME}")
        chat_member = bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        status = chat_member.status
        print(f"[DEBUG] حالة المستخدم {user_id} في القناة @{CHANNEL_USERNAME}: {status}")
        return status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"[ERROR] خطأ في التحقق من الاشتراك للمستخدم {user_id}: {e}")
        return False

# دالة استخراج معلومات الملصقات المميزة
def get_premium_sticker_info(custom_emoji_ids):
    try:
        sticker_set = bot.get_custom_emoji_stickers(custom_emoji_ids)
        return [f'https://api.telegram.org/file/bot{TOKEN}/{bot.get_file(sticker.thumb.file_id).file_path}' for sticker in sticker_set if sticker.thumb]
    except Exception as e:
        print(f"Error retrieving sticker info: {e}")
        return []

# إرسال التقرير اليومي عند الطلب
def send_daily_report(chat_id):
    try:
        chat_id = str(chat_id)
        if chat_id in daily_reports and daily_reports[chat_id]:
            report_msg = (
                "📊 التقرير اليومي للمجموعة\n"
                f"🕒 تاريخ التقرير: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                "━━━━━━━━━━━━━━━━━━━━━━━\n"
            )
            
            violations = daily_reports[chat_id]
            report_msg += f"📈 إجمالي المخالفات: {len(violations)}\n\n"
            for idx, violation in enumerate(violations, 1):
                report_msg += (
                    f"#{idx} المستخدم: {violation['user_name']} ({violation['username']})\n"
                    f"🆔 المعرف: {violation['user_id']}\n"
                    f"⚠️ نوع المخالفة: {violation['violation_type']}\n"
                    f"⏰ الوقت: {violation['time']}\n"
                    f"🔢 عدد المخالفات الكلي: {violation['total_violations']}\n"
                    "───────────────────\n"
                )
            report_msg += "━━━━━━━━━━━━━━━━━━━━━━━\n📢 البوت يعمل بكفاءة لحماية المجموعة!"
            
            if len(report_msg) > 4096:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode='w', encoding='utf-8') as tmp_file:
                    tmp_file.write(report_msg)
                    tmp_file_path = tmp_file.name
                
                with open(tmp_file_path, 'rb') as file:
                    bot.send_document(chat_id, file, caption="📈 تنبيه: المخالفات كثيرة جدًا! الملف يحتوي على التقرير الكامل.")
                os.unlink(tmp_file_path)
            else:
                bot.send_message(chat_id, report_msg)
            print(f"[DEBUG] أرسلت التقرير اليومي لـ chat_id: {chat_id}")
        else:
            bot.send_message(chat_id, "✅ لا توجد مخالفات مسجلة اليوم! المجموعة نظيفة وآمنة!")
            print(f"[DEBUG] لا توجد مخالفات لـ chat_id: {chat_id}")
    except Exception as e:
        print(f"[ERROR] خطأ في إرسال التقرير اليومي لـ chat_id: {chat_id}: {e}")

# تصفير التقارير اليومية عند تغير اليوم
def reset_daily_reports():
    global daily_reports
    daily_reports = {}
    save_reports()
    print("✅ تم تصفير التقارير اليومية.")
    
    to_remove = []
    for chat_id, data in activations.items():
        if data['expiry_date'] != 'permanent' and datetime.strptime(data['expiry_date'], '%Y-%m-%d').date() < date.today():
            to_remove.append(chat_id)
    
    for chat_id in to_remove:
        del activations[chat_id]
        try:
            markup = telebot.types.InlineKeyboardMarkup()
            contact_button = telebot.types.InlineKeyboardButton("تواصل مع المطور", url=PROGRAMMER_URL)
            markup.add(contact_button)
            bot.send_message(
                chat_id,
                "🚨 تنبيه فوري: انتهى اشتراك البوت!\n📢 يرجى التواصل مع المطور للتفعيل إذا أردت إعادة تفعيل البوت.",
                reply_markup=markup
            )
            print(f"✅ تم إرسال تنبيه انتهاء الاشتراك إلى {chat_id}")
        except Exception as e:
            print(f"خطأ في إرسال تنبيه إلى {chat_id}: {e}")
    
    save_activations()
    print("✅ تم إزالة التفعيلات المنتهية.")

# خيط للتحقق من تغير اليوم
def check_day_change():
    global current_date
    while True:
        today = date.today().isoformat()
        if today != current_date:
            reset_daily_reports()
            current_date = today
        time.sleep(3600)

# أمر البدء مع الاشتراك الإجباري والأزرار (مع logging إضافي)
# أمر البدء مع الاشتراك الإجباري والأزرار (مع logging إضافي)
@bot.message_handler(commands=['start'])
def start(message):
    print(f"[DEBUG] تلقيت أمر /start من user_id: {message.from_user.id}, chat_id: {message.chat.id}")
    try:
        user_id = message.from_user.id
        
        # تفعيل التحقق من الاشتراك
        subscription_enabled = True  
        if subscription_enabled and not is_user_subscribed(user_id):
            print(f"[DEBUG] المستخدم {user_id} لم يشترك في القناة")
            markup = telebot.types.InlineKeyboardMarkup()
            subscribe_button = telebot.types.InlineKeyboardButton("اشترك الآن", url=CHANNEL_URL)
            check_button = telebot.types.InlineKeyboardButton("🔄 تحقق من الاشتراك", callback_data="check_subscription")
            markup.add(subscribe_button, check_button)
            
            bot.send_message(
                message.chat.id,
                f"⚠️ يجب عليك الاشتراك في القناة أولاً لاستخدام البوت!\n\n👉 {CHANNEL_URL}",
                reply_markup=markup
            )
            print(f"[DEBUG] أرسلت رسالة طلب الاشتراك لـ user_id: {user_id}")
            return

        print(f"[DEBUG] المستخدم {user_id} يمكنه الوصول، عرض رسالة البدء")
        markup = telebot.types.InlineKeyboardMarkup()
        programmer_button = telebot.types.InlineKeyboardButton("المطور", url=PROGRAMMER_URL)
        add_to_group_button = telebot.types.InlineKeyboardButton("➕ أضفني إلى مجموعتك", url=f"https://t.me/{bot.get_me().username}?startgroup=true")
        markup.add(programmer_button, add_to_group_button)

        bot.send_message(
            message.chat.id,
            (
                "<b>اهلا بك في بوت لحماية المتطور الخاص بلميديا المقدم من سورس سوريا 🇸🇾</b>\n\n"
                "للمزيد من الخيارات استعمل في المجموعة /setting واتبع التعليمات\n"
                "للاطلاع على اشتراكك في البوت استخدم الامر /subscription في مجموعتك المفعلة"
            ),
            parse_mode="HTML",
            reply_markup=markup
        )
        print(f"[DEBUG] أرسلت رسالة الترحيب لـ user_id: {user_id}")
    except Exception as e:
        print(f"[ERROR] خطأ في معالجة /start لـ user_id: {user_id}: {e}")

# التعامل مع زر التحقق من الاشتراك
@bot.callback_query_handler(func=lambda call: call.data == "check_subscription")
def check_subscription_callback(call):
    try:
        user_id = call.from_user.id
        print(f"[DEBUG] تلقيت طلب تحقق من الاشتراك من user_id: {user_id}")
        if is_user_subscribed(user_id):
            markup = telebot.types.InlineKeyboardMarkup()
            programmer_button = telebot.types.InlineKeyboardButton("المطور", url=PROGRAMMER_URL)
            add_to_group_button = telebot.types.InlineKeyboardButton("➕ أضفني إلى مجموعتك", url=f"https://t.me/{bot.get_me().username}?startgroup=true")
            markup.add(programmer_button, add_to_group_button)

            bot.edit_message_text(
                (
                    "<b>اهلا بك في بوت لحماية المتطور الخاص بلميديا المقدم من سورس سوريا 🇸🇾</b>\n\n"
                    "للمزيد من الخيارات استعمل في المجموعة /setting واتبع التعليمات\n"
                    "للاطلاع على اشتراكك في البوت استخدم الامر /subscription في مجموعتك المفعلة"
                ),
                call.message.chat.id,
                call.message.message_id,
                parse_mode="HTML",
                reply_markup=markup
            )
            print(f"[DEBUG] أرسلت رسالة الترحيب بعد التحقق لـ user_id: {user_id}")
        else:
            bot.answer_callback_query(call.id, "⚠️ لم تشترك بعد! الرجاء الاشتراك في القناة أولاً.", show_alert=True)
            print(f"[DEBUG] المستخدم {user_id} لم يشترك بعد")
    except Exception as e:
        print(f"[ERROR] خطأ في معالجة check_subscription لـ user_id: {user_id}: {e}")


@bot.message_handler(commands=['rest'])
def restart_bot_command(message):
    """إعادة تشغيل البوت مع التأثيرات الجمالية"""
    if str(message.from_user.id) not in [DEVELOPER_ID, DEVELOPER_CHAT_ID]:
        bot.reply_to(message, "❌ هذا الأمر مخصص للمطور فقط.")
        print(f"[DEBUG] رفض /rest: user_id {message.from_user.id} ليس المطور")
        return

    chat_id = message.chat.id
    message_id = message.message_id

    # حفظ بيانات الرسالة في ملف JSON
    with open(DATA_FILE, "w", encoding='utf-8') as f:
        json.dump({"chat_id": chat_id}, f, ensure_ascii=False)

    progress_messages = [
        "■ 10%", "■■ 20%", "■■■ 30%", "■■■■ 40%", 
        "■■■■■ 50%", "■■■■■■ 60%", "■■■■■■■ 70%", 
        "■■■■■■■■ 80%", "■■■■■■■■■ 90%", "■■■■■■■■■■ 100%"
    ]

    msg = bot.send_message(chat_id, "🚀 <b>جاري تحديث البوت عزيزي المطور...</b> ⏳\n", parse_mode="HTML")

    for progress in progress_messages:
        time.sleep(0.5)
        bot.edit_message_text(
            f"🚀 <b>جاري تحديث البوت عزيزي المطور...</b> ⏳\n{progress}",
            chat_id, msg.message_id, parse_mode="HTML"
        )

    time.sleep(1)
    final_msg = bot.edit_message_text(
        "⎙ <b>جاري إعادة تشغيل البوت وجلب التحديثات...</b> ✨",
        chat_id, msg.message_id, parse_mode="HTML"
    )

    # حفظ معرف الرسالة الأخيرة
    with open(DATA_FILE, "w", encoding='utf-8') as f:
        json.dump({"chat_id": chat_id, "last_message_id": final_msg.message_id}, f, ensure_ascii=False)

    time.sleep(2)

    # حذف الرسالة الأخيرة
    try:
        bot.delete_message(chat_id, final_msg.message_id)
    except Exception as e:
        print(f"[ERROR] فشل في حذف رسالة إعادة التشغيل: {e}")

    # سحب التحديثات من GitHub
    try:
        subprocess.run(["git", "pull", "origin", "main"], check=True)
        print("[INFO] تم سحب التحديثات من GitHub بنجاح")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] فشل في سحب التحديثات من GitHub: {e}")

    # إعادة تشغيل البوت
    os.execv(sys.executable, ['python3', 'bot.py'])  # استبدل 'bot.py' باسم ملف البوت الفعلي

def send_restart_message():
    """إرسال رسالة جديدة بعد إعادة التشغيل"""
    time.sleep(3)  # تأخير للتأكد من جاهزية البوت
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding='utf-8') as f:
                data = json.load(f)
                chat_id = data.get("chat_id")
                if chat_id:
                    bot.send_message(
                        chat_id,
                        "✅ <b>تـم تشغـيل البوت بنجاح وجلب التحـديثات الأخـيرة عـزيزي المطور ✔️</b>",
                        parse_mode="HTML"
                    )
            os.remove(DATA_FILE)  # حذف الملف بعد الاستخدام
        except Exception as e:
            print(f"[ERROR] خطأ بعد إعادة التشغيل: {e}")

# استدعاء دالة إرسال الرسالة بعد إعادة التشغيل
if os.path.exists(DATA_FILE):
    send_restart_message()

# أمر التفعيل /ran
@bot.message_handler(commands=['ran'])
def activate_bot(message):
    print(f"[DEBUG] تلقيت أمر /ran من user_id: {message.from_user.id}, chat_id: {message.chat.id}")
    try:
        if str(message.from_user.id) != DEVELOPER_ID:
            bot.reply_to(message, "❌ هذا الأمر مخصص للمطور فقط!")
            print(f"[DEBUG] رفض /ran: user_id {message.from_user.id} ليس المطور")
            return
        
        chat_id = str(message.chat.id)
        if message.chat.type not in ['group', 'supergroup']:
            bot.reply_to(message, "❌ هذا الأمر يعمل فقط في المجموعات!")
            print(f"[DEBUG] رفض /ran: ليس في مجموعة")
            return
        
        args = message.text.split()[1:] if len(message.text.split()) > 1 else []
        if not args:
            bot.reply_to(message, "❌ استخدم: /ran <عدد الشهور>m أو /ran permanent")
            print(f"[DEBUG] رفض /ran: لا توجد وسيطات")
            return
        
        param = args[0].lower()
        if param == 'permanent':
            expiry = 'permanent'
        elif param.endswith('m') and param[:-1].isdigit():
            months = int(param[:-1])
            expiry_date = date.today() + timedelta(days=months * 30)
            expiry = expiry_date.strftime('%Y-%m-%d')
        else:
            bot.reply_to(message, "❌ تنسيق غير صحيح! مثال: /ran 1m أو /ran permanent")
            print(f"[DEBUG] رفض /ran: تنسيق غير صحيح")
            return
        
        if not is_bot_admin_with_permissions(message.chat.id):
            bot.reply_to(message, "❌ البوت ليس مشرفاً أو ليس لديه صلاحيات حذف الرسائل وحظر المستخدمين. الرجاء منحي الصلاحيات اللازمة!")
            print(f"[DEBUG] رفض /ran: البوت ليس مشرفاً")
            return
        
        activations[chat_id] = {
            'expiry_date': expiry,
            'activated_by': DEVELOPER_ID,
            'violence_enabled': False
        }
        save_activations()
        
        remaining = get_remaining_time(message.chat.id)
        bot.reply_to(message, (
            f"✅ تم التفعيل بنجاح!\n"
            f"🛡️ الوضع الحالي: نشط\n"
            f"⏳ المدة: {remaining}\n"
            f"📊 تقرير التفعيل: المجموعة محفوظة الآن."
        ))
        print(f"[DEBUG] تم تفعيل المجموعة {chat_id} بنجاح")
    except Exception as e:
        print(f"[ERROR] خطأ في معالجة /ran لـ user_id: {message.from_user.id}: {e}")

# أمر عرض الاشتراك /subscription
@bot.message_handler(commands=['subscription'])
def show_subscription(message):
    print(f"[DEBUG] تلقيت أمر /subscription من user_id: {message.from_user.id}, chat_id: {message.chat.id}")
    try:
        if message.chat.type not in ['group', 'supergroup']:
            bot.reply_to(message, "❌ هذا الأمر يعمل فقط في المجموعات!")
            print(f"[DEBUG] رفض /subscription: ليس في مجموعة")
            return
        
        if not is_user_admin(message.chat.id, message.from_user.id):
            bot.reply_to(message, "❌ هذا الأمر مخصص للمشرفين فقط!")
            print(f"[DEBUG] رفض /subscription: ليس مشرفاً")
            return
        
        remaining = get_remaining_time(message.chat.id)
        if remaining == "غير مفعل":
            bot.reply_to(message, "❌ اشتراك المجموعة غير مفعل. تواصل مع المطور للتفعيل.")
            print(f"[DEBUG] عرض /subscription: الاشتراك غير مفعل")
        else:
            bot.reply_to(message, f"🛡️ حالة الاشتراك: نشط\n⏳ الوقت المتبقي: {remaining}")
            print(f"[DEBUG] عرض /subscription: الاشتراك نشط، المدة: {remaining}")
    except Exception as e:
        print(f"[ERROR] خطأ في معالجة /subscription لـ user_id: {message.from_user.id}: {e}")

# أمر /setting لقائمة الإعدادات
@bot.message_handler(commands=['setting'])
def show_settings(message):
    print(f"[DEBUG] تلقيت أمر /setting من user_id: {message.from_user.id}, chat_id: {message.chat.id}")
    try:
        if message.chat.type not in ['group', 'supergroup']:
            bot.reply_to(message, "❌ هذا الأمر يعمل فقط في المجموعات!")
            return
        
        if not is_group_activated(message.chat.id):
            bot.reply_to(message, "❌ الاشتراك غير مفعل! لا يمكن الوصول إلى الإعدادات.")
            return
        
        if not is_user_admin(message.chat.id, message.from_user.id):
            bot.reply_to(message, "❌ هذا الأمر مخصص للمشرفين فقط!")
            return
        
        chat_id_str = str(message.chat.id)
        violence_status = "مفعل" if is_violence_enabled(message.chat.id) else "معطل"
        
        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        markup.add(telebot.types.InlineKeyboardButton(f"كاشف العنف: {violence_status}", callback_data="toggle_violence"))
        markup.add(telebot.types.InlineKeyboardButton("إدارة الكلمات المحظورة", callback_data="manage_banned_words"))
        markup.add(telebot.types.InlineKeyboardButton("قناة المطور", url=CHANNEL_URL))
        
        bot.send_message(message.chat.id, (
            "🛠️ <b>اهلاً بك في قائمة إعدادات البوت!</b>\n"
            "اختر الخدمة لتعديلها.\n\n"
            "⚠️ <b>تحذير لكاشف العنف:</b> هذه الميزة تحت التجربة وقد لا تكون دقيقة أو تقوم بمسح محتوى عادي. يمكنك تفعيلها وتعطيلها إذا لم تعجبك."
        ), parse_mode="HTML", reply_markup=markup)
    except Exception as e:
        print(f"[ERROR] خطأ في معالجة /setting لـ user_id: {message.from_user.id}: {e}")

# التعامل مع أزرار /setting
@bot.callback_query_handler(func=lambda call: call.data in ["toggle_violence", "manage_banned_words", "back_settings"])
def settings_callback(call):
    print(f"[DEBUG] تلقيت callback {call.data} من user_id: {call.from_user.id}, chat_id: {call.message.chat.id}")
    chat_id_str = str(call.message.chat.id)
    if call.data == "toggle_violence":
        activations[chat_id_str]['violence_enabled'] = not activations[chat_id_str].get('violence_enabled', False)
        save_activations()
        status = "تم تفعيل" if activations[chat_id_str]['violence_enabled'] else "تم تعطيل"
        bot.answer_callback_query(call.id, f"{status} كاشف العنف.")
        violence_status = "مفعل" if activations[chat_id_str]['violence_enabled'] else "معطل"
        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        markup.add(telebot.types.InlineKeyboardButton(f"كاشف العنف: {violence_status}", callback_data="toggle_violence"))
        markup.add(telebot.types.InlineKeyboardButton("إدارة الكلمات المحظورة", callback_data="manage_banned_words"))
        markup.add(telebot.types.InlineKeyboardButton("قناة المطور", url=CHANNEL_URL))
        bot.edit_message_text(
            (
                "🛠️ <b>اهلاً بك في قائمة إعدادات البوت!</b>\n"
                "اختر الخدمة لتعديلها.\n\n"
                "⚠️ <b>تحذير لكاشف العنف:</b> هذه الميزة تحت التجربة وقد لا تكون دقيقة أو تقوم بمسح محتوى عادي. يمكنك تفعيلها وتعطيلها إذا لم تعجبك."
            ),
            call.message.chat.id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=markup
        )
    elif call.data == "manage_banned_words":
        bot.answer_callback_query(call.id, "استخدم /l1 لإضافة كلمة محظورة، و /l1l لإزالتها.")
        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        back_button = telebot.types.InlineKeyboardButton("رجوع", callback_data="back_settings")
        markup.add(back_button)
        bot.edit_message_text(
            "البوت ميزة الكلمات متطورة جدا مقدمة من سورس سوريا حيث ان اي كلمة حتى لو اضفت اليها تشكيل سوف يتم مسحها تلقائينا ولن يسمح بلكلمة بلمجموعة مهما حاول احد كتابتها.\n\n"
            "لإضافة كلمة: /l1 كلمة\n"
            "لإزالة كلمة: /l1l كلمة",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    elif call.data == "back_settings":
        bot.delete_message(call.message.chat.id, call.message.message_id)

# أمر /l1 لإضافة كلمة محظورة
@bot.message_handler(commands=['l1'])
def add_banned_word(message):
    if message.chat.type not in ['group', 'supergroup']:
        bot.reply_to(message, "❌ هذا الأمر مخصص للمجموعات فقط.")
        return

    if not is_user_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ هذا الأمر متاح للمشرفين فقط.")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "❌ يرجى تزويد الكلمة التي تريد إضافتها.")
        return

    word = parts[1].strip()
    group_id = str(message.chat.id)

    banned_words.setdefault(group_id, [])
    if word.lower() in [w.lower() for w in banned_words[group_id]]:
        bot.reply_to(message, f"ℹ️ الكلمة '{word}' موجودة بالفعل في القائمة المحظورة لهذه المجموعة.")
    else:
        banned_words[group_id].append(word)
        save_banned_words()
        bot.reply_to(message, f"✅ تم إضافة الكلمة '{word}' إلى القائمة المحظورة للمجموعة.")

# أمر /l1l لإزالة كلمة محظورة
@bot.message_handler(commands=['l1l'])
def remove_banned_word(message):
    if message.chat.type not in ['group', 'supergroup']:
        bot.reply_to(message, "❌ هذا الأمر مخصص للمجموعات فقط.")
        return

    if not is_user_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ هذا الأمر متاح للمشرفين فقط.")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "❌ يرجى تزويد الكلمة التي تريد إزالتها.")
        return

    word = parts[1].strip()
    group_id = str(message.chat.id)

    if group_id not in banned_words or word.lower() not in [w.lower() for w in banned_words[group_id]]:
        bot.reply_to(message, f"ℹ️ الكلمة '{word}' غير موجودة في القائمة المحظورة لهذه المجموعة.")
    else:
        banned_words[group_id] = [w for w in banned_words[group_id] if w.lower() != word.lower()]
        save_banned_words()
        bot.reply_to(message, f"✅ تم إزالة الكلمة '{word}' من القائمة المحظورة للمجموعة.")

# أمر /ban لحظر مجموعة
@bot.message_handler(commands=['ban'])
def ban_group(message):
    print(f"[DEBUG] تلقيت أمر /ban من user_id: {message.from_user.id}")
    try:
        if str(message.from_user.id) != DEVELOPER_ID:
            bot.reply_to(message, "❌ هذا الأمر مخصص للمطور فقط!")
            print(f"[DEBUG] رفض /ban: user_id {message.from_user.id} ليس المطور")
            return
        
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            bot.reply_to(message, "❌ يرجى تزويد ID المجموعة. مثال: /ban -100123456789")
            print(f"[DEBUG] رفض /ban: لم يتم تزويد ID المجموعة")
            return
        
        group_id = parts[1].strip()
        banned_groups.add(group_id)
        save_banned_groups()
        
        try:
            if is_bot_admin_with_permissions(group_id):
                bot.send_message(
                    group_id,
                    "<b>عذرا تم حظر هذه المجموعة من قبل مطور البوت</b>",
                    parse_mode="HTML"
                )
                bot.leave_chat(group_id)
                print(f"[DEBUG] تم حظر ومغادرة المجموعة {group_id}")
            else:
                print(f"[DEBUG] البوت ليس مشرفًا في المجموعة {group_id}، تم الحظر بدون إرسال رسالة")
        except Exception as e:
            print(f"[DEBUG] فشل في إرسال رسالة حظر أو مغادرة المجموعة {group_id}: {e}")
        
        bot.reply_to(message, f"✅ تم حظر المجموعة {group_id} بنجاح!")
        print(f"[DEBUG] تم حظر المجموعة {group_id} بنجاح")
    except Exception as e:
        print(f"[ERROR] خطأ في معالجة /ban لـ user_id: {message.from_user.id}: {e}")

# أمر /unblock لإلغاء حظر مجموعة
@bot.message_handler(commands=['unblock'])
def unblock_group(message):
    print(f"[DEBUG] تلقيت أمر /unblock من user_id: {message.from_user.id}")
    try:
        if str(message.from_user.id) != DEVELOPER_ID:
            bot.reply_to(message, "❌ هذا الأمر مخصص للمطور فقط!")
            print(f"[DEBUG] رفض /unblock: user_id {message.from_user.id} ليس المطور")
            return
        
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            bot.reply_to(message, "❌ يرجى تزويد ID المجموعة. مثال: /unblock -100123456789")
            print(f"[DEBUG] رفض /unblock: لم يتم تزويد ID المجموعة")
            return
        
        group_id = parts[1].strip()
        if group_id in banned_groups:
            banned_groups.remove(group_id)
            save_banned_groups()
            bot.reply_to(message, f"✅ تم إلغاء حظر المجموعة {group_id} بنجاح!")
            print(f"[DEBUG] تم إلغاء حظر المجموعة {group_id} بنجاح")
        else:
            bot.reply_to(message, f"ℹ️ المجموعة {group_id} غير محظورة بالفعل.")
            print(f"[DEBUG] المجموعة {group_id} غير محظورة")
    except Exception as e:
        print(f"[ERROR] خطأ في معالجة /unblock لـ user_id: {message.from_user.id}: {e}")                
        
        

# أمر /stats
@bot.message_handler(commands=['stats'])
def show_stats(message):
    try:
        chat_id = str(message.chat.id)
        user_id = message.from_user.id
        
        if not is_user_admin(chat_id, user_id):
            bot.reply_to(message, "❌ عذرًا! هذا الأمر مخصص للمشرفين فقط.")
            print(f"[DEBUG] رفض /stats: user_id {user_id} ليس مشرفاً")
            return
        
        send_daily_report(chat_id)
        print(f"[DEBUG] أرسلت التقرير اليومي لـ chat_id: {chat_id}")
    except Exception as e:
        print(f"[ERROR] خطأ في معالجة /stats لـ user_id: {message.from_user.id}: {e}")

# الترحيب عند إضافة البوت إلى مجموعة
# الترحيب عند إضافة البوت إلى مجموعة
@bot.message_handler(content_types=['new_chat_members'])
def on_user_joins(message):
    try:
        print(f"[DEBUG] تلقيت حدث انضمام في chat_id: {message.chat.id}")
        for member in message.new_chat_members:
            if member.id == bot.get_me().id:
                chat_id = str(message.chat.id)
                # التحقق مما إذا كانت المجموعة محظورة
                if chat_id in banned_groups:
                    bot.send_message(
                        message.chat.id,
                        "<b>عذرا تم حظر هذه المجموعة من قبل مطور البوت</b>",
                        parse_mode="HTML"
                    )
                    bot.leave_chat(message.chat.id)
                    print(f"[DEBUG] المجموعة {chat_id} محظورة، تم الخروج منها")
                    return
                
                # إرسال إشعار للمطور
                adder_name = message.from_user.first_name if message.from_user.first_name else "غير معروف"
                group_title = message.chat.title or "بدون عنوان"
                group_id = message.chat.id
                group_link = "غير متوفر"
                try:
                    if is_bot_admin_with_permissions(message.chat.id):
                        group_link = bot.export_chat_invite_link(message.chat.id) or "غير متوفر"
                except Exception as e:
                    print(f"[DEBUG] فشل في الحصول على رابط المجموعة {group_id}: {e}")
                
                notification = (
                    f"🔔 تمت إضافة البوت إلى مجموعة جديدة:\n"
                    f"🏷️ اسم المجموعة: {group_title}\n"
                    f"🆔 ID المجموعة: {group_id}\n"
                    f"🔗 رابط المجموعة: {group_link}\n"
                    f"👤 الشخص الذي أضاف البوت: {adder_name}"
                )
                bot.send_message(DEVELOPER_ID, notification)
                print(f"[DEBUG] أرسلت إشعار إضافة مجموعة {chat_id} إلى المطور")
                
                # رسالة ترحيب في المجموعة
                if is_group_activated(message.chat.id):
                    remaining = get_remaining_time(message.chat.id)
                    bot.send_message(
                        message.chat.id,
                        (
                            "🦅 شكراً على إضافتي مجدداً!\n"
                            f"🛡️ لديك اشتراك نشط. الوقت المتبقي: {remaining}\n"
                            "سأقوم تلقائيًا بمراقبة الصور، الفيديوهات، الملصقات، والرموز التعبيرية."
                        )
                    )
                    print(f"[DEBUG] أرسلت رسالة ترحيب لإضافة البوت في المجموعة {chat_id}")
                else:
                    markup = telebot.types.InlineKeyboardMarkup()
                    contact_button = telebot.types.InlineKeyboardButton("تواصل مع المطور", url=PROGRAMMER_URL)
                    markup.add(contact_button)
                    bot.send_message(
                        message.chat.id,
                        (
                            "😔 أسف!\n"
                            "لا يمكنني العمل على فحص الميديا بدون تفعيل من قبل المطور.\n"
                            "📢 الرجاء التواصل معه للتفعيل."
                        ),
                        reply_markup=markup
                    )
                    print(f"[DEBUG] أرسلت رسالة طلب تفعيل للمجموعة {chat_id}")
    except Exception as e:
        print(f"[ERROR] خطأ في معالجة انضمام البوت لـ chat_id: {message.chat.id}: {e}")

# معالجة الصور
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    if not is_group_activated(message.chat.id):
        return
    
    file_id = message.photo[-1].file_id
    file_info = bot.get_file(file_id)
    file_link = f'https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}'

    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
        response = requests.get(file_link)
        tmp_file.write(response.content)
        temp_path = tmp_file.name

    res = check_image_safety(temp_path)
    if res == 'nude':
        handle_violation(message, 'صورة', 'إباحية')
    
    if is_violence_enabled(message.chat.id) and check_violence_safety(temp_path):
        handle_violation(message, 'صورة', 'عنف')
    
    os.remove(temp_path)

# معالجة الملصقات
@bot.message_handler(content_types=['sticker'])
def handle_sticker(message):
    if not is_group_activated(message.chat.id):
        return
    
    if message.sticker.thumb:
        file_info = bot.get_file(message.sticker.thumb.file_id)
        sticker_url = f'https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}'

        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
            response = requests.get(sticker_url)
            tmp_file.write(response.content)
            temp_path = tmp_file.name

        res = check_image_safety(temp_path)
        if res == 'nude':
            handle_violation(message, 'ملصق', 'إباحية')
        
        if is_violence_enabled(message.chat.id) and check_violence_safety(temp_path):
            handle_violation(message, 'ملصق', 'عنف')
        
        os.remove(temp_path)

# معالجة الفيديوهات
@bot.message_handler(content_types=['video'])
def handle_video(message):
    if not is_group_activated(message.chat.id):
        return
    
    file_info = bot.get_file(message.video.file_id)
    file_url = f'https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}'
    response = requests.get(file_url)
    if response.status_code == 200:
        media_queue.put((response.content, '.mp4', message, 'فيديو'))
    
    if is_violence_enabled(message.chat.id):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
            tmp_file.write(response.content)
            temp_path = tmp_file.name
        if check_video(temp_path):
            handle_violation(message, 'فيديو', 'عنف')
        os.remove(temp_path)

# معالجة الصور المتحركة (GIF)
@bot.message_handler(content_types=['animation'])
def handle_gif(message):
    if not is_group_activated(message.chat.id):
        return
    
    file_info = bot.get_file(message.animation.file_id)
    file_url = f'https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}'
    response = requests.get(file_url)
    if response.status_code == 200:
        media_queue.put((response.content, '.gif', message, 'صورة متحركة'))
    
    if is_violence_enabled(message.chat.id):
        try:
            with tempfile.NamedTemporaryFile(delete=True, suffix=".gif") as tmp_file:
                tmp_file.write(response.content)
                tmp_file.flush()  # التأكد من كتابة المحتوى
                temp_path = tmp_file.name
                if check_gif(temp_path):
                    handle_violation(message, 'صورة متحركة', 'عنف')
        except Exception as e:
            print(f"[ERROR] خطأ في معالجة الصورة المتحركة: {e}")
            # استمر دون توقف البوت
# معالجة الرموز التعبيرية المميزة
@bot.message_handler(func=lambda message: message.entities and any(entity.type == 'custom_emoji' for entity in message.entities))
def handle_custom_emoji(message):
    if not is_group_activated(message.chat.id):
        return
    
    custom_emoji_ids = [entity.custom_emoji_id for entity in message.entities if entity.type == 'custom_emoji']
    sticker_links = get_premium_sticker_info(custom_emoji_ids)
    for link in sticker_links:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
            response = requests.get(link)
            tmp_file.write(response.content)
            temp_path = tmp_file.name

        res = check_image_safety(temp_path)
        if res == 'nude':
            handle_violation(message, 'رمز تعبيري مميز', 'إباحية')
        
        if is_violence_enabled(message.chat.id) and check_violence_safety(temp_path):
            handle_violation(message, 'رمز تعبيري مميز', 'عنف')
        
        os.remove(temp_path)

# معالج زر رفع القيود
@bot.callback_query_handler(func=lambda call: call.data.startswith("unban_"))
def handle_unban_callback(call):
    try:
        user_id = call.from_user.id
        chat_id = call.message.chat.id
        restricted_user_id = call.data.split("_")[1]  # استخراج معرف المستخدم المقيد من callback_data
        
        print(f"[DEBUG] تلقيت طلب رفع قيود من user_id: {user_id} للمستخدم: {restricted_user_id} في chat_id: {chat_id}")
        
        # التحقق مما إذا كان المستخدم مشرفًا أو المطور
        if is_user_admin(str(chat_id), str(user_id)) or str(user_id) == DEVELOPER_ID:
            # رفع القيود عن المستخدم
            bot.restrict_chat_member(
                chat_id,
                restricted_user_id,
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_change_info=True,
                can_invite_users=True,
                can_pin_messages=True
            )
            bot.edit_message_text(
                (
                    f"✅ <b>تم رفع القيود!</b>\n"
                    f"👤 <b>العضو:</b> <a href='tg://user?id={restricted_user_id}'>{call.message.text.split('العضو:')[1].split('</a>')[0]}</a>\n"
                    f"🛡️ <b>بواسطة:</b> <a href='tg://user?id={user_id}'>{call.from_user.first_name}</a>"
                ),
                chat_id,
                call.message.message_id,
                parse_mode="HTML"
            )
            print(f"[DEBUG] تم رفع القيود عن user_id: {restricted_user_id} بواسطة user_id: {user_id}")
        else:
            bot.answer_callback_query(call.id, "🚫 لاتلعب! هذا الزر ليس لك، مخصص للمشرفين والمطور فقط!", show_alert=True)
            print(f"[DEBUG] رفض رفع القيود: user_id {user_id} ليس مشرفًا أو مطورًا")
            
    except Exception as e:
        print(f"[ERROR] خطأ في معالجة رفع القيود لـ user_id: {user_id}, restricted_user_id: {restricted_user_id}: {e}")
        bot.answer_callback_query(call.id, "⚠️ حدث خطأ أثناء محاولة رفع القيود!", show_alert=True)

# معالج رسالة كلمة "المطور"
@bot.message_handler(func=lambda message: message.text and "المطور" in message.text.lower())
def handle_developer_keyword(message):
    try:
        print(f"[DEBUG] تلقيت كلمة 'المطور' من user_id: {message.from_user.id}, chat_id: {message.chat.id}")
        bot.reply_to(message, "مطور البوت👈🏻 @S_Y_K")
        print(f"[DEBUG] أرسلت رد 'مطور البوت👈🏻 @S_Y_K' لـ user_id: {message.from_user.id}")
    except Exception as e:
        print(f"[ERROR] خطأ في معالجة كلمة 'المطور' لـ user_id: {message.from_user.id}: {e}")
        
# معالج رسالة كلمة "السورس"
@bot.message_handler(func=lambda message: message.text and "السورس" in message.text.lower())
def handle_source_keyword(message):
    try:
        print(f"[DEBUG] تلقيت كلمة 'السورس' من user_id: {message.from_user.id}, chat_id: {message.chat.id}")
        
        # الحصول على صورة البوت
        profile_photos = bot.get_user_profile_photos(BOT_ID, limit=1)
        photo_file_id = None
        if profile_photos.total_count > 0:
            photo_file_id = profile_photos.photos[0][-1].file_id  # أكبر حجم للصورة
        
        # إعداد الزر
        markup = telebot.types.InlineKeyboardMarkup()
        channel_button = telebot.types.InlineKeyboardButton("القناة الرسمية", url="https://t.me/F_U_2")
        markup.add(channel_button)
        
        # النص مع الرابط
        caption = '<a href="https://t.me/F_U_2">𝐒𝐘𝐑𝐈𝐀 𝐒𝐎𝐔𝐑𝐂𝐄 سورس سوريا</a>'
        
        if photo_file_id:
            bot.send_photo(
                message.chat.id,
                photo_file_id,
                caption=caption,
                parse_mode="HTML",
                reply_markup=markup,
                reply_to_message_id=message.message_id
            )
        else:
            bot.reply_to(message, caption, parse_mode="HTML", reply_markup=markup)
        
        print(f"[DEBUG] أرسلت رد '𝐒𝐘𝐑𝐈𝐀 𝐒𝐎𝐔𝐑𝐂𝐄 سورس سوريا' لـ user_id: {message.from_user.id}")
    except Exception as e:
        print(f"[ERROR] خطأ في معالجة كلمة 'السورس' لـ user_id: {message.from_user.id}: {e}")                                                                                                        
        

# معالجة الرسائل النصية للكلمات المحظورة
@bot.message_handler(content_types=['text'])
def handle_text(message):
    if not is_group_activated(message.chat.id):
        return
    
    if check_banned_words(message):
        handle_violation(message, 'كلمة', 'كلمة محظورة')

# معالجة الرسائل المعدلة (نصوص تحتوي على رموز تعبيرية مميزة)
@bot.edited_message_handler(content_types=['text'])
def handle_edited_custom_emoji_message(message):
    if not is_group_activated(message.chat.id):
        return
    
    user_id = message.from_user.id
    user_name = f"@{message.from_user.username}" if message.from_user.username else f"({user_id})"

    if message.entities:
        custom_emoji_ids = [entity.custom_emoji_id for entity in message.entities if entity.type == 'custom_emoji']
        if custom_emoji_ids:
            sticker_links = get_premium_sticker_info(custom_emoji_ids)
            for link in sticker_links:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                    response = requests.get(link)
                    tmp_file.write(response.content)
                    temp_path = tmp_file.name

                res = check_image_safety(temp_path)
                if res == 'nude':
                    bot.delete_message(message.chat.id, message.message_id)
                    alert_message = (
                        f"🚨 <b>تنبيه فوري!</b>\n"
                        f"🔗 <b>المستخدم:</b> {user_name} <b>عدّل رسالة وأضاف رمز تعبيري مميز غير لائق!</b>\n"
                        "📢 <b>يرجى اتخاذ الإجراء اللازم.</b>"
                    )
                    bot.send_message(message.chat.id, alert_message, parse_mode="HTML")
                    handle_violation(message, 'رمز تعبيري مميز معدل', 'إباحية')
                
                if is_violence_enabled(message.chat.id) and check_violence_safety(temp_path):
                    bot.delete_message(message.chat.id, message.message_id)
                    alert_message = (
                        f"🚨 <b>تنبيه فوري!</b>\n"
                        f"🔗 <b>المستخدم:</b> {user_name} <b>عدّل رسالة وأضاف رمز تعبيري مميز عنيف!</b>\n"
                        "📢 <b>يرجى اتخاذ الإجراء اللازم.</b>"
                    )
                    bot.send_message(message.chat.id, alert_message, parse_mode="HTML")
                    handle_violation(message, 'رمز تعبيري مميز معدل', 'عنف')
                
                os.remove(temp_path)

# معالجة الميديا المعدلة
@bot.edited_message_handler(content_types=['photo', 'video', 'animation', 'sticker'])
def handle_edited_media(message):
    if not is_group_activated(message.chat.id):
        return
    
    user_id = message.from_user.id
    user_name = f"@{message.from_user.username}" if message.from_user.username else f"({user_id})"

    if message.content_type == 'photo':
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        file_link = f'https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}'

        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
            response = requests.get(file_link)
            tmp_file.write(response.content)
            temp_path = tmp_file.name

        res = check_image_safety(temp_path)
        if res == 'nude':
            bot.delete_message(message.chat.id, message.message_id)
            alert_message = (
                f"🚨 <b>تنبيه فوري!</b>\n"
                f"🔗 <b>المستخدم:</b> {user_name} <b>عدّل رسالة إلى صورة غير لائقة!</b>\n"
                "📢 <b>يرجى اتخاذ الإجراء اللازم.</b>"
            )
            bot.send_message(message.chat.id, alert_message, parse_mode="HTML")
            handle_violation(message, 'صورة معدلة', 'إباحية')
        
        if is_violence_enabled(message.chat.id) and check_violence_safety(temp_path):
            bot.delete_message(message.chat.id, message.message_id)
            alert_message = (
                f"🚨 <b>تنبيه فوري!</b>\n"
                f"🔗 <b>المستخدم:</b> {user_name} <b>عدّل رسالة إلى صورة عنيفة!</b>\n"
                "📢 <b>يرجى اتخاذ الإجراء اللازم.</b>"
            )
            bot.send_message(message.chat.id, alert_message, parse_mode="HTML")
            handle_violation(message, 'صورة معدلة', 'عنف')
        
        os.remove(temp_path)

    elif message.content_type == 'video':
        handle_video(message)
    elif message.content_type == 'animation':
        handle_gif(message)
    elif message.content_type == 'sticker':
        handle_sticker(message)

# تحميل البيانات عند التشغيل وتشغيل معالج الفيديوهات
load_violations()
load_banned_groups()
load_reports()
load_activations()
load_banned_words()
threading.Thread(target=process_media_worker, daemon=True).start()

# تشغيل البوت
def restart_bot():
    """إعادة تشغيل البوت"""
    print("[INFO] إعادة تشغيل البوت التلقائية...")
    os.execv(sys.executable, ['python3', 'zx5.py'])  # تأكد من أن 'zx5.py' هو اسم ملف البوت

def schedule_restart():
    """جدولة إعادة التشغيل كل 5 دقائق"""
    print("[INFO] جدولة إعادة تشغيل البوت بعد 5 دقائق...")
    threading.Timer(300, restart_bot).start()  # جدولة إعادة التشغيل بعد 300 ثانية

if __name__ == "__main__":
    # تشغيل خيط التحقق من تغيير اليوم
    threading.Thread(target=check_day_change, daemon=True).start()
    # جدولة أول إعادة تشغيل
    schedule_restart()
    print("البوت يعمل الآن...")

    while True:
        try:
            bot.polling(non_stop=True, timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"[ERROR] خطأ في تشغيل البوت: {e}")
            print("[INFO] جاري إعادة المحاولة بعد 10 ثوان...")
            time.sleep(10)
            continue
