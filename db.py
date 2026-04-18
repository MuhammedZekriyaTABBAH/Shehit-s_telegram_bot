import sqlite3
import re
from typing import List, Optional, Dict, Any

DB_NAME = "database.db"

def normalize_text(text: str) -> str:
    """تطبيع النص للبحث"""
    if not text:
        return text
    text = text.strip().lower()
    # توحيد أشكال الألف
    text = re.sub(r"[أإآا]", "ا", text)
    # توحيد التاء المربوطة
    text = re.sub(r"ة$", "ه", text)
    return text

def connect():
    """إنشاء اتصال بقاعدة البيانات"""
    return sqlite3.connect(DB_NAME)

def create_table():
    """إنشاء الجدول إذا لم يكن موجوداً"""
    conn = connect()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS people (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        last_name TEXT NOT NULL,
        first_name TEXT,
        birth_year INTEGER,
        country TEXT,
        job TEXT,
        death_year INTEGER,
        death_place TEXT,
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # إنشاء فهرس للبحث السريع
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_last_name ON people(last_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_country ON people(country)")
    
    cursor.execute("PRAGMA journal_mode=WAL;")
    conn.commit()
    conn.close()

def add_person(**kwargs) -> bool:
    """إضافة شخص جديد"""
    try:
        conn = connect()
        cursor = conn.cursor()
        
        cursor.execute("""
        INSERT INTO people (
            last_name, first_name, birth_year,
            country, job, death_year, death_place, created_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            kwargs.get('last_name'),
            kwargs.get('first_name'),
            kwargs.get('birth_year'),
            kwargs.get('country'),
            kwargs.get('job'),
            kwargs.get('death_year'),
            kwargs.get('death_place'),
            kwargs.get('created_by')
        ))
        
        conn.commit()
        conn.close()
        return True
    
    except Exception as e:
        print(f"Error adding person: {e}")
        return False

def search_people(keyword: str) -> List[Dict[str, Any]]:
    """البحث في البيانات باستخدام كلمة مفتاحية"""
    keyword = normalize_text(keyword)
    
    conn = connect()
    conn.row_factory = sqlite3.Row  # للوصول للأعمدة بالاسم
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT * FROM people
    WHERE last_name LIKE ? 
       OR first_name LIKE ? 
       OR country LIKE ?
       OR job LIKE ?
    ORDER BY 
        CASE WHEN last_name = ? THEN 0 ELSE 1 END,
        last_name, first_name
    """, (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", keyword))
    
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return results

def get_person_by_last_name(last_name: str) -> List[Dict[str, Any]]:
    """البحث باللقب بالضبط"""
    last_name = normalize_text(last_name)
    
    conn = connect()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT * FROM people
    WHERE last_name = ?
    ORDER BY created_at DESC
    """, (last_name,))
    
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return results

def get_person_by_id(person_id: int) -> Optional[Dict[str, Any]]:
    """الحصول على شخص بواسطة المعرف"""
    conn = connect()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM people WHERE id = ?", (person_id,))
    result = cursor.fetchone()
    conn.close()
    
    return dict(result) if result else None

def update_person(person_id: int, field: str, value: Any) -> bool:
    """تحديث حقل معين لشخص"""
    allowed_fields = ['last_name', 'first_name', 'birth_year', 'country', 
                      'job', 'death_year', 'death_place']
    
    if field not in allowed_fields:
        return False
    
    try:
        conn = connect()
        cursor = conn.cursor()
        
        query = f"UPDATE people SET {field} = ? WHERE id = ?"
        cursor.execute(query, (value, person_id))
        
        conn.commit()
        conn.close()
        return True
    
    except Exception as e:
        print(f"Error updating person: {e}")
        return False

def delete_person(person_id: int) -> bool:
    """حذف شخص (للمسؤولين فقط)"""
    try:
        conn = connect()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM people WHERE id = ?", (person_id,))
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected > 0
    
    except Exception as e:
        print(f"Error deleting person: {e}")
        return False

def get_recent_people(limit: int = 10) -> List[Dict[str, Any]]:
    """الحصول على آخر الإضافات"""
    conn = connect()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT * FROM people 
    ORDER BY created_at DESC 
    LIMIT ?
    """, (limit,))
    
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return results

def get_statistics() -> Dict[str, Any]:
    """إحصائيات عن قاعدة البيانات"""
    conn = connect()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM people")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT country) FROM people WHERE country IS NOT NULL")
    countries = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'total_people': total,
        'total_countries': countries
    }