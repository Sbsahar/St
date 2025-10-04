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
import subprocess  # جديد: لـ FFmpeg في كاشف العنف
from transformers import pipeline  # جديد: لنموذج العنف

# إعدادات البوت
TOKEN = '8196365414:AAEUhb_Puvx8IVrKvbLAuJ8xz1IeRWw-2Ec'
CHANNEL_USERNAME = '@SYR_SB'
CHANNEL_URL = 'https://t.me/SYR_SB'
PROGRAMMER_URL = 'https://t.me/S_Y_K'
DEVELOPER_ID = '6789179634'  # معرف المطور
NSFW_THRESHOLD = 0.5  # العتبة القابلة للتخصيص
bot = telebot.TeleBot(TOKEN)
BOT_ID = bot.get_me().id

# ملفات التخزين وقائمة الرسائل المفحوصة
VIOLATIONS_FILE = "user_violations.json"
REPORTS_FILE = "daily_reports.json"
ACTIVATIONS_FILE = "activations.json"
BANNED_WORDS_FILE = "banned_words.json"  # جديد: للكلمات المحظورة
user_violations = {}
daily_reports = {}
activations = {}
banned_words = {}  # جديد
current_date = date.today().isoformat()
media_queue = Queue()  # قائمة انتظار لمعالجة الفيديوهات

# جديد: تحميل نموذج كاشف العنف
print("📦 جاري تحميل نموذج الكشف عن العنف والدماء...")
violence_classifier = pipeline("image-classification", model="Falconsai/nsfw_image_detection")
print("✅ تم تحميل النموذج بنجاح!")

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

# تحميل التفعيلات (مع violence_enabled)
def load_activations():
    global activations
    try:
        with open(ACTIVATIONS_FILE, 'r', encoding='utf-8') as f:
            activations = json.load(f)
        # إضافة violence_enabled إذا غير موجود
        for chat_id in activations:
            if 'violence_enabled' not in activations[chat_id]:
                activations[chat_id]['violence_enabled'] = False
    except (FileNotFoundError, json.JSONDecodeError):
        activations = {}

# حفظ التفعيلات
def save_activations():
    with open(ACTIVATIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(activations, f, ensure_ascii=False, indent=4)

# جديد: تحميل الكلمات المحظورة
def load_banned_words():
    global banned_words
    try:
        with open(BANNED_WORDS_FILE, 'r', encoding='utf-8') as f:
            banned_words = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        banned_words = {}

# جديد: حفظ الكلمات المحظورة
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

# جديد: التحقق إذا كان كاشف العنف مفعل
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

# جديد: فحص الصور للعنف
def check_violence_safety(image_path):
    try:
        image = Image.open(image_path).convert("RGB")
        results = violence_classifier(image)
        for r in results:
            label = r.get('label', '').lower()
            score = float(r.get('score', 0))
            if label in ['violence', 'gore', 'weapon'] and score >= NSFW_THRESHOLD:
                print(f"[VIOLENCE DETECTED] {label} ({score}) في {image_path}")
                return True
        return False
    except Exception as e:
        print(f"⚠️ خطأ في فحص العنف: {e}")
        return False

# جديد: استخراج إطارات الفيديو لفحص العنف
def extract_frames(video_path, output_folder):
    os.makedirs(output_folder, exist_ok=True)
    cmd = [
        'ffmpeg', '-i', video_path,
        '-vf', 'fps=1',
        f'{output_folder}/frame_%03d.jpg',
        '-hide_banner', '-loglevel', 'error'
    ]
    subprocess.run(cmd, check=True)

# جديد: فحص الفيديو للعنف
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

# جديد: فحص GIF للعنف
def check_gif(gif_path):
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as frame:
            cmd = [
                'ffmpeg', '-i', gif_path, '-vframes', '1',
                '-q:v', '2', frame.name,
                '-hide_banner', '-loglevel', 'error'
            ]
            subprocess.run(cmd, check=True)
            result = check_violence_safety(frame.name)
        os.remove(frame.name)
        return result
    except Exception as e:
        print(f"⚠️ خطأ في فحص GIF: {e}")
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

# جديد: تطبيع النص للكلمات المحظورة
def normalize_text(text):
    text = re.sub(r'[\u0617-\u061A\u064B-\u065F]', '', text)
    text = re.sub(r'[-\s\u0640]+', '', text)
    return text.lower()

# جديد: فحص الكلمات المحظورة
def check_banned_words(message):
    chat_id_str = str(message.chat.id)
    if chat_id_str not in banned_words:
        return False
    text = normalize_text(message.text or message.caption or "")
    for word in banned_words[chat_id_str]:
        if normalize_text(word) in text:
            return True
    return False

# معالجة المخالفات مع تسجيل التقرير (معدل لدعم violation_type)
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
                "🛡️ <b>ملاحظة:</b> المستخدم مشرف لايمكن تقيده إذا تجاوز الحد\n"
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
            bot.send_message(chat_id, (
                f"🚫 <b>تم تقييد العضو!</b>\n"
                f"👤 <b>العضو:</b> <a href='tg://user?id={user_id}'>{message.from_user.first_name}</a>\n"
                f"⏳ <b>المدة:</b> 24 ساعة\n"
                "📢 <b>السبب:</b> تجاوز 10 مخالفات!"
            ), parse_mode="HTML")
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
            print(f"User {user_id} is the developer, bypassing subscription check.")
            return True
        
        chat_member = bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        status = chat_member.status
        print(f"User {user_id} status in channel @{CHANNEL_USERNAME}: {status}")
        return status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"Error checking subscription for user {user_id}: {e}")
        return False

