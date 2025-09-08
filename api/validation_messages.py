VALIDATION_MESSAGES = {
    'ar': {
        # رسائل التسجيل
        'email_already_exists': 'هذا البريد الإلكتروني مستخدم بالفعل',
        'passwords_dont_match': 'كلمات المرور غير متطابقة',
        'organization_email_exists': 'هذا البريد الإلكتروني مستخدم من قبل مؤسسة',
        'phone_required': 'رقم الهاتف مطلوب',
        
        # رسائل تسجيل الخروج
        'token_invalid': 'الرمز المميز غير صحيح أو منتهي الصلاحية',
        
        # رسائل استرجاع كلمة المرور
        'email_not_registered': 'هذا البريد الإلكتروني غير مسجل',
        'reset_token_invalid': 'رمز استعادة كلمة المرور غير صحيح أو منتهي الصلاحية',
        'invalid_user_id': 'معرف المستخدم غير صحيح',
        
        # رسائل تغيير كلمة المرور
        'current_password_incorrect': 'كلمة المرور الحالية غير صحيحة',
        'new_passwords_dont_match': 'كلمات المرور الجديدة غير متطابقة',
    },
    
    'en': {
        # Signup messages
        'email_already_exists': 'This email is already in use',
        'passwords_dont_match': 'Passwords do not match',
        'organization_email_exists': 'A user with this email already exists.',
        'phone_required': 'Phone number is required.',
        
        # Logout messages
        'token_invalid': 'Token is invalid or expired',
        
        # Forgot password messages
        'email_not_registered': 'This email is not registered',
        'reset_token_invalid': 'Invalid or expired reset token',
        'invalid_user_id': 'Invalid user ID',
        
        # Change password messages
        'current_password_incorrect': 'Current password is incorrect',
        'new_passwords_dont_match': 'New passwords do not match',
    }
}

# دالة للحصول على الرسالة حسب اللغة
def get_message(key, language='ar'):
    """
    استخراج الرسالة حسب المفتاح واللغة
    """
    if language not in VALIDATION_MESSAGES:
        language = 'ar'  # اللغة الافتراضية
    
    messages = VALIDATION_MESSAGES.get(language, VALIDATION_MESSAGES['ar'])
    return messages.get(key, key)

# كلاس مساعد للاستخدام في الـ serializers
class ValidationMessages:
    """
    كلاس مساعد لإدارة رسائل التحقق
    """
    
    def __init__(self, language='ar'):
        self.language = language
        self.messages = VALIDATION_MESSAGES.get(language, VALIDATION_MESSAGES['ar'])
    
    def get(self, key, default=None):
        """الحصول على الرسالة"""
        return self.messages.get(key, default or key)
    
    def __getitem__(self, key):
        """استخدام مع الـ square brackets"""
        return self.get(key)

# دالة للحصول على اللغة من الـ request
def get_user_language(request=None):
    """
    استخراج لغة المستخدم من الـ request
    """
    if request is None:
        return 'ar'
    
    # من الـ headers
    language = request.META.get('HTTP_ACCEPT_LANGUAGE', '').lower()
    if 'ar' in language:
        return 'ar'
    elif 'en' in language:
        return 'en'
    
    # من الـ query parameters
    lang_param = request.GET.get('lang', '').lower()
    if lang_param in ['ar', 'en']:
        return lang_param
    
    # من الـ user profile إذا كان مسجل دخول
    if hasattr(request, 'user') and request.user.is_authenticated:
        # يمكنك إضافة حقل language في نموذج المستخدم
        user_lang = getattr(request.user, 'language', 'ar')
        if user_lang in ['ar', 'en']:
            return user_lang
    
    return 'ar'  # اللغة الافتراضية

# Exception مخصص للرسائل متعددة اللغات
class ValidationError(Exception):
    """
    Exception مخصص لرسائل التحقق متعددة اللغات
    """
    
    def __init__(self, message_key, language='ar', field=None):
        self.message_key = message_key
        self.language = language
        self.field = field
        self.message = get_message(message_key, language)
        super().__init__(self.message)