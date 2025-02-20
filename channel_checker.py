from telethon import TelegramClient, events
import os
import tempfile
import requests
from nsfw_detector import predict
import json

# بيانات تسجيل الدخول
API_ID = 21290600  # ضع API_ID هنا
API_HASH = "2bd56b3e7715ec5862d6f856047caa95"  # ضع API_HASH هنا
BOT_TOKEN = "7067951946:AAEEW6mX9JVqwExL0CLVoawGptEKjDCjR3E"  # ضع توكن البوت هنا

client = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

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
@client.on(events.NewMessage(pattern='/setreportgroup'))
async def set_report_group(event):
    """تحديد مجموعة التقارير للقناة"""
    if not event.is_group:
        await event.reply("❌ يجب استخدام هذا الأمر في مجموعة التقارير.")
        return

    if not event.reply_to or not event.reply_to.fwd_from:
        await event.reply("❌ يرجى إعادة توجيه رسالة من القناة ثم استخدام الأمر.")
        return

    channel_id = str(event.reply_to.fwd_from.channel_id)
    report_groups[channel_id] = event.chat_id
    save_report_groups()
    await event.reply(f"✅ تم تعيين مجموعة التقارير للقناة.")

async def send_violation_report(channel_id, message, violation_type):
    """إرسال تقرير عند كشف مخالفة"""
    report_group_id = report_groups.get(str(channel_id))
    if not report_group_id:
        return

    report_text = f"🚨 **تقرير مخالفة** 🚨\n📢 **القناة:** {message.chat.title}\n⚠️ **المخالفة:** {violation_type}"

    await client.send_message(report_group_id, report_text)

# فحص الميديا في القنوات
@client.on(events.NewMessage(chats="me", func=lambda m: m.photo or m.video or m.sticker or m.animation))
async def handle_media(event):
    """فحص الصور، الفيديوهات، المتحركات، الملصقات في القنوات"""

    if event.photo:
        media_type = "📸 صورة غير لائقة"
        file = await event.download_media()

    elif event.video:
        media_type = "🎥 فيديو غير لائق"
        file = await event.download_media()

    elif event.animation:
        media_type = "🎞 صورة متحركة غير لائقة"
        file = await event.download_media()

    elif event.sticker and event.sticker.thumbs:
        media_type = "🎭 ملصق غير لائق"
        file = await event.download_media()

    else:
        return  # تجاهل إذا لم يكن هناك ميديا قابلة للفحص

    # تحليل الصورة أو الفيديو
    try:
        result = predict.classify(file)  # استخدم نموذج OpenNSFW أو أي نظام آخر
        os.remove(file)

        if "nude" in result and result["nude"] > 0.5:
            await event.delete()
            await send_violation_report(event.chat_id, event, media_type)

    except Exception as e:
        print(f"❌ خطأ في فحص الميديا: {e}")

# فحص الرسائل المعدلة
@client.on(events.MessageEdited(chats="me"))
async def handle_edited_media(event):
    """فحص الرسائل المعدلة في القنوات"""
    await handle_media(event)

print("✅ البوت يعمل الآن...")
client.run_until_disconnected()
