"""
مدير البيانات - يتعامل مع تحميل وحفظ جميع ملفات JSON
"""
import json
import os
from config import (
    DETECTION_FILE, REPLIES_FILE, BANNED_WORDS_FILE, 
    REPORT_GROUPS_FILE, VERIFICATION_FILE, WELCOME_FILE, MENTIONS_FILE
)


class DataManager:
    """مدير البيانات لتحميل وحفظ ملفات JSON"""
    
    def __init__(self):
        # تهيئة جميع البيانات
        self.group_detection_status = self.load_json(DETECTION_FILE, {})
        self.group_replies = self.load_json(REPLIES_FILE, {})
        self.banned_words = self.load_json(BANNED_WORDS_FILE, {})
        self.report_groups = self.load_json(REPORT_GROUPS_FILE, {})
        self.welcome_messages = self.load_json(WELCOME_FILE, {})
        self.active_mentions = self.load_json(MENTIONS_FILE, {})
        
        # تحميل حالة التحقق
        verification_status = self.load_json(VERIFICATION_FILE, {'mode': {}, 'pending': {}})
        self.verification_mode = verification_status.get('mode', {})
        self.verification_pending = verification_status.get('pending', {})
        
        # متغيرات إضافية
        self.warnings = {}  # {group_id: {user_id: count}}
        self.user_violations = {}
        self.activated_groups = {}
        self.daily_reports = {}
        self.ban_tracker = {}
        self.pending_replies = {}
        self.bot_promoted_admins = {}
        self.pending_promotions = {}
        self.users = set()
        self.groups = set()
        self.stop_mentions = {}
        self.stop_mentions_flag = {}
        self.welcome_pending = {}
    
    @staticmethod
    def load_json(filename, default=None):
        """تحميل ملف JSON"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return default if default is not None else {}
    
    @staticmethod
    def save_json(filename, data):
        """حفظ بيانات إلى ملف JSON"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    
    def save_detection_status(self):
        """حفظ حالة الكشف"""
        self.save_json(DETECTION_FILE, self.group_detection_status)
    
    def save_replies(self):
        """حفظ الردود"""
        self.save_json(REPLIES_FILE, self.group_replies)
    
    def save_banned_words(self):
        """حفظ الكلمات المحظورة"""
        self.save_json(BANNED_WORDS_FILE, self.banned_words)
    
    def save_report_groups(self):
        """حفظ مجموعات التقارير"""
        self.save_json(REPORT_GROUPS_FILE, self.report_groups)
    
    def save_welcome(self):
        """حفظ رسائل الترحيب"""
        self.save_json(WELCOME_FILE, self.welcome_messages)
    
    def save_mentions(self):
        """حفظ بيانات الإشارات"""
        self.save_json(MENTIONS_FILE, self.active_mentions)
    
    def save_verification_status(self):
        """حفظ حالة التحقق"""
        verification_status = {
            'mode': self.verification_mode,
            'pending': self.verification_pending
        }
        self.save_json(VERIFICATION_FILE, verification_status)
    
    def get_warnings(self, group_id, user_id):
        """الحصول على عدد التحذيرات لمستخدم في مجموعة"""
        group_id = str(group_id)
        user_id = str(user_id)
        return self.warnings.get(group_id, {}).get(user_id, 0)
    
    def add_warning(self, group_id, user_id):
        """إضافة تحذير لمستخدم"""
        group_id = str(group_id)
        user_id = str(user_id)
        if group_id not in self.warnings:
            self.warnings[group_id] = {}
        self.warnings[group_id][user_id] = self.warnings[group_id].get(user_id, 0) + 1
        return self.warnings[group_id][user_id]
    
    def remove_warning(self, group_id, user_id):
        """إزالة تحذير من مستخدم"""
        group_id = str(group_id)
        user_id = str(user_id)
        if group_id in self.warnings and user_id in self.warnings[group_id]:
            if self.warnings[group_id][user_id] > 0:
                self.warnings[group_id][user_id] -= 1
                return True
        return False
    
    def clear_warnings(self, group_id, user_id):
        """مسح جميع التحذيرات لمستخدم"""
        group_id = str(group_id)
        user_id = str(user_id)
        if group_id in self.warnings and user_id in self.warnings[group_id]:
            del self.warnings[group_id][user_id]
            return True
        return False


# إنشاء نسخة عامة من مدير البيانات
data_manager = DataManager()
