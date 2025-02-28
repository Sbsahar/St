import time
import os
import subprocess
import json
from requests import get
from telebot.types import ChatMemberUpdated

# إعدادات قاعدة بيانات لحفظ حالة المجموعات والقنوات المفعلة لنشر الآيات
RAMADAN_GROUPS_FILE = "ramadan_groups.json"
ramadan_groups = {}  # {chat_id: current_ayah_number} للمجموعات والقنوات

def load_ramadan_groups():
    global ramadan_groups
    try:
        with open(RAMADAN_GROUPS_FILE, "r", encoding="utf-8") as f:
            ramadan_groups = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        ramadan_groups = {}

def save_ramadan_groups():
    with open(RAMADAN_GROUPS_FILE, "w", encoding="utf-8") as f:
        json.dump(ramadan_groups, f, ensure_ascii=False, indent=4)

def get_ayah(num: int) -> str:
    num = int(num)
    url = 'https://cdn.islamic.network/quran/audio/128/ar.alafasy/'
    if 1 <= num <= 6236:
        url = url + f'{num}.mp3'
    x = get(url)
    with open(f"sura{num}.mp3", "wb") as f:
        f.write(x.content)
    filename = os.path.splitext(f'sura{num}.mp3')[0]
    audio_path_ogg = filename + '.ogg'
    subprocess.run(["ffmpeg", '-i', f'sura{num}.mp3', '-vn', '-acodec', 'libopus', '-b:a', '16k', audio_path_ogg, '-y'], stderr=subprocess.PIPE, encoding='utf-8')
    with open(audio_path_ogg, 'rb') as f:
        data = f.read()
    os.remove(f"sura{num}.mp3")
    return audio_path_ogg

def en_ar_nums(text):
    arabic_numbers = {'0': '٠', '1': '١', '2': '٢', '3': '٣', '4': '٤', '5': '٥', '6': '٦', '7': '٧', '8': '٨', '9': '٩'}
    result = ''
    for char in str(text):
        if char.isdigit():
            result += arabic_numbers[char]
        else:
            result += char
    return result

def ramadan_broadcast(bot):
    while True:
        if not ramadan_groups:
            time.sleep(60)  # الانتظار إذا لم تكن هناك مجموعات أو قنوات مفعلة
            continue
        
        for chat_id in list(ramadan_groups.keys()):
            try:
                current_ayah = ramadan_groups[chat_id]
                if current_ayah > 6236:
                    del ramadan_groups[chat_id]
                    save_ramadan_groups()
                    bot.send_message(chat_id, "✅ تم الانتهاء من نشر القرآن الكريم.")
                    continue
                
                x = get(f"http://api.alquran.cloud/v1/ayah/{current_ayah}/ar.asad")
                if x.status_code == 200 and x.json():
                    ayah = x.json()["data"]["text"]
                    surah_name = x.json()["data"]["surah"]["name"]
                    as_audio = get_ayah(current_ayah)
                    voice_file = open(as_audio, "rb")
                    message = ("{} ﴿{}﴾" '\n\n - {} " الجُزء {}، صفحة {}"').format(
                        ayah,
                        en_ar_nums(x.json()['data']['numberInSurah']),
                        surah_name,
                        en_ar_nums(x.json()["data"]["juz"]),
                        en_ar_nums(x.json()["data"]["page"]),
                    )
                    bot.send_voice(chat_id, voice_file, caption=message)
                    os.remove(as_audio)
                    
                    ramadan_groups[chat_id] += 1
                    save_ramadan_groups()
            except Exception as e:
                print(f"خطأ في نشر الآية لـ {chat_id}: {e}")
                time.sleep(10)  # تأخير قصير في حالة الخطأ
        
        time.sleep(1200)  