# جديد: دالة استخراج معلومات الملصقات المميزة
def get_premium_sticker_info(custom_emoji_ids):
    try:
        sticker_set = bot.get_custom_emoji_stickers(custom_emoji_ids)
        return [f'https://api.telegram.org/file/bot{TOKEN}/{bot.get_file(sticker.thumb.file_id).file_path}' for sticker in sticker_set if sticker.thumb]
    except Exception as e:
        print(f"Error retrieving sticker info: {e}")
        return []

# معالجة الصور (معدل لدعم العنف)
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
    
    # جديد: فحص العنف إذا مفعل
    if is_violence_enabled(message.chat.id) and check_violence_safety(temp_path):
        handle_violation(message, 'صورة', 'عنف')
    
    os.remove(temp_path)

# معالجة الملصقات (معدل لدعم العنف)
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
        
        # جديد: فحص العنف إذا مفعل
        if is_violence_enabled(message.chat.id) and check_violence_safety(temp_path):
            handle_violation(message, 'ملصق', 'عنف')
        
        os.remove(temp_path)

# معالجة الفيديوهات (معدل لدعم العنف)
@bot.message_handler(content_types=['video'])
def handle_video(message):
    if not is_group_activated(message.chat.id):
        return
    
    file_info = bot.get_file(message.video.file_id)
    file_url = f'https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}'
    response = requests.get(file_url)
    if response.status_code == 200:
        media_queue.put((response.content, '.mp4', message, 'فيديو'))
    
    # جديد: فحص العنف إذا مفعل
    if is_violence_enabled(message.chat.id):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
            tmp_file.write(response.content)
            temp_path = tmp_file.name
        if check_video(temp_path):
            handle_violation(message, 'فيديو', 'عنف')
        os.remove(temp_path)

# معالجة الصور المتحركة (GIF) (معدل لدعم العنف)
@bot.message_handler(content_types=['animation'])
def handle_gif(message):
    if not is_group_activated(message.chat.id):
        return
    
    file_info = bot.get_file(message.animation.file_id)
    file_url = f'https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}'
    response = requests.get(file_url)
    if response.status_code == 200:
        media_queue.put((response.content, '.gif', message, 'صورة متحركة'))
    
    # جديد: فحص العنف إذا مفعل
    if is_violence_enabled(message.chat.id):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".gif") as tmp_file:
            tmp_file.write(response.content)
            temp_path = tmp_file.name
        if check_gif(temp_path):
            handle_violation(message, 'صورة متحركة', 'عنف')
        os.remove(temp_path)

# معالجة الرموز التعبيرية المميزة (معدل لدعم العنف)
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
        
        # جديد: فحص العنف إذا مفعل
        if is_violence_enabled(message.chat.id) and check_violence_safety(temp_path):
            handle_violation(message, 'رمز تعبيري مميز', 'عنف')
        
        os.remove(temp_path)

# جديد: معالجة الرسائل النصية للكلمات المحظورة
@bot.message_handler(content_types=['text'])
def handle_text(message):
    if not is_group_activated(message.chat.id):
        return
    
    if check_banned_words(message):
        handle_violation(message, 'كلمة', 'كلمة محظورة')

# معالجة الرسائل المعدلة (نصوص تحتوي على رموز تعبيرية مميزة) (معدل لدعم العنف)
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
                
                # جديد: فحص العنف إذا مفعل
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

