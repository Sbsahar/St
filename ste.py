import channel_checker
from youtube_module import YoutubeModule
import telebot
import re
import opennsfw2 as n2
from PIL import Image
from yt_dlp import YoutubeDL
import tempfile
import tempfile
import os
import random
import threading
import requests
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import time
import json
from telebot.types import BotCommand
import logging
from telebot.types import ChatMemberUpdated
# إعدادات التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()]
)

TOKEN = '7327783438:AAGmnM5fE1aKO-bEYNfb1dqUHOfLryH3a6g'
YOUTUBE_API_KEY = 'AIzaSyBG81yezyxy-SE4cd_-JCK55gEzHkPV9aw'
BOT_USERNAME = '@SY_SBbot'
CHANNEL_URL = 'https://t.me/SYR_SB'
CHANNEL_USERNAME = 'SYR_SB' 
DEVELOPER_CHAT_ID = '6789179634'
DEVELOPER_CHAT_ID = 6789179634
VIDEO_URL = "https://t.me/srevbo67/5" 
bot = telebot.TeleBot(TOKEN)
youtube_module = YoutubeModule(bot, YOUTUBE_API_KEY, BOT_USERNAME)
youtube_module.setup_handlers()
welcome_messages = {}
active_mentions = {}
stop_mentions = {}
stop_mentions_flag = {}
welcome_pending = {}
# تخزين عمليات الحظر لكل مشرف
ban_tracker = {}
pending_replies = {} 
bot_promoted_admins = {}
pending_promotions = {}
users = set()
warnings = {}
groups = set()
user_violations = {}
activated_groups = {}  # {group_id: report_chat_id}
daily_reports = {}     # {group_id: {"banned": [], "muted": [], "deleted_content": [], "manual_actions": []}}
DETECTION_FILE = "detection_status.json"
group_detection_status = {}
REPLIES_FILE = "replies.json"
BANNED_WORDS_FILE = "banned_words.json"
REPORT_GROUPS_FILE = "report_groups.json"
report_groups = {}

# القاموس العام لتخزين الكلمات لكل مجموعة بصيغة {"group_id": ["كلمة1", "كلمة2", ...]}
banned_words = {}
# قائمة الصلاحيات الافتراضية مع أسمائها بالعربية
PERMISSION_NAMES = {
    "can_delete_messages": "حذف الرسائل",
    "can_restrict_members": "تقييد الأعضاء",
    "can_invite_users": "إضافة أعضاء",
    "can_pin_messages": "تثبيت الرسائل",
    "can_change_info": "تغيير معلومات المجموعة",
    "can_manage_chat": "إدارة المجموعة"
}

DEFAULT_PERMISSIONS = {perm: False for perm in PERMISSION_NAMES}

gbt_enabled = False
commands = [
    BotCommand('gbt', 'استخدام الذكاء الاصطناعي (GPT)'),
    BotCommand('opengbt', 'تفعيل الذكاء الاصطناعي (للمشرفين فقط)'),
    BotCommand('closegbt', 'تعطيل الذكاء الاصطناعي (للمشرفين فقط)')
]
bot.set_my_commands(commands)
def load_welcome():
    global welcome_messages
    try:
        with open('welcome.json', 'r') as f:
            welcome_messages = json.load(f)
    except FileNotFoundError:
        welcome_messages = {}
def load_detection_status():
    global group_detection_status
    try:
        with open(DETECTION_FILE, 'r', encoding='utf-8') as f:
            group_detection_status = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        group_detection_status = {}
def save_detection_status():
    with open(DETECTION_FILE, 'w', encoding='utf-8') as f:
        json.dump(group_detection_status, f, ensure_ascii=False, indent=4)
def load_report_groups():
    global report_groups
    try:
        with open(REPORT_GROUPS_FILE, "r", encoding="utf-8") as f:
            report_groups = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        report_groups = {}

# حفظ إعدادات التقارير
def save_report_groups():
    with open(REPORT_GROUPS_FILE, "w", encoding="utf-8") as f:
        json.dump(report_groups, f, ensure_ascii=False, indent=4)

load_report_groups()


        


def save_welcome():
    with open('welcome.json', 'w') as f:
        json.dump(welcome_messages, f, indent=2)
def get_blackbox_response(user_input):
    """ إرسال استفسار إلى Blackbox AI واسترجاع الرد """
    url = "https://api.blackbox.ai/api/chat"
    headers = {
        "Content-Type": "application/json"
    }
    json_data = json.dumps({
        "messages": [{"content": user_input, "role": "user"}],
        "model": "deepseek-ai/DeepSeek-V3",
        "max_tokens": "1024"
    })
    max_retries = 3  
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, data=json_data, timeout=10)  # زيادة المهلة
            print(f"Response Status: {response.status_code}")
            print(f"Response Text: {response.text}")
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"Parsed Response: {data}")
                    return data.get("response", "⚠️ لا يوجد رد متاح.")
                except json.JSONDecodeError:
                    if response.text.strip():
                        return response.text
                    else:
                        return "⚠️ لا يوجد رد متاح."
            else:
                return f"⚠️ خطأ: {response.status_code} - {response.text}"     
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)  
            else:
                return "الخدمة مشغولة حاليًا، يرجى المحاولة مرة أخرى لاحقًا."
