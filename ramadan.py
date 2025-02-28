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
        
        time.sleep(1200)  # 20 دقيقة

def setup_handlers(bot):
    # أوامر للمجموعات
    @bot.message_handler(commands=['quran'])
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
        
        bot.reply_to(message, "✅ تم تفعيل النشر التلقائي للآيات القرآنية كل 20 دقيقة.")
        ramadan_groups[str(chat_id)] = 1
        save_ramadan_groups()

    @bot.message_handler(commands=['stop_quran'])
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

    # أمر لتفعيل النشر في القنوات
    @bot.message_handler(commands=['start_quran'])
    def start_channel_quran(message):
        chat_id = message.chat.id
        if message.chat.type != 'channel':
            bot.send_message(chat_id, "❌ هذا الأمر متاح فقط في القنوات.")
            return
        
        try:
            me = bot.get_chat_member(chat_id, bot.get_me().id)
            if me.status != 'administrator':
                bot.send_message(chat_id, "❌ يجب أن أكون مشرفًا لتفعيل النشر.")
                return
            
            if str(chat_id) in ramadan_groups:
                bot.send_message(chat_id, "⚠️ النشر التلقائي مفعل بالفعل في هذه القناة.")
                return
            
            bot.send_message(chat_id, "✅ تم تفعيل النشر التلقائي للآيات القرآنية كل 20 دقيقة.")
            ramadan_groups[str(chat_id)] = 1
            save_ramadan_groups()
            print(f"تم تفعيل النشر يدويًا في القناة: {chat_id}")
        except Exception as e:
            print(f"فشل تفعيل النشر في القناة {chat_id}: {e}")
            bot.send_message(chat_id, f"❌ حدث خطأ: {e}")

    # أمر لإيقاف النشر في القنوات
    @bot.message_handler(commands=['stop_qurancl'])
    def stop_channel_quran(message):
        chat_id = message.chat.id
        if message.chat.type != 'channel':
            bot.send_message(chat_id, "❌ هذا الأمر متاح فقط في القنوات.")
            return
        
        try:
            me = bot.get_chat_member(chat_id, bot.get_me().id)
            if me.status != 'administrator':
                bot.send_message(chat_id, "❌ يجب أن أكون مشرفًا لإيقاف النشر.")
                return
            
            if str(chat_id) not in ramadan_groups:
                bot.send_message(chat_id, "⚠️ النشر التلقائي غير مفعل في هذه القناة.")
                return
            
            del ramadan_groups[str(chat_id)]
            save_ramadan_groups()
            bot.send_message(chat_id, "✅ تم إيقاف النشر التلقائي للآيات القرآنية.")
            print(f"تم إيقاف النشر يدويًا في القناة: {chat_id}")
        except Exception as e:
            print(f"فشل إيقاف النشر في القناة {chat_id}: {e}")
            bot.send_message(chat_id, f"❌ حدث خطأ: {e}")

    # التعامل مع إضافة البوت إلى قناة أو مجموعة
    @bot.chat_member_handler()
    def handle_new_chat_member(update: ChatMemberUpdated):
        chat = update.chat
        new_member = update.new_chat_member
        
        if new_member.user.id == bot.get_me().id and new_member.status == 'administrator' and chat.type == 'channel':
            chat_id = str(chat.id)
            if chat_id in ramadan_groups:
                return
            
            try:
                bot.send_message(chat_id, "✅ تم إضافة البوت إلى القناة. استخدم /start_quran لتفعيل النشر التلقائي للآيات القرآنية.")
                print(f"تم اكتشاف القناة: {chat.title} ({chat_id}). في انتظار تفعيل يدوي.")
            except Exception as e:
                print(f"فشل إرسال رسالة ترحيب في القناة {chat_id}: {e}")

    # التعامل مع المنشورات في القناة (للأوامر فقط)
    @bot.channel_post_handler()
    def handle_channel_post(message):
        chat_id = str(message.chat.id)
        if message.chat.type != 'channel':
            return
        
        try:
            me = bot.get_chat_member(chat_id, bot.get_me().id)
            if me.status != 'administrator' or not me.can_post_messages:
                print(f"البوت ليس لديه صلاحية النشر في القناة {chat_id}")
                return

            # التحقق من الأوامر فقط، بدون تفعيل تلقائي
            if message.text:
                if message.text.startswith('/start_quran'):
                    if chat_id in ramadan_groups:
                        bot.send_message(chat_id, "⚠️ النشر التلقائي مفعل بالفعل في هذه القناة.")
                    else:
                        bot.send_message(chat_id, "✅ تم تفعيل النشر التلقائي للآيات القرآنية كل 20 دقيقة.")
                        ramadan_groups[chat_id] = 1
                        save_ramadan_groups()
                        print(f"تم تفعيل النشر في القناة: {message.chat.title} ({chat_id})")

                elif message.text.startswith('/stop_qurancl'):
                    if chat_id not in ramadan_groups:
                        bot.send_message(chat_id, "⚠️ النشر التلقائي غير مفعل في هذه القناة.")
                    else:
                        del ramadan_groups[chat_id]
                        save_ramadan_groups()
                        bot.send_message(chat_id, "✅ تم إيقاف النشر التلقائي للآيات القرآنية.")
                        print(f"تم إيقاف النشر في القناة: {message.chat.title} ({chat_id})")

        except Exception as e:
            print(f"فشل في التحقق من حالة البوت أو معالجة المنشور في القناة {chat_id}: {e}")