# معالجة الميديا المعدلة (معدل لدعم العنف)
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
        
        # جديد: فحص العنف إذا مفعل
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

# جديد: أمر /l1 لإضافة كلمة محظورة
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

# جديد: أمر /l1l لإزالة كلمة محظورة
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

# جديد: أمر /setting لقائمة الإعدادات
@bot.message_handler(commands=['setting'])
def show_settings(message):
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
    markup.add(telebot.types.InlineKeyboardButton("رجوع", callback_data="back_settings"))
    
    bot.send_message(message.chat.id, (
        "🛠️ <b>اهلاً بك في قائمة إعدادات البوت!</b>\n"
        "اختر الخدمة لتعديلها.\n\n"
        "⚠️ <b>تحذير لكاشف العنف:</b> هذه الميزة تحت التجربة وقد لا تكون دقيقة أو تقوم بمسح محتوى عادي. يمكنك تفعيلها وتعطيلها إذا لم تعجبك."
    ), parse_mode="HTML", reply_markup=markup)

# جديد: التعامل مع أزرار /setting
@bot.callback_query_handler(func=lambda call: call.data in ["toggle_violence", "manage_banned_words", "back_settings"])
def settings_callback(call):
    chat_id_str = str(call.message.chat.id)
    if call.data == "toggle_violence":
        activations[chat_id_str]['violence_enabled'] = not activations[chat_id_str].get('violence_enabled', False)
        save_activations()
        status = "تم تفعيل" if activations[chat_id_str]['violence_enabled'] else "تم تعطيل"
        bot.answer_callback_query(call.id, f"{status} كاشف العنف.")
        # إعادة عرض القائمة
        violence_status = "مفعل" if activations[chat_id_str]['violence_enabled'] else "معطل"
        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        markup.add(telebot.types.InlineKeyboardButton(f"كاشف العنف: {violence_status}", callback_data="toggle_violence"))
        markup.add(telebot.types.InlineKeyboardButton("إدارة الكلمات المحظورة", callback_data="manage_banned_words"))
        markup.add(telebot.types.InlineKeyboardButton("رجوع", callback_data="back_settings"))
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
    elif call.data == "back_settings":
        bot.delete_message(call.message.chat.id, call.message.message_id)

# أمر البدء مع الاشتراك الإجباري والأزرار
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    
    if not is_user_subscribed(user_id):
        markup = telebot.types.InlineKeyboardMarkup()
        subscribe_button = telebot.types.InlineKeyboardButton("اشترك الآن", url=CHANNEL_URL)
        check_button = telebot.types.InlineKeyboardButton("🔄 تحقق من الاشتراك", callback_data="check_subscription")
        markup.add(subscribe_button, check_button)
        
        bot.send_message(
            message.chat.id,
            f"⚠️ <b>تنبيه:</b> يجب عليك الاشتراك في القناة أولاً لاستخدام البوت!\n\n"
            f"👉 <a href='{CHANNEL_URL}'>اضغط هنا للاشتراك</a>",
            parse_mode="HTML",
            reply_markup=markup
        )
        return

    markup = telebot.types.InlineKeyboardMarkup()
    programmer_button = telebot.types.InlineKeyboardButton("المطور", url=PROGRAMMER_URL)
    add_to_group_button = telebot.types.InlineKeyboardButton("➕ أضفني إلى مجموعتك", url=f"https://t.me/{bot.get_me().username}?startgroup=true")
    markup.add(programmer_button, add_to_group_button)

    bot.send_message(
        message.chat.id,
        (
            "🛡️ <b>مرحبا بك في بوت الحماية المتطور المقدم من سورس سوريا </b>\n"
            "أنا هنا لحماية مجموعاتك من المحتوى غير اللائق تلقائيًا.\n"
            "📊 <b>الأستخدام</b> استخدم /stats لعرض التقرير اليومي.\ في المجموعة المفعلة\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚡ <b>أضفني الآن واستمتع بالأمان!</b>"
        ),
        parse_mode="HTML",
        reply_markup=markup
    )

