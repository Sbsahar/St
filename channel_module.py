import json
import os
from telebot import types

# ملف لتخزين إعدادات القنوات لكل مجموعة (دائم)
DATA_FILE = 'group_channels.json'

# تحميل بيانات المجموعات إذا كان الملف موجوداً
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'r') as f:
        group_channels = json.load(f)
else:
    group_channels = {}

def save_group_channels():
    with open(DATA_FILE, 'w') as f:
        json.dump(group_channels, f)

def is_admin(bot, chat_id, user_id):
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ['administrator', 'creator']
    except Exception:
        return False

def is_subscribed(bot, channel_username, user_id):
    try:
        member = bot.get_chat_member(channel_username, user_id)
        if member.status in ['left', 'kicked']:
            return False
        return True
    except Exception:
        return False

# المتغير لتخزين معرفات الرسائل التحذيرية لكل مستخدم
last_warning = {}

def set_channel(message, bot):
    chat_id = message.chat.id

    # التأكد أن الأمر داخل مجموعة
    if message.chat.type not in ['group', 'supergroup']:
        bot.reply_to(message, "هذا الأمر يمكن استخدامه فقط في المجموعات.")
        return

    # التأكد من أن المرسل مشرف في المجموعة
    if not is_admin(bot, chat_id, message.from_user.id):
        bot.reply_to(message, "يجب أن تكون مشرفاً في المجموعة لاستخدام هذا الأمر.")
        return

    # التأكد من صلاحيات البوت في المجموعة
    bot_member = bot.get_chat_member(chat_id, bot.user.id)
    if bot_member.status not in ['administrator', 'creator']:
        bot.reply_to(message, "أنا لست مشرفاً في المجموعة ولا يمكنني تعيين قناة اشتراك إجباري.")
        return

    args = message.text.split()
    if len(args) < 2:
        welcome_text = (
            "أهلاً بك في قسم الخدمات الخاص بتعيين قناتك اشتراك إجباري.\n\n"
            "الخطوات المطلوبة:\n"
            "1. قم برفع البوت مشرف في قناتك مع إعطائه صلاحيات دعوة المستخدمين.\n"
            "2. قم برفع البوت مشرف في المجموعة مع صلاحيات حذف الرسائل.\n"
            "3. استخدم الأمر بالشكل التالي:\n"
            "   /setchannel @channelusername"
        )
        bot.reply_to(message, welcome_text)
        return

    channel_username = args[1]
    group_channels[str(chat_id)] = channel_username
    save_group_channels()
    bot.reply_to(message, f"تم تعيين قناة الاشتراك الإجباري لهذه المجموعة على {channel_username}")

def stop_set_channel(message, bot):
    chat_id = message.chat.id

    if message.chat.type not in ['group', 'supergroup']:
        bot.reply_to(message, "هذا الأمر يمكن استخدامه فقط في المجموعات.")
        return

    if not is_admin(bot, chat_id, message.from_user.id):
        bot.reply_to(message, "يجب أن تكون مشرفاً في المجموعة لاستخدام هذا الأمر.")
        return

    if str(chat_id) in group_channels:
        del group_channels[str(chat_id)]
        save_group_channels()
        bot.reply_to(message, "تم إيقاف الاشتراك الإجباري لهذه المجموعة.")
    else:
        bot.reply_to(message, "لم يتم تعيين قناة اشتراك إجباري لهذه المجموعة.")

def check_subscription(message, bot):
    chat_id = message.chat.id

    if message.chat.type not in ['group', 'supergroup']:
        return

    if str(chat_id) not in group_channels:
        return

    channel_username = group_channels[str(chat_id)]
    user_id = message.from_user.id

    if is_subscribed(bot, channel_username, user_id):
        return

    try:
        bot.delete_message(chat_id, message.message_id)
    except Exception:
        pass

    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("أضـغط للأشـتراك", url=f"https://t.me/{channel_username.lstrip('@')}")
    markup.add(btn)
    
    warning_text = "<b>مرحباً عزيزي، لا يمكنك الكتابة وإرسال الرسائل هنا إذا لم تكن مشتركاً في قناة المجموعة.</b>"

    key = f"{chat_id}_{user_id}"
    if key in last_warning:
        try:
            bot.delete_message(chat_id, last_warning[key])
        except Exception:
            pass

    sent = bot.send_message(chat_id, warning_text, reply_markup=markup, parse_mode="HTML")
    last_warning[key] = sent.message_id

def register_channel_handlers(bot):
    """
    تقوم هذه الدالة بتسجيل معالجات الرسائل الخاصة بتعيين القناة والتحقق من الاشتراك.
    """
    # تسجيل أمر /setchannel
    bot.register_message_handler(lambda message: set_channel(message, bot), commands=['setchannel'])
    # تسجيل أمر /stopsetchannel
    bot.register_message_handler(lambda message: stop_set_channel(message, bot), commands=['stopsetchannel'])
    # تسجيل المعالج لجميع الرسائل لفحص الاشتراك
    bot.register_message_handler(lambda message: check_subscription(message, bot), 
                                 func=lambda message: True, 
                                 content_types=['text', 'photo', 'video', 'document', 'sticker'])
