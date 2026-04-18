import asyncio
import logging
from typing import Dict, Optional
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.enums import ParseMode
from config import BOT_TOKEN, ADMINS
import db

# إعدادات التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# تهيئة البوت
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# إنشاء الجداول
db.create_table()

# تخزين حالات المستخدمين
user_states: Dict[int, dict] = {}
edit_states: Dict[int, dict] = {}

# =============== لوحة المفاتيح الرئيسية ===============
def get_main_keyboard() -> ReplyKeyboardMarkup:
    """إنشاء أزرار القائمة الرئيسية"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ إضافة شهيد"), KeyboardButton(text="🔍 بحث")],
            [KeyboardButton(text="✏️ تعديل"), KeyboardButton(text="📋 آخر الإضافات")]
        ],
        resize_keyboard=True,
        input_field_placeholder="اختر أحد الخيارات..."
    )
    return keyboard

# =============== أوامر البوت ===============
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """معالج أمر البدء"""
    logger.info(f"المستخدم {message.from_user.id} بدأ البوت")
    await message.answer(
        "✨ **بوت إدارة بيانات الشهداء** ✨\n\n"
        "يمكنك إضافة وتعديل والبحث عن بيانات الشهداء بسهولة.\n"
        "استخدم الأزرار أدناه للتحكم:",
        reply_markup=get_main_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """معالج أمر المساعدة"""
    help_text = (
        "📖 **دليل الاستخدام**\n\n"
        "➕ **إضافة شهيد**: إدخال بيانات شهيد جديد\n"
        "🔍 **بحث**: البحث باللقب أو الاسم أو البلد\n"
        "✏️ **تعديل**: تعديل بيانات شخص باستخدام اللقب\n"
        "📋 **آخر الإضافات**: عرض أحدث 10 إضافات\n\n"
        "💡 *ملاحظة: يمكنك تخطي أي حقل غير معروف بكتابة 'skip'*"
    )
    await message.answer(help_text, parse_mode=ParseMode.MARKDOWN)

# =============== زر الإضافة ===============
@dp.message(F.text == "➕ إضافة شهيد")
async def add_person_start(message: types.Message):
    """بدء عملية إضافة شهيد جديد"""
    user_states[message.from_user.id] = {}
    await message.answer(
        "📝 **إضافة شهيد جديد**\n\n"
        "أدخل **اللقب الحركي** (مثال: أبو خالد الشمالي ، بتار الحلبي, الخ):",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=ReplyKeyboardRemove()
    )

# =============== زر البحث ===============
@dp.message(F.text == "🔍 بحث")
async def search_start(message: types.Message):
    """بدء عملية البحث"""
    user_states[message.from_user.id] = {"mode": "search"}
    await message.answer(
        "🔍 **البحث**\n\n"
        "أدخل **اللقب الحركي** أو **الاسم الحقيقي** أو **البلد** الذي تبحث عنه:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=ReplyKeyboardRemove()
    )

# =============== زر التعديل ===============
@dp.message(F.text == "✏️ تعديل")
async def edit_start(message: types.Message):
    """بدء عملية التعديل"""
    edit_states[message.from_user.id] = {"action": "select_person"}
    await message.answer(
        "✏️ **تعديل البيانات**\n\n"
        "أدخل **اللقب الحركي** للشهيد الذي تريد تعديل بياناته:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=ReplyKeyboardRemove()
    )

# =============== زر آخر الإضافات ===============
@dp.message(F.text == "📋 آخر الإضافات")
async def show_recent(message: types.Message):
    """عرض آخر الإضافات"""
    results = db.get_recent_people(10)
    
    if not results:
        await message.answer(
            "📭 **لا توجد بيانات**\n\n"
            "لم يتم إضافة أي شخص بعد. استخدم زر 'إضافة شهيد' للبدء.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_keyboard()
        )
        return
    
    response = "📋 **آخر 10 إضافات**\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for idx, person in enumerate(results, 1):
        response += f"{idx}. **{person['last_name']}**"
        if person['first_name']:
            response += f" {person['first_name']}"
        response += f"\n   📍 {person['country'] or 'غير محدد'} | ⚔️ {person['job'] or 'غير محدد'}\n\n"
    
    response += "━━━━━━━━━━━━━━━━━━━━━━\n🔍 استخدم زر 'بحث' للتفاصيل الكاملة"
    
    await message.answer(response, parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_keyboard())

# =============== أمر التصدير (للمسؤول فقط) ===============
@dp.message(Command("export"))
async def export_data(message: types.Message):
    """تصدير البيانات - للمسؤولين فقط"""
    if message.from_user.id not in ADMINS:
        await message.answer("⛔ غير مصرح")
        return
    
    await message.answer("📊 جاري التصدير...")
    
    try:
        from openpyxl import Workbook
        from datetime import datetime
        
        # جلب البيانات من Supabase
        results = db.get_recent_people(1000)  # جلب آخر 1000 شخص
        
        if not results:
            await message.answer("📭 لا توجد بيانات")
            return
        
        # إنشاء ملف Excel
        wb = Workbook()
        ws = wb.active
        ws.title = "البيانات"
        
        # إضافة رؤوس الأعمدة
        headers = ['اللقب', 'الاسم', 'سنة الميلاد', 'البلد', 'المهنة', 'سنة الوفاة', 'مكان الوفاة', 'تاريخ الإضافة']
        ws.append(headers)
        
        # إضافة البيانات
        for person in results:
            row = [
                person.get('last_name', ''),
                person.get('first_name', ''),
                person.get('birth_year', ''),
                person.get('country', ''),
                person.get('job', ''),
                person.get('death_year', ''),
                person.get('death_place', ''),
                person.get('created_at', '')
            ]
            ws.append(row)
        
        # حفظ الملف
        filename = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        wb.save(filename)
        
        # إرسال الملف
        file = types.FSInputFile(filename)
        await message.answer_document(file, caption=f"📊 تصدير {len(results)} سجل")
        
    except Exception as e:
        await message.answer(f"❌ خطأ: {str(e)[:100]}")

# =============== المعالج العام للنصوص ===============
@dp.message(F.text & ~F.text.startswith('/'))
async def handle_messages(message: types.Message):
    """معالج النصوص العامة"""
    user_id = message.from_user.id
    text = message.text.strip()
    
    # تجاهل أزرار القائمة
    if text in ["➕ إضافة شهيد", "🔍 بحث", "✏️ تعديل", "📋 آخر الإضافات"]:
        return
    
    try:
        # معالجة البحث
        if user_id in user_states and user_states[user_id].get("mode") == "search":
            await handle_search(message, user_id, text)
        
        # معالجة التعديل
        elif user_id in edit_states:
            await handle_edit(message, user_id, text)
        
        # معالجة الإضافة
        elif user_id in user_states:
            await handle_add_person(message, user_id, text)
        
        else:
            await message.answer(
                "❓ **خيار غير معروف**\nاستخدم الأزرار أدناه:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_main_keyboard()
            )
    
    except Exception as e:
        logger.error(f"خطأ في معالجة الرسالة: {e}")
        await message.answer(
            "⚠️ **حدث خطأ**\nيرجى المحاولة مرة أخرى.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_keyboard()
        )

# =============== دوال المساعدة ===============
async def handle_search(message: types.Message, user_id: int, keyword: str):
    """معالجة البحث وإظهار النتائج"""
    results = db.search_people(keyword)
    
    if not results:
        await message.answer(
            f"🔍 **نتيجة البحث:** '{keyword}'\n\n"
            "❌ **لا توجد نتائج**\n"
            "حاول استخدام كلمات أخرى أو تحقق من الإملاء.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_keyboard()
        )
        del user_states[user_id]
        return
    
    response = f"🔍 **نتائج البحث عن:** '{keyword}'\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for idx, person in enumerate(results[:15], 1):
        response += f"**{idx}. {person['last_name']}**"
        if person['first_name']:
            response += f" {person['first_name']}"
        response += "\n"
        response += f"   📅 الميلاد: {person['birth_year'] or 'غير معروف'} | 🌍 {person['country'] or 'غير معروف'}\n"
        response += f"   ⚔️ {person['job'] or 'غير محدد'}"
        if person['death_year']:
            response += f" 🤲 استشهد: {person['death_year']}"
        response += "\n\n"
    
    if len(results) > 15:
        response += f"⚠️ يوجد {len(results)} نتيجة، تم عرض أول 15 فقط"
    
    response += "\n━━━━━━━━━━━━━━━━━━━━━━\n✏️ للتعديل، استخدم زر 'تعديل' وأدخل اللقب"
    
    await message.answer(response, parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_keyboard())
    del user_states[user_id]

async def handle_edit(message: types.Message, user_id: int, text: str):
    """معالجة عملية التعديل"""
    state = edit_states[user_id]
    
    if state["action"] == "select_person":
        # البحث عن الشخص باللقب
        results = db.search_people(text)
        
        if not results:
            await message.answer(
                f"❌ **لم يتم العثور على '{text}'**\n"
                "تأكد من صحة اللقب وحاول مرة أخرى.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_main_keyboard()
            )
            del edit_states[user_id]
            return
        
        if len(results) > 1:
            response = f"⚠️ **تم العثور على {len(results)} شخص باللقب '{text}':**\n\n"
            for idx, p in enumerate(results, 1):
                response += f"{idx}. {p['last_name']} {p['first_name'] or ''} - {p['country'] or 'بلد غير معروف'}\n"
            response += f"\n📝 **أدخل الرقم (1-{len(results)}) لاختيار الشخص:**"
            
            edit_states[user_id] = {
                "action": "select_by_number",
                "results": results
            }
            await message.answer(response, parse_mode=ParseMode.MARKDOWN)
        else:
            person = results[0]
            edit_states[user_id] = {
                "action": "edit_field",
                "person_id": person['id'],
                "person": person
            }
            await show_edit_fields(message, person)
    
    elif state["action"] == "select_by_number":
        try:
            choice = int(text) - 1
            if 0 <= choice < len(state["results"]):
                person = state["results"][choice]
                edit_states[user_id] = {
                    "action": "edit_field",
                    "person_id": person['id'],
                    "person": person
                }
                await show_edit_fields(message, person)
            else:
                await message.answer("❌ رقم غير صحيح، حاول مرة أخرى:")
        except ValueError:
            await message.answer("❌ الرجاء إدخال رقم صحيح:")
    
    elif state["action"] == "edit_field":
        field_map = {
            "1": "last_name",
            "2": "first_name",
            "3": "birth_year",
            "4": "country",
            "5": "job",
            "6": "death_year",
            "7": "death_place"
        }
        
        if text in field_map:
            field = field_map[text]
            edit_states[user_id]["field"] = field
            edit_states[user_id]["action"] = "edit_value"
            
            # تحويل اسم الحقل للعربية
            field_names = {
                "last_name": "اللقب",
                "first_name": "الاسم",
                "birth_year": "سنة الميلاد",
                "country": "البلد",
                "job": "الاختصاص",
                "death_year": "سنة الاستشهاد",
                "death_place": "مكان الاستشهاد"
            }
            field_arabic = field_names.get(field, field)
            
            await message.answer(
                f"📝 **تعديل {field_arabic}**\n\nأدخل القيمة الجديدة (أو 'skip' للتخطي):",
                parse_mode=ParseMode.MARKDOWN
            )
        elif text.lower() == "cancel":
            await message.answer("❌ تم إلغاء التعديل", reply_markup=get_main_keyboard())
            del edit_states[user_id]
        else:
            await message.answer("❌ رقم غير صحيح، أدخل رقماً من 1 إلى 7، أو 'cancel':")
    
    elif state["action"] == "edit_value":
        if text.lower() == "cancel":
            await message.answer("❌ تم إلغاء التعديل", reply_markup=get_main_keyboard())
            del edit_states[user_id]
            return
        
        person_id = state["person_id"]
        field = state["field"]
        
        # معالجة القيم
        if field in ["birth_year", "death_year"]:
            try:
                value = int(text) if text.lower() != "skip" and text != "0" else None
            except ValueError:
                await message.answer("❌ يجب أن تكون السنة رقماً صحيحاً")
                return
        else:
            value = None if text.lower() == "skip" else text
        
        success = db.update_person(person_id, field, value)
        
        # تحويل اسم الحقل للعربية
        field_names = {
            "last_name": "اللقب",
            "first_name": "الاسم",
            "birth_year": "سنة الميلاد",
            "country": "البلد",
            "job": "الاختصاص",
            "death_year": "سنة الاستشهاد",
            "death_place": "مكان الاستشهاد"
        }
        field_arabic = field_names.get(field, field)
        
        if success:
            await message.answer(
                f"✅ **تم التعديل بنجاح**\nتم تحديث '{field_arabic}'.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_main_keyboard()
            )
        else:
            await message.answer("❌ **فشل التعديل**", reply_markup=get_main_keyboard())
        
        del edit_states[user_id]

async def show_edit_fields(message: types.Message, person: dict):
    """عرض حقول التعديل المتاحة"""
    
    # بناء الرسالة بشكل نظيف
    response = "✏️ **تعديل البيانات**\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # عرض اسم الشخص
    response += f"👤 **{person['last_name']}**"
    if person['first_name']:
        response += f" {person['first_name']}"
    
    # عرض باقي البيانات
    response += f"\n\n📅 **الميلاد:** {person['birth_year'] or 'غير معروف'}"
    response += f"\n🌍 **البلد:** {person['country'] or 'غير معروف'}"
    response += f"\n⚔️ **الاختصاص:** {person['job'] or 'غير معروف'}"
    response += f"\n🤲 **سنة الاستشهاد:** {person['death_year'] or 'غير معروف'}"
    response += f"\n📍 **مكان الاستشهاد:** {person['death_place'] or 'غير معروف'}"
    
    # حقول التعديل
    response += "\n\n━━━━━━━━━━━━━━━━━━━━━━\n"
    response += "**اختر الحقل المراد تعديله:**\n\n"
    response += "1️⃣ اللقب\n"
    response += "2️⃣ الاسم\n"
    response += "3️⃣ سنة الميلاد\n"
    response += "4️⃣ البلد\n"
    response += "5️⃣ المهنة\n"
    response += "6️⃣ سنة الوفاة\n"
    response += "7️⃣ مكان الوفاة\n\n"
    response += "📝 أرسل رقم الحقل (1-7)\n"
    response += "❌ أو اكتب 'cancel' للإلغاء"
    
    await message.answer(response, parse_mode=ParseMode.MARKDOWN)

async def handle_add_person(message: types.Message, user_id: int, text: str):
    """إضافة شخص جديد خطوة بخطوة"""
    state = user_states[user_id]
    
    if "last_name" not in state:
        state["last_name"] = db.normalize_text(text)
        await message.answer("📝 أدخل **الاسم** (أو 'skip' للتخطي):", parse_mode=ParseMode.MARKDOWN)
    
    elif "first_name" not in state:
        state["first_name"] = None if text.lower() == "skip" else text
        await message.answer(" أدخل **سنة الميلاد** (أو 'skip' مثال: 1975):", parse_mode=ParseMode.MARKDOWN)
    
    elif "birth_year" not in state:
        try:
            year = int(text) if text.lower() != "skip" else None
            if year and not (1000 <= year <= 2026):
                raise ValueError
            state["birth_year"] = year
            await message.answer("🌍 أدخل **البلد** (مثال: حلب, الغوطة , عندان, الجزيرة العربية,تركيا):", parse_mode=ParseMode.MARKDOWN)
        except:
            await message.answer("❌ أدخل سنة صحيحة بين 1900 و 2026، أو 'skip':")
            return
    
    elif "country" not in state:
        state["country"] = None if text.lower() == "skip" else text
        await message.answer("⚔️ أدخل **الاختصاص** (مثال: مشاة, مضادات, حراري , طبية...):", parse_mode=ParseMode.MARKDOWN)
    
    elif "job" not in state:
        state["job"] = None if text.lower() == "skip" else text
        await message.answer("🤲 أدخل **سنة الاستشهاد** (أو 'skip' إذا كنت غير متأكد):", parse_mode=ParseMode.MARKDOWN)
    
    elif "death_year" not in state:
        try:
            year = int(text) if text.lower() not in ["skip", "0"] else None
            state["death_year"] = year
            await message.answer("📍 أدخل **مكان الاستشهاد** (أو 'skip'):", parse_mode=ParseMode.MARKDOWN)
        except:
            await message.answer("❌ أدخل سنة صحيحة، أو 'skip':")
            return
    
    elif "death_place" not in state:
        state["death_place"] = None if text.lower() == "skip" else text
        
        success = db.add_person(
            last_name=state["last_name"],
            first_name=state["first_name"],
            birth_year=state["birth_year"],
            country=state["country"],
            job=state["job"],
            death_year=state["death_year"],
            death_place=state["death_place"],
            created_by=user_id
        )
        
        if success:
            await message.answer(
                f"✅ **تم الحفظ بنجاح!**\n\n"
                f"👤 {state['last_name']} {state['first_name'] or ''}\n"
                f"تمت إضافة البيانات إلى قاعدة المعلومات.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_main_keyboard()
            )
        else:
            await message.answer(
                "❌ **حدث خطأ أثناء الحفظ**\nيرجى المحاولة مرة أخرى.",
                reply_markup=get_main_keyboard()
            )
        
        del user_states[user_id]

# =============== تشغيل البوت ===============
async def main():
    """الدالة الرئيسية لتشغيل البوت"""
    logger.info("🚀 جاري تشغيل البوت...")
    logger.info(f"✅ البوت يعمل على token: {BOT_TOKEN[:10]}...")
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"خطأ في تشغيل البوت: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())