# التعامل مع زر التحقق من الاشتراك
@bot.callback_query_handler(func=lambda call: call.data == "check_subscription")
def check_subscription_callback(call):
    user_id = call.from_user.id
    if is_user_subscribed(user_id):
        markup = telebot.types.InlineKeyboardMarkup()
        programmer_button = telebot.types.InlineKeyboardButton("المطور", url=PROGRAMMER_URL)
        add_to_group_button = telebot.types.InlineKeyboardButton("➕ أضفني إلى مجموعتك", url=f"https://t.me/{bot.get_me().username}?startgroup=true")
        markup.add(programmer_button, add_to_group_button)

        bot.edit_message_text(
            (
                "🛡️ <b>مرحبًا بك في بوت syria security</b>\n"
                "أنا هنا لحماية مجموعاتك من المحتوى غير اللائق تلقائيًا.\n"
                "📊 <b>للمشرفين:</b> استخدم /stats لعرض التقرير اليومي.\n"
                "━━━━━━━━━━━━━━━━━━━━━━━\n"
                "⚡ <b>أضفني الآن واستمتع بالأمان!</b>"
            ),
            call.message.chat.id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=markup
        )
    else:
        bot.answer_callback_query(call.id, "⚠️ لم تشترك بعد! الرجاء الاشتراك في القناة أولاً.", show_alert=True)

# أمر التفعيل /ran (معدل لإضافة violence_enabled)
@bot.message_handler(commands=['ran'])
def activate_bot(message):
    if str(message.from_user.id) != DEVELOPER_ID:
        bot.reply_to(message, "❌ هذا الأمر مخصص للمطور فقط!")
        return
    
    chat_id = str(message.chat.id)
    if message.chat.type not in ['group', 'supergroup']:
        bot.reply_to(message, "❌ هذا الأمر يعمل فقط في المجموعات!")
        return
    
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    if not args:
        bot.reply_to(message, "❌ استخدم: /ran <عدد الشهور>m أو /ran permanent")
        return
    
    param = args[0].lower()
    if param == 'permanent':
        expiry = 'permanent'
    elif param.endswith('m') and param[:-1].isdigit():
        months = int(param[:-1])
        expiry_date = date.today() + timedelta(days=months * 30)  # تقريباً 30 يوم للشهر
        expiry = expiry_date.strftime('%Y-%m-%d')
    else:
        bot.reply_to(message, "❌ تنسيق غير صحيح! مثال: /ran 1m أو /ran permanent")
        return
    
    if not is_bot_admin_with_permissions(message.chat.id):
        bot.reply_to(message, "❌ البوت ليس مشرفاً أو ليس لديه صلاحيات حذف الرسائل وحظر المستخدمين. الرجاء منحي الصلاحيات اللازمة!")
        return
    
    activations[chat_id] = {
        'expiry_date': expiry,
        'activated_by': DEVELOPER_ID,
        'violence_enabled': False  # جديد: افتراضياً معطل
    }
    save_activations()
    
    remaining = get_remaining_time(message.chat.id)
    bot.reply_to(message, (
        f"✅ تم التفعيل بنجاح!\n"
        f"🛡️ الوضع الحالي: نشط\n"
        f"⏳ المدة: {remaining}\n"
        f"📊 تقرير التفعيل: المجموعة محفوظة الآن."
    ))

# أمر عرض الاشتراك /subscription
@bot.message_handler(commands=['subscription'])
def show_subscription(message):
    if message.chat.type not in ['group', 'supergroup']:
        bot.reply_to(message, "❌ هذا الأمر يعمل فقط في المجموعات!")
        return
    
    if not is_user_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ هذا الأمر مخصص للمشرفين فقط!")
        return
    
    remaining = get_remaining_time(message.chat.id)
    if remaining == "غير مفعل":
        bot.reply_to(message, "❌ اشتراك المجموعة غير مفعل. تواصل مع المطور للتفعيل.")
    else:
        bot.reply_to(message, f"🛡️ حالة الاشتراك: نشط\n⏳ الوقت المتبقي: {remaining}")

# الترحيب عند إضافة البوت إلى مجموعة
@bot.message_handler(content_types=['new_chat_members'])
def on_user_joins(message):
    for member in message.new_chat_members:
        if member.id == bot.get_me().id:
            chat_id = message.chat.id
            if is_group_activated(chat_id):
                remaining = get_remaining_time(chat_id)
                bot.send_message(
                    chat_id,
                    (
                        "🦅 <b>شكراً على إضافتي مجدداً!</b>\n"
                        f"🛡️ لديك اشتراك نشط. الوقت المتبقي: {remaining}\n"
                        "سأقوم تلقائيًا بمراقبة الصور، الفيديوهات، الملصقات، والرموز التعبيرية.\n"
                        "📊 <b>للمشرفين:</b> استخدم /stats لعرض الإحصائيات اليومية أو /subscription للاشتراك.\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━\n"
                        "⚡ <b>مجموعتك الآن تحت الحماية الكاملة!</b>"
                    ),
                    parse_mode="HTML"
                )
            else:
                markup = telebot.types.InlineKeyboardMarkup()
                contact_button = telebot.types.InlineKeyboardButton("تواصل مع المطور", url=PROGRAMMER_URL)
                markup.add(contact_button)
                bot.send_message(
                    chat_id,
                    (
                        "😔 <b>أسف!</b>\n"
                        "لا يمكنني العمل على فحص الميديا بدون تفعيل من قبل المطور.\n"
                        "📢 الرجاء التواصل معه للتفعيل."
                    ),
                    parse_mode="HTML",
                    reply_markup=markup
                )

