"""
ملف الإعدادات - يحتوي على المتغيرات الحساسة ومعلومات البوت
"""

# معلومات البوت
TOKEN = '7588670003:AAGvfATw4v2SHVxG3mrocydqL1D-JUJjROg'
BOT_USERNAME = '@SY_SBbot'

# مفاتيح API
YOUTUBE_API_KEY = 'AIzaSyBG81yezyxy-SE4cd_-JCK55gEzHkPV9aw'

# معلومات القناة
CHANNEL_URL = 'https://t.me/SYR_SB'
CHANNEL_USERNAME = 'SYR_SB'

# معلومات المطور
DEVELOPER_CHAT_ID = '6789179634'

# روابط إضافية
VIDEO_URL = "https://64.media.tumblr.com/3cfa430aea644288ede38845e8f40f18/tumblr_owse940yxU1w2zpqco1_540.gif"

# أسماء ملفات البيانات
DETECTION_FILE = "detection_status.json"
REPLIES_FILE = "replies.json"
BANNED_WORDS_FILE = "banned_words.json"
REPORT_GROUPS_FILE = "report_groups.json"
DATA_FILE = "restart_data.json"
VERIFICATION_FILE = 'verification_status.json'
WELCOME_FILE = 'welcome.json'
MENTIONS_FILE = 'mentions.json'

# الصلاحيات الافتراضية
PERMISSION_NAMES = {
    "can_delete_messages": "حذف الرسائل",
    "can_restrict_members": "تقييد الأعضاء",
    "can_invite_users": "إضافة أعضاء",
    "can_pin_messages": "تثبيت الرسائل",
    "can_change_info": "تغيير معلومات المجموعة",
    "can_manage_chat": "إدارة المجموعة"
}

DEFAULT_PERMISSIONS = {perm: False for perm in PERMISSION_NAMES}
