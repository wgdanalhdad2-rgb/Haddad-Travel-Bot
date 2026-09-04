import os
import sys
import time
import asyncio
import logging
from collections import defaultdict
from threading import Thread

from flask import Flask
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from google import genai
from google.genai import types

# ===================== الإعدادات والسجلات =====================
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ===================== المتغيرات البيئية =====================
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("API_KEY")
ADMIN_IDS = [
    int(value) for value in os.environ.get("ADMIN_IDS", "").split(",")
    if value.strip().isdigit()
]

if not API_ID or not API_HASH or not BOT_TOKEN:
    logger.critical("يجب ضبط API_ID وAPI_HASH وBOT_TOKEN في متغيرات Render")
    raise RuntimeError("Missing required Telegram environment variables")

# ===================== سيرفر Flask للصحة =====================
web_app = Flask(__name__)

@web_app.get("/")
def home():
    return "OK - Abu Majd Telegram bot is running", 200

@web_app.get("/health")
def health():
    return {"status": "ok"}, 200

# ===================== الردود المحلية =====================
LOCAL_RESPONSES = {
    "السلام عليكم": "وعليكم السلام ورحمة الله وبركاته 👋\nمرحباً بك في مكتب أبو مجد الحداد للسفريات والتأشيرات.",
    "سلام عليكم": "وعليكم السلام ورحمة الله وبركاته 👋\nكيف يمكنني مساعدتك اليوم؟",
    "كم سعر": "🛂 الأسعار تختلف حسب المهنة والجنسية.\nأرسل لي المهنة والجنسية لأعطيك السعر الدقيق.",
    "اسعار": "🛂 الأسعار تختلف حسب المهنة والجنسية.\nأرسل لي المهنة والجنسية لأعطيك السعر الدقيق.",
    "سعر": "🛂 الأسعار تختلف حسب المهنة والجنسية.\nأرسل لي المهنة والجنسية لأعطيك السعر الدقيق.",
    "الخدمات": "يسعدنا تقديم الخدمات التالية:\n\n• تأشيرات عمل لجميع الدول\n• حجز تذاكر طيران\n• عمرة وزيارة\n• خدمات سياحية\n\n📞 للتواصل: 775012242",
    "رقم": "📞 أرقام التواصل الرسمية:\n• 775012242\n• 738465200",
    "ارقام": "📞 أرقام التواصل الرسمية:\n• 775012242\n• 738465200",
}

chat_history = defaultdict(list)
MAX_HISTORY = 8
gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

SYSTEM_PROMPT = """أنت المساعد الرسمي لمكتب أبو مجد الحداد للسفريات والتأشيرات في اليمن.
كن محترفاً ولطيفاً، ولا تخترع معلومات. الخدمات: تأشيرات عمل، حجز طيران، عمرة وزيارة، وخدمات سياحية.
عند السؤال عن الأسعار اطلب المهنة والجنسية. أرقام التواصل: 775012242 و738465200.
رد بالعربية الفصحى المبسطة والواضحة."""

async def ask_gemini(user_id: int, text: str) -> str:
    if not gemini_client:
        return "⚠️ خدمة الذكاء الاصطناعي غير متاحة حالياً.\nتواصل معنا: 775012242"

    chat_history[user_id].append({"role": "user", "parts": [text]})
    chat_history[user_id] = chat_history[user_id][-MAX_HISTORY:]
    contents = [{"role": "user", "parts": [SYSTEM_PROMPT]}] + chat_history[user_id]

    try:
        # مكتبة google-genai المستخدمة هنا متزامنة؛ لا تحجب event loop الخاص بـ Pyrogram.
        response = await asyncio.to_thread(
            gemini_client.models.generate_content,
            model="gemini-2.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(temperature=0.65, max_output_tokens=900),
        )
        reply = (response.text or "").strip()
        if not reply:
            raise RuntimeError("Gemini returned an empty response")
        chat_history[user_id].append({"role": "model", "parts": [reply]})
        return reply
    except Exception:
        logger.exception("Gemini request failed")
        return "عذراً، أواجه ضغطاً حالياً ⏳\nحاول بعد قليل أو تواصل على: 775012242"

# ===================== القوائم =====================
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛂 خدماتنا", callback_data="services"), InlineKeyboardButton("💰 الأسعار", callback_data="prices")],
        [InlineKeyboardButton("✈️ حجز طيران", callback_data="flights"), InlineKeyboardButton("🕋 عمرة وزيارة", callback_data="omrah")],
        [InlineKeyboardButton("📞 تواصل معنا", callback_data="contact")],
    ])

def back_menu():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="back")]])

# ===================== تهيئة البوت =====================
app = Client(
    "abu_majd_bot",
    bot_token=BOT_TOKEN,
    api_id=int(API_ID),
    api_hash=API_HASH,
)

@app.on_message(filters.command("start") & filters.private)
async def start_handler(_, message: Message):
    await message.reply_text(
        "👋 أهلاً وسهلاً بك في مكتب أبو مجد الحداد\nللسفريات • التأشيرات • الحجوزات\n\nاختر الخدمة أو اكتب سؤالك مباشرة:",
        reply_markup=main_menu(),
    )

@app.on_message(filters.command("help") & filters.private)
async def help_handler(_, message: Message):
    await message.reply_text(
        "📌 اكتب سؤالك مباشرة، أو استخدم الأزرار.\nللأسعار أرسل المهنة والجنسية.",
        reply_markup=main_menu(),
    )

@app.on_message(filters.command("admin") & filters.private)
async def admin_handler(_, message: Message):
    if message.from_user and message.from_user.id in ADMIN_IDS:
        await message.reply_text(f"📊 عدد المستخدمين النشطين: {len(chat_history)}")

@app.on_message(filters.command("broadcast") & filters.private)
async def broadcast_handler(client: Client, message: Message):
    if not message.from_user or message.from_user.id not in ADMIN_IDS:
        return
    if len(message.command) < 2:
        await message.reply_text("استخدم: /broadcast نص الرسالة")
        return
    text = message.text.split(None, 1)[1]
    success = 0
    for user_id in list(chat_history):
        try:
            await client.send_message(user_id, f"📢 إعلان من المكتب:\n\n{text}")
            success += 1
            await asyncio.sleep(0.1)
        except Exception:
            logger.exception("Broadcast failed for %s", user_id)
    await message.reply_text(f"✅ تم الإرسال إلى {success} مستخدم")

@app.on_callback_query()
async def callback_handler(_, query: CallbackQuery):
    data = query.data
    await query.answer()
    if data == "contact":
        text = "📞 أرقام التواصل الرسمية:\n\n• 775012242\n• 738465200"
    elif data == "services":
        text = LOCAL_RESPONSES["الخدمات"]
    elif data == "prices":
        text = LOCAL_RESPONSES["كم سعر"]
    elif data == "flights":
        text = "✈️ أرسل الوجهة، تاريخ السفر، تاريخ العودة إن وجد، وعدد الأشخاص."
    elif data == "omrah":
        text = "🕋 أرسل نوع البرنامج، التاريخ المطلوب، وعدد الأشخاص."
    elif data == "back":
        await query.edit_message_text("👋 أهلاً بك مجدداً.\nاختر الخدمة المطلوبة:", reply_markup=main_menu())
        return
    else:
        return
    await query.edit_message_text(text, reply_markup=back_menu())

@app.on_message(filters.private & ~filters.me & ~filters.bot & filters.text)
async def reply_handler(client: Client, message: Message):
    if not message.from_user or message.from_user.is_bot:
        return
    if time.time() - message.date.timestamp() > 40:
        return
    try:
        await client.send_chat_action(message.chat.id, enums.ChatAction.TYPING)
        text = message.text.strip()
        for key, response in LOCAL_RESPONSES.items():
            if key in text:
                await message.reply_text(response, reply_markup=main_menu())
                return
        response = await ask_gemini(message.from_user.id, text)
        await message.reply_text(response, reply_markup=main_menu())
    except Exception:
        logger.exception("Message handling failed")
        await message.reply_text("حدث خطأ مؤقت ⚠️\nتواصل معنا: 775012242")

# ===================== التشغيل =====================
def run_web_server():
    port = int(os.environ.get("PORT", "10000"))
    web_app.run(host="0.0.0.0", port=port, use_reloader=False)

if __name__ == "__main__":
    logger.info("Starting health server and Telegram polling client")
    Thread(target=run_web_server, daemon=True, name="health-server").start()
    app.run()
