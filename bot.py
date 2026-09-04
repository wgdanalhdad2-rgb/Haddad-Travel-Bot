import os
import logging
import sys
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
from threading import Thread
from google import genai
from google.genai import types

# ================= إعدادات السجلات (Logging) =================
logging.basicConfig(
    format='%(asctime)s | %(levelname)s | %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ================= المتغيرات البيئية =================
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("API_KEY")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

if not API_ID or not API_HASH:
    logger.critical("❌ API_ID أو API_HASH غير موجودين في الإعدادات!")
    sys.exit(1)

# ================= سيرفر الويب (Flask) =================
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "✅ بوت أبو مجد الحداد (الرد المباشر) - يعمل بنجاح على Render"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    # إيقاف إعادة التشغيل التلقائي لمنع التضارب
    web_app.run(host="0.0.0.0", port=port, use_reloader=False) 

# ================= الردود المحلية (جديد) =================
LOCAL_RESPONSES = {
    "السلام عليكم": "وعليكم السلام ورحمة الله وبركاته 👋\nمرحباً بك في مكتب أبو مجد الحداد للسفريات والخدمات.",
    "كم سعر": "🛂 الأسعار تختلف حسب المهنة والجنسية.\nأرسل لي (المهنة + الجنسية) لأعطيك السعر الدقيق.",
    "الخدمات": "يسعدنا تقديم الخدمات التالية:\n• تأشيرات عمل\n• حجز طيران\n• زيارة وعمرة\n• خدمات سياحية\n\n📞 للتواصل: 775012242"
}

# ================= الذكاء الاصطناعي (Gemini) =================
gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

async def ask_gemini(text: str):
    if not gemini_client:
        return "⚠️ خدمة الذكاء الاصطناعي غير متاحة حالياً بسبب نقص المفتاح."
    try:
        # تم تحديث التعليمات لتطابق البوت الأول
        prompt = """أنت مساعد مكتب أبو مجد الحداد للسفريات والتأشيرات في اليمن.
كن محترفاً، لبقاً، ورحب بالعملاء بأحر التهاني واستخدم الإيموجي المناسب.
ركز على تقديم الخدمات: تأشيرات، حجوزات طيران، عمرة وزيارة.
أذكر أرقام التواصل عند الحاجة: 775012242 و 738465200."""
        
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash", # تم تصحيح الموديل هنا
            contents=f"{prompt}\n\nالعميل: {text}",
            config=types.GenerateContentConfig(temperature=0.7)
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini Error: {e}")
        return "عذراً، أواجه ضغطاً حالياً. يرجى المحاولة بعد قليل أو التواصل على +967775012242"

# ================= أزرار القائمة المطورة =================
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛂 خدماتنا", callback_data="services"), InlineKeyboardButton("💰 أسعارنا", callback_data="prices")],
        [InlineKeyboardButton("📞 تواصل معنا", callback_data="contact"), InlineKeyboardButton("✈️ حجز طيران", callback_data="flights")],
        [InlineKeyboardButton("🕋 عمرة وزيارة", callback_data="omrah")]
    ])

# ================= تهيئة البوت (Client) =================
if BOT_TOKEN:
    app = Client("bot", bot_token=BOT_TOKEN, api_id=int(API_ID), api_hash=API_HASH)
else:
    # سيقرأ ملف my_account.session ولن يطلب رقم الهاتف
    app = Client("my_account", api_id=int(API_ID), api_hash=API_HASH)

# ================= الفلاتر والأوامر (Handlers) =================
@app.on_message(filters.command("start") & filters.private)
async def start(_, msg):
    if BOT_TOKEN:
        await msg.reply_text("👋 أهلاً بك في مكتب أبو مجد الحداد للسفريات والتأشيرات.\nالرجاء اختيار الخدمة المطلوبة:", reply_markup=main_menu())
    else:
        await msg.reply_text("👋 أهلاً بك في مكتب أبو مجد الحداد. كيف يمكنني مساعدتك اليوم؟")

@app.on_callback_query()
async def cb_handler(_, query):
    if query.data == "contact":
        await query.edit_message_text("📞 للتواصل المباشر:\n• 775012242\n• 738465200", reply_markup=main_menu())
    elif query.data == "services":
        await query.edit_message_text(LOCAL_RESPONSES["الخدمات"], reply_markup=main_menu())
    elif query.data == "prices":
        await query.edit_message_text(LOCAL_RESPONSES["كم سعر"], reply_markup=main_menu())
    elif query.data in ["flights", "omrah"]:
        await query.edit_message_text("يسعدنا خدمتك! الرجاء تزويدنا بتفاصيل طلبك (التواريخ، الوجهة) وسنقوم بالرد عليك فوراً.", reply_markup=main_menu())
    else:
        await query.edit_message_text("✅ تم الاستلام، سيتم الرد قريباً...", reply_markup=main_menu())

@app.on_message(filters.private & ~filters.me)
async def reply_handler(client, message):
    if not message.text:
        return
        
    try:
        # إظهار "جاري الكتابة..."
        await client.send_chat_action(message.chat.id, enums.ChatAction.TYPING)
        
        # 1. فحص الردود المحلية أولاً (نفس فكرة البوت الأول)
        for key in LOCAL_RESPONSES:
            if key in message.text:
                await message.reply_text(LOCAL_RESPONSES[key])
                return
                
        # 2. إذا لم يكن هناك رد محلي، إرسال للذكاء الاصطناعي
        response = await ask_gemini(message.text)
        await message.reply_text(response)
        logger.info(f"تم الرد بنجاح على: {message.from_user.id}")
    except Exception as e:
        logger.error(f"خطأ أثناء الرد: {e}")

# ================= كود التشغيل الأساسي المضاف =================
if __name__ == "__main__":
    print("🌐 جاري تشغيل سيرفر الويب (Flask)...")
    Thread(target=run_flask).start()
    
    print("🤖 جاري بدء تشغيل البوت (Pyrogram)...")
    app.run()

