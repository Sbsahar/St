import telebot
import subprocess
import json
import os
import threading
import time
import logging

#ملف بوت راديو القرأن الكريم أجر لي ولكم من قناة التقنية السورية
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


TOKEN = "7911974989:AAE3OOUukFD2neHAG6u1EhMpzq77UpKuiOM"
DATA_FILE = "user_data.json"
#هنا تحط رابط اي صورة جميلة للقرأن الكريم من جوجل دور على صور جميلة انسخ رابكها وخلي هنا بلاسفل لتظهر عند التشغيل
BROADCAST_IMAGE = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRLAl9z7uNZClHpJg3B7VfaXg1hLqV0mzNOjZyADXBQIqNFzlEDv1APAl0&s=10"

#هنا بتقدر تضيف اذاعات جديدة اذا عندك
STATIONS = {
    "1": {"name": "إذاعة آيات السكينة", "url": "https://qurango.net/radio/sakeenah"},
    "2": {"name": "إذاعة القرآن من مكة المكرمة", "url": "http://n07.radiojar.com/0tpy1h0kxtzuv?rj-ttl=5&rj-tok=AAABlaaGy1sA0n1Oo_t_c-9DGw"},
    "3": {"name": "إذاعة الحرم المكي", "url": "http://r7.tarat.com:8004/stream?type=http&nocache=114"},
    "4": {"name": "إذاعة تلاوات خاشعة", "url": "https://qurango.net/radio/salma"},
    "5": {"name": "إذاعة أحمد العجمي", "url": "https://qurango.net/radio/ahmad_alajmy"},
    "6": {"name": "إذاعة إدريس أبكر", "url": "https://qurango.net/radio/idrees_abkr"},
    "7": {"name": "إذاعة عبد الباسط عبد الصمد", "url": "https://qurango.net/radio/abdulbasit_abdulsamad_mojawwad"},
    "8": {"name": "إذاعة عبد الرحمن السديس", "url": "https://qurango.net/radio/abdulrahman_alsudaes"},
    "9": {"name": "إذاعة ماهر المعيقلي", "url": "https://qurango.net/radio/maher_al_meaqli"},
    "10": {"name": "إذاعة محمد اللحيدان", "url": "https://qurango.net/radio/mohammed_allohaidan"},
    "11": {"name": "إذاعة ياسر الدوسري", "url": "https://qurango.net/radio/yasser_aldosari"},
    "12": {"name": "إذاعة مشاري العفاسي", "url": "https://qurango.net/radio/mishary_alafasi"},
    "13": {"name": "إذاعة فارس عباد", "url": "https://qurango.net/radio/fares_abbad"}
}

#لاتنسى ذكر الله
bot = telebot.TeleBot(TOKEN)

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

user_data = load_data()
user_state = {}

def restart_broadcasts():
    while True:
        for user_id, channels in user_data.items():
            for channel_name, info in channels.get("channels", {}).items():
                if "station" in info and "rtmps_url" in info:
                    if "process" in info:
                        try:
                            subprocess.Popen(["kill", str(info["process"])])
                        except subprocess.SubprocessError:
                            pass
                    ffmpeg_command = ["ffmpeg", "-re", "-i", info["station"], "-c:a", "aac", "-f", "flv", info["rtmps_url"]]
                    process = subprocess.Popen(ffmpeg_command)
                    user_data[user_id]["channels"][channel_name]["process"] = process.pid
        save_data(user_data)
        time.sleep(1800)  

threading.Thread(target=restart_broadcasts, daemon=True).start()
@bot.message_handler(commands=['start'])
def start(message):
    if message.chat.type != "private":
        return
    user_id = str(message.from_user.id)
    username = message.from_user.first_name
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.add(telebot.types.InlineKeyboardButton("إضافة قناة أو مجموعة", callback_data="add_channel"))
    keyboard.add(telebot.types.InlineKeyboardButton("اختيار إذاعة", callback_data="select_station"))
    keyboard.add(telebot.types.InlineKeyboardButton("بدء البث", callback_data="start_broadcast"))
    keyboard.add(telebot.types.InlineKeyboardButton("إيقاف البث", callback_data="stop_broadcast"))
    keyboard.add(telebot.types.InlineKeyboardButton("القنوات المضافة", callback_data="list_channels"))
    keyboard.add(telebot.types.InlineKeyboardButton("عمليات البث", callback_data="active_broadcasts"))
    bot.reply_to(message, 
        f"أهلاً بك يا {username} في راديو القرآن الكريم\n\n"
        "يمكنك من خلال هذا البوت بث القرآن الكريم لقناتك أو مجموعتك بكل سهولة بواسطة البث المباشر\n\n"
        "لمزيد من المعلومات اضغط /help",
        reply_markup=keyboard
    )

