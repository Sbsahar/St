import json
import os
from telebot import TeleBot, types

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
        return member.status not in ['left', 'kicked']
    except Exception:
        return False

# المتغير لتخزين معرفات الرسائل التحذيرية لكل مستخدم
last_warning = {}

def set_channel(message, bot):
    chat_id = message.chat.id
    if message.chat.type not in ['group', 'supergroup']:
        bot.reply_to(message, "هذا الأمر يمكن استخدامه فقط في المجموعات.")
        return
    if not is_admin(bot, chat_id, message.from_user.id):
        bot.reply_to(message, "يجب أن تكون مشرفاً في المجموعة لاستخدام هذا الأمر.")
        return
    bot_member = bot.get_chat_member(chat_id, bot.user.id)
    if bot_member.status not in ['administrator', 'creator']:
        bot.reply_to(message, "أنا لست مشرفاً في المجموعة ولا يمكنني تعيين قناة اشتراك إجباري.")
        return
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "يرجى استخدام الأمر بالشكل التالي: /setchannel @channelusername")
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

# ✅ دالة تسجيل المعالجات بشكل صحيح
def register_channel_handlers(bot: TeleBot):
    # استخدام MessageHandler من TeleBot مباشرة
    bot.add_message_handler(types.MessageHandler(lambda message: set_channel(message, bot), commands=['setchannel']))
    bot.add_message_handler(types.MessageHandler(lambda message: stop_set_channel(message, bot), commands=['stopsetchannel']))
    bot.add_message_handler(types.MessageHandler(lambda message: check_subscription(message, bot), 
                                                 func=lambda message: True, 
                                                 content_types=['text', 'photo', 'video', 'document', 'sticker']))