# أمر عرض الإحصائيات اليومية
@bot.message_handler(commands=['stats'])
def show_stats(message):
    chat_id = str(message.chat.id)
    user_id = message.from_user.id
    
    if not is_user_admin(chat_id, user_id):
        bot.reply_to(message, "❌ <b>عذرًا!</b> هذا الأمر مخصص للمشرفين فقط.", parse_mode="HTML")
        return
    
    send_daily_report(chat_id)

# إرسال التقرير اليومي عند الطلب
def send_daily_report(chat_id):
    chat_id = str(chat_id)
    if chat_id in daily_reports and daily_reports[chat_id]:
        report_msg = (
            "📊 <b>التقرير اليومي للمجموعة</b>\n"
            f"🕒 <b>تاريخ التقرير:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        
        violations = daily_reports[chat_id]
        report_msg += f"📈 <b>إجمالي المخالفات:</b> {len(violations)}\n\n"
        for idx, violation in enumerate(violations, 1):
            report_msg += (
                f"#{idx} <b>المستخدم:</b> {violation['user_name']} ({violation['username']})\n"
                f"🆔 <b>المعرف:</b> <code>{violation['user_id']}</code>\n"
                f"⚠️ <b>نوع المخالفة:</b> {violation['violation_type']}\n"
                f"⏰ <b>الوقت:</b> {violation['time']}\n"
                f"🔢 <b>عدد المخالفات الكلي:</b> {violation['total_violations']}\n"
                "───────────────────\n"
            )
        report_msg += "━━━━━━━━━━━━━━━━━━━━━━━\n📢 <b>البوت يعمل بكفاءة لحماية المجموعة!</b>"
        
        if len(report_msg) > 4096:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode='w', encoding='utf-8') as tmp_file:
                tmp_file.write(report_msg.replace('<b>', '').replace('</b>', '').replace('<a href="tg://user?id=', '').replace('">', ' - ').replace('</a>', '').replace('<code>', '`').replace('</code>', '`'))
                tmp_file_path = tmp_file.name
            
            with open(tmp_file_path, 'rb') as file:
                bot.send_document(chat_id, file, caption=(
                    "📈 <b>تنبيه:</b> المخالفات كثيرة جدًا لإرسالها في رسالة واحدة!\n"
                    "📎 <b>الملف المرفق يحتوي على التقرير اليومي الكامل.</b>"
                ), parse_mode="HTML")
            os.unlink(tmp_file_path)
        else:
            bot.send_message(chat_id, report_msg, parse_mode="HTML")
    else:
        bot.send_message(chat_id, "✅ <b>لا توجد مخالفات مسجلة اليوم!</b>\n📢 <b>المجموعة نظيفة وآمنة!</b>", parse_mode="HTML")

# تصفير التقارير اليومية عند تغير اليوم (مع إزالة التفعيلات المنتهية وإرسال تنبيه)
def reset_daily_reports():
    global daily_reports
    daily_reports = {}
    save_reports()
    print("✅ تم تصفير التقارير اليومية.")
    
    # إزالة التفعيلات المنتهية وإرسال تنبيه
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
                "🚨 <b>تنبيه فوري:</b> انتهى اشتراك البوت!\n📢 يرجى التواصل مع المطور للتفعيل إذا أردت إعادة تفعيل البوت.",
                parse_mode="HTML",
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

# تحميل البيانات عند التشغيل وتشغيل معالج الفيديوهات
load_violations()
load_reports()
load_activations()
load_banned_words()  # جديد
threading.Thread(target=process_media_worker, daemon=True).start()

# تشغيل البوت
if __name__ == "__main__":
    threading.Thread(target=check_day_change, daemon=True).start()
    print("البوت يعمل الآن...")
    bot.polling(non_stop=True)
