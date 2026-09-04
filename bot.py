import os
import sys
import time
import logging
from collections import defaultdict
from threading import Thread
from flask import Flask
from pyrogram import Client, filters, enums
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from google import genai
from google.genai import types

# ===================== الإعدادات والسجلات =====================
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ===================== المتغيرات البيئية =====================
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("API_KEY")
ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip().isdigit()]

if not API_ID or not API_HASH:
    logger.critical("❌ يجب وضع API_ID و API_HASH")
    sys.exit(1)

# ===================== سيرفر Flask =====================
web_app = Flask(__name__)

@web_app.route("/")
def home():
    return "✅ بوت أبو مجد الحداد يعمل بنجاح"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host="0.0.0.0", port=port, use_reloader=False)

# ===================== الردود المحلية =====================
LOCAL_RESPONSES = {
    "السلام عليكم": "وعليكم السلام ورحمة الله وبركاته 👋\nمرحباً بك في مكتب أبو مجد الحداد للسفريات والتأشيرات.",
    "سلام عليكم": "وعليكم السلام ورحمة الله وبركاته 👋\nكيف يمكنني مساعدتك اليوم؟",
    "كم سعر": "🛂 الأسعار تختلف حسب المهنة والجنسية.\nأرسل لي (المهنة + الجنسية) لأعطيك السعر الدقيق فوراً.",
    "اسعار": "🛂 الأسعار تختلف حسب المهنة والجنسية.\nأرسل لي (المهنة + الجنسية) لأعطيك السعر الدقيق فوراً.",
    "سعر": "🛂 الأسعار تختلف حسب المهنة والجنسية.\nأرسل لي (المهنة + الجنسية) لأعطيك السعر الدقيق.",
    "الخدمات": "يسعدنا تقديم الخدمات التالية:\n\n• تأشيرات عمل لجميع الدول\n• حجز تذاكر طيران\n• عمرة وزيارة\n• خدمات سياحية\n\n📞 للتواصل: 775012242",
    "رقم": "📞 أرقام التواصل الرسمية:\n• 775012242\n• 738465200",
    "ارقام": "📞 أرقام التواصل الرسمية:\n• 775012242\n• 738465200",
}

# ===================== ذاكرة المحادثات =====================
chat_history = defaultdict(list)
MAX_HISTORY = 8

# ===================== Gemini =====================
gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

SYSTEM_PROMPT = """أنت المساعد الرسمي لمكتب أبو مجد الحداد للسفريات والتأشيرات في اليمن.
- كن محترفاً ولطيفاً واستخدم الإيموجي بشكل مناسب.
- الخدمات: تأشيرات عمل، حجز طيران، عمرة وزيارة، خدمات سياحية.
- أرقام التواصل: 775012242 و 738465200.
- عند السؤال عن الأسعار اطلب المهنة + الجنسية.
- لا تخترع معلومات. إذا لم تكن متأكداً قل: "سأتحقق وأرد عليك فوراً".
- رد دائماً بالعربية الفصحى المبسطة والواضحة."""

async def ask_gemini(user_id: int, text: str) -> str:
    if not gemini_client:
        return "⚠️ خدمة الذكاء الاصطناعي غير متاحة حالياً.\nتواصل معنا مباشرة: 775012242"

    chat_history[user_id].append({"role": "user", "parts": [text]})
    if len(chat_history[user_id]) > MAX_HISTORY:
        chat_history[user_id] = chat_history[user_id][-MAX_HISTORY:]

    try:
        contents = [{"role": "user", "parts": [SYSTEM_PROMPT]}] + chat_history[user_id]

        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=0.65,
                max_output_tokens=900
            )
        )
        reply = response.text.strip()
        chat_history[user_id].append({"role": "model", "parts": [reply]})
        return reply
    except Exception as e:
        logger.error(f"Gemini Error: {e}")
        return "عذراً، أواجه ضغطاً حالياً ⏳\nحاول بعد قليل أو تواصل على:\n📞 775012242"

# ===================== القوائم =====================
def main_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🛂 خدماتنا", callback_data="services"),
            InlineKeyboardButton("💰 الأسعار", callback_data="prices")
        ],
        [
            InlineKeyboardButton("✈️ حجز طيران", callback_data="flights"),
            InlineKeyboardButton("🕋 عمرة وزيارة", callback_data="omrah")
        ],
        [
            InlineKeyboardButton("📞 تواصل معنا", callback_data="contact")
        ]
    ])

def back_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="back")]
    ])

# ===================== تهيئة البوت =====================
if BOT_TOKEN:
    app = Client(
        "abu_majd_bot",
        bot_token=BOT_TOKEN,
        api_id=int(API_ID),
        api_hash=API_HASH
    )
else:
    app = Client(
        "my_account",
        api_id=int(API_ID),
        api_hash=API_HASH
    )

