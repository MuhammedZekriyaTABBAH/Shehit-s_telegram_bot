from supabase_py import create_client, Client
from datetime import datetime
from typing import List, Dict, Any, Optional
import os

# إعدادات Supabase - أدخل بياناتك هنا
SUPABASE_URL = "https://xxxxx.supabase.co"  # ضع الـ URL هنا
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIs..."    # ضع الـ anon key هنا

# إنشاء عميل Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def normalize_text(text: str) -> str:
    """تطبيع النص للبحث"""
    if not text:
        return text
    import re
    text = text.strip().lower()
    text = re.sub(r"[أإآا]", "ا", text)
    text = re.sub(r"ة$", "ه", text)
    return text

def create_table():
    """الجدول يتم إنشاؤه يدوياً من SQL Editor"""
    print("✅ Supabase جاهز للعمل")

def add_person(**kwargs) -> bool:
    """إضافة شخص جديد"""
    try:
        data = {
            "last_name": kwargs.get('last_name'),
            "first_name": kwargs.get('first_name'),
            "birth_year": kwargs.get('birth_year'),
            "country": kwargs.get('country'),
            "job": kwargs.get('job'),
            "death_year": kwargs.get('death_year'),
            "death_place": kwargs.get('death_place'),
            "created_by": kwargs.get('created_by')
        }
        
        result = supabase.table('people').insert(data).execute()
        return True
    except Exception as e:
        print(f"خطأ في الإضافة: {e}")
        return False

def search_people(keyword: str) -> List[Dict[str, Any]]:
    """البحث في البيانات"""
    keyword = normalize_text(keyword)
    
    try:
        # في supabase-py 1.2.0، البحث يكون هكذا
        result = supabase.table('people').select('*').execute()
        
        # تصفية النتائج يدوياً (لأن الإصدار القديم لا يدعم ilike)
        filtered = []
        for item in result.get('data', []):
            if (keyword in item.get('last_name', '').lower() or
                keyword in item.get('first_name', '').lower() or
                keyword in item.get('country', '').lower() or
                keyword in item.get('job', '').lower()):
                filtered.append(item)
        
        return filtered
    except Exception as e:
        print(f"خطأ في البحث: {e}")
        return []

def get_person_by_id(person_id: int) -> Optional[Dict[str, Any]]:
    """الحصول على شخص بواسطة المعرف"""
    try:
        result = supabase.table('people').select('*').eq('id', person_id).execute()
        data = result.get('data', [])
        return data[0] if data else None
    except Exception as e:
        print(f"خطأ في البحث بالمعرف: {e}")
        return None

def update_person(person_id: int, field: str, value: Any) -> bool:
    """تحديث حقل معين"""
    allowed_fields = ['last_name', 'first_name', 'birth_year', 'country', 
                      'job', 'death_year', 'death_place']
    
    if field not in allowed_fields:
        return False
    
    try:
        result = supabase.table('people').update({field: value}).eq('id', person_id).execute()
        return True
    except Exception as e:
        print(f"خطأ في التحديث: {e}")
        return False

def delete_person(person_id: int) -> bool:
    """حذف شخص"""
    try:
        result = supabase.table('people').delete().eq('id', person_id).execute()
        return True
    except Exception as e:
        print(f"خطأ في الحذف: {e}")
        return False

def get_recent_people(limit: int = 10) -> List[Dict[str, Any]]:
    """آخر الإضافات"""
    try:
        result = supabase.table('people').select('*').order('created_at', desc=True).limit(limit).execute()
        return result.get('data', [])
    except Exception as e:
        print(f"خطأ في جلب آخر الإضافات: {e}")
        return []

def get_statistics() -> Dict[str, Any]:
    """إحصائيات"""
    try:
        result = supabase.table('people').select('*').execute()
        data = result.get('data', [])
        total = len(data)
        
        countries = set()
        for item in data:
            if item.get('country'):
                countries.add(item['country'])
        
        return {
            'total_people': total,
            'total_countries': len(countries)
        }
    except Exception as e:
        print(f"خطأ في الإحصائيات: {e}")
        return {'total_people': 0, 'total_countries': 0}