@bot.message_handler(commands=['help'])
def help_command(message):
    if message.chat.type != "private":
        return
    bot.reply_to(message,
        "كيفية استخدام راديو القرآن الكريم\n"
        "أضف البوت إلى قناتك أو مجموعتك كمشرف مع صلاحية دعوة المستخدمين\n"
        "اكتب /start في الخاص ثم اضغط إضافة قناة أو مجموعة وأرسل رابطها أو معرفها\n"
        "أرسل مفتاح البث RTMPS الخاص بالقناة أو المجموعة\n"
        "اختر إذاعة من اختيار إذاعة\n"
        "اضغط بدء البث وحدد القناة أو المجموعة\n"
        "للإيقاف اضغط إيقاف البث واختر ما تريد\n"
        "يمكنك إضافة عدة قنوات وتشغيل إذاعات مختلفة لكل منها\n"
        "اطلع على قنواتك بـ القنوات المضافة وتابع البث بـ عمليات البث\n"
        "البوت أجر لي ولكم زينوا قنواتكم بالقرآن الكريم\n"
        "للمساعدة شاهد الفيديو التفصيلي [اضغط هنا](https://t.me/SYR_SB/1217)"
    )

@bot.callback_query_handler(func=lambda call: True)
def button(call):
    if call.message.chat.type != "private":
        return
    user_id = str(call.from_user.id)

    if call.data == "add_channel":
        user_state[user_id] = "awaiting_channel"
        keyboard = telebot.types.InlineKeyboardMarkup()
        keyboard.add(telebot.types.InlineKeyboardButton("رجوع", callback_data="back"))
        bot.edit_message_text(
            "أرسل رابط القناة أو المجموعة مثل @ChannelName أو معرفها إذا كانت خاصة مثل -100123456789\n"
            "يجب أن أكون مشرفاً فيها مع صلاحية دعوة المستخدمين لأتعرف عليها",
            chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=keyboard
        )
    elif call.data == "select_station":
        keyboard = telebot.types.InlineKeyboardMarkup()
        for i in range(1, 7):
            keyboard.add(telebot.types.InlineKeyboardButton(STATIONS[str(i)]["name"], callback_data=f"station_{i}"))
        for i in range(7, 14):
            keyboard.add(telebot.types.InlineKeyboardButton(STATIONS[str(i)]["name"], callback_data=f"station_{i}"))
        keyboard.add(telebot.types.InlineKeyboardButton("رجوع", callback_data="back"))
        bot.edit_message_text("اختر إذاعة من القائمة التالية", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=keyboard)
    elif call.data == "start_broadcast":
        show_channels_to_broadcast(user_id, call)
    elif call.data == "stop_broadcast":
        show_active_broadcasts(user_id, call, stop=True)
    elif call.data == "list_channels":
        list_channels(user_id, call)
    elif call.data == "active_broadcasts":
        show_active_broadcasts(user_id, call)
    elif call.data == "back":
        user_state.pop(user_id, None)
        show_main_menu(user_id, call)
    elif call.data.startswith("station_"):
        station_id = call.data.split("_")[1]
        user_data.setdefault(user_id, {}).setdefault("temp_station", STATIONS[station_id]["url"])
        keyboard = telebot.types.InlineKeyboardMarkup()
        keyboard.add(telebot.types.InlineKeyboardButton("رجوع", callback_data="back"))
        bot.edit_message_text(
            f"تم اختيار إذاعة {STATIONS[station_id]['name']}\nاضغط بدء البث وحدد القناة أو المجموعة",
            chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=keyboard
        )
    elif call.data.startswith("broadcast_"):
        channel_name = call.data.split("_")[1]
        start_broadcast(user_id, channel_name, call)
    elif call.data.startswith("stop_"):
        channel_name = call.data.split("_")[1]
        stop_broadcast(user_id, channel_name, call)
    elif call.data.startswith("delete_"):
        channel_name = call.data.split("_")[1]
        keyboard = telebot.types.InlineKeyboardMarkup()
        keyboard.add(telebot.types.InlineKeyboardButton("نعم", callback_data=f"confirm_delete_{channel_name}"), 
                     telebot.types.InlineKeyboardButton("لا", callback_data="back"))
        bot.edit_message_text(f"هل ترغب في حذف {channel_name} من القائمة", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=keyboard)
    elif call.data.startswith("confirm_delete_"):
        channel_name = call.data.split("_")[2]
        if user_id in user_data and "channels" in user_data[user_id] and channel_name in user_data[user_id]["channels"]:
            if "process" in user_data[user_id]["channels"][channel_name]:
                pid = user_data[user_id]["channels"][channel_name]["process"]
                subprocess.Popen(["kill", str(pid)])
            del user_data[user_id]["channels"][channel_name]
            save_data(user_data)
        keyboard = telebot.types.InlineKeyboardMarkup()
        keyboard.add(telebot.types.InlineKeyboardButton("رجوع", callback_data="back"))
        bot.edit_message_text(f"تم حذف {channel_name} بنجاح", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=keyboard)

