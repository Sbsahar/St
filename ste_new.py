"""
بوت Telegram لإدارة المجموعات - نسخة محسّنة ومنظمة
مستوحى من Group Help Bot
"""

# استيراد المكتبات الأساسية
import telebot
import logging
from telebot.types import BotCommand

# استيراد الإعدادات
from config import TOKEN, BOT_USERNAME, YOUTUBE_API_KEY

# استيراد مدير البيانات
from data_manager import data_manager

# استيراد الوحدات الجديدة
from bot_modules.admin import register_admin_handlers
from bot_modules.settings import register_settings_handlers
from bot_modules.moderation import (
    check_image_safety, process_media, check_banned_words,
    check_links, is_media_detection_enabled, is_link_blocking_enabled
)
from bot_modules.utils import is_user_admin, get_message_text

# استيراد الوحدات القديمة (سنبقيها كما هي)
from channel_module import register_channel_handlers
from sh1 import register_download_handlers
from youtube_module import YoutubeModule
from ramadan import setup_handlers
import channel_checker

# إعداد السجل (Logging)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# إنشاء البوت
bot = telebot.TeleBot(TOKEN)

# إعداد وحدة اليوتيوب
youtube_module = YoutubeModule(bot, YOUTUBE_API_KEY, BOT_USERNAME)
youtube_module.setup_handlers()

# تسجيل المعالجات من الوحدات القديمة
register_channel_handlers(bot)
register_download_handlers(bot, is_user_admin)
setup_handlers(bot)

# تسجيل المعالجات من الوحدات الجديدة
register_admin_handlers(bot, data_manager)
register_settings_handlers(bot, data_manager)

# إعداد أوامر البوت
commands = [
    BotCommand('settings', 'لوحة التحكم الرئيسية'),
    BotCommand('ban', 'حظر مستخدم'),
    BotCommand('unban', 'إلغاء حظر مستخدم'),
    BotCommand('mute', 'كتم مستخدم'),
    BotCommand('unmute', 'إلغاء كتم مستخدم'),
    BotCommand('warn', 'تحذير مستخدم'),
    BotCommand('unwarn', 'إزالة تحذير'),
    BotCommand('warnings', 'عرض التحذيرات'),
    BotCommand('gbt', 'استخدام الذكاء الاصطناعي'),
]
bot.set_my_commands(commands)


# ==================== معالجات الرسائل ====================

@bot.message_handler(commands=['start'])
def start_command(message):
    """أمر البداية"""
    if message.chat.type == 'private':
        bot.reply_to(
            message,
            "👋 مرحباً! أنا بوت إدارة المجموعات.\n\n"
            "قم بإضافتي إلى مجموعتك ورفعني مشرفاً للبدء!\n\n"
            "استخدم /settings لعرض لوحة التحكم."
        )
    else:
        bot.reply_to(message, "✅ البوت يعمل بشكل صحيح!")


@bot.message_handler(commands=['help'])
def help_command(message):
    """أمر المساعدة"""
    help_text = (
        "📚 **قائمة الأوامر المتاحة:**\n\n"
        "**للمشرفين:**\n"
        "• `/settings` - لوحة التحكم الرئيسية\n"
        "• `/ban` - حظر مستخدم\n"
        "• `/unban` - إلغاء حظر\n"
        "• `/mute` - كتم مستخدم\n"
        "• `/unmute` - إلغاء كتم\n"
        "• `/warn` - تحذير مستخدم\n"
        "• `/unwarn` - إزالة تحذير\n\n"
        "**للجميع:**\n"
        "• `/warnings` - عرض تحذيراتك\n"
        "• `/gbt` - استخدام الذكاء الاصطناعي\n\n"
        "استخدم `/settings` للوصول إلى جميع الإعدادات!"
    )
    bot.reply_to(message, help_text, parse_mode="Markdown")


@bot.message_handler(commands=['addword'])
def add_banned_word(message):
    """إضافة كلمة محظورة"""
    if not is_user_admin(bot, message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ هذا الأمر متاح للمشرفين فقط")
        return
    
    try:
        chat_id = str(message.chat.id)
        
        # استخراج الكلمة من الأمر
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            bot.reply_to(message, "❌ الاستخدام: `/addword كلمة`", parse_mode="Markdown")
            return
        
        word = parts[1].strip()
        
        # إضافة الكلمة إلى القائمة
        if chat_id not in data_manager.banned_words:
            data_manager.banned_words[chat_id] = []
        
        if word in data_manager.banned_words[chat_id]:
            bot.reply_to(message, "⚠️ هذه الكلمة محظورة بالفعل")
            return
        
        data_manager.banned_words[chat_id].append(word)
        data_manager.save_banned_words()
        
        bot.reply_to(message, f"✅ تم إضافة الكلمة `{word}` إلى قائمة الكلمات المحظورة", parse_mode="Markdown")
        
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ: {str(e)}")


@bot.message_handler(commands=['removeword'])
def remove_banned_word(message):
    """إزالة كلمة محظورة"""
    if not is_user_admin(bot, message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ هذا الأمر متاح للمشرفين فقط")
        return
    
    try:
        chat_id = str(message.chat.id)
        
        # استخراج الكلمة من الأمر
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            bot.reply_to(message, "❌ الاستخدام: `/removeword كلمة`", parse_mode="Markdown")
            return
        
        word = parts[1].strip()
        
        # إزالة الكلمة من القائمة
        if chat_id in data_manager.banned_words and word in data_manager.banned_words[chat_id]:
            data_manager.banned_words[chat_id].remove(word)
            data_manager.save_banned_words()
            bot.reply_to(message, f"✅ تم إزالة الكلمة `{word}` من قائمة الكلمات المحظورة", parse_mode="Markdown")
        else:
            bot.reply_to(message, "⚠️ هذه الكلمة غير موجودة في القائمة")
        
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ: {str(e)}")


@bot.message_handler(commands=['setwelcome'])
def set_welcome(message):
    """تعيين رسالة ترحيب"""
    if not is_user_admin(bot, message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ هذا الأمر متاح للمشرفين فقط")
        return
    
    try:
        chat_id = str(message.chat.id)
        
        # استخراج الرسالة
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            bot.reply_to(message, "❌ الاستخدام: `/setwelcome رسالة الترحيب`", parse_mode="Markdown")
            return
        
        welcome_text = parts[1].strip()
        
        # حفظ رسالة الترحيب
        data_manager.welcome_messages[chat_id] = welcome_text
        data_manager.save_welcome()
        
        bot.reply_to(message, "✅ تم تعيين رسالة الترحيب بنجاح!")
        
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ: {str(e)}")


@bot.message_handler(commands=['delwelcome'])
def delete_welcome(message):
    """حذف رسالة الترحيب"""
    if not is_user_admin(bot, message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ هذا الأمر متاح للمشرفين فقط")
        return
    
    try:
        chat_id = str(message.chat.id)
        
        if chat_id in data_manager.welcome_messages:
            del data_manager.welcome_messages[chat_id]
            data_manager.save_welcome()
            bot.reply_to(message, "✅ تم حذف رسالة الترحيب")
        else:
            bot.reply_to(message, "⚠️ لا توجد رسالة ترحيب محفوظة")
        
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ: {str(e)}")


# معالج الأعضاء الجدد
@bot.message_handler(content_types=['new_chat_members'])
def welcome_new_members(message):
    """الترحيب بالأعضاء الجدد"""
    try:
        chat_id = str(message.chat.id)
        
        if chat_id in data_manager.welcome_messages:
            welcome_text = data_manager.welcome_messages[chat_id]
            
            # استبدال المتغيرات في رسالة الترحيب
            for new_member in message.new_chat_members:
                user_name = new_member.first_name
                welcome_msg = welcome_text.replace("{name}", user_name)
                welcome_msg = welcome_msg.replace("{username}", f"@{new_member.username}" if new_member.username else user_name)
                
                bot.send_message(message.chat.id, welcome_msg)
    
    except Exception as e:
        logger.error(f"خطأ في الترحيب بالأعضاء الجدد: {e}")


# معالج الرسائل العامة (للفحص التلقائي)
@bot.message_handler(content_types=['text', 'photo', 'video', 'animation', 'document'])
def handle_messages(message):
    """معالجة الرسائل للفحص التلقائي"""
    try:
        chat_id = str(message.chat.id)
        
        # تجاهل رسائل المشرفين
        if is_user_admin(bot, message.chat.id, message.from_user.id):
            return
        
        # فحص الكلمات المحظورة
        if check_banned_words(message, bot, data_manager):
            return
        
        # فحص الروابط (إذا كان مفعلاً)
        if is_link_blocking_enabled(chat_id, data_manager):
            if check_links(message, bot, data_manager):
                return
        
        # فحص الميديا (إذا كان مفعلاً)
        if is_media_detection_enabled(chat_id, data_manager):
            # فحص الصور
            if message.content_type == 'photo':
                try:
                    import tempfile
                    import os
                    
                    file_info = bot.get_file(message.photo[-1].file_id)
                    downloaded_file = bot.download_file(file_info.file_path)
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                        temp_file.write(downloaded_file)
                        temp_file_path = temp_file.name
                    
                    result = check_image_safety(temp_file_path)
                    os.unlink(temp_file_path)
                    
                    if result == 'nude':
                        from bot_modules.moderation import handle_violation
                        handle_violation(message, "صورة", bot, data_manager)
                
                except Exception as e:
                    logger.error(f"خطأ في فحص الصورة: {e}")
            
            # فحص الفيديو والصور المتحركة
            elif message.content_type in ['video', 'animation']:
                try:
                    if message.content_type == 'video':
                        file_id = message.video.file_id
                        media_type = "فيديو"
                    else:
                        file_id = message.animation.file_id
                        media_type = "صورة متحركة"
                    
                    file_info = bot.get_file(file_id)
                    downloaded_file = bot.download_file(file_info.file_path)
                    
                    file_extension = '.mp4' if message.content_type == 'video' else '.gif'
                    process_media(downloaded_file, file_extension, message, media_type, bot, data_manager)
                
                except Exception as e:
                    logger.error(f"خطأ في فحص الفيديو/الصورة المتحركة: {e}")
    
    except Exception as e:
        logger.error(f"خطأ في معالجة الرسالة: {e}")


# ==================== تشغيل البوت ====================

if __name__ == "__main__":
    logger.info("🚀 بدء تشغيل البوت...")
    logger.info(f"📝 اسم البوت: {BOT_USERNAME}")
    
    try:
        # بدء البوت
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        logger.error(f"❌ خطأ في تشغيل البوت: {e}")
