import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import json
import asyncio

# إعداد التسجيل
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# توكن البوت (نفس التوكن المستخدم في ste.py)
TOKEN = '7588670003:AAEJSTkUqMYiNdjL17UsoM5O4a87YPiHhsc'

# ملف لتخزين حالة التحقق (مشترك مع ste.py)
VERIFICATION_FILE = 'verification_status.json'

# متغيرات التتبع
pending_verifications = {}  # {chat_id: {user_id: timestamp}}

def load_verification_status():
    try:
        with open(VERIFICATION_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {'mode': {}, 'pending': {}}

def save_verification_status(status):
    with open(VERIFICATION_FILE, 'w') as f:
        json.dump(status, f)

# التعامل مع انضمام الأعضاء الجدد
async def handle_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    verification_status = load_verification_status()
    verification_mode = verification_status['mode']
    
    chat_id = str(update.effective_chat.id)
    if not verification_mode.get(chat_id, False):
        logger.info(f"وضع التحقق غير مفعل في {chat_id}")
        return

    if not update.message.new_chat_members:
        return

    for member in update.message.new_chat_members:
        user_id = str(member.id)
        mention = f'<a href="tg://user?id={user_id}">{member.first_name}</a>'
        
        keyboard = [[InlineKeyboardButton("✅ أنا إنسان", callback_data=f"verify_{user_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            msg = await context.bot.send_message(
                chat_id,
                f"👋 <b>أهلاً بك عزيزي {mention}!</b>\n"
                "يرجى الضغط على 'أنا إنسان' خلال 3 دقائق للتحقق منك، وإلا سأظنك زومبي وسأطردك! 🧟‍♂️",
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            pending_verifications.setdefault(chat_id, {})[user_id] = asyncio.get_event_loop().time()
            logger.info(f"تم طلب التحقق من {user_id} في {chat_id}")
            
            # جدولة الطرد بعد 3 دقائق
            context.job_queue.run_once(check_verification_timeout, 180, data={'chat_id': chat_id, 'user_id': user_id, 'user_name': member.first_name})
        except Exception as e:
            logger.error(f"خطأ في إرسال رسالة التحقق: {e}")

# التحقق من انتهاء المهلة
async def check_verification_timeout(context: ContextTypes.DEFAULT_TYPE) -> None:
    job_data = context.job.data
    chat_id = job_data['chat_id']
    user_id = job_data['user_id']
    user_name = job_data['user_name']
    
    if chat_id in pending_verifications and user_id in pending_verifications[chat_id]:
        try:
            await context.bot.ban_chat_member(chat_id, user_id)
            mention = f'<a href="tg://user?id={user_id}">{user_name}</a>'
            await context.bot.send_message(
                chat_id,
                f"🚪 <b>تم طرد {mention}!</b>\n"
                "تبين معنا إنه زومبي 🧟‍♂️ وليس بشر، لم يثبت إنسانيته في الوقت المحدد!",
                parse_mode='HTML'
            )
            del pending_verifications[chat_id][user_id]
            logger.info(f"تم طرد {user_id} من {chat_id} لعدم التحقق")
        except Exception as e:
            logger.error(f"Error kicking user {user_id}: {e}")

# التعامل مع ضغط الزر
async def handle_verification(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    chat_id = str(query.message.chat_id)
    user_id = query.data.split('_')[1]
    
    if chat_id in pending_verifications and user_id in pending_verifications[chat_id]:
        if str(query.from_user.id) == user_id:
            del pending_verifications[chat_id][user_id]
            await query.edit_message_text(
                f"✅ <b>تم التحقق!</b>\n"
                f"أهلاً بك <a href='tg://user?id={user_id}'>{query.from_user.first_name}</a>، أنت إنسان حقيقي! 🎉",
                parse_mode='HTML'
            )
            logger.info(f"تم التحقق من {user_id} في {chat_id}")
        else:
            await query.answer("🚫 هذا الزر ليس لك!", show_alert=True)
    else:
        await query.answer("⏰ انتهت مهلة التحقق أو تم التحقق مسبقًا!", show_alert=True)

def main() -> None:
    application = Application.builder().token(TOKEN).build()

    # إضافة المعالجات
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_member))
    application.add_handler(CallbackQueryHandler(handle_verification, pattern=r'verify_'))

    # تشغيل البوت
    application.run_polling()

if __name__ == '__main__':
    main()