@bot.message_handler(content_types=['text'])
def handle_message(message):
    if message.chat.type != "private":
        return
    user_id = str(message.from_user.id)
    text = message.text.strip()

    if user_id in user_state:
        if user_state[user_id] == "awaiting_channel":
            try:
                chat = bot.get_chat(text)
                chat_id = str(chat.id)
                member = bot.get_chat_member(chat_id, bot.get_me().id)
                if member.status not in ["administrator", "creator"] or not member.can_invite_users:
                    keyboard = telebot.types.InlineKeyboardMarkup()
                    keyboard.add(telebot.types.InlineKeyboardButton("رجوع", callback_data="back"))
                    bot.reply_to(message, "يرجى إضافتي كمشرف في القناة أو المجموعة مع صلاحية دعوة المستخدمين لأتمكن من العمل", reply_markup=keyboard)
                    return
                user_data.setdefault(user_id, {}).setdefault("channels", {}).setdefault(chat.title, {"chat_id": chat_id})
                user_state[user_id] = "awaiting_rtmps"
                keyboard = telebot.types.InlineKeyboardMarkup()
                keyboard.add(telebot.types.InlineKeyboardButton("رجوع", callback_data="back"))
                bot.reply_to(message, f"تم التعرف على {chat.title} بنجاح\nالآن أرسل مفتاح البث RTMPS URL الخاص بها\nمثال `rtmps://dc4-1.rtmp.t.me/s/12345:abc`", reply_markup=keyboard)
            except:
                keyboard = telebot.types.InlineKeyboardMarkup()
                keyboard.add(telebot.types.InlineKeyboardButton("رجوع", callback_data="back"))
                bot.reply_to(message, "حدث خطأ في التعرف على القناة، تأكد من الرابط أو المعرف", reply_markup=keyboard)
        elif user_state[user_id] == "awaiting_rtmps":
            if not text.startswith("rtmps://"):
                keyboard = telebot.types.InlineKeyboardMarkup()
                keyboard.add(telebot.types.InlineKeyboardButton("رجوع", callback_data="back"))
                bot.reply_to(message, "مفتاح البث غير صحيح يجب أن يبدأ بـ rtmps:// أعد المحاولة", reply_markup=keyboard)
                return
            last_channel = list(user_data[user_id]["channels"].keys())[-1]
            user_data[user_id]["channels"][last_channel]["rtmps_url"] = text
            save_data(user_data)
            user_state.pop(user_id)
            keyboard = telebot.types.InlineKeyboardMarkup()
            keyboard.add(telebot.types.InlineKeyboardButton("رجوع", callback_data="back"))
            bot.reply_to(message, f"تم حفظ مفتاح البث لـ {last_channel} بنجاح\nاختر إذاعة الآن من اختيار إذاعة", reply_markup=keyboard)

def start_broadcast(user_id, channel_name, call):
    if user_id not in user_data or "channels" not in user_data[user_id] or channel_name not in user_data[user_id]["channels"]:
        bot.edit_message_text("لم يتم العثور على القناة أو المجموعة", chat_id=call.message.chat.id, message_id=call.message.message_id)
        return
    if "temp_station" not in user_data[user_id]:
        bot.edit_message_text("يرجى اختيار إذاعة أولاً من اختيار إذاعة", chat_id=call.message.chat.id, message_id=call.message.message_id)
        return
    station_url = user_data[user_id]["temp_station"]
    rtmps_url = user_data[user_id]["channels"][channel_name]["rtmps_url"]
    chat_id = user_data[user_id]["channels"][channel_name]["chat_id"]
    station_name = next(s["name"] for s in STATIONS.values() if s["url"] == station_url)

    ffmpeg_command = ["ffmpeg", "-re", "-i", station_url, "-c:a", "aac", "-f", "flv", rtmps_url]
    process = subprocess.Popen(ffmpeg_command)
    user_data[user_id]["channels"][channel_name].update({"station": station_url, "process": process.pid})
    save_data(user_data)

    try:
        keyboard = telebot.types.InlineKeyboardMarkup()
        keyboard.add(telebot.types.InlineKeyboardButton("رابط الإذاعة", url=station_url))
        bot.send_photo(
            chat_id=chat_id,
            photo=BROADCAST_IMAGE,
            caption=(
                "راديو القرآن الكريم\n"
                "تم بدء بث القرآن الكريم بنجاح\n"
                f"اسم الإذاعة {station_name}\n"
                f"اسم القناة/المجموعة {channel_name}\n"
                "حالة البث يعمل"
            ),
            reply_markup=keyboard
        )
    except Exception:
        pass

    keyboard = telebot.types.InlineKeyboardMarkup()
    for c in user_data[user_id]["channels"]:
        if c != channel_name:
            keyboard.add(telebot.types.InlineKeyboardButton(f"البث لـ {c}", callback_data=f"broadcast_{c}"))
    keyboard.add(telebot.types.InlineKeyboardButton("رجوع", callback_data="back"))
    bot.edit_message_text(
        f"تم بدء البث لـ {channel_name}\nالإذاعة {station_name}\nيمكنك بث القرآن لقنوات أخرى أو إضافة المزيد",
        chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=keyboard
    )

def stop_broadcast(user_id, channel_name, call):
    if (user_id not in user_data or "channels" not in user_data[user_id] or 
        channel_name not in user_data[user_id]["channels"] or 
        "process" not in user_data[user_id]["channels"][channel_name]):
        keyboard = telebot.types.InlineKeyboardMarkup()
        keyboard.add(telebot.types.InlineKeyboardButton("رجوع", callback_data="back"))
        bot.edit_message_text("لا يوجد بث نشط لهذه القناة أو المجموعة حالياً", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=keyboard)
        return
    pid = user_data[user_id]["channels"][channel_name]["process"]
    subprocess.Popen(["kill", str(pid)])
    del user_data[user_id]["channels"][channel_name]["process"]
    if "temp_station" in user_data[user_id]:
        del user_data[user_id]["temp_station"]
    save_data(user_data)
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.add(telebot.types.InlineKeyboardButton("رجوع", callback_data="back"))
    bot.edit_message_text(
        f"تم إيقاف البث لـ {channel_name} بنجاح\nالآن يمكنك اختيار إذاعة جديدة من اختيار إذاعة",
        chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=keyboard
    )

def show_channels_to_broadcast(user_id, call):
    if user_id not in user_data or "channels" not in user_data[user_id]:
        keyboard = telebot.types.InlineKeyboardMarkup()
        keyboard.add(telebot.types.InlineKeyboardButton("رجوع", callback_data="back"))
        bot.edit_message_text("لم يتم إضافة قنوات أو مجموعات بعد اضغط إضافة قناة أو مجموعة", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=keyboard)
        return
    keyboard = telebot.types.InlineKeyboardMarkup()
    for channel in user_data[user_id]["channels"]:
        keyboard.add(telebot.types.InlineKeyboardButton(channel, callback_data=f"broadcast_{channel}"))
    keyboard.add(telebot.types.InlineKeyboardButton("رجوع", callback_data="back"))
    bot.edit_message_text("اختر القناة أو المجموعة التي تريد البث فيها", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=keyboard)

def list_channels(user_id, call):
    if user_id not in user_data or "channels" not in user_data[user_id]:
        keyboard = telebot.types.InlineKeyboardMarkup()
        keyboard.add(telebot.types.InlineKeyboardButton("رجوع", callback_data="back"))
        bot.edit_message_text("لم يتم إضافة قنوات أو مجموعات بعد جرب إضافة قناة أو مجموعة", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=keyboard)
        return
    keyboard = telebot.types.InlineKeyboardMarkup()
    for channel in user_data[user_id]["channels"]:
        keyboard.add(telebot.types.InlineKeyboardButton(channel, callback_data=f"delete_{channel}"))
    keyboard.add(telebot.types.InlineKeyboardButton("رجوع", callback_data="back"))
    bot.edit_message_text("القنوات والمجموعات المضافة\nاضغط على أي منها لحذفها", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=keyboard)

def show_active_broadcasts(user_id, call, stop=False):
    try:
        if user_id not in user_data or "channels" not in user_data[user_id]:
            keyboard = telebot.types.InlineKeyboardMarkup()
            keyboard.add(telebot.types.InlineKeyboardButton("رجوع", callback_data="back"))
            bot.edit_message_text("لا توجد بثوث نشطة حالياً", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=keyboard)
            return
        active = {c: info for c, info in user_data[user_id]["channels"].items() if "process" in info}
        if not active:
            keyboard = telebot.types.InlineKeyboardMarkup()
            keyboard.add(telebot.types.InlineKeyboardButton("رجوع", callback_data="back"))
            bot.edit_message_text("لا توجد بثوث نشطة حالياً", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=keyboard)
            return
        keyboard = telebot.types.InlineKeyboardMarkup()
        for c, info in active.items():
            try:
                station_name = next(s['name'] for s in STATIONS.values() if s['url'] == info['station'])
                keyboard.add(telebot.types.InlineKeyboardButton(f"{c} {station_name}", callback_data=f"stop_{c}"))
            except (KeyError, StopIteration) as e:
                logging.error(f"خطأ في استرجاع اسم الإذاعة للقناة {c}: {e}")
                keyboard.add(telebot.types.InlineKeyboardButton(f"{c} (إذاعة غير معروفة)", callback_data=f"stop_{c}"))
        keyboard.add(telebot.types.InlineKeyboardButton("رجوع", callback_data="back"))
        bot.edit_message_text(
            "البثوث النشطة حالياً\n" + "\n".join(f"{c} {next(s['name'] for s in STATIONS.values() if s['url'] == info['station'])}" for c, info in active.items()),
            chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=keyboard
        )
    except Exception as e:
        logging.error(f"خطأ في show_active_broadcasts: {e}")
        keyboard = telebot.types.InlineKeyboardMarkup()
        keyboard.add(telebot.types.InlineKeyboardButton("رجوع", callback_data="back"))
        bot.edit_message_text("حدث خطأ أثناء عرض البثوث النشطة، حاول مرة أخرى", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=keyboard)

def show_main_menu(user_id, call):
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.add(telebot.types.InlineKeyboardButton("إضافة قناة أو مجموعة", callback_data="add_channel"))
    keyboard.add(telebot.types.InlineKeyboardButton("اختيار إذاعة", callback_data="select_station"))
    keyboard.add(telebot.types.InlineKeyboardButton("بدء البث", callback_data="start_broadcast"))
    keyboard.add(telebot.types.InlineKeyboardButton("إيقاف البث", callback_data="stop_broadcast"))
    keyboard.add(telebot.types.InlineKeyboardButton("القنوات المضافة", callback_data="list_channels"))
    keyboard.add(telebot.types.InlineKeyboardButton("عمليات البث", callback_data="active_broadcasts"))
    bot.edit_message_text(
        f"أهلاً بك يا {call.from_user.first_name} في راديو القرآن الكريم\n\n"
        "يمكنك من خلال هذا البوت بث القرآن الكريم لقناتك أو مجموعتك بكل سهولة بواسطة البث المباشر\n\n"
        "لمزيد من المعلومات اضغط /help",
        chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=keyboard
    )


if __name__ == "__main__":
    while True:
        try:
            logging.info("بدء تشغيل البوت...")
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            logging.error(f"حدث خطأ في البوت: {e}")
            time.sleep(5) 
            logging.info("إعادة تشغيل البوت...")
