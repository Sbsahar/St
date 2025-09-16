import os
import subprocess
import telebot
import whisper
from moviepy.editor import VideoFileClip, CompositeVideoClip, ImageClip
from deep_translator import GoogleTranslator
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import textwrap
import re
import gc
import time
import io

# تحديد الخطوط
arabic_font_path = "NotoNaskhArabic-Regular.ttf"
latin_font_path = "DejaVuSans.ttf"

# قاموس لتخزين بيانات المستخدم
user_data_storage = {}

# دالة تصحيح اللهجة العامية
def correct_dialect(text):
    print(f"Correcting dialect for: {text}")
    corrections = {
        "وش": "شو",
        "متزوش": "متزوج",
        "قدامة": "قدي",
        "عد": "عند",
        "مرتي": "زوجتي",
        "بتسأل": "تسأل"
    }
    for wrong, correct in corrections.items():
        text = text.replace(wrong, correct)
    print(f"Corrected to: {text}")
    return text

# دالة لتحسين الترجمة (مخصصة للأغاني)
def improve_translation(text, is_song=True):
    print(f"Improving translation for: {text}")
    original = text
    
    # قواعد عامة
    text = text.replace("غنيني ، النوم الآن ، أغنيني ، وسأنام", "غنّيني لأنام")
    text = text.replace("يجب أن أغنيني ، أنام الآن ، النوم", "غنّيني لأهدأ وأنام")
    text = text.replace("شفتيك تتحرك ، يمكنني سماع شيء", "شفتاك تتحركان ولا أسمع شيئًا")
    text = text.replace("لقد أصبحت ما لا يمكنك احتضان ذاكرتنا سيكون تهويدي", "أصبحتُ ما لا تستطيع احتضانه، ذكرياتنا تهويدتي")

    # قواعد مخصصة لـ "Headlights" بناءً على الكلمات الدقيقة
    if is_song:
        text = text.replace("ز لنا", "أوه، أوه، سأستخدم كل نبضة قلب")
        text = text.replace("أنا قادم عميق جدا", "أركض بحرية في الظلام")
        text = text.replace("كلهم فوق ظلالهم", "كل الظلال خلفي")
        text = text.replace("عش حول هذا الموضوع", "عشها بكل قوتك")
        text = text.replace("عشني يا حبيبي", "عشها معي، حبيبي")
        text = text.replace("Runnin 'صحيح", "أركض في الأضواء الأمامية")
        text = text.replace("يجب أن أتذوق كل ليلة سعيدة", "يجب أن أطارد كل الضوء الجيد")
        text = text.replace("أنا في السيدة", "أنا أركض في الظلام")
        text = text.replace("سألعبها على حد سواء", "سألعبها من كلا الجانبين")
        text = text.replace("وكل ما أنا عليه على الحافة", "وأنا أحتسي على الحافة")
        text = text.replace("لا تكن أصدقاء خداع", "لا تخدع الأصدقاء")
        text = text.replace("فقط أكرهني على طول الطريق", "خذني إلى النهاية")
        text = text.replace("يعيش.", "عشها بكل قوتك")
        text = text.replace("لقد كنت على نفس الشيء", "لقد كنت على نفس الطريق")
        text = text.replace("لقد كنت على", "أنا أركض في الأضواء")
        text = text.replace("أوه أوه ، يجب أن أتذوق كل الضوء الجيد", "أوه أوه، يجب أن أطارد كل الضوء الجيد")
        text = text.replace("حبيبي أنا كل شيء عن ذلك", "حبيبي، أنا كل شيء عن الأضواء الأمامية")
    
    print(f"Improved from: {original} to: {text}")
    return text

