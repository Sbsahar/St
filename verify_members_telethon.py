from telethon import TelegramClient, events
from telethon.tl.custom import InlineKeyboardMarkup, InlineKeyboardButton
import json
import os
import asyncio
import logging

# إعداد التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# إعدادات Telethon
api_id = 21290600
api_hash = '2bd56b3e7715ec5862d6f856047caa95'
bot_token = '7588670003:AAEJSTkUqMYiNdjL17UsoM5O4a87YPiHhsc'  # نفس توكن البوت

# إنشاء عميل Telethon
client = TelegramClient('bot_session', api_id, api_hash)

# ملف لتخزين حالة التحقق (مشترك مع ste.py)
VERIFICATION_FILE = 'verification_status.json'

def load_verification_status():
    try:
        with open(VERIFICATION_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {'mode': {}, 'pending': {}}

def save_verification_status(status):
    with open(VERIFICATION_FILE, 'w') as f:
        json.dump(status, f)

# تحميل الحالة عند البداية
verification_status = load_verification_status()
verification_mode = verification_status['mode']  # {chat_id: True/False}
pending_verifications = verification_status['pending']  # {chat_id: {user_id: timestamp}}

# التعامل مع انضمام الأعضاء الجدد
@client.on(events.ChatAction)
async def handle_new_member(event):
    chat_id = str(event.chat_id)
    if not verification_mode.get(chat_id, False):
        logger.info(f"وضع التحقق غير مفعل في {chat_id}")
        return

    if event.user_added or event.user_joined:
        user_id = str(event.user_id)
        user = await client.get_entity(event.user_id)
        mention = f'<a href="tg://user?id={user_id}">{user.first_name}</a>'
        
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("✅ أنا إنسان", callback_data=f"verify_{user_id}")]])
        
        try:
            msg = await client.send_message(
                chat_id,
                f"👋 <b>أهلاً بك عزيزي {mention}!</b>\n"
                "يرجى الضغط على 'أنا إنسان' خلال 3 دقائق للتحقق منك، وإلا سأظنك زومبي وسأطردك! 🧟‍♂️",
                parse_mode='html',
                buttons=markup
            )
            pending_verifications.setdefault(chat_id, {})[user_id] = time.time()
            logger.info(f"تم طلب التحقق من {user_id} في {chat_id}")
            
            # جدولة الطرد بعد 3 دقائق
            await asyncio.sleep(180)
            await check_verification_timeout(chat_id, user_id, user.first_name)
        except Exception as e:
            logger.error(f"خطأ في إرسال رسالة التحقق: {e}")

# التحقق من انتهاء المهلة
async def check_verification_timeout(chat_id, user_id, user_name):
    if chat_id in pending_verifications and user_id in pending_verifications[chat_id]:
        try:
            await client.kick_participant(chat_id, user_id)
            mention = f'<a href="tg://user?id={user_id}">{user_name}</a>'
            await client.send_message(
                chat_id,
                f"🚪 <b>تم طرد {mention}!</b>\n"
                "تبين معنا إنه زومبي 🧟‍♂️ وليس بشر، لم يثبت إنسانيته في الوقت المحدد!",
                parse_mode='html'
            )
            del pending_verifications[chat_id][user_id]
            save_verification_status({'mode': verification_mode, 'pending': pending_verifications})
            logger.info(f"تم طرد {user_id} من {chat_id} لعدم التحقق")
        except Exception as e:
            logger.error(f"Error kicking user {user_id}: {e}")

# التعامل مع ضغط الزر
@client.on(events.CallbackQuery(pattern=r'verify_'))
async def handle_verification(event):
    chat_id = str(event.chat_id)
    user_id = event.data.decode('utf-8').split('_')[1]
    
    if chat_id in pending_verifications and user_id in pending_verifications[chat_id]:
        if event.sender_id == int(user_id):
            del pending_verifications[chat_id][user_id]
            await event.edit(
                f"✅ <b>تم التحقق!</b>\n"
                f"أهلاً بك <a href='tg://user?id={user_id}'>{event.sender.first_name}</a>، أنت إنسان حقيقي! 🎉",
                parse_mode='html'
            )
            save_verification_status({'mode': verification_mode, 'pending': pending_verifications})
            logger.info(f"تم التحقق من {user_id} في {chat_id}")
        else:
            await event.answer("🚫 هذا الزر ليس لك!", alert=True)
    else:
        await event.answer("⏰ انتهت مهلة التحقق أو تم التحقق مسبقًا!", alert=True)

# تشغيل العميل
async def main():
    await client.start(bot_token=bot_token)
    logger.info("Telethon client started")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