# ===================== الأوامر =====================
@app.on_message(filters.command("start") & filters.private)
async def start_handler(_, message: Message):
    text = (
        "👋 أهلاً وسهلاً بك في **مكتب أبو مجد الحداد**\n"
        "للسفريات • التأشيرات • الحجوزات\n\n"
        "اختر الخدمة من الأزرار أو اكتب سؤالك مباشرة:"
    )
    await message.reply_text(text, reply_markup=main_menu())

@app.on_message(filters.command("help") & filters.private)
async def help_handler(_, message: Message):
    await message.reply_text(
        "📌 **كيفية استخدام البوت:**\n\n"
        "• اكتب سؤالك مباشرة وسأرد عليك فوراً\n"
        "• استخدم الأزرار للوصول السريع\n"
        "• للأرقام اكتب: رقم\n"
        "• للأسعار أرسل: المهنة + الجنسية",
        reply_markup=main_menu()
    )

@app.on_message(filters.command("admin") & filters.private)
async def admin_handler(_, message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    total = len(chat_history)
    await message.reply_text(f"📊 **لوحة التحكم**\n\nعدد المستخدمين النشطين: `{total}`")

@app.on_message(filters.command("broadcast") & filters.private)
async def broadcast_handler(client: Client, message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    if len(message.command) < 2:
        await message.reply_text("استخدم الأمر هكذا:\n`/broadcast نص الرسالة`")
        return

    text = message.text.split(None, 1)[1]
    success = 0
    for user_id in list(chat_history.keys()):
        try:
            await client.send_message(user_id, f"📢 **إعلان من المكتب:**\n\n{text}")
            success += 1
            time.sleep(0.1)
        except:
            pass
    await message.reply_text(f"✅ تم الإرسال إلى {success} مستخدم")

# ===================== معالجة الأزرار =====================
@app.on_callback_query()
async def callback_handler(_, query: CallbackQuery):
    data = query.data

    if data == "contact":
        text = (
            "📞 **أرقام التواصل الرسمية:**\n\n"
            "• 775012242\n"
            "• 738465200\n\n"
            "نحن في خدمتك على مدار الساعة ❤️"
        )
        await query.edit_message_text(text, reply_markup=back_menu())

    elif data == "services":
        await query.edit_message_text(LOCAL_RESPONSES["الخدمات"], reply_markup=back_menu())

    elif data == "prices":
        await query.edit_message_text(LOCAL_RESPONSES["كم سعر"], reply_markup=back_menu())

    elif data == "flights":
        await query.edit_message_text(
            "✈️ **حجز تذاكر الطيران**\n\n"
            "أرسل لنا:\n• الوجهة\n• تاريخ السفر\n• تاريخ العودة (إن وجد)\n• عدد الأشخاص\n\nوسنرد عليك فوراً.",
            reply_markup=back_menu()
        )

    elif data == "omrah":
        await query.edit_message_text(
            "🕋 **العمرة والزيارة**\n\n"
            "أرسل لنا:\n• نوع البرنامج (عمرة / زيارة)\n• التاريخ المطلوب\n• عدد الأشخاص\n\nوسنقدم لك أفضل العروض.",
            reply_markup=back_menu()
        )

    elif data == "back":
        await query.edit_message_text(
            "👋 أهلاً بك مجدداً.\nاختر الخدمة المطلوبة:",
            reply_markup=main_menu()
        )

    else:
        await query.answer("✅ تم الاستلام", show_alert=False)

# ===================== الرد التلقائي الرئيسي =====================
@app.on_message(filters.private & ~filters.me & ~filters.bot & filters.text)
async def reply_handler(client: Client, message: Message):
    if not message.from_user or message.from_user.is_bot:
        return

    # تجاهل الرسائل القديمة
    if time.time() - message.date.timestamp() > 40:
        return

    text = message.text.strip()
    user_id = message.from_user.id

    try:
        await client.send_chat_action(message.chat.id, enums.ChatAction.TYPING)

        # الردود المحلية أولاً
        for key, response in LOCAL_RESPONSES.items():
            if key in text:
                await message.reply_text(response, reply_markup=main_menu())
                return

        # الذكاء الاصطناعي
        response = await ask_gemini(user_id, text)
        await message.reply_text(response, reply_markup=main_menu())
        logger.info(f"تم الرد على: {user_id}")

    except Exception as e:
        logger.error(f"خطأ: {e}")
        await message.reply_text(
            "حدث خطأ مؤقت ⚠️\nحاول مرة أخرى أو تواصل معنا:\n📞 775012242"
        )

# ===================== التشغيل =====================
if __name__ == "__main__":
    print("🌐 جاري تشغيل سيرفر الويب...")
    Thread(target=run_flask, daemon=True).start()

    print("🤖 جاري تشغيل بوت أبو مجد الحداد...")
    app.run()
