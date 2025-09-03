import re

def validate_iranian_postal_code(postal_code):
    """Validate Iranian postal code format"""
    if not re.match(r'^\d{10}$', postal_code):
        return False, 'کد پستی باید ۱۰ رقم باشد'
    return True, 'معتبر'

def validate_iranian_phone(phone_number):
    """Validate Iranian mobile phone number"""
    if not re.match(r'^09\d{9}$', phone_number):
        return False, 'شماره موبایل باید با ۰۹ شروع شود و ۱۱ رقم باشد'
    return True, 'معتبر'

def validate_iranian_national_id(national_id):
    """Validate Iranian national ID"""
    if not re.match(r'^\d{10}$', national_id):
        return False, 'کد ملی باید ۱۰ رقم باشد'
    
    # Checksum validation
    check = int(national_id[9])
    sum_digits = sum(int(national_id[i]) * (10 - i) for i in range(9))
    remainder = sum_digits % 11
    
    if remainder < 2 and check == remainder:
        return True, 'معتبر'
    elif remainder >= 2 and check == 11 - remainder:
        return True, 'معتبر'
    
    return False, 'کد ملی نامعتبر است'