def load_replies():
    if os.path.exists(REPLIES_FILE):
        with open(REPLIES_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    return {}  # إذا ما كان الملف موجود، يرجّع قاموس فارغ

# حفظ الردود إلى الملف
def save_replies():
    with open(REPLIES_FILE, "w", encoding="utf-8") as file:
        json.dump(group_replies, file, ensure_ascii=False, indent=4)


group_replies = load_replies()        


def split_message(message, max_length=4096):
    """ تقسيم الرسالة إلى أجزاء إذا كانت طويلة """
    return [message[i:i + max_length] for i in range(0, len(message), max_length)]
def check_gbt_status(chat_id):
    """ التحقق من حالة الذكاء الاصطناعي وإرسال رسالة إذا كان معطلًا """
    global gbt_enabled
    if not gbt_enabled:
        bot.send_message(chat_id, "للأسف، قام المشرفون بتعطيل الذكاء الاصطناعي. يرجى طلب تفعيله من أحد المشرفين.")
        return False
    return True

def load_banned_words():
    """تحميل الكلمات المحظورة عند بدء تشغيل البوت"""
    global banned_words
    try:
        with open(BANNED_WORDS_FILE, "r", encoding="utf-8") as f:
            banned_words = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        banned_words = {}

def save_banned_words():
    """حفظ الكلمات المحظورة إلى ملف JSON لضمان بقاء البيانات بعد إعادة التشغيل"""
    with open(BANNED_WORDS_FILE, "w", encoding="utf-8") as f:
        json.dump(banned_words, f, ensure_ascii=False, indent=4)
        
# ------ دوال تفعيل التقارير ------
def save_mentions_data():
    with open('mentions.json', 'w') as f:
        json.dump(active_mentions, f)

def load_mentions_data():
    try:
        with open('mentions.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# تحميل البيانات عند التشغيل
active_mentions = load_mentions_data()
def get_all_members(chat_id):
    members = []
    offset = 0
    while True:
        chunk = bot.get_chat_members(chat_id, offset=offset)
        if not chunk:
            break
        members.extend(chunk)
        offset += len(chunk)
    return members
    
def is_user_admin(chat_id, user_id):
    """التحقق من صلاحية المشرف"""
    try:
        admins = bot.get_chat_administrators(chat_id)
        return any(admin.user.id == user_id for admin in admins)
    except Exception as e:
        print(f"خطأ في التحقق من الصلاحيات: {e}")
        return False


def check_image_safety(image_path):
    """فحص إذا كانت الصورة غير مناسبة باستخدام مكتبة OpenNSFW2"""
    try:
        # تحميل الصورة
        image = Image.open(image_path)
        
        # توقع احتمالية NSFW
        nsfw_probability = n2.predict_image(image)
        
        # تحديد إذا كانت الصورة غير لائقة
        if nsfw_probability > 0.5:  # يمكنك تعديل العتبة حسب الحاجة
            return 'nude'
        return 'ok'
    
    except Exception as e:
        print(f"حدث خطأ أثناء تحليل الصورة: {e}")
        return 'error'
            
def is_user_admin(chat_id, user_id):
    """التحقق من صلاحية المشرف"""
    try:
        admins = bot.get_chat_administrators(chat_id)
        return any(admin.user.id == user_id for admin in admins)
    except Exception as e:
        print(f"خطأ في التحقق من الصلاحيات: {e}")
        return False

def update_violations(user_id, chat_id):
    """تحديث عدد المخالفات وتطبيق العقوبات"""
    try:
        # زيادة عدد المخالفات
        user_violations[user_id] = user_violations.get(user_id, 0) + 1
        
        # إذا وصلت المخالفات إلى 10
        if user_violations[user_id] >= 10:
            if is_user_admin(chat_id, user_id):
                bot.send_message(
                    chat_id,
                    f"🚨 المشرف {get_user_mention(user_id)} تجاوز 10 مخالفات!",
                    parse_mode="HTML"
                )
                return
            
            # تقييد المستخدم لمدة 24 ساعة
            bot.restrict_chat_member(
                chat_id,
                user_id,
                until_date=int(time.time()) + 86400,
                can_send_messages=False
            )
            
            # إرسال إشعار للمجموعة
            bot.send_message(
                chat_id,
                f"🚫 تم تقييد العضو {get_user_mention(user_id)}\n"
                "❌ السبب: تجاوز عدد المخالفات المسموح بها (10 مرات)\n"
                "⏳ المدة: 24 ساعة",
                parse_mode="HTML"
            )
            
            # إعادة تعيين العداد
            user_violations[user_id] = 0
            
    except Exception as e:
        print(f"خطأ في تحديث المخالفات: {e}")

def get_user_mention(user_id):
    """الحصول على mention للمستخدم"""
    try:
        user = bot.get_chat(user_id)
        return f'<a href="tg://user?id={user.id}">{user.first_name}</a>'
    except:
        return f"المستخدم ({user_id})"

def process_media(content, file_extension, message, media_type):
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
                handle_violation(message, media_type)
            
            os.unlink(temp_file.name)
    except Exception as e:
        print(f"خطأ في معالجة الميديا: {e}")

def handle_violation(message, content_type):
    """معالجة المخالفة: حذف الرسالة، إرسال التحذير وتحديث عدد المخالفات"""
    try:
        # حذف الرسالة الأصلية
        bot.delete_message(message.chat.id, message.message_id)
        
        # إرسال التحذير
        warning_msg = (
            f"⚠️ <b>تنبيه!</b>\n"
            f"العضو: {get_user_mention(message.from_user.id)}\n"
            f"نوع المخالفة: {content_type} غير لائق\n"
            f"عدد المخالفات: {user_violations.get(message.from_user.id, 0)+1}/10"
        )
        bot.send_message(message.chat.id, warning_msg, parse_mode="HTML")
        
        # تحديث عدد المخالفات
        update_violations(message.from_user.id, message.chat.id)
        
    except Exception as e:
        print(f"خطأ في معالجة المخالفة: {e}")           
            


        
                        
def is_admin(chat_id, user_id):
    """التحقق من صلاحية المشرف"""
    try:
        admins = bot.get_chat_administrators(chat_id)
        return any(admin.user.id == user_id for admin in admins)
    except Exception as e:
        print(f"Error checking admin status: {e}")
        return False 
        
                
                                
def is_user_admin(bot, chat_id, user_id):
    """
    التحقق مما إذا كان المستخدم مشرفًا في المجموعة.
    """
    try:
        admins = bot.get_chat_administrators(chat_id)
        for admin in admins:
            if admin.user.id == user_id:
                return True
        return False
    except Exception as e:
        print(f"Error checking admin status: {e}")
        return False
def extract_user_info(bot, message):
    """
    استخراج الأيدي أو اليوزرنيم من الرسالة.
    """
    if message.reply_to_message:
        return message.reply_to_message.from_user.id, message.reply_to_message.from_user.username
    elif len(message.text.split()) > 1:
        target = message.text.split()[1]
        if target.startswith("@"): 
            try:
                user_info = bot.get_chat(target)
                return user_info.id, user_info.username 
            except Exception as e:
                print(f"Error getting user info: {e}")
                return None, None
        else: 
            try:
                user_id = int(target) 
                return user_id, None  
            except ValueError:
                print("Invalid user ID format")
                return None, None
    else:
        return None, None
def is_user_subscribed(user_id):
    """التحقق من اشتراك المستخدم في القناة"""
    try:
        chat_member = bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        return chat_member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"Error checking subscription: {e}")
        return False

def send_violation_report(channel_id, message, violation_type):
    """إرسال تقرير لمجموعة التقارير الخاصة بالقناة"""
    report_group_id = report_groups.get(str(channel_id))
    if not report_group_id:
        print(f"❌ لم يتم العثور على مجموعة تقارير للقناة: {channel_id}")
        return

    # إصلاح عنوان القناة إذا لم يكن لديه username
    chat_title = message.chat.title if message.chat.title else "Unknown Channel"
    chat_link = f"https://t.me/{message.chat.username}" if message.chat.username else "لا يوجد رابط"

    report_text = (
        f"🚨 **تقرير مخالفة في القناة** 🚨\n"
        f"📢 **القناة:** {chat_title}\n"
        f"🔗 **الرابط:** {chat_link}\n"
        f"⚠️ **المخالفة:** {violation_type}\n"
        f"🕒 **الوقت:** {time.strftime('%Y-%m-%d %H:%M:%S')}"
    )

    try:
        bot.send_message(
            report_group_id,
            report_text,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
        print(f"✅ تم إرسال التقرير إلى المجموعة {report_group_id}")
    except Exception as e:
        print(f"❌ خطأ في إرسال التقرير: {str(e)}")


@bot.chat_member_handler()
def welcome_developer(update: ChatMemberUpdated):
    """ترحب بالمطور عند انضمامه إلى أي مجموعة يكون فيها البوت"""
    if update.new_chat_member.user.id == DEVELOPER_CHAT_ID and update.new_chat_member.status in ["member", "administrator", "creator"]:
        bot.send_message(
            update.chat.id,
            f"⚡ <b>انضم مطور البوت</b> <a href='tg://user?id={DEVELOPER_CHAT_ID}'>@SB_SAHAR</a> <b>إلى المجموعة</b> ⚡\n\n"
            "☺️ <b>أهلاً بك مطوري العزيز!</b>",
            parse_mode="HTML"
        )


@bot.message_handler(content_types=['left_chat_member'])
def handle_manual_ban(message):
    """تسجيل عمليات الطرد أو الحظر اليدوي وحفظها في التقرير اليومي"""
    chat_id = message.chat.id
    removed_user = message.left_chat_member

    if chat_id in activated_groups:
        user_info = f"👤 الاسم: {removed_user.first_name}\n" \
                    f"📎 اليوزر: @{removed_user.username if removed_user.username else 'لا يوجد'}\n" \
                    f"🆔 الآيدي: <code>{removed_user.id}</code>"

        event = f"🚷 <b>تم طرد أو حظر عضو يدويًا:</b>\n\n{user_info}"

        # ✅ التأكد من وجود سجل للمجموعة
        if chat_id not in daily_reports:
            daily_reports[chat_id] = {
                "banned": [],
                "muted": [],
                "deleted_content": [],
                "manual_actions": []
            }

        # ✅ تسجيل الحدث في التقرير اليومي تحت قسم "الإجراءات اليدوية"
        daily_reports[chat_id]["manual_actions"].append(event)

        # ✅ إرسال إشعار فوري إلى مجموعة التقارير
        report_chat_id = activated_groups[chat_id]
        bot.send_message(report_chat_id, event, parse_mode="HTML")

@bot.message_handler(content_types=['new_chat_members'])
def handle_new_members(message):
    """تسجيل انضمام الأعضاء الجدد (اختياري)"""
    chat_id = message.chat.id
    for member in message.new_chat_members:
        if chat_id in activated_groups:
            user_info = f"👤 الاسم: {member.first_name}\n" \
                        f"📎 اليوزر: @{member.username if member.username else 'لا يوجد'}\n" \
                        f"🆔 الآيدي: <code>{member.id}</code>"

            event = f"✅ <b>انضمام عضو جديد:</b>\n\n{user_info}"
            
            # حفظ الحدث في التقرير اليومي
            daily_reports[chat_id]["manual_actions"].append(event)

            # إرسال إشعار إلى مجموعة التقارير
            report_chat_id = activated_groups[chat_id]
            bot.send_message(report_chat_id, event, parse_mode="HTML")        
        
@bot.message_handler(commands=['enable_reports'])
def activate_reports(message):
    # التحقق من كون المستخدم مشرف
    if not is_user_admin(bot, message.chat.id, message.from_user.id):
        bot.send_message(message.chat.id, "❌ يجب أن تكون مشرفًا في المجموعة لتفعيل التقارير.")
        return

    msg = bot.send_message(message.chat.id, "📝 أرسل ID المجموعة المراد تفعيل التقارير لها.")
    bot.register_next_step_handler(msg, process_group_id_step)

def process_group_id_step(message):
    try:
        group_id = int(message.text.strip())  # تحويل الإدخال إلى رقم
        if not is_user_admin(bot, group_id, message.from_user.id):  # تحقق من المشرف في المجموعة
            bot.send_message(message.chat.id, "❌ يجب أن تكون مشرفًا في المجموعة لتفعيل التقارير.")
            return

        activated_groups[group_id] = message.chat.id
        daily_reports[group_id] = {"banned": [], "muted": [], "deleted_content": [], "manual_actions": []}
        bot.send_message(message.chat.id, f"✅ تم تفعيل التقارير للمجموعة (ID: {group_id})")
        schedule_daily_report(group_id)
    except ValueError:
        bot.send_message(message.chat.id, "❌ يرجى إدخال ID صحيح للمجموعة.")        



@bot.channel_post_handler(content_types=['photo', 'video', 'animation', 'sticker', 'text'])
def handle_channel_media(message):
    channel_checker.process_channel_media(message)

@bot.channel_post_handler(func=lambda message: message.edit_date is not None)
def handle_edited_channel_message(message):
    """التعامل مع جميع الرسائل المعدلة في القنوات"""
    channel_checker.process_edited_channel_media(message)



@bot.message_handler(commands=['gbt'])
def handle_gbt_command(message):
    """ التعامل مع الأمر /gbt """
    if not check_gbt_status(message.chat.id):
        return
    
    user_input = message.text.split('/gbt', 1)[-1].strip()
    if not user_input:
        bot.send_message(message.chat.id, "يرجى إرسال سؤال بعد /gbt")
        return
    
    thinking_message = bot.send_message(message.chat.id, "جاري الاتصال بالذكاء، انتظر قليلًا...", parse_mode="Markdown")
    response = get_blackbox_response(user_input)
    bot.delete_message(message.chat.id, thinking_message.message_id)
    
    message_parts = split_message(response)
    for part in message_parts:
        bot.send_message(message.chat.id, part, parse_mode="Markdown")   
@bot.message_handler(commands=['l1'])
def add_banned_word(message):
    if message.chat.type == "private":
        bot.reply_to(message, "❌ هذا الأمر مخصص للمجموعات فقط.")
        return

    if not is_user_admin(bot, message.chat.id, message.from_user.id):
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


@bot.message_handler(commands=['l1l'])
def remove_banned_word(message):
    if message.chat.type == "private":
        bot.reply_to(message, "❌ هذا الأمر مخصص للمجموعات فقط.")
        return

    if not is_user_admin(bot, message.chat.id, message.from_user.id):
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
  # بمجرد اكتشاف أول كلمة ممنوعة نخرج من الحلقة
@bot.channel_post_handler(func=lambda message: message.entities and any(entity.type == 'custom_emoji' for entity in message.entities))
def handle_channel_custom_emoji(message):
    channel_checker.process_channel_custom_emoji(message)




@bot.message_handler(commands=['opengbt'])
def handle_opengbt_command(message):
    """ تفعيل الذكاء الاصطناعي """
    global gbt_enabled
    try:
        # التحقق من أن المستخدم مشرف أو مالك المجموعة
        chat_member = bot.get_chat_member(message.chat.id, message.from_user.id)
        if chat_member.status in ["administrator", "creator"]:
            gbt_enabled = True
            bot.send_message(message.chat.id, "تم تفعيل الذكاء الاصطناعي بنجاح.✓")
        else:
            bot.send_message(message.chat.id, "عذرًا، فقط المشرفون يمكنهم تفعيل الذكاء الاصطناعي.")
    except Exception as e:
        print(f"Error checking admin status: {e}")
        bot.send_message(message.chat.id, "حدث خطأ أثناء التحقق من الصلاحيات.")   
   
        
       
@bot.message_handler(commands=['detection'])
def smart_detector(message):
    if message.chat.type == 'private':
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    if not is_admin(chat_id, user_id):
        bot.send_message(chat_id, "❌ هذا الأمر متاح للمشرفين فقط!")
        return

    markup = InlineKeyboardMarkup()
    current_status = group_detection_status.get(str(chat_id), 'disabled')
    
    btn_text = "✅ مفعل" if current_status == 'enabled' else "☑️ معطل"
    markup.row(
        InlineKeyboardButton(f"التفعيل {btn_text}", callback_data=f"detector_toggle_{chat_id}")
    )
    markup.row(
        InlineKeyboardButton("🗑 إغلاق القائمة", callback_data="detector_close")
    )

    welcome_msg = (
        "🛡️ *مرحبا بك في لوحة تحكم الكاشف الذكي*\n\n"
        "• فحص الصور والملصقات تلقائياً\n"
        "•والفيديو والمتحركات ورسائل المعدلة \n"
        "•سوف أحمي مجموعتك من كل المحتوى الأباحـي والغير لائق في مجموعتك✓\n\n"
        f"*الحالة الحالية:* {'مفعل 🟢' if current_status == 'enabled' else 'معطل 🔴'}"
    )

    bot.send_message(
        chat_id,
        welcome_msg,
        reply_markup=markup,
        parse_mode="Markdown"
    )

# عدل callback handler كما يلي
@bot.callback_query_handler(func=lambda call: call.data.startswith('detector_'))
def handle_detector_callback(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    message_id = call.message.message_id

    if not is_admin(chat_id, user_id):
        bot.answer_callback_query(call.id, "❌ أنت لست مشرفاً!", show_alert=True)
        return

    if call.data == 'detector_close':
        try:
            bot.delete_message(chat_id, message_id)
        except:
            pass
        return

    if 'toggle' in call.data:
        current_status = group_detection_status.get(str(chat_id), 'disabled')
        new_status = 'disabled' if current_status == 'enabled' else 'enabled'
        group_detection_status[str(chat_id)] = new_status
        save_detection_status()  # حفظ الحالة الجديدة

        markup = InlineKeyboardMarkup()
        btn_text = "✅ مفعل" if new_status == 'enabled' else "☑️ معطل"
        markup.row(
            InlineKeyboardButton(f"التفعيل {btn_text}", callback_data=f"detector_toggle_{chat_id}")
        )
        markup.row(
            InlineKeyboardButton("🗑 إغلاق القائمة", callback_data="detector_close")
        )

        updated_text = (
            f"🛡️ **تم تحديث الحالة بنجاح!**\n\n"
            f"• الحالة الجديدة: {'مفعل 🟢' if new_status == 'enabled' else 'معطل 🔴'}\n"
            "• سيتم تطبيق التغييرات فورياً\n"
            "• يمكنك تعديل الإعدادات في أي وقت"
        )

        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=updated_text,
                reply_markup=markup,
                parse_mode="Markdown"
            )
        except:
            pass

        status_msg = " *تـم تفـعيل نظـام الحمايـة الذكيـة*✓" if new_status == 'enabled' else "❌ *تـم تعطيل نظام الحمايـة الذكية*"
        bot.send_message(chat_id, status_msg, parse_mode="Markdown")
        bot.answer_callback_query(call.id, "✓ تم حفظ الإعدادات")                
                
          
@bot.message_handler(commands=['closegbt'])
def handle_closegbt_command(message):
    """ تعطيل الذكاء الاصطناعي """
    global gbt_enabled
    try:
        # التحقق من أن المستخدم مشرف أو مالك المجموعة
        chat_member = bot.get_chat_member(message.chat.id, message.from_user.id)
        if chat_member.status in ["administrator", "creator"]:
            gbt_enabled = False
            bot.send_message(message.chat.id, "تم تعطيل الذكاء الاصطناعي بنجاح.✓")
        else:
            bot.send_message(message.chat.id, "عذرًا، فقط المشرفون يمكنهم تعطيل الذكاء الاصطناعي.")
    except Exception as e:
        print(f"Error checking admin status: {e}")
        bot.send_message(message.chat.id, "حدث خطأ أثناء التحقق من الصلاحيات.")

            
        
@bot.message_handler(commands=['ban'])
def ban_user(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    # التحقق من أن المستخدم مشرف
    if not is_user_admin(bot, chat_id, user_id):
        bot.reply_to(message, "⚠️ <b>عذرًا!</b>\nهذا الأمر مخصص للمشرفين فقط.\nلا تقم بذلك مرة أخرى، هذا أمر خطير!", parse_mode="HTML")
        return

    # استخراج معلومات الهدف
    target_id, target_username = extract_user_info(bot, message)
    
    # إذا كان الرد على الرسالة، أخذ الاسم الكامل للمستخدم
    if message.reply_to_message:
        target_full_name = message.reply_to_message.from_user.first_name or target_username  # استخدم الاسم الأول أو اليوزر
    else:
        target_full_name = target_username  # في حال لم يكن هناك رد على رسالة

    if not target_id:
        bot.reply_to(message, "📌 <b>كيفية استخدام الأمر:</b>\n"
                              "1️⃣ بالرد على رسالة العضو: <code>/ban</code>\n"
                              "2️⃣ باستخدام الآيدي: <code>/ban 12345</code>", parse_mode="HTML")
        return

    # منع حظر المشرفين الآخرين
    if is_user_admin(bot, chat_id, target_id):
        bot.reply_to(message, "⚠️ <b>عذرًا!</b>\nلا يمكنك حظر مشرف آخر.\n❌ دعك من هذا المزاح!", parse_mode="HTML")
        return

    try:
        bot.ban_chat_member(chat_id, target_id)

        # ------ التعديل الجديد ------
        if chat_id in activated_groups:
            event = f"تم حظر العضو: {target_full_name} (ID: {target_id})"
            daily_reports[chat_id]["banned"].append(event)
        # ------ نهاية التعديل ------

        # تنسيق رسالة الحظر
        banned_message = (
            f"👤 <b>الـحـلـو:</b> <a href='tg://user?id={target_id}'>{target_full_name}</a>\n"
            "✅ <b>تـم حظـره بنجـاح</b> 🚫"
        )

        bot.reply_to(message, banned_message, parse_mode="HTML")

    except Exception as e:
        bot.reply_to(message, f"❌ <b>حدث خطأ أثناء محاولة حظر العضو:</b> {e}", parse_mode="HTML")	
@bot.message_handler(commands=['unban'])
def unban_user(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    # التحقق من أن المستخدم مشرف
    if not is_user_admin(bot, chat_id, user_id):
        bot.reply_to(message, "⚠️ <b>عذرًا!</b>\nهذا الأمر مخصص للمشرفين فقط.\nلا تقم بذلك مرة أخرى، هذا أمر خطير!", parse_mode="HTML")
        return

    # استخراج معلومات الهدف
    target_id, target_username = extract_user_info(bot, message)
    
    # إذا كان الرد على الرسالة، أخذ الاسم الكامل للمستخدم
    if message.reply_to_message:
        target_full_name = message.reply_to_message.from_user.first_name or target_username  # استخدم الاسم الأول أو اليوزر
    else:
        target_full_name = target_username  # في حال لم يكن هناك رد على رسالة

    if not target_id:
        bot.reply_to(message, "📌 <b>كيفية استخدام الأمر:</b>\n"
                              "1️⃣ بالرد على رسالة العضو: <code>/unban</code>\n"
                              "2️⃣ باستخدام الآيدي: <code>/unban 12345</code>", parse_mode="HTML")
        return

    try:
        bot.unban_chat_member(chat_id, target_id)

        # تنسيق رسالة إلغاء الحظر
        unbanned_message = (
            f"✓ <b>تـم الغاء حظـره</b> <a href='tg://user?id={target_id}'>{target_full_name}</a>\n"
            "👀 <b>يستطـيع الأن العـودة بسـلام</b>"
        )

        bot.reply_to(message, unbanned_message, parse_mode="HTML")

    except Exception as e:
        bot.reply_to(message, f"❌ <b>حدث خطأ أثناء محاولة إلغاء حظر العضو:</b> {e}", parse_mode="HTML")
@bot.message_handler(commands=['mute'])
def mute_user(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    # التحقق من أن المستخدم مشرف
    if not is_user_admin(bot, chat_id, user_id):
        bot.reply_to(message, "⚠️ <b>عذرًا!</b>\nهذا الأمر مخصص للمشرفين فقط.\nلا تقم بذلك مرة أخرى، هذا أمر خطير!", parse_mode="HTML")
        return
    
    # استخراج معلومات العضو المستهدف
    target_id, target_username = extract_user_info(bot, message)
    if not target_id:
        bot.reply_to(message, "📌 <b>كيفية استخدام الأمر:</b>\n"
                              "1️⃣ بالرد على رسالة العضو: <code>/mute</code>\n"
                              "2️⃣ باستخدام الأيدي: <code>/mute 12345</code>\n"
                              "3️⃣ لتقييد مؤقت: <code>/mute 12345 30</code> (30 دقيقة مثال)", parse_mode="HTML")
        return
    
    command_parts = message.text.split()
    
    # إذا كان الأمر بالرد على رسالة العضو
    if message.reply_to_message:
        if len(command_parts) > 1:
            try:
                mute_duration = int(command_parts[1])
            except ValueError:
                bot.reply_to(message, "❌ <b>خطأ!</b>\nالمدة الزمنية يجب أن تكون رقمًا صحيحًا.", parse_mode="HTML")
                return
        else:
            mute_duration = None
    else:
        if len(command_parts) > 2:
            try:
                mute_duration = int(command_parts[2])
            except ValueError:
                bot.reply_to(message, "❌ <b>خطأ!</b>\nالمدة الزمنية يجب أن تكون رقمًا صحيحًا.", parse_mode="HTML")
                return
        else:
            mute_duration = None
    
    # تطبيق الكتم
    if mute_duration:
        until_date = int(time.time()) + mute_duration * 60
        bot.restrict_chat_member(chat_id, target_id, until_date=until_date, can_send_messages=False)
        
        # رسالة التقيد المؤقت مع ذكر المدة
        mute_message = (
            f"🕛 <b>تـم تقـييـد الحـلـو</b> <a href='tg://user?id={target_id}'>{target_username or 'المستخدم'}</a> <b>المدة</b>: {mute_duration} دقيقة\n"
            f"<b>بعـد أنتهـاء الوقت ⌛ سيعـود لأزعـاجنـا</b>"
        )
        bot.reply_to(message, mute_message, parse_mode="HTML")
    else:
        bot.restrict_chat_member(chat_id, target_id, can_send_messages=False)

        # رسالة التقيد الدائم
        mute_message = (
            f"🔇 <b>تـم تقـييـد الحـلـو</b> <a href='tg://user?id={target_id}'>{target_username or 'المستخدم'}</a> <b>بشكل دائـم</b>"
        )
        bot.reply_to(message, mute_message, parse_mode="HTML")
@bot.message_handler(commands=['unmute'])
def unmute_user(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    # التحقق مما إذا كان المستخدم مشرفًا
    if not is_user_admin(bot, chat_id, user_id):
        bot.reply_to(message, "⚠️ <b>عذرًا!</b>\nهذا الأمر مخصص للمشرفين فقط.\nلا تقم بذلك مرة أخرى، هذا أمر خطير!", parse_mode="HTML")
        return

    # استخراج معلومات المستخدم
    target_id, target_username = extract_user_info(bot, message)
    if not target_id:
        bot.reply_to(message, "📌 <b>كيفية استخدام الأمر:</b>\n"
                              "1️⃣ بالرد على رسالة العضو: <code>/unmute</code>\n"
                              "2️⃣ باستخدام الأيدي: <code>/unmute 12345</code>\n", parse_mode="HTML")
        return

    try:
        # إلغاء تقييد المستخدم
        bot.restrict_chat_member(chat_id, target_id, can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True)

        # إنشاء التاك بناءً على اسم المستخدم أو نص افتراضي
        mention = f'<a href="tg://user?id={target_id}">{target_username or "المستخدم"}</a>'

        # الرد مع التاك
        bot.reply_to(message, f"<b>تـم إلغاء تقييد الحـلـو</b> {mention}.\n"
                              f"🎉 <b>الآن يمكنه التحدث بحرية مرة أخرى!</b>", parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ أثناء محاولة إلغاء تقييد العضو: {e}")
              
@bot.message_handler(commands=['help'])
def help_user(message):
    help_message = """
<b>اهلا بك في بوت شاهين لحماية المجموعة</b>
<b>استطيع حماية مجموعتك من كل خطر عن طريق فحص الميديا بواسطة الذكاء الأصطناعي 🦅 في مجموعتك بشكل كامل</b>
<b>فقط اضفني الى مجموعتك واعطني صلاحيات</b>

<b>ويمكنك أيضا تفعيل التقارير لمجموعتك من خلالي</b>
<b>وحظر الأعضاء والتقيد وكثير أشياء</b>
<b>والتحدث مع الذكاء الأصطناعي أيضا</b>

<b>لمتابعة أخر تحديثاتي تابع قناة المطور لكل جديد</b>
<b>تحياتي شاهين 🦅</b>
    """
    bot.reply_to(message, help_message, parse_mode="HTML")   
@bot.message_handler(commands=['pr'])
def promote_handler(message):
    if not message.reply_to_message and len(message.text.split()) < 2:
        bot.reply_to(message, "⚠️ استخدم الأمر بالرد على المستخدم أو إدخال الـ ID.")
        return
    
    user_id = message.reply_to_message.from_user.id if message.reply_to_message else message.text.split()[1]
    chat_id = message.chat.id

    if not bot.get_chat_member(chat_id, message.from_user.id).status in ['administrator', 'creator']:
        bot.reply_to(message, "⚠️ هذا الأمر للمشرفين فقط.")
        return

    pending_promotions[chat_id] = {
        "user_id": int(user_id),
        "permissions": DEFAULT_PERMISSIONS.copy(),
        "admin_id": message.from_user.id  # لحماية القائمة من التعديل من قبل غير المشرف الذي أنشأها
    }

    send_permissions_menu(chat_id, message)

def send_permissions_menu(chat_id, message):
    data = pending_promotions.get(chat_id, {})
    if not data:
        return
    
    markup = InlineKeyboardMarkup(row_width=2)
    
    for perm, value in data["permissions"].items():
        btn_text = f"✅ {PERMISSION_NAMES[perm]}" if value else f"❌ {PERMISSION_NAMES[perm]}"
        markup.add(InlineKeyboardButton(btn_text, callback_data=f"toggle_{perm}"))

    markup.add(
        InlineKeyboardButton("✔️ تأكيد", callback_data="confirm_promotion"),
        InlineKeyboardButton("❌ إلغاء", callback_data="cancel_promotion")
    )

    if isinstance(message, int):  
        bot.edit_message_text("⚙️ <b>اختر صلاحيات المشرف:</b>", chat_id, message, reply_markup=markup, parse_mode="HTML")
    else:
        sent_message = bot.send_message(chat_id, "⚙️ <b>اختر صلاحيات المشرف:</b>", reply_markup=markup, parse_mode="HTML")
        pending_promotions[chat_id]["message_id"] = sent_message.message_id

@bot.callback_query_handler(func=lambda call: call.data.startswith("toggle_"))
def toggle_permission(call):
    chat_id = call.message.chat.id
    data = pending_promotions.get(chat_id, {})

    if not data:
        return

    # إذا الشخص اللي ضغط الزر مش نفسه اللي أنشأ القائمة، نمنعه
    if call.from_user.id != data["admin_id"]:
        bot.answer_callback_query(call.id, "🚫 هذا الأمر لا يخصك!", show_alert=True)
        return
    
    perm = call.data.split("_", 1)[1]
    data["permissions"][perm] = not data["permissions"][perm]

    send_permissions_menu(chat_id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data in ["confirm_promotion", "cancel_promotion"])
def confirm_or_cancel_promotion(call):
    chat_id = call.message.chat.id
    data = pending_promotions.pop(chat_id, None)

    if not data:
        return

    if call.data == "confirm_promotion":
        bot.promote_chat_member(chat_id, data["user_id"], **data["permissions"])

        bot_promoted_admins.setdefault(chat_id, []).append(data["user_id"])

        bot.edit_message_text(
            f"✅ <b>تم رفع المستخدم كمشرف بالصلاحيات المحددة.</b>", 
            chat_id, call.message.message_id, parse_mode="HTML"
        )
    else:
        bot.edit_message_text("❌ <b>تم إلغاء العملية.</b>", chat_id, call.message.message_id, parse_mode="HTML")

@bot.message_handler(commands=['dt'])
def demote_handler(message):
    if not message.reply_to_message and len(message.text.split()) < 2:
        bot.reply_to(message, "⚠️ استخدم الأمر بالرد على المشرف أو إدخال الـ ID.")
        return
    
    user_id = message.reply_to_message.from_user.id if message.reply_to_message else message.text.split()[1]
    
    chat_id = message.chat.id
    if not bot.get_chat_member(chat_id, message.from_user.id).status in ['administrator', 'creator']:
        bot.reply_to(message, "⚠️ هذا الأمر للمشرفين فقط.")
        return

    bot.promote_chat_member(
        chat_id, 
        int(user_id),
        can_delete_messages=False,
        can_restrict_members=False,
        can_invite_users=False,
        can_pin_messages=False,
        can_change_info=False,
        can_manage_chat=False
    )
    
    bot.reply_to(message, "✅ تم تنزيل المشرف وإلغاء جميع صلاحياته.")

@bot.message_handler(content_types=['new_chat_members', 'left_chat_member'])
def track_bans(message):
    chat_id = message.chat.id
    user = message.left_chat_member

    if not user:
        return

    admin = bot.get_chat_member(chat_id, message.from_user.id)
    if admin.status not in ["administrator", "creator"]:
        return  

    admin_id = message.from_user.id
    current_time = time.time()

    if chat_id not in ban_tracker:
        ban_tracker[chat_id] = {}

    if admin_id not in ban_tracker[chat_id]:
        ban_tracker[chat_id][admin_id] = []

    ban_tracker[chat_id][admin_id].append(current_time)

    ban_tracker[chat_id][admin_id] = [
        t for t in ban_tracker[chat_id][admin_id] if current_time - t < 3600
    ]

    if len(ban_tracker[chat_id][admin_id]) > 20:
        handle_abusive_admin(chat_id, admin_id)

def handle_abusive_admin(chat_id, admin_id):
    admin_info = bot.get_chat_member(chat_id, admin_id)
    username = f"@{admin_info.user.username}" if admin_info.user.username else "بدون معرف"
    full_name = admin_info.user.first_name
    user_id = admin_info.user.id

    if user_id in bot_promoted_admins.get(chat_id, []):
        bot.promote_chat_member(
            chat_id, user_id,
            can_delete_messages=False,
            can_restrict_members=False,
            can_invite_users=False,
            can_pin_messages=False,
            can_change_info=False,
            can_manage_chat=False
        )
        
        bot.send_message(
            chat_id,
            f"<b>🚨 تم تنزيل المشرف من منصبه!</b>\n\n"
            f"👤 <b>الاسم:</b> {full_name}\n"
            f"📎 <b>المعرف:</b> {username}\n"
            f"🆔 <b>الآيدي:</b> {user_id}\n\n"
            f"⚠️ <b>السبب:</b> قام بطرد أكثر من 20 عضو في أقل من ساعة!",
            parse_mode="HTML"
        )
        
        bot_promoted_admins[chat_id].remove(user_id)
    else:
        admins = bot.get_chat_administrators(chat_id)
        admin_mentions = " ".join(
            [f"@{admin.user.username}" for admin in admins if admin.user.username]
        )

        bot.send_message(
            chat_id,
            f"🚨 <b>تنبيه للمشرفين:</b>\n\n"
            f"👤 <b>الاسم:</b> {full_name}\n"
            f"📎 <b>المعرف:</b> {username}\n"
            f"🆔 <b>الآيدي:</b> {user_id}\n\n"
            f"⚠️ <b>هذا المشرف قام بطرد أكثر من 20 عضو خلال ساعة!</b>\n"
            f"❌ <b>ليس لدي صلاحيات لتنزيله، يرجى التعامل معه!</b>\n\n"
            f"{admin_mentions}",
            parse_mode="HTML"
        )

# دالة إضافة الردود
@bot.message_handler(commands=['ad'])
def add_reply_command(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if message.chat.type == "private":
        return bot.send_message(chat_id, "❌ هذا الأمر للجروبات فقط")

    if not is_admin(chat_id, user_id):
        return bot.reply_to(message, "❌ للمشرفين فقط")

    command_parts = message.text.split(maxsplit=1)
    if len(command_parts) < 2:
        return bot.reply_to(message, "❌ استخدم: `/ad كلمة`", parse_mode="Markdown")

    keyword = command_parts[1].strip().lower()
    pending_replies[user_id] = {'chat_id': chat_id, 'keyword': keyword}
    bot.reply_to(message, "✅ أرسل الرد الآن (نص/صورة/ملف/إلخ)")

# دالة حفظ الردود بأنواعها
@bot.message_handler(func=lambda m: m.from_user.id in pending_replies, content_types=['text', 'photo', 'video', 'sticker', 'voice', 'audio', 'document', 'animation'])
def save_reply(message):
    user_data = pending_replies.pop(message.from_user.id, None)
    if not user_data: return

    chat_id = user_data['chat_id']
    keyword = user_data['keyword']
    reply_data = None

    if message.content_type == 'text':
        reply_data = {'type': 'text', 'content': message.text}
    elif message.content_type == 'photo':
        reply_data = {'type': 'photo', 'content': message.photo[-1].file_id}
    elif message.content_type == 'video':
        reply_data = {'type': 'video', 'content': message.video.file_id}
    elif message.content_type == 'sticker':
        reply_data = {'type': 'sticker', 'content': message.sticker.file_id}
    elif message.content_type == 'voice':
        reply_data = {'type': 'voice', 'content': message.voice.file_id}
    elif message.content_type == 'audio':
        reply_data = {'type': 'audio', 'content': message.audio.file_id}
    elif message.content_type == 'document':
        reply_data = {'type': 'document', 'content': message.document.file_id}
    elif message.content_type == 'animation':
        reply_data = {'type': 'animation', 'content': message.animation.file_id}

    if reply_data:
        group_replies.setdefault(chat_id, {})[keyword] = reply_data
        save_replies()
        bot.reply_to(message, f"✅ تم ربط الرد بــ `{keyword}`", parse_mode="Markdown")
    else:
        bot.reply_to(message, "❌ نوع غير مدعوم")
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

@bot.message_handler(commands=['settings'])
def settings(message):
    """عرض إعدادات البوت مع أزرار أونلاين"""
    chat_id = message.chat.id
    user_id = message.from_user.id

    # التحقق من أن المستخدم مشرف
    if not is_user_admin(bot, chat_id, user_id):
        bot.reply_to(message, "❌ <b>هذا الأمر متاح للمشرفين فقط.</b>", parse_mode="HTML")
        return

    # إنشاء لوحة الأزرار مع تضمين ID المشرف الذي فتح القائمة
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🛡️ إعدادات الحماية", callback_data=f"settings_protection_{user_id}"))
    keyboard.add(InlineKeyboardButton("⚙️ إعدادات المجموعة", callback_data=f"settings_group_{user_id}"))
    keyboard.add(InlineKeyboardButton("💬 الردود والمنشن", callback_data=f"settings_replies_{user_id}"))
    keyboard.add(InlineKeyboardButton("📥 التحميل من السوشيال ميديا", callback_data=f"settings_downloads_{user_id}"))
    keyboard.add(InlineKeyboardButton("🔍 الحماية المتقدمة والكاشف الذكي", callback_data=f"settings_detection_{user_id}"))
    keyboard.add(InlineKeyboardButton("المطور 👩🏻‍💻", url="https://t.me/SB_SAHAR"))

    # إرسال رسالة الإعدادات مع الأزرار
    bot.send_message(
        chat_id, "<b>⚙️ إعـدادات الـبـوت</b>\n\nاخـتـر أحـد الأقـسـام أدنـاه:", 
        reply_markup=keyboard, parse_mode="HTML"
    )

# استقبال ضغطات الأزرار مع التحقق من هوية المستخدم
         
# استقبال ضغطات الأزرار مع التحقق من هوية المستخدم
@bot.callback_query_handler(func=lambda call: call.data.startswith("settings_"))
def handle_settings_callback(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    user_id = call.from_user.id
    data_parts = call.data.split("_")
    original_user_id = int(data_parts[-1])  # استخراج ID المشرف الذي فتح القائمة
    setting_type = "_".join(data_parts[:-1])  # استخراج نوع الإعداد

    # منع الأعضاء الآخرين من التفاعل مع الأزرار
    if user_id != original_user_id:
        bot.answer_callback_query(call.id, "هذا الأمر لا يخصك 🥷🏻", show_alert=True)
        return

    # محتوى الإعدادات حسب الزر المضغوط
    if setting_type == "settings_protection":
        text = (
            "<b>🛡️ إعدادات الحماية</b>\n\n"
            "• <code>/ban</code> - لحظر عضو (بالرد أو بالإيدي)\n"
            "• <code>/unban</code> - لإلغاء حظر عضو\n"
            "• <code>/mute</code> - لتقييد عضو دائمًا\n"
            "• <code>/mute 1</code> - لتقييد مؤقت (استبدل 1 بالمدة بالدقائق)\n"
            "• <code>/unmute</code> - لإلغاء التقييد"
        )
    elif setting_type == "settings_group":
        text = (
            "<b>⚙️ إعدادات المجموعة</b>\n\n"
            "• <code>/pp</code> - تثبيت رسالة\n"
            "• <code>/de</code> - حذف رسالة\n"
            "• <code>/wwa</code> - إرسال إنذار لعضو (3 إنذارات = تقييد)\n"
            "• <code>/unwa</code> - إزالة الإنذارات عن مستخدم\n"
            "• <code>/pr</code> - رفع مشرف\n"
            "• <code>/dt</code> - تنزيل مشرف وإزالة جميع صلاحياته (بالرد أو بالإيدي)\n"
            "• <code>/l1</code> - إضافة كلمة محظورة للاستخدام في المجموعة\n"
            "• <code>/l1l</code> - إزالة كلمة من قائمة الحظر"
        )
    elif setting_type == "settings_replies":
        text = (
            "<b>💬 إعدادات الردود والمنشن</b>\n\n"
            "• <code>/ad</code> - لإضافة رد لكلمة معينة بالمجموعة\n"
            "• <code>/adde</code> - لحذف رد معين"
        )
    elif setting_type == "settings_downloads":
        text = (
            "<b>📥 التحميل من مواقع السوشيال ميديا</b>\n\n"
            "• <code>/tt</code> - لتحميل مقاطع الفيديو من تيكتوك\n\n"
            "<code>/tf</code> - لتحميل ريلز من أنستا وفيسبوك\n"
            "<code>/ty</code> لتحميل اغنية من يوتيوب اكتب /ty اسم الاغنية"
        )
    elif setting_type == "settings_detection":
        text = (
            "<b>🔍 الحماية المتقدمة والكاشف الذكي</b>\n\n"
            "لتفعيل الحماية المتقدمة استخدم الأمر:\n"
            "<code>/detection</code>\n\n"
            "بعد ذلك فعل الكاشف واقرأ التعليمات التي تظهر لك قبل تفعيله."
        )

    # إنشاء زر الرجوع
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("ᵇᵃᶜᵏ", callback_data=f"back_to_settings_{original_user_id}"))

    # تعديل الرسالة بدلاً من إرسال رسالة جديدة
    bot.edit_message_text(text, chat_id, message_id, parse_mode="HTML", reply_markup=keyboard)

# زر الرجوع للقائمة الرئيسية مع التحقق من المستخدم
@bot.callback_query_handler(func=lambda call: call.data.startswith("back_to_settings"))
def back_to_settings(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    user_id = call.from_user.id
    original_user_id = int(call.data.split("_")[-1])  # استخراج ID المشرف الذي فتح القائمة

    # منع الأعضاء الآخرين من التفاعل
    if user_id != original_user_id:
        bot.answer_callback_query(call.id, "هذا الأمر لا يخصك 🥷🏻", show_alert=True)
        return

    # إعادة إرسال قائمة الإعدادات
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🛡️ إعدادات الحماية", callback_data=f"settings_protection_{original_user_id}"))
    keyboard.add(InlineKeyboardButton("⚙️ إعدادات المجموعة", callback_data=f"settings_group_{original_user_id}"))
    keyboard.add(InlineKeyboardButton("💬 الردود والمنشن", callback_data=f"settings_replies_{original_user_id}"))
    keyboard.add(InlineKeyboardButton("📥 التحميل من السوشيال ميديا", callback_data=f"settings_downloads_{original_user_id}"))
    keyboard.add(InlineKeyboardButton("🔍 الحماية المتقدمة والكاشف الذكي", callback_data=f"settings_detection_{original_user_id}"))
    keyboard.add(InlineKeyboardButton("المطور 👩🏻‍💻", url="https://t.me/SB_SAHAR"))

    bot.edit_message_text(
        "<b>⚙️ إعـدادات الـبـوت</b>\n\nاخـتـر أحـد الأقـسـام أدنـاه:", 
        chat_id, message_id, reply_markup=keyboard, parse_mode="HTML"
        )

# الأمر /pp لتثبيت رسالة

@bot.message_handler(commands=['pp'])
def pin_message(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    # التحقق مما إذا كان المستخدم مشرفًا
    if not is_user_admin(bot, chat_id, user_id):
        bot.reply_to(message, "<b>❌ هذا الأمر متاح للمشرفين فقط.</b>", parse_mode='HTML')
        return

    # التحقق مما إذا كان هناك رد على رسالة
    if not message.reply_to_message:
        bot.reply_to(message, "<b>❌ الرجاء الرد على رسالة لتثبيتها.</b>", parse_mode='HTML')
        return

    # الرد أولاً بأننا بصدد تثبيت الرسالة
    try:
        # إرسال رسالة "جاري التثبيت"
        progress_message = bot.reply_to(message, "<b>🔃 جاري تثبيت الرسالة...</b>", parse_mode='HTML')

        # تثبيت الرسالة
        bot.pin_chat_message(chat_id, message.reply_to_message.message_id)

        # تأخير لمدة ثانيتين ثم إرسال رسالة جديدة بتثبيت الرسالة بنجاح
        time.sleep(2)
        bot.edit_message_text(
            "<b>✔️ تم تثبيت الرسالة بنجاح.</b>",
            chat_id=chat_id,
            message_id=progress_message.message_id,
            parse_mode='HTML'
        )
    except Exception as e:
        bot.reply_to(message, f"<b>❌ حدث خطأ أثناء تثبيت الرسالة: {e}</b>", parse_mode='HTML')

# الأمر /delete لحذف رسال

@bot.message_handler(commands=['de'])
def delete_message(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    # التحقق مما إذا كان المستخدم مشرفًا
    if not is_user_admin(bot, chat_id, user_id):
        bot.reply_to(message, "❌ هذا الأمر متاح للمشرفين فقط.")
        return

    # التحقق مما إذا كان هناك رد على رسالة
    if not message.reply_to_message:
        bot.reply_to(message, "❌ الرجاء الرد على رسالة لحذفها.")
        return

    # حذف الرسالة التي تم الرد عليها
    try:
        bot.delete_message(chat_id, message.reply_to_message.message_id)
        success_message = bot.reply_to(message, "🗑️ تم حذف الرسالة بنجاح.")
        
        # تأخير لمدة ثانيتين ثم حذف رسالة البوت
        time.sleep(2)
        bot.delete_message(chat_id, success_message.message_id)

        # تأخير لمدة ثانيتين أخرى ثم حذف الرسالة التي أرسلت أمر /delete
        time.sleep(2)
        bot.delete_message(chat_id, message.message_id)
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ أثناء حذف الرسالة: {e}")

# الأمر /wwa لإرسال إنذار
@bot.message_handler(commands=['wwa'])
def warn_user(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    # التحقق مما إذا كان المستخدم مشرفًا
    if not is_user_admin(bot, chat_id, user_id):
        bot.reply_to(message, "❌ هذا الأمر متاح للمشرفين فقط.")
        return

    # التحقق مما إذا كان هناك رد على رسالة
    if not message.reply_to_message:
        bot.reply_to(message, "❌ الرجاء الرد على رسالة لإرسال إنذار.")
        return

    target_user_id = message.reply_to_message.from_user.id
    target_user_name = message.reply_to_message.from_user.first_name

    # تحديث الإنذارات
    if chat_id not in warnings:
        warnings[chat_id] = {}
    if target_user_id not in warnings[chat_id]:
        warnings[chat_id][target_user_id] = 0

    warnings[chat_id][target_user_id] += 1
    current_warnings = warnings[chat_id][target_user_id]

    # الرد على الإنذار
    if current_warnings >= 3:
        try:
            bot.restrict_chat_member(chat_id, target_user_id, until_date=time.time() + 86400)  # تقييد لمدة يوم
            bot.reply_to(message, f"🚫 {target_user_name} تم تقييده بسبب تلقي 3 إنذارات.")
            warnings[chat_id][target_user_id] = 0  # إعادة تعيين الإنذارات
        except Exception as e:
            bot.reply_to(message, f"❌ حدث خطأ أثناء تقييد المستخدم: {e}")
    else:
        bot.reply_to(message, f"⚠️ {target_user_name} تلقى إنذارًا جديدًا ({current_warnings}/3).")

# الأمر /unwa لإزالة الإنذارات
@bot.message_handler(commands=['unwa'])
def un_warn_user(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    # التحقق مما إذا كان المستخدم مشرفًا
    if not is_user_admin(bot, chat_id, user_id):
        bot.reply_to(message, "❌ هذا الأمر متاح للمشرفين فقط.")
        return

    # التحقق مما إذا كان هناك رد على رسالة
    if not message.reply_to_message:
        bot.reply_to(message, "❌ الرجاء الرد على رسالة لإزالة الإنذارات.")
        return

    target_user_id = message.reply_to_message.from_user.id
    target_user_name = message.reply_to_message.from_user.first_name

    # إزالة الإنذارات
    if chat_id in warnings and target_user_id in warnings[chat_id]:
        warnings[chat_id][target_user_id] = 0
        bot.reply_to(message, f"✅ تم إزالة جميع الإنذارات عن {target_user_name}.")
    else:
        bot.reply_to(message, f"ℹ️ {target_user_name} لا يملك أي إنذارات.")  
        
@bot.message_handler(commands=['tt'])
def handle_tiktok_download(message):
    chat_id = message.chat.id
    
    if len(message.text.split()) < 2:
        bot.reply_to(message, "❌ يرجى إرسال رابط تيك توك مع الأمر!\nمثال: `/tt https://vm.tiktok.com/xyz`", parse_mode="Markdown")
        return
    
    url = message.text.split()[1]
    
    # إنشاء لوحة اختيار مبسطة
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🎥 فيديو ", callback_data=f"tt_v_{url}"),
        InlineKeyboardButton("🎵 مقطع صوتي", callback_data=f"tt_a_{url}")
    )
    markup.row(InlineKeyboardButton("❌ إلغاء", callback_data="tt_cancel"))
    
    bot.send_message(
        chat_id,
        "🔄 **اختر نوع التحميل:**",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('tt_'))
def handle_tt_choice(call):
    chat_id = call.message.chat.id
    data = call.data
    
    try:
        if data.startswith('tt_v_'):
            url = data.split('tt_v_')[1]
            download_tt(chat_id, url, 'video')
            
        elif data.startswith('tt_a_'):
            url = data.split('tt_a_')[1]
            download_tt(chat_id, url, 'audio')
            
        elif data == 'tt_cancel':
            bot.delete_message(chat_id, call.message.message_id)
            
    except Exception as e:
        bot.send_message(chat_id, f"❌ حدث خطأ: {str(e)}")

def sanitize_filename(filename):
    """تنظيف اسم الملف من الرموز غير المسموحة"""
    return re.sub(r'[\\/*?:"<>|#]', '', filename)[:50]  # تقليل الطول إلى 50 حرف

def download_tt(chat_id, url, format_type):
    temp_dir = tempfile.gettempdir()
    
    ydl_opts = {
        'outtmpl': os.path.join(temp_dir, 'tt_download.%(ext)s'),
        'restrictfilenames': True,
        'quiet': True,
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # تحديد التنسيق الأمثل
            if format_type == 'video':
                ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            elif format_type == 'audio':
                ydl_opts['format'] = 'bestaudio/best'
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]

            # التنزيل الفعلي
            ydl.download([url])
            
            # البحث عن الملف المحمل
            for file in os.listdir(temp_dir):
                if file.startswith('tt_download'):
                    file_path = os.path.join(temp_dir, file)
                    
                    # إرسال الملف
                    with open(file_path, 'rb') as f:
                        if format_type == 'video':
                            bot.send_video(chat_id, f)
                        elif format_type == 'audio':
                            bot.send_audio(chat_id, f)
                    
                    # تنظيف الملفات
                    os.remove(file_path)
                    break

    except Exception as e:
        bot.send_message(chat_id, f"❌ فشل التحميل: {str(e)}")
        if 'file_path' in locals():
            os.remove(file_path)
                        
                                                                        
                                           
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    users.add(user_id)

    # التحقق من الاشتراك بالقناة  
    if not is_user_subscribed(user_id):  
        markup = types.InlineKeyboardMarkup()  
        subscribe_button = types.InlineKeyboardButton("اشترك الآن", url=CHANNEL_URL)  
        check_button = types.InlineKeyboardButton("🔄 تحقق من الاشتراك", callback_data="check_subscription")  
        markup.add(subscribe_button, check_button)  

        bot.send_message(  
            message.chat.id,  
            "⚠️ <b>يجب عليك الاشتراك في القناة أولاً لاستخدام البوت:</b>\n\n"  
            f"👉 <a href='{CHANNEL_URL}'>اضغط هنا للاشتراك</a>",  
            parse_mode="HTML",  
            reply_markup=markup  
        )  
        return  

    # إرسال إشعار للمطور عن المستخدم الجديد  
    notification_message = (  
        f"<b>📢 مستخدم جديد بدأ استخدام البوت!</b>\n\n"  
        f"<b>👤 الاسم:</b> {message.from_user.first_name}\n"  
        f"<b>📎 اليوزر:</b> @{message.from_user.username or 'بدون'}\n"  
        f"<b>🆔 الآيدي:</b> {user_id}"  
    )  
    bot.send_message(DEVELOPER_CHAT_ID, notification_message, parse_mode="HTML")  

    # رسالة الترحيب الرسمية مع الرابط  
    welcome_message = (  
        f"🔹 <a href='https://t.me/SYR_SB'>𝐒𝐎𝐔𝐑𝐂𝐄 𝐒𝐁</a>\n\n"  # <-- هذه هي الإضافة المطلوبة  
        "✨ <b>أهلاً وسهلاً بك في بوت شاهين المتطور!</b> ✨\n\n"  
        "🛡️ <b>هذا البوت مُصمم لحماية المجموعات بأحدث التقنيات.</b>\n"  
        "⚡ <b>سريع – ذكي – موثوق</b>\n\n"  
        "📌 <b>لمزيد من المعلومات اضغط:</b> /help\n\n"  
        "🚀 <b>استمتع بتجربة الحماية المتكاملة مع شاهين! 🦅</b>"  
    )  

    # أزرار التفاعل  
    markup = types.InlineKeyboardMarkup()  
    button_add_group = types.InlineKeyboardButton("➕ أضفني إلى مجموعتك", url=f"https://t.me/{bot.get_me().username}?startgroup=true")  
    button_channel = types.InlineKeyboardButton("📢 قناة المطور", url=CHANNEL_URL)  
    markup.add(button_add_group, button_channel)  

    # إرسال الفيديو مع رسالة الترحيب  
    bot.send_video(message.chat.id, VIDEO_URL, caption=welcome_message, parse_mode="HTML", reply_markup=markup)
@bot.message_handler(content_types=['left_chat_member'])
def handle_manual_ban(message):
    chat_id = message.chat.id
    if chat_id in activated_groups:
        user = message.left_chat_member
        event = f"تم طرد العضو يدويًا: @{user.username if user.username else user.id}"
        daily_reports[chat_id]["manual_actions"].append(event)        


@bot.message_handler(commands=['info'])
def get_user_info(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    # استخراج معلومات المستخدم المستهدف
    target_id, target_username = extract_user_info(bot, message)
    if not target_id:
        bot.reply_to(
            message, 
            "🔎 <b>كيفية استخدام الأمر:</b>\n"
            "1️⃣ <b>بالرد على رسالة العضو:</b> <code>/info</code>\n"
            "2️⃣ <b>باستخدام الآيدي:</b> <code>/info 12345</code>", 
            parse_mode="HTML"
        )
        return

    try:
        target_id = int(target_id)
        print(f"target_id: {target_id}, DEVELOPER_CHAT_ID: {DEVELOPER_CHAT_ID}")

        # إذا كان المستخدم هو المطور
        if target_id == DEVELOPER_CHAT_ID:
            role = "👑 <b>المطور الأساسي</b>"
            header = "👑 <b>معلومات المطور:</b>\n"
            # محاولة استخدام الرسالة المردود عليها إذا كانت موجودة
            if message.reply_to_message:
                user = message.reply_to_message.from_user
            else:
                user = bot.get_chat(target_id)
        else:
            header = "📌 <b>معلومات العضو</b>\n"
            if chat_id < 0:  # داخل مجموعة
                chat_member = bot.get_chat_member(chat_id, target_id)
                user = chat_member.user
                status = chat_member.status
                role = "🔰 <b>مشرف</b>" if status in ["creator", "administrator"] else "👤 <b>عضو</b>"
            else:
                user = bot.get_chat(target_id)
                role = "👤 <b>عضو</b>"

        is_premium = "💎 <b>بريميوم</b>" if getattr(user, "is_premium", False) else "👤 <b>عادي</b>"
        violation_count = user_violations.get(target_id, 0)

        info_message = (
            header +
            "━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>الاسم:</b> {user.first_name}\n"
            f"📎 <b>اليوزر:</b> @{user.username if user.username else '🚫 لا يوجد'}\n"
            f"🆔 <b>الآيدي:</b> <code>{target_id}</code>\n"
            f"🏅 <b>الرتبة:</b> {role}\n"
            f"⚠️ <b>المخالفات:</b> {violation_count}\n"
            f"🏆 <b>النوع:</b> {is_premium}\n"
            "━━━━━━━━━━━━━━━━━━"
        )

        bot.send_message(chat_id, info_message, parse_mode="HTML")
    except Exception as e:
        bot.reply_to(
            message, 
            f"🚫 <b>خطأ:</b>\n<code>{e}</code>", 
            parse_mode="HTML"
        )

def extract_user_info(bot, message):
    # إذا تم الرد على رسالة
    if message.reply_to_message:
        user = message.reply_to_message.from_user
        return user.id, user.username
    # إذا تم استخدام الآيدي مع الأمر
    elif len(message.text.split()) > 1:
        target_id = message.text.split()[1]
        return target_id, None
    else:
        return None, None
@bot.message_handler(commands=['info_group'])
def get_group_info(message):
    chat_id = message.chat.id
    
    if chat_id > 0:
        bot.reply_to(message, "🚫 هذا الأمر يعمل فقط داخل المجموعات.")
        return

    try:
        chat = bot.get_chat(chat_id)
        members_count = bot.get_chat_member_count(chat_id)  # تم التصحيح هنا
        admins = bot.get_chat_administrators(chat_id)
        admins_count = len(admins)
        
        # إزالة الجزء الخاص بالمحظورين لعدم وجود دالة مناسبة
        # إزالة عد البوتات لعدم وجود طريقة مباشرة
        
        group_link = chat.invite_link if chat.invite_link else "🚫 لا يوجد رابط، هذه مجموعة خاصة"

        group_info = (
            "<b>📌 معلومات المجموعة:</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"📝 <b>اسم المجموعة:</b> {chat.title}\n"
            f"🆔 <b>آيدي المجموعة:</b> <code>{chat_id}</code>\n"
            f"🔗 <b>رابط المجموعة:</b> {group_link}\n"
            f"👥 <b>عدد الأعضاء:</b> {members_count}\n"
            f"🔰 <b>عدد المشرفين:</b> {admins_count}\n"
            "━━━━━━━━━━━━━━━━━━"
        )

        bot.send_message(chat_id, group_info, parse_mode="HTML")
    
    except Exception as e:
        bot.reply_to(
            message, 
            f"🚫 <b>خطأ:</b>\n<code>{e}</code>", 
            parse_mode="HTML"
        )
        
                        

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    """التعامل مع الصور المرسلة والتحقق من محتواها باستخدام مكتبة OpenNSFW2"""
    chat_id = str(message.chat.id)  # تأكد من تخزين كـ string
    if group_detection_status.get(chat_id, 'disabled') == 'enabled':
        # الحصول على الـ file_id والمعلومات
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        file_link = f'https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}'

        try:
            # تنزيل الصورة مؤقتًا
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                response = requests.get(file_link)
                if response.status_code == 200:
                    tmp_file.write(response.content)
                    temp_path = tmp_file.name
                else:
                    print(f"فشل تحميل الصورة، رمز الحالة: {response.status_code}")
                    return

            # فحص الصورة بعد التنزيل
            res = check_image_safety(temp_path)

            # حذف الملف بعد الفحص
            os.remove(temp_path)

            # التصرف بناءً على نتيجة الفحص
            if res == 'nude':
                bot.delete_message(message.chat.id, message.message_id)
                warning_message = (
                    f"🚫 <b>لا تبعت صور غير لائقة يا {message.from_user.first_name}!</b>\n"
                    f"🥷🏻 @{message.from_user.username or str(message.from_user.id)}، <b>هذا تنبيه لك!</b>\n"
                    "<b>🤖 البوت يراقب ويمنع المحتوى غير الملائم 🛂</b>"
                )
                bot.send_message(message.chat.id, warning_message, parse_mode="HTML")
                update_violations(str(message.from_user.id), chat_id)

        except Exception as e:
            print(f"❌ حدث خطأ أثناء معالجة الصورة: {e}")
            
@bot.message_handler(content_types=['sticker'])
def handle_sticker(message):
    """التعامل مع الملصقات المرسلة والتحقق من محتواها باستخدام مكتبة OpenNSFW2"""
    chat_id = str(message.chat.id)  # تأكد من تخزين كـ string
    if group_detection_status.get(chat_id, 'disabled') == 'enabled':
        if message.sticker.thumb:  # بعض الملصقات قد لا تحتوي على صورة مصغرة
            file_info = bot.get_file(message.sticker.thumb.file_id)
            sticker_url = f'https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}'

            try:
                # تنزيل الصورة المصغرة مؤقتًا
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                    response = requests.get(sticker_url)
                    if response.status_code == 200:
                        tmp_file.write(response.content)
                        temp_path = tmp_file.name
                    else:
                        print(f"❌ فشل تحميل الملصق، رمز الحالة: {response.status_code}")
                        return

                # فحص الصورة المصغرة للملصق
                res = check_image_safety(temp_path)

                # حذف الملف المؤقت بعد الفحص
                os.remove(temp_path)

                # التصرف بناءً على نتيجة الفحص
                if res == 'nude':
                    bot.delete_message(message.chat.id, message.message_id)
                    warning_message = (
                        f"🚫 <b>لا ترسل ملصقات غير لائقة يا {message.from_user.first_name}!</b>\n"
                        f"🥷🏻 @{message.from_user.username or str(message.from_user.id)}، <b>هذا تحذير لك!</b>\n"
                        "<b>🤖 البوت يراقب ويمنع المحتوى غير اللائق 🛂</b>"
                    )
                    bot.send_message(message.chat.id, warning_message, parse_mode="HTML")
                    update_violations(str(message.from_user.id), chat_id)

            except Exception as e:
                print(f"❌ حدث خطأ أثناء معالجة الملصق: {e}")            
            
                
@bot.message_handler(func=lambda message: message.entities and any(entity.type == 'custom_emoji' for entity in message.entities))
def handle_custom_emoji_message(message):
    """التعامل مع الرموز التعبيرية الخاصة والتحقق من محتواها باستخدام مكتبة OpenNSFW2"""
    chat_id = str(message.chat.id)  # تأكد من تخزين كـ string
    if group_detection_status.get(chat_id, 'disabled') == 'enabled':
        custom_emoji_ids = [entity.custom_emoji_id for entity in message.entities if entity.type == 'custom_emoji']
        if custom_emoji_ids:
            sticker_links = get_premium_sticker_info(custom_emoji_ids)
            if sticker_links:
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

                        if res == 'nude':
                            bot.delete_message(message.chat.id, message.message_id)
                            warning_message = (
                                f"🚫 <b>لا تبعت رموز تعبيرية غير لائقة يا {message.from_user.first_name}!</b>\n"
                                f"🥷🏻 @{message.from_user.username or str(message.from_user.id)}، <b>هذا تحذير لك!</b>\n"
                                "<b>🤖 البوت يراقب ويمنع المحتوى غير اللائق 🛂</b>"
                            )
                            bot.send_message(message.chat.id, warning_message, parse_mode="HTML")
                            update_violations(str(message.from_user.id), chat_id)

                    except Exception as e:
                        print(f"❌ حدث خطأ أثناء معالجة الرمز التعبيري: {e}")

def get_premium_sticker_info(custom_emoji_ids):
    """استخراج الروابط الخاصة بالرموز التعبيرية"""
    try:
        sticker_set = bot.get_custom_emoji_stickers(custom_emoji_ids)
        sticker_links = []
        for sticker in sticker_set:
            if sticker.thumb:
                file_info = bot.get_file(sticker.thumb.file_id)
                file_link = f'https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}'
                sticker_links.append(file_link)
        return sticker_links
    except Exception as e:
        print(f"Error retrieving sticker info: {e}")
        return []



@bot.edited_message_handler(content_types=['text'])
def handle_edited_custom_emoji_message(message):
    """التعامل مع الرسائل المعدلة وفحص الرموز التعبيرية المميزة باستخدام مكتبة OpenNSFW2"""
    chat_id = str(message.chat.id)  # تأكد من تخزين كـ string
    if group_detection_status.get(chat_id, 'disabled') == 'enabled':
        user_id = message.from_user.id
        user_name = f"@{message.from_user.username}" if message.from_user.username else f"({user_id})"

        if message.entities:
            custom_emoji_ids = [entity.custom_emoji_id for entity in message.entities if entity.type == 'custom_emoji']
            if custom_emoji_ids:
                sticker_links = get_premium_sticker_info(custom_emoji_ids)
                if sticker_links:
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

                            if res == 'nude':
                                bot.delete_message(chat_id, message.message_id)
                                alert_message = (
                                    f"🚨 <b>تنبيه:</b>\n"
                                    f"🔗 المستخدم {user_name} <b>عدل رسالة وأضاف ملصق مميز غير لائق!</b>\n\n"
                                    "⚠️ <b>يجب على المشرفين اتخاذ الإجراءات اللازمة.</b>"
                                )
                                bot.send_message(chat_id, alert_message, parse_mode="HTML")
                                update_violations(str(user_id), chat_id)

                        except Exception as e:
                            print(f"❌ حدث خطأ أثناء معالجة الرمز التعبيري المعدل: {e}")
                            
@bot.edited_message_handler(content_types=['photo', 'sticker'])
def handle_edited_message(message):
    chat_id = str(message.chat.id)  # تأكد من تخزين كـ string
    if group_detection_status.get(chat_id, 'disabled') == 'enabled':
        user_id = message.from_user.id
        user_name = f"@{message.from_user.username}" if message.from_user.username else f"({user_id})"

        # فحص الصور المعدلة
        if message.content_type == 'photo':
            file_id = message.photo[-1].file_id
            file_info = bot.get_file(file_id)
            file_link = f'https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}'

            # تنزيل الصورة مؤقتًا
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                response = requests.get(file_link)
                if response.status_code == 200:
                    tmp_file.write(response.content)
                    temp_path = tmp_file.name
                else:
                    print(f"❌ فشل تحميل الصورة: {response.status_code}")
                    return

            # فحص الصورة
            res = check_image_safety(temp_path)
            os.remove(temp_path)

            if res == 'nude':
                bot.delete_message(chat_id, message.message_id)
                alert_message = (
                    f"🚨 <b>تنبيه:</b>\n"
                    f"🔗 المستخدم {user_name} <b>قام بتعديل رسالة إلى صورة غير لائقة!</b>\n\n"
                    "⚠️ <b>يرجى اتخاذ الإجراء اللازم.</b>"
                )
                bot.send_message(chat_id, alert_message, parse_mode="HTML")
                update_violations(str(user_id), chat_id)

        # فحص الملصقات المعدلة
        elif message.content_type == 'sticker' and message.sticker.thumb:
            file_info = bot.get_file(message.sticker.thumb.file_id)
            sticker_url = f'https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}'

            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                response = requests.get(sticker_url)
                if response.status_code == 200:
                    tmp_file.write(response.content)
                    temp_path = tmp_file.name
                else:
                    print(f"فشل تحميل الملصق: {response.status_code}")
                    return

            res = check_image_safety(temp_path)
            os.remove(temp_path)

            if res == 'nude':
                bot.delete_message(chat_id, message.message_id)
                alert_message = (
                    f"🚨 <b>تنبيه:</b>\n"
                    f"🔗 المستخدم {user_name} <b>قام بتعديل رسالة إلى ملصق غير لائق!</b>\n\n"
                    "⚠️ <b>يرجى اتخاذ الإجراء اللازم.</b>"
                )
                bot.send_message(chat_id, alert_message, parse_mode="HTML")
                update_violations(user_id, chat_id)

def update_violations(user_id, chat_id):
    global user_violations

    # زيادة عدد مخالفات المستخدم
    if user_id not in user_violations:
        user_violations[user_id] = 0
    user_violations[user_id] += 1

    # جلب معلومات المستخدم
    try:
        chat_member = bot.get_chat_member(chat_id, user_id)
        user = chat_member.user
        user_name = user.first_name or "غير معروف"
        user_username = f"@{user.username}" if user.username else "لا يوجد"
        user_id_text = f"<code>{user_id}</code>"  # لجعل الآيدي يظهر بشكل واضح
        violation_count = user_violations[user_id]

        # تقرير المخالفة
        violation_report = (
            f"🚨 <b>تنبيه بمخالفة جديدة!</b>\n\n"
            f"👤 <b>الاسم:</b> {user_name}\n"
            f"📎 <b>اليوزر:</b> {user_username}\n"
            f"🆔 <b>الآيدي:</b> {user_id_text}\n"
            f"🔢 <b>عدد المخالفات:</b> {violation_count}"
        )

        # إرسال التقرير إلى المجموعة المفعلة إذا كانت التقارير مفعلة
        if chat_id in activated_groups:
            report_chat_id = activated_groups[chat_id]
            daily_reports[chat_id]["deleted_content"].append(violation_report)
            bot.send_message(report_chat_id, violation_report, parse_mode="HTML")

    except Exception as e:
        print(f"❌ خطأ أثناء جلب معلومات المستخدم: {e}")
        return

    # تقييد المستخدم تلقائيًا إذا تجاوز 10 مخالفات (باستثناء المشرفين)
    if violation_count >= 10:
        try:
            if chat_member.status in ['administrator', 'creator']:
                warning_message = (
                    f"🚨 <b>تحذير!</b>\n"
                    f"👤 <b>المستخدم:</b> {user_name}\n"
                    f"📎 <b>اليوزر:</b> {user_username}\n"
                    f"🆔 <b>الآيدي:</b> {user_id_text}\n"
                    f"⚠️ <b>قام بارتكاب مخالفات كثيرة، لكنه مشرف ولا يمكن تقييده.</b>\n"
                    "⚠️ <b>يرجى التعامل معه يدويًا.</b>"
                )
                bot.send_message(chat_id, warning_message, parse_mode="HTML")
            else:
                bot.restrict_chat_member(chat_id, user_id, until_date=None, can_send_messages=False)
                restriction_message = (
                    f"🚫 <b>تم تقييد المستخدم بسبب تجاوز الحد المسموح به من المخالفات!</b>\n\n"
                    f"👤 <b>الاسم:</b> {user_name}\n"
                    f"📎 <b>اليوزر:</b> {user_username}\n"
                    f"🆔 <b>الآيدي:</b> {user_id_text}\n"
                    f"🔢 <b>عدد المخالفات:</b> {violation_count}\n\n"
                    "⚠️ <b>تم تقييده تلقائيًا.</b>"
                )
                bot.send_message(chat_id, restriction_message, parse_mode="HTML")

        except Exception as e:
            print(f"❌ خطأ أثناء محاولة تقييد المستخدم: {e}")


@bot.edited_message_handler(content_types=['text'])
def handle_channel_edited_message(message):
    """استدعاء فحص الرموز التعبيرية المميزة في الرسائل المعدلة داخل القنوات"""
    process_channel_edited_emoji(message)

@bot.message_handler(content_types=['animation'])
def handle_gif(message):
    """معالجة ملفات GIF (الصور المتحركة) فقط إذا كان الكاشف مفعلًا"""
    chat_id = str(message.chat.id)

    # التحقق مما إذا كان الكاشف مفعلًا في المجموعة
    if group_detection_status.get(chat_id, 'disabled') != 'enabled':
        print(f"🚫 الكاشف معطل في المجموعة {chat_id}. لن يتم فحص الـ GIF.")
        return

    try:
        file_info = bot.get_file(message.animation.file_id)
        file_url = f'https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}'
        response = requests.get(file_url)
        
        if response.status_code == 200:
            process_media(response.content, '.gif', message, 'صورة متحركة')
    except Exception as e:
        print(f"⚠️ خطأ في معالجة GIF: {e}")                        
@bot.message_handler(content_types=['video'])
def handle_video(message):
    """معالجة الفيديوهات باستخدام OpenNSFW2 فقط إذا كان الكاشف مفعّلًا"""
    chat_id = str(message.chat.id)

    # التحقق مما إذا كان الكاشف مفعلًا في المجموعة
    if group_detection_status.get(chat_id, 'disabled') != 'enabled':
        print(f"🚫 الكاشف معطل في المجموعة {chat_id}. لن يتم فحص الفيديوهات.")
        return

    try:
        file_info = bot.get_file(message.video.file_id)
        file_url = f'https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}'
        response = requests.get(file_url)
        
        if response.status_code == 200:
            process_media(response.content, '.mp4', message, 'فيديو')
    except Exception as e:
        print(f"⚠️ خطأ في معالجة الفيديو: {e}")

@bot.edited_message_handler(content_types=['animation', 'video'])
def handle_edited_media(message):
    """معالجة الميديا المعدلة فقط إذا كان الكاشف مفعّلًا"""
    chat_id = str(message.chat.id)

    # التحقق مما إذا كان الكاشف مفعلًا في المجموعة
    if group_detection_status.get(chat_id, 'disabled') != 'enabled':
        print(f"🚫 الكاشف معطل في المجموعة {chat_id}. لن يتم فحص الميديا المعدلة.")
        return

    if message.animation:
        handle_gif(message)
    elif message.video:
        handle_video(message)      
            
                        
            
@bot.message_handler(content_types=['new_chat_members'])
def on_user_joins(message):
    """التعامل مع انضمام أعضاء جدد للمجموعة"""
    for member in message.new_chat_members:
        groups.add(message.chat.id) 
        added_by = message.from_user
        try:
            if bot.get_chat_member(message.chat.id, added_by.id).can_invite_users:
                group_link = bot.export_chat_invite_link(message.chat.id)
                welcome_message = (
                    f"🤖 <b>تم إضافة البوت بواسطة:</b>\n"
                    f"👤 <b>الاسم:</b> {added_by.first_name}\n"
                    f"📎 <b>اليوزر:</b> @{added_by.username or 'بدون'}\n"
                    f"🆔 <b>الآيدي:</b> {added_by.id}\n"
                )                
                if group_link:
                    welcome_message += f"\n🔗 <b>رابط الدعوة للمجموعة:</b> {group_link}"
                bot.send_message(message.chat.id, welcome_message, parse_mode="HTML")
        except Exception as e:
            print(f"Error while exporting chat invite link: {e}")
def broadcast_message(message_text):
    for user_id in users:
        try:
            bot.send_message(user_id, message_text)
        except Exception as e:
            print(f"Error sending message to user {user_id}: {e}")    
    for group_id in groups:
        try:
            bot.send_message(group_id, message_text)
        except Exception as e:
            print(f"Error sending message to group {group_id}: {e}")
@bot.message_handler(commands=['broadcast'])
def handle_broadcast(message):
    """إرسال رسالة جماعية للمستخدمين والمجموعات"""
    if str(message.chat.id) == DEVELOPER_CHAT_ID:
        msg_text = message.text.split(maxsplit=1)
        if len(msg_text) > 1:
            broadcast_message(msg_text[1])
            bot.send_message(message.chat.id, "📢 تم إرسال الرسالة بنجاح إلى جميع المستخدمين والمجموعات!")
        else:
            bot.send_message(message.chat.id, "🚫 يرجى كتابة الرسالة بعد الأمر /broadcast.")
    else:
        bot.send_message(message.chat.id, "🚫 هذا الأمر مخصص للمطور فقط.")
@bot.message_handler(commands=['sb'])
def handle_sb_command(message):
    """رد خاص للمطور عند إرسال أمر /sb"""
    if str(message.from_user.id) == DEVELOPER_CHAT_ID:
        bot.reply_to(message, "نعم عزيزي المطور البوت يعمل بنجاح 💪")
    else:
        bot.reply_to(message, "🚫 هذا الأمر مخصص للمطور فقط.")


def schedule_daily_report(group_id):
    """جدولة إرسال التقرير اليومي تلقائيًا كل 24 ساعة"""
    def send_report():
        send_group_report(group_id)  # إرسال التقرير
        threading.Timer(86400, send_report).start()  # إعادة التشغيل بعد 24 ساعة
    
    threading.Timer(86400, send_report).start()

@bot.message_handler(commands=['report'])
def manual_daily_report(message):
    """عرض التقرير اليومي عند الطلب"""
    chat_id = message.chat.id
    user_id = message.from_user.id

    # التحقق مما إذا كان المستخدم مشرفًا
    if not is_user_admin(bot, chat_id, user_id):
        bot.reply_to(message, "❌ هذا الأمر متاح للمشرفين فقط.")
        return

    # إرسال التقرير يدويًا
    send_group_report(chat_id)

def send_group_report(group_id):
    """تجميع وإرسال التقرير للمجموعة"""
    if group_id in daily_reports and any(daily_reports[group_id].values()):  # التأكد أن هناك بيانات
        report = daily_reports[group_id]
        report_chat_id = activated_groups.get(group_id, group_id)  # تحديد مجموعة الإشعارات أو نفس المجموعة

        msg = "📅 **التقرير اليومي**\n\n"
        msg += f"🔨 الأعضاء المحظورين:\n" + ("\n".join(report["banned"]) if report["banned"] else "لا يوجد") + "\n\n"
        msg += f"🔇 الأعضاء المكتمين:\n" + ("\n".join(report["muted"]) if report["muted"] else "لا يوجد") + "\n\n"
        msg += f"🚮 المحتوى المحذوف:\n" + ("\n".join(report["deleted_content"]) if report["deleted_content"] else "لا يوجد") + "\n\n"
        msg += f"👥 الإجراءات اليدوية:\n" + ("\n".join(report["manual_actions"]) if report["manual_actions"] else "لا يوجد")

        bot.send_message(report_chat_id, msg, parse_mode="Markdown")

    else:
        bot.send_message(group_id, "📢 لا يوجد سجل للمخالفات اليوم.", parse_mode="Markdown")

def reset_daily_reports():
    """إعادة تصفير السجلات كل 24 ساعة"""
    global daily_reports
    daily_reports = {group_id: {"banned": [], "muted": [], "deleted_content": [], "manual_actions": []} for group_id in activated_groups}
    print("✅ تم إعادة تصفير السجلات اليومية.")
    threading.Timer(86400, reset_daily_reports).start()  # إعادة التصغير بعد 24 ساعة

            

@bot.chat_member_handler(func=lambda message: message.new_chat_member is not None)
def notify_developer(message):
    """إعلام المطور عند إضافة البوت إلى مجموعة جديدة ورفعه كمشرف"""
    if message.new_chat_member.user.id == bot.id:  # التأكد أن البوت هو الذي تمت إضافته
        user_id = message.from_user.id
        username = message.from_user.username
        chat_id = message.chat.id
        chat_title = message.chat.title
        invite_link = f'https://t.me/{message.chat.username}' if message.chat.username else 'رابط المجموعة غير متوفر'

        # إرسال الرسالة للمطور
        bot.send_message(DEVELOPER_CHAT_ID, f"✅ تم إضافة البوت إلى مجموعة جديدة!\n\n"
                                           f"• **اسم المجموعة**: {chat_title}\n"
                                           f"• **ايدي المجموعة**: {chat_id}\n"
                                           f"• **الشخص الذي أضاف البوت**: {username} (ID: {user_id})\n"
                                           f"• **رابط المجموعة**: {invite_link}")
                
commands = [
telebot.types.BotCommand("settings", "عرض اعدادات المجموعة"),
    telebot.types.BotCommand("ban", "حظر عضو (بالرد، الأيدي، أو اليوزرنيم)"),
    telebot.types.BotCommand("unban", "إلغاء حظر عضو (بالرد، الأيدي، أو اليوزرنيم)"),
    telebot.types.BotCommand("mute", "تقييد عضو من الكتابة (بالرد، الأيدي، أو اليوزرنيم)"),
    telebot.types.BotCommand("unmute", "إلغاء تقييد عضو (بالرد، الأيدي، أو اليوزرنيم)"),
     telebot.types.BotCommand("opengbt", "للمشرف فقط (تفعيل الذكاء بلمجموعة)"),
      telebot.types.BotCommand("closegbt", "للمشرف فقط (تعطيل الذكاء بلمجموعة)"),
       telebot.types.BotCommand("gbt", "الذكاء الأصطناعي gbt-4 (ارسل رسالتك للذكاء مع الأمر)"),
telebot.types.BotCommand("enable_reports", "تفعيل إرسال التقارير اليومية لمجموعتك"),
           
]
bot.set_my_commands(commands)



# 5️⃣ دوال الرد التلقائي (الردود العشوائية)
shahin_replies = [
    "🥷🏻 <b>شاهين معك</b>",
    "🦅 <b>الشاهين فخر الثورة السورية</b>",
    "👀 <b>شاهين بالأجواء</b>",
    "🦾 <b>شاهين لديك لا خوف عليك</b>",
    "✨ <b>نعم صديقي، معك شاهين</b>",
    "🦦 <b>ماني فاضي عندي شغل</b>",
    "🗿 <b>مشغول شوي، بعدين برد</b>"
]

#bot_replies = [
 #   "🥷🏻 <b>اسمي شاهين، شو بقدر ساعدك؟</b>",
#    "🧑🏻‍💻 <b>مشغول</b>",
#    "⌛ <b>بعدين مو هلق</b>",
#    "🤯 <b>صرعتني ها، حاج تصيح بوت!</b>",
#    "🎤 <b>أي أي، كمان صيح بوت بوت</b>",
#    "🦅 <b>واحد متلك بوت، بتجي KD عندي 10</b>",
#    "🎮 <b>عم العب ببجي، ماني فاضي</b>"
#]

revolution_replies = [
    "💚 <b>الثورة عز والشهادة فخر</b>",
    "💚 <b>الثورة مالها حل غير النصر، إرادة الشعوب دائمًا تنتصر</b>"
]

deterrence_replies = [
    "🦅 <b>ردع العدوان</b>"
]

syria_replies = [
    "<b>سوريا أرض العز</b>"
]

syrian_replies = [
    "🦅 <b>أرفع راسك فوق أنت سوري حر</b>"
]

# دوال الرد على الكلمات
@bot.message_handler(func=lambda message: "شاهين" in message.text.lower())
def shahin_reply(message):
    bot.reply_to(message, random.choice(shahin_replies), parse_mode="HTML")

#@bot.message_handler(func=lambda message: "بوت" in message.text.lower())
#def bot_reply(message):
#    bot.reply_to(message, random.choice(bot_replies), parse_mode="HTML")

@bot.message_handler(func=lambda message: "ثورة" in message.text.lower())
def revolution_reply(message):
    bot.reply_to(message, random.choice(revolution_replies), parse_mode="HTML")

@bot.message_handler(func=lambda message: "ردع" in message.text.lower())
def deterrence_reply(message):
    bot.reply_to(message, random.choice(deterrence_replies), parse_mode="HTML")

@bot.message_handler(func=lambda message: "سوريا" in message.text.lower())
def syria_reply(message):
    bot.reply_to(message, random.choice(syria_replies), parse_mode="HTML")

@bot.message_handler(func=lambda message: "سوري" in message.text.lower())
def syrian_reply(message):
    bot.reply_to(message, random.choice(syrian_replies), parse_mode="HTML")
@bot.message_handler(func=lambda message: 'يلعن روحه' in message.text)
def send_audio(message):
    audio_file_id = 'https://t.me/srevbo67/6' 
    bot.send_audio(message.chat.id, audio_file_id, caption="يلعن روحه بقبره")  
@bot.message_handler(func=lambda message: 'مطور' in message.text or 'المطور' in message.text)
def send_animation(message):
    animation_file_id = 'https://t.me/srevbo67/8'  # رابط الصورة المتحركة (GIF)

    caption = """<b>✦ ⚡مـطورة الـبوت ✦</b>  
🚀 <b>𝐒𝐎𝐔𝐑𝐂𝐄 𝐒𝐁</b> ⚡  .

🌟 <b>مـعلومـات الـمـطـور:</b>  
👤 <b>الاســم:</b> 𝐒𝐀𝐇𝐀𝐑 𝐒𝐁 <i>(سـحـر)</i>  
🔹 <b>اليـوزر:</b> @SB_SAHAR  
🆔 <b>الايـدي:</b> 6789179634  
⚡ <b>الرتبــه:</b> <i>👑DEV الـمـطـورة</i>  
📜 <b>البايـو:</b>  
ᵖʳᵒᵍʳᵃᵐᵐᵉʳ ʷᶦᵗʰ ⁱⁿᵗᵉˡˡᶦᵍᵉⁿᶜᵉ ᵇʳᵉᵃᵏᶦⁿᵍ ᵗʰᵉ ⁱᵐᵖᵒˢˢᶦᵇˡᵉ  
🔗 <b>قـنـاتـي:</b> @SYR_SB  |  @SY_SBbot
"""

    # إنشاء زر تفاعلي للتواصل مع المطور
    keyboard = types.InlineKeyboardMarkup()
    contact_button = types.InlineKeyboardButton("💬 𝙳𝙴𝚅 𝚂𝙰𝙷𝙰𝚁", url="https://t.me/SB_SAHAR")
    keyboard.add(contact_button)

    bot.send_animation(message.chat.id, animation_file_id, caption=caption, parse_mode="HTML", reply_markup=keyboard)





# دالة إضافة الردود
@bot.message_handler(commands=['ad', 'adde'])
def manage_replies(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    command = message.text.split()[0][1:]  # الحصول على الأمر بدون /

    if message.chat.type == "private":
        return bot.send_message(chat_id, "❌ هذا الأمر للجروبات فقط")

    if not is_admin(chat_id, user_id):
        return bot.reply_to(message, "❌ للمشرفين فقط")

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return bot.reply_to(message, f"❌ استخدم: `/{command} كلمة`", parse_mode="Markdown")

    keyword = args[1].strip().lower()

    if command == 'ad':
        pending_replies[user_id] = {'chat_id': chat_id, 'keyword': keyword}
        bot.reply_to(message, "✅ أرسل الرد الآن (نص/صورة/ملف/إلخ)")
    
    elif command == 'adde':
        if chat_id in group_replies and keyword in group_replies[chat_id]:
            del group_replies[chat_id][keyword]
            save_replies()
            bot.reply_to(message, f"✅ تم حذف الرد `{keyword}`", parse_mode="Markdown")
        else:
            bot.reply_to(message, f"❌ لا يوجد رد مسجل لـ `{keyword}`", parse_mode="Markdown")

# دالة حفظ الردود بأنواعها
@bot.message_handler(
    func=lambda m: m.from_user.id in pending_replies,
    content_types=['text', 'photo', 'video', 'sticker', 'voice', 'audio', 'document', 'animation']
)
def save_reply(message):
    user_data = pending_replies.pop(message.from_user.id, None)
    if not user_data:
        return

    chat_id = user_data['chat_id']
    keyword = user_data['keyword']
    reply_data = None

    content_types = {
        'text': ('text', message.text),
        'photo': ('photo', message.photo[-1].file_id),
        'video': ('video', message.video.file_id),
        'sticker': ('sticker', message.sticker.file_id),
        'voice': ('voice', message.voice.file_id),
        'audio': ('audio', message.audio.file_id),
        'document': ('document', message.document.file_id),
        'animation': ('animation', message.animation.file_id)
    }

    reply_type, content = content_types.get(message.content_type, (None, None))
    
    if reply_type:
        group_replies.setdefault(chat_id, {})[keyword] = {'type': reply_type, 'content': content}
        save_replies()
        bot.reply_to(message, f"✅ تم ربط الرد بــ `{keyword}`", parse_mode="Markdown")
    else:
        bot.reply_to(message, "❌ نوع الوسائط غير مدعوم")
@bot.message_handler(func=lambda message: message.content_type == 'text')
def handle_messages(message):
    if message.chat.type == "private":
        return

    chat_id = message.chat.id
    text = get_message_text(message).strip().lower()

    # === (1) فحص الكلمات المحظورة ===
    group_id = str(chat_id)
    if group_id in banned_words and banned_words[group_id]:
        for word in banned_words[group_id]:
            pattern = r'\b' + re.escape(word) + r'\b'
            if re.search(pattern, text, flags=re.IGNORECASE):
                try:
                    bot.delete_message(chat_id, message.message_id)
                except Exception as e:
                    print(f"Error deleting message: {e}")

                mention = f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name}</a>'
                bot.send_message(
                    chat_id,
                    f"⚠️ <b>تم استخدام كلمة محظورة!</b>\n"
                    f"{mention}، تم مسح رسالتك تلقائيًا.\n"
                    "🚫 ممنوع إرسال كلمات محظورة في المجموعة.",
                    parse_mode="HTML"
                )
                return  # إيقاف التنفيذ بعد حذف الرسالة

    # === (2) فحص الردود التلقائية ===
    if message.reply_to_message:
        replied_text = get_message_text(message.reply_to_message).strip().lower()
        if replied_text in group_replies.get(chat_id, {}):
            send_auto_reply(message.reply_to_message, original_message=message)
    elif text in group_replies.get(chat_id, {}):
        send_auto_reply(message)

def get_message_text(msg):
    return msg.text or msg.caption or ""

def send_auto_reply(target_msg, original_message=None):
    chat_id = target_msg.chat.id
    keyword = get_message_text(target_msg).strip().lower()
    reply_data = group_replies.get(chat_id, {}).get(keyword)

    if not reply_data:
        return

    try:
        reply_to_id = original_message.message_id if original_message else target_msg.message_id
        
        if reply_data["type"] == "text":
            bot.send_message(chat_id, reply_data["content"], reply_to_message_id=reply_to_id)
        else:
            method = getattr(bot, f'send_{reply_data["type"]}', None)
            if method:
                method(chat_id, reply_data["content"], reply_to_message_id=reply_to_id)
            else:
                bot.send_message(chat_id, "❌ نوع الرد غير مدعوم", reply_to_message_id=reply_to_id)
    except Exception as e:
        print(f"Error: {e}")




            


load_banned_words()         
load_detection_status()          
reset_daily_reports()        
if __name__ == '__main__':
    bot.polling(none_stop=True)