# دالة إنشاء النص مع ضبط المسافات وحجم الخط والارتفاع (مع حواف سوداء بدون خلفية)
def create_text_clip_pil(text, fontsize, color, bg_color, max_width, start_time, end_time, position):
    print(f"Creating text clip for: {text} from {start_time}s to {end_time}s")
    
    try:
        arabic_font = ImageFont.truetype(arabic_font_path, fontsize)
        latin_font = ImageFont.truetype(latin_font_path, fontsize)
        print("Fonts loaded successfully!")
    except Exception as e:
        print(f"Error loading font: {e}")
        arabic_font = ImageFont.load_default()
        latin_font = ImageFont.load_default()

    # تقسيم النص إلى أجزاء (عربية وأجنبية)
    segments = re.split(r'([A-Za-z0-9\s]+)', text)
    text_parts = [(seg, latin_font if re.match(r'[A-Za-z0-9\s]+', seg) else arabic_font) for seg in segments if seg.strip()]
    text_parts.reverse()  # عكس الترتيب للكتابة من اليمين إلى اليسار

    # لف النص ليناسب العرض (تحسين لتجنب التداخل)
    avg_char_width = fontsize * 0.5
    max_chars = int(max_width // avg_char_width)
    wrapped_text = textwrap.fill(text, width=max_chars)
    lines = wrapped_text.split("\n")
    print(f"Text wrapped into {len(lines)} lines")

    # حساب الأبعاد لكل سطر مع ضبط الارتفاع
    dummy_img = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    draw = ImageDraw.Draw(dummy_img)
    line_heights = []
    line_widths = []
    for line in lines:
        total_width = 0
        total_height = 0
        line_segments = re.split(r'([A-Za-z0-9\s]+)', line)
        for seg in line_segments:
            if seg.strip():
                font = latin_font if re.match(r'[A-Za-z0-9\s]+', seg) else arabic_font
                bbox = draw.textbbox((0, 0), seg, font=font)
                total_width += bbox[2] - bbox[0] + 5
                total_height = max(total_height, bbox[3] - bbox[1] + 5)
        line_widths.append(total_width - 5)
        line_heights.append(total_height)

    img_width = max(line_widths) + 20 if line_widths else 100
    img_height = sum(line_heights) + 15 * len(lines) if line_heights else 50
    
    # رسم النص مع حواف سوداء (بدون خلفية)
    img = Image.new("RGBA", (img_width, img_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    current_h = 0

    for line_idx, (line, h) in enumerate(zip(lines, line_heights)):
        # رسم النص مع حواف سوداء
        line_segments = re.split(r'([A-Za-z0-9\s]+)', line)
        line_segments = [seg for seg in line_segments if seg.strip()]
        line_segments.reverse()
        line_width = line_widths[line_idx]
        current_x = img_width - line_width - 10
        for seg in line_segments:
            font = latin_font if re.match(r'[A-Za-z0-9\s]+', seg) else arabic_font
            bbox = draw.textbbox((0, 0), seg, font=font)
            # رسم النص مع stroke أسود
            draw.text((current_x, current_h), seg, font=font, fill=color, stroke_width=1, stroke_fill="black")
            current_x += (bbox[2] - bbox[0]) + 5
        current_h += h + 15

    img_array = np.array(img)
    clip_duration = end_time - start_time
    clip = ImageClip(img_array).set_duration(clip_duration)\
                               .set_start(start_time)\
                               .crossfadein(0.5)\
                               .set_position(position)\
                               .set_opacity(0.8)
    print(f"Text clip created successfully for segment {start_time}-{end_time}")
    return clip

# دالة إضافة الترجمة إلى الفيديو
def add_subtitles(video_path, segments, is_translation=True):
    print(f"Starting subtitle addition for {len(segments)} segments")
    video_clip = VideoFileClip(video_path)
    print(f"Video clip loaded: {video_clip.w}x{video_clip.h}, duration: {video_clip.duration}s")
    clips = []
    
    for i, (start_time, end_time, text) in enumerate(segments):
        print(f"Processing subtitle {i+1}/{len(segments)}")
        text_clip = create_text_clip_pil(
            text,
            fontsize=28,
            color="white",
            bg_color="black",
            max_width=video_clip.w * 0.8,
            start_time=start_time,
            end_time=end_time,
            position=("center", "bottom")
        )
        clips.append(text_clip)

    final_clip = CompositeVideoClip([video_clip] + clips)
    output_path = video_path.replace(".mp4", "_with_subtitles.mp4")
    print(f"Writing final video to: {output_path}")
    start_time_write = time.time()
    final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", threads=4, verbose=False, logger=None)
    print(f"Video writing completed in {time.time() - start_time_write:.2f} seconds!")
    
    video_clip.close()
    final_clip.close()
    for clip in clips:
        clip.close()
    print("All clips closed successfully")
    
    return output_path

# دالة إنشاء ملف الترجمات
def create_subtitles_file(segments, file_path):
    with open(file_path, 'w', encoding='utf-8') as f:
        for seg in segments:
            time_str = f"{int(seg[0]//60):02d}:{int(seg[0]%60):02d}"
            f.write(f"[{time_str}] {seg[2]}\n")
    return file_path

# تحسين جودة الصوت
def enhance_audio(audio_path):
    print(f"Enhancing audio: {audio_path}")
    enhanced_audio_path = audio_path.replace(".wav", "_enhanced.wav")
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", audio_path, "-af", "volume=2.0,highpass=f=200,lowpass=f=3000,equalizer=f=1000:t=h:w=200:g=2", enhanced_audio_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        print(f"Audio enhanced successfully: {enhanced_audio_path}")
        return enhanced_audio_path
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if e.stderr else "Unknown ffmpeg error"
        print(f"Error enhancing audio: {error_msg}")
        return audio_path

# التوكن هنا
TOKEN = "7942028086:AAE-I3_aoVqQ7gNE2CfuPb4JeZw77eewV9s"
bot = telebot.TeleBot(TOKEN)

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

print("جارٍ تحميل نموذج Whisper...")
start_load = time.time()
model = whisper.load_model("medium", device="cpu")
print(f"تم تحميل نموذج Whisper بنجاح في {time.time() - start_load:.2f} ثوانٍ!")
translator = GoogleTranslator(source="auto", target="ar")
print("تم تحميل نموذج الترجمة بنجاح!")

# رسالة ترحيبية
@bot.message_handler(commands=['start'])
def send_welcome(message):
    print(f"User {message.from_user.id} started the bot")
    welcome_message = (
        "🎥 *مرحبًا بك في بوت الترجمة السحري* 🎥\n\n"
        "أنا هنا لأجعل فيديوهاتك تتحدث بالعربية بطريقة احترافية 😍\n"
        "كل ما عليك هو إرسال فيديو وسأقوم باستخراج النص أو ترجمته وإضافته بأسلوب مميز مع تأثيرات بصرية رائعة.\n\n"
        "✨ *مميزاتي*:\n"
        "- استخراج النص العربي بدقة عالية.\n"
        "- ترجمة الفيديوهات من أي لغة إلى العربية.\n"
        "- نصوص بخط نسخ عربي أنيق مع حواف سوداء.\n"
        "- إمكانية تصحيح النصوص والترجمات بسهولة!\n\n"
        "🚀 جاهز؟ أرسل فيديو الآن وجرب السحر بنفسك!"
    )
    bot.reply_to(message, welcome_message, parse_mode='Markdown')

# معالجة الفيديو (مع خيار الاستخراج أو الترجمة)
@bot.message_handler(content_types=['video'])
def handle_video(message):
    print(f"New video message from user {message.from_user.id}, file_id: {message.video.file_id}, duration: {message.video.duration}s")
    chat_id = message.chat.id
    user_id = message.from_user.id
    user_data = {'video_path': None, 'audio_path': None, 'segments': None, 'language': None, 'mode': None}
    
    bot.send_message(chat_id, "📥 *جارٍ تحميل الفيديو الخاص بك، لحظه واحدة* ⏳", parse_mode='Markdown')
    
    file_info = bot.get_file(message.video.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    video_path = os.path.join(DOWNLOAD_FOLDER, f"{message.video.file_id}.mp4")
    
    with open(video_path, "wb") as new_file:
        new_file.write(downloaded_file)
    
    print(f"Video downloaded to: {video_path}")
    bot.send_message(chat_id, "🎥 *تم تحميل الفيديو بنجاح، جارٍ العمل عليه* 🎉", parse_mode='Markdown')
    
    audio_path = video_path.replace(".mp4", ".wav")
    try:
        print("Starting audio extraction with ffmpeg...")
        bot.send_message(chat_id, "🎤 *جارٍ استخراج الصوت، انتظر قليلاً* 🎶", parse_mode='Markdown')
        subprocess.run(
            ["ffmpeg", "-y", "-i", video_path, "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", audio_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        print(f"Audio extracted successfully to: {audio_path}")
        bot.send_message(chat_id, "🎤 *تم استخراج الصوت بنجاح* ✅", parse_mode='Markdown')
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if e.stderr else "Unknown ffmpeg error"
        print(f"FFmpeg error during audio extraction: {error_msg}")
        bot.send_message(chat_id, f"❌ *عذراً، حدث خطأ أثناء استخراج الصوت: {error_msg}* 😔", parse_mode='Markdown')
        return
    
    # تحسين الصوت
    audio_path = enhance_audio(audio_path)
    
    bot.send_message(chat_id, "📝 *جارٍ تحويل الصوت إلى نص، أعمل بجد* ✍️", parse_mode='Markdown')
    try:
        print("Starting Whisper transcription...")
        start_transcribe = time.time()
        result = model.transcribe(
            audio_path,
            language="ar",
            fp16=False,
            verbose=False,
            word_timestamps=False,
            condition_on_previous_text=False
        )
        transcribe_time = time.time() - start_transcribe
        detected_language = "ar"
        segments = result["segments"]
        print(f"Transcription completed in {transcribe_time:.2f} seconds: {len(segments)} segments found, language: {detected_language}")
        if len(segments) == 0:
            print("No segments detected! Trying without specified language...")
            result = model.transcribe(
                audio_path,
                language=None,
                fp16=False,
                verbose=False,
                word_timestamps=False,
                condition_on_previous_text=False
            )
            detected_language = result.get("language", "unknown")
            segments = result["segments"]
            print(f"Retry transcription without language: {len(segments)} segments found")
        
        # تصحيح اللهجة للنصوص العربية دون تجاهل أي segments
        filtered_segments = []
        for segment in segments:
            # تصحيح اللهجة للنصوص العربية
            if detected_language == "ar":
                segment["text"] = correct_dialect(segment["text"])
            filtered_segments.append(segment)
        
        segments = filtered_segments
        print(f"Processed segments: {len(segments)} (no intro filtering)")
        
        # حفظ البيانات للمستخدم
        user_data['video_path'] = video_path
        user_data['audio_path'] = audio_path
        user_data['segments'] = segments
        user_data['language'] = detected_language
        user_data_storage[(user_id, chat_id)] = user_data
        
        # رسالة توضيح اللغة المكتشفة
        if detected_language == "ar":
            lang_message = "🌟 *تم اكتشاف اللغة العربية، جارٍ إعداد النصوص لإضافتها إلى الفيديو* 📝"
        else:
            lang_message = f"🌍 *تم اكتشاف اللغة: {detected_language}، جارٍ ترجمة الفيديو إلى العربية* ✨"
        bot.send_message(chat_id, lang_message, parse_mode='Markdown')
        
        # رسالة الخيار
        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        btn_extract = telebot.types.InlineKeyboardButton("استخراج النص العربي ودمجه مع الفيديو 📝", callback_data="extract")
        btn_translate = telebot.types.InlineKeyboardButton("ترجمة الفيديو إلى العربية ودمجها 🌐", callback_data="translate")
        markup.add(btn_extract, btn_translate)
        bot.send_message(chat_id, f"✅ *تم استخراج النص بنجاح ({len(segments)} جزء)!*\n\n*ماذا تريد؟*\n\n⚠️ *ملاحظة: للعامية (مصري/خليجي)، الدقة جيدة لكن قد تكون أقل من الفصحى.*", reply_markup=markup, parse_mode='Markdown')
        
    except Exception as e:
        print(f"Whisper transcription error: {str(e)}")
        bot.send_message(chat_id, f"❌ *عذراً، حدث خطأ أثناء تحويل الصوت إلى نص: {str(e)}* 😓\nحاول مرة أخرى مع فيديو آخر!", parse_mode='Markdown')
        return

# معالجة الخيارات
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    data = call.data
    
    user_data = user_data_storage.get((user_id, chat_id))
    if not user_data:
        bot.answer_callback_query(call.id, "❌ خطأ في البيانات. أعد إرسال الفيديو.")
        return
    
    video_path = user_data['video_path']
    audio_path = user_data['audio_path']
    segments = user_data['segments']
    detected_language = user_data['language']
    
    try:
        if data == "extract":
            print("User chose extract Arabic text")
            bot.answer_callback_query(call.id, "جارٍ دمج النص العربي...")
            extracted_segments = [(seg['start'], seg['end'], seg['text'].strip()) for seg in segments if seg['text'].strip()]
            user_data['mode'] = 'extract'
            user_data['extracted_segments'] = extracted_segments  # حفظ النصوص المستخرجة للتصحيح
            user_data_storage[(user_id, chat_id)] = user_data
            final_video_path = add_subtitles(video_path, extracted_segments, is_translation=False)
            bot.send_message(chat_id, "✅ *تم دمج النص العربي بنجاح* 📝\nإليك الفيديو مع النصوص الأصلية!", parse_mode='Markdown')
            with open(final_video_path, "rb") as video_file:
                bot.send_video(chat_id, video_file, caption="🎥 إليك الفيديو مع النص العربي بأسلوب احترافي 😊", parse_mode='Markdown')
            
            # إنشاء وإرسال ملف النصوص
            subtitles_file = os.path.join(DOWNLOAD_FOLDER, f"{user_id}_subtitles.txt")
            create_subtitles_file(extracted_segments, subtitles_file)
            with open(subtitles_file, "rb") as file:
                bot.send_document(chat_id, file, caption="📄 *هذا ملف النصوص المستخرجة للتصحيح. افتحه، عدل ما تريد، ثم أرسل التصحيحات بالصيغة: MM:SS: النص المُصحح*\n\n*مثال: 01:02: هذا النص الصحيح*\n\n*أرسل كل تصحيح في رسالة منفصلة.*", parse_mode='Markdown')
            
            # إضافة زر التعديل
            markup = telebot.types.InlineKeyboardMarkup(row_width=1)
            btn_edit = telebot.types.InlineKeyboardButton("تعديل النصوص ✏️", callback_data="edit")
            markup.add(btn_edit)
            bot.send_message(chat_id, "✨ *هل تريد تعديل النصوص المستخرجة؟ اضغط على الزر أدناه للبدء في التصحيح.*", reply_markup=markup, parse_mode='Markdown')
            print(f"Extracted video sent to user {chat_id}")
        
        elif data == "translate":
            print("User chose translation")
            bot.answer_callback_query(call.id, "جارٍ الترجمة...")
            translated_segments = []
            for segment in segments:
                start_time = segment["start"]
                end_time = segment["end"]
                original_text = segment["text"].strip()
                if not original_text:
                    continue
                print(f"Segment - Original: {original_text} ({start_time}s - {end_time}s)")
                if detected_language == "ar":
                    translated_text = correct_dialect(original_text)
                else:
                    translated_text = translator.translate(original_text)
                    if translated_text:
                        translated_text = improve_translation(translated_text, is_song=True)
                    else:
                        print(f"Translation failed for segment: {original_text}")
                        continue
                print(f"Translated: {translated_text}")
                translated_segments.append((start_time, end_time, translated_text))
            
            if not translated_segments:
                bot.send_message(chat_id, "❌ *عذراً، فشلت الترجمة* 😢\nحاول مرة أخرى مع فيديو آخر!", parse_mode='Markdown')
                return
            
            user_data['mode'] = 'translate'
            user_data['translated_segments'] = translated_segments  # حفظ الترجمات للتصحيح
            user_data_storage[(user_id, chat_id)] = user_data
            
            final_video_path = add_subtitles(video_path, translated_segments, is_translation=True)
            bot.send_message(chat_id, "✅ *تم دمج الترجمة بنجاح* 🌐\nإليك الفيديو المترجم إلى العربية!", parse_mode='Markdown')
            with open(final_video_path, "rb") as video_file:
                bot.send_video(chat_id, video_file, caption="🎥 إليك الفيديو المترجم بأسلوب احترافي 😊", parse_mode='Markdown')
            
            # إنشاء وإرسال ملف الترجمات
            subtitles_file = os.path.join(DOWNLOAD_FOLDER, f"{user_id}_subtitles.txt")
            create_subtitles_file(translated_segments, subtitles_file)
            with open(subtitles_file, "rb") as file:
                bot.send_document(chat_id, file, caption="📄 *هذا ملف الترجمات للتصحيح. افتحه، عدل ما تريد، ثم أرسل التصحيحات بالصيغة: MM:SS: النص المُصحح*\n\n*مثال: 01:02: هذا النص الصحيح*\n\n*أرسل كل تصحيح في رسالة منفصلة.*", parse_mode='Markdown')
            
            # إضافة زر التعديل
            markup = telebot.types.InlineKeyboardMarkup(row_width=1)
            btn_edit = telebot.types.InlineKeyboardButton("تعديل الترجمات ✏️", callback_data="edit")
            markup.add(btn_edit)
            bot.send_message(chat_id, "✨ *هل تريد تعديل الترجمات؟ اضغط على الزر أدناه للبدء في التصحيح.*", reply_markup=markup, parse_mode='Markdown')
            print(f"Translated video sent to user {chat_id}")
        
        elif data == "edit":
            bot.answer_callback_query(call.id, "جارٍ إعداد وضع التصحيح...")
            mode = user_data.get('mode', 'extract')
            if mode == 'extract':
                msg = "🔧 *وضع تصحيح النصوص المستخرجة مفعل!*"
            else:
                msg = "🔧 *وضع تصحيح الترجمات مفعل!*"
            bot.send_message(chat_id, f"{msg}\n\n*كيفية التصحيح:*\n1. افتح الملف المرسل سابقًا.\n2. لاحظ الوقت (مثل 01:02) والنص.\n3. أرسل رسالة هنا بالصيغة: `MM:SS: النص الجديد`\n\n*مثال:*\n`00:05: هذا النص المُصحح`\n\n*أرسل التصحيحات واحدة تلو الأخرى. عند الانتهاء، أرسل `/done` لإعادة بناء الفيديو.*\n\n*ملاحظة: الوقت بالدقائق:ثوانٍ (MM:SS). سأحدث فقط الجزء المقابل.*", parse_mode='Markdown')
            user_data['edit_mode'] = True
            user_data_storage[(user_id, chat_id)] = user_data
    
    except Exception as e:
        print(f"Error during subtitle integration: {str(e)}")
        bot.send_message(chat_id, f"❌ *عذراً، حدث خطأ أثناء دمج النص/الترجمة: {str(e)}* 😢\nحاول مرة أخرى!", parse_mode='Markdown')
    
    finally:
        # تنظيف البيانات (لا تنظف هنا إلا بعد التصحيح)
        pass

# معالجة التصحيحات
@bot.message_handler(content_types=['text'], func=lambda message: user_data_storage.get((message.from_user.id, message.chat.id), {}).get('edit_mode', False))
def handle_correction(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    user_data = user_data_storage.get((user_id, chat_id))
    if not user_data or not user_data.get('edit_mode'):
        return
    
    text = message.text.strip()
    
    if text == '/done':
        # إنهاء التصحيح وإعادة بناء الفيديو
        bot.send_message(chat_id, "✅ *تم الانتهاء من التصحيحات! جارٍ إعادة بناء الفيديو...* ⏳", parse_mode='Markdown')
        video_path = user_data['video_path']
        mode = user_data.get('mode', 'extract')
        if mode == 'extract':
            segments = user_data['extracted_segments']
        else:
            segments = user_data['translated_segments']
        final_video_path = add_subtitles(video_path, segments, is_translation=(mode == 'translate'))
        with open(final_video_path, "rb") as video_file:
            if mode == 'extract':
                bot.send_video(chat_id, video_file, caption="🎥 *إليك الفيديو مع النصوص المُصححة!* 😊", parse_mode='Markdown')
            else:
                bot.send_video(chat_id, video_file, caption="🎥 *إليك الفيديو مع الترجمات المُصححة!* 😊", parse_mode='Markdown')
        
        # تنظيف كامل
        user_data_storage.pop((user_id, chat_id), None)
        print("Edit mode ended and cleanup completed")
        bot.send_message(chat_id, "🧹 *تم مسح السياق. أرسل فيديو جديد للبدء من جديد!*", parse_mode='Markdown')
        return
    
    # التحقق من صيغة التصحيح
    match = re.match(r'(\d{2}:\d{2}):\s*(.+)', text)
    if not match:
        bot.reply_to(message, "❌ *الصيغة غير صحيحة! استخدم: MM:SS: النص الجديد*\n\n*مثال: 01:02: هذا النص الصحيح*", parse_mode='Markdown')
        return
    
    time_str = match.group(1)
    new_text = match.group(2).strip()
    
    # تحويل الوقت إلى ثوانٍ
    try:
        minutes, seconds = map(int, time_str.split(':'))
        target_time = minutes * 60 + seconds
    except ValueError:
        bot.reply_to(message, "❌ *خطأ في تنسيق الوقت! استخدم MM:SS*", parse_mode='Markdown')
        return
    
    # البحث عن الـ segment الأقرب
    mode = user_data.get('mode', 'extract')
    if mode == 'extract':
        segments = user_data['extracted_segments']
    else:
        segments = user_data['translated_segments']
    updated = False
    for i, (start, end, _) in enumerate(segments):
        if abs(start - target_time) < 3:  # تحمل 3 ثوانٍ
            segments[i] = (start, end, new_text)
            updated = True
            break
    
    if updated:
        if mode == 'extract':
            user_data['extracted_segments'] = segments
        else:
            user_data['translated_segments'] = segments
        user_data_storage[(user_id, chat_id)] = user_data
        bot.reply_to(message, f"✅ *تم تحديث النص في {time_str} إلى: {new_text}*", parse_mode='Markdown')
    else:
        bot.reply_to(message, f"❌ *لم أجد وقتًا مطابقًا لـ {time_str} (تحمل ±3 ثوانٍ). تحقق من الملف.*", parse_mode='Markdown')

# معالجة النصوص العادية
@bot.message_handler(content_types=['text'])
def handle_text(message):
    print(f"Text message from user {message.from_user.id}: {message.text}")
    bot.reply_to(message, "🤔 *عذراً، أنا بوت ترجمة فيديو احترافي!* أرسل فيديو وسأعالجه بأسلوب سحري ✨", parse_mode='Markdown')

print("Bot started and polling...")
bot.polling()