def check_existing_channels(bot):
    """التحقق من القنوات التي ينتمي إليها البوت عند التشغيل"""
    try:
        # جلب قائمة الدردشات عبر API مباشرة (لا يوجد طريقة مباشرة في telebot، لذا نستخدم حلًا بديلًا)
        # ملاحظة: هذا يعتمد على استقبال التحديثات، لكن سنضيف القنوات يدويًا إذا لزم الأمر
        print("جاري التحقق من القنوات الموجودة...")
        # للحصول على القنوات، يمكننا الاعتماد على المعالج أو إضافة القنوات يدويًا إذا كنت تعرفها
    except Exception as e:
        print(f"فشل في التحقق من القنوات الموجودة: {e}")

def setup_handlers(bot):
    # أوامر للمجموعات فقط
    @bot.message_handler(commands=['Quran'])
    def start_ramadan(message):
        chat_id = message.chat.id
        if message.chat.type not in ['group', 'supergroup']:
            bot.reply_to(message, "❌ هذا الأمر متاح فقط في المجموعات.")
            return
        
        from ste import is_user_admin
        if not is_user_admin(bot, chat_id, message.from_user.id):
            bot.reply_to(message, "❌ هذا الأمر متاح للمشرفين فقط.")
            return
        
        if str(chat_id) in ramadan_groups:
            bot.reply_to(message, "⚠️ النشر التلقائي للآيات مفعل بالفعل في هذه المجموعة.")
            return
        
        bot.reply_to(message, "✅ تم تفعيل النشر التلقائي للآيات القرآنية كل 5 دقائق.")
        ramadan_groups[str(chat_id)] = 1
        save_ramadan_groups()

    @bot.message_handler(commands=['stop_Quran'])
    def stop_ramadan(message):
        chat_id = message.chat.id
        if message.chat.type not in ['group', 'supergroup']:
            bot.reply_to(message, "❌ هذا الأمر متاح فقط في المجموعات.")
            return
        
        from ste import is_user_admin
        if not is_user_admin(bot, chat_id, message.from_user.id):
            bot.reply_to(message, "❌ هذا الأمر متاح للمشرفين فقط.")
            return
        
        if str(chat_id) not in ramadan_groups:
            bot.reply_to(message, "⚠️ النشر التلقائي غير مفعل في هذه المجموعة.")
            return
        
        del ramadan_groups[str(chat_id)]
        save_ramadan_groups()
        bot.reply_to(message, "✅ تم إيقاف النشر التلقائي للآيات القرآنية.")

    # التعامل مع إضافة البوت إلى قناة أو مجموعة جديدة
    @bot.chat_member_handler()
    def handle_new_chat_member(update: ChatMemberUpdated):
        chat = update.chat
        new_member = update.new_chat_member
        
        if new_member.user.id == bot.get_me().id and new_member.status == 'administrator':
            chat_id = str(chat.id)
            if chat_id in ramadan_groups:
                return  # تجنب التكرار
            
            try:
                bot.send_message(chat_id, "✅ تم إضافة البوت. سيبدأ النشر التلقائي للآيات القرآنية كل 5 دقائق.")
                ramadan_groups[chat_id] = 1
                save_ramadan_groups()
                print(f"تم تفعيل النشر في {chat.type}: {chat.title} ({chat_id})")
            except Exception as e:
                print(f"فشل تفعيل النشر في {chat_id}: {e}")

    # التعامل مع أي رسالة في القناة لتفعيل النشر إذا لم يكن مفعلاً
    @bot.channel_post_handler()
    def handle_channel_post(message):
        chat_id = str(message.chat.id)
        if message.chat.type == 'channel' and chat_id not in ramadan_groups:
            try:
                # التحقق من أن البوت مشرف
                me = bot.get_chat_member(message.chat.id, bot.get_me().id)
                if me.status == 'administrator':
                    ramadan_groups[chat_id] = 1
                    save_ramadan_groups()
                    bot.send_message(chat_id, "✅ تم الكشف عن القناة. سيبدأ النشر التلقائي للآيات القرآنية كل 5 دقائق.")
                    print(f"تم تفعيل النشر في القناة: {message.chat.title} ({chat_id})")
            except Exception as e:
                print(f"فشل في التحقق من حالة البوت في القناة {chat_id}: {e}")
