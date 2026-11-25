import os
import asyncio
import io
import pandas as pd
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, 
    ReplyKeyboardMarkup, KeyboardButton, CallbackQuery, BufferedInputFile
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID", "") 
CHANNEL_USERNAME = "@uchunuqta_1"  # Majburiy kanal username

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Ma'lumotlar ombori
votes_db = {}  # {user_id: {"name": str, "birth_year": str, "candidate": str, "username": str}}
candidates = ["Nomzod 1", "Nomzod 2", "Nomzod 3"]
poll_active = True
all_users = set()

# --- FSM (Bosqichlar) ---
class VoteState(StatesGroup):
    waiting_for_fullname = State()
    waiting_for_birthyear = State()
    waiting_for_candidate = State()

class FeedbackState(StatesGroup):
    waiting_for_message = State()

class BroadcastState(StatesGroup):
    waiting_for_message = State()

# --- KANALGA A'ZOLIKNI TEKSHIRISH FUNKSIYASI ---
async def check_channel_sub(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if member.status in ["creator", "administrator", "member"]:
            return True
        return False
    except Exception:
        return True # Xatolik bo'lsa jarayon to'xtab qolmasligi uchun

def get_sub_keyboard():
    buttons = [
        [InlineKeyboardButton(text="📢 Kanalga obuna bo'lish", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")],
        [InlineKeyboardButton(text="✅ A'zo bo'ldim (Tekshirish)", callback_data="check_subscription")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# --- TUGMALAR ---

def get_main_keyboard(user_id: int):
    keyboard = [
        [KeyboardButton(text="🗳 Ovoz berish"), KeyboardButton(text="📊 Natijalarni ko'rish")],
        [KeyboardButton(text="ℹ️ Qoidalar"), KeyboardButton(text="👤 Mening ovozim")],
        [KeyboardButton(text="📞 Bog'lanish")]
    ]
    if str(user_id) == str(ADMIN_ID):
        keyboard.append([KeyboardButton(text="👑 Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_poll_inline_keyboard():
    buttons = []
    for cand in candidates:
        buttons.append([InlineKeyboardButton(text=f"🗳 {cand}", callback_data=f"vote_{cand}")])
    buttons.append([InlineKeyboardButton(text="📊 Natijalarni ko'rish", callback_data="show_results")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_inline_keyboard():
    status_text = "🔴 So'rovnomani yopish" if poll_active else "🟢 So'rovnomani ochish"
    buttons = [
        [InlineKeyboardButton(text="📥 Excel faylda yuklash", callback_data="admin_download_excel")],
        [InlineKeyboardButton(text=status_text, callback_data="admin_toggle_poll")],
        [InlineKeyboardButton(text="📢 Hammaga e'lon yuborish", callback_data="admin_broadcast")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_results_text():
    total_votes = len(votes_db)
    text = "📊 **Joriy ovoz berish natijalari:**\n\n"
    counts = {c: 0 for c in candidates}
    for item in votes_db.values():
        cand = item.get("candidate")
        if cand in counts:
            counts[cand] += 1
            
    for cand in candidates:
        cnt = counts[cand]
        pct = (cnt / total_votes * 100) if total_votes > 0 else 0
        text += f"🔹 **{cand}**: {cnt} ta ovoz ({pct:.1f}%)\n"
        
    text += f"\n👥 **Jami ovoz berganlar:** {total_votes} kishi"
    return text

# --- HANDLERLAR ---

@dp.message(CommandStart())
async def start_handler(message: types.Message, state: FSMContext):
    await state.clear()
    all_users.add(message.from_user.id)
    await message.answer(
        "Assalomu alaykum! So'rovnoma botiga xush kelibsiz.\n"
        "Quyidagi menyudan kerakli bo'limni tanlang:",
        reply_markup=get_main_keyboard(message.from_user.id)
    )

# --- OVOZ BERISH VA KANAL TEKSHIRUV ---

@dp.message(F.text == "🗳 Ovoz berish")
async def start_voting(message: types.Message, state: FSMContext):
    if not poll_active:
        await message.answer("⚠️ Hozirda ovoz berish jarayoni to'xtatilgan.")
        return
        
    user_id = message.from_user.id
    if user_id in votes_db:
        cand = votes_db[user_id]["candidate"]
        await message.answer(f"⚠️ Siz allaqachon **{cand}** uchun ovoz bergansiz!", parse_mode="Markdown")
        return

    # Kanalga obunani tekshirish
    is_subscribed = await check_channel_sub(user_id)
    if not is_subscribed:
        await message.answer(
            f"⚠️ Ovoz berishdan oldin **{CHANNEL_USERNAME}** kanalimizga obuna bo'lishingiz kerak!",
            reply_markup=get_sub_keyboard()
        )
        return

    await state.set_state(VoteState.waiting_for_fullname)
    await message.answer("Iltimos, **Ism va Familiyangizni** kiriting:\n*(Masalan: Javohir Toshpo'latov)*", parse_mode="Markdown")

@dp.callback_query(F.data == "check_subscription")
async def check_sub_callback(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    is_subscribed = await check_channel_sub(user_id)
    
    if is_subscribed:
        await callback.answer("✅ Obuna tasdiqlandi!", show_alert=True)
        await callback.message.delete()
        await state.set_state(VoteState.waiting_for_fullname)
        await callback.message.answer("Iltimos, **Ism va Familiyangizni** kiriting:\n*(Masalan: Javohir Toshpo'latov)*", parse_mode="Markdown")
    else:
        await callback.answer("❌ Siz hali kanalga obuna bo'lmadingiz!", show_alert=True)

@dp.message(VoteState.waiting_for_fullname)
async def process_fullname(message: types.Message, state: FSMContext):
    await state.update_data(fullname=message.text)
    await state.set_state(VoteState.waiting_for_birthyear)
    await message.answer("Rahmat! Endi **tug'ilgan yilingizni** kiriting:\n*(Masalan: 1999)*", parse_mode="Markdown")

@dp.message(VoteState.waiting_for_birthyear)
async def process_birthyear(message: types.Message, state: FSMContext):
    if not message.text.isdigit() or len(message.text) != 4:
        await message.answer("⚠️ Iltimos, tug'ilgan yilingizni 4 ta raqamda kiriting (masalan: 1999):")
        return
        
    await state.update_data(birthyear=message.text)
    await state.set_state(VoteState.waiting_for_candidate)
    await message.answer("Ma'lumotlar qabul qilindi. Endi quyidagi nomzodlardan biriga ovoz bering:", reply_markup=get_poll_inline_keyboard())

@dp.callback_query(VoteState.waiting_for_candidate, F.data.startswith("vote_"))
async def handle_vote_finish(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    candidate = callback.data.replace("vote_", "")
    user_data = await state.get_data()

    votes_db[user_id] = {
        "name": user_data.get("fullname"),
        "birth_year": user_data.get("birthyear"),
        "username": callback.from_user.username or "Mavjud emas",
        "candidate": candidate
    }
    
    await state.clear()
    await callback.answer("✅ Ovozingiz qabul qilindi!", show_alert=False)
    await callback.message.answer(f"✅ Ovozingiz qabul qilindi!\n\n{get_results_text()}", parse_mode="Markdown")

# --- BOG'LANISH BOʻLIMI ---

@dp.message(F.text == "📞 Bog'lanish")
async def contact_info(message: types.Message, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Bot orqali xabar yozish", callback_data="send_feedback")]
    ])
    await message.answer(
        "📞 **Tashkilotchi bilan bog'lanish:**\n\n"
        "📱 Telefondagi raqam: **+998993449930**\n\n"
        "Agar bot orqali xabar yubormoqchi bo'lsangiz, quyidagi tugmani bosing:",
        reply_markup=kb,
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "send_feedback")
async def ask_feedback(callback: CallbackQuery, state: FSMContext):
    await state.set_state(FeedbackState.waiting_for_message)
    await callback.message.answer("✍️ Admin uchun xabaringizni yozib yuboring:")
    await callback.answer()

@dp.message(FeedbackState.waiting_for_message)
async def forward_feedback_to_admin(message: types.Message, state: FSMContext):
    if ADMIN_ID:
        sender_info = f"📩 **Yangi xabar!**\n👤 Kimdan: {message.from_user.full_name} (@{message.from_user.username or 'yoq'})\nID: `{message.from_user.id}`\n\nMatn:\n{message.text}"
        try:
            await bot.send_message(chat_id=ADMIN_ID, text=sender_info, parse_mode="Markdown")
            await message.answer("✅ Xabaringiz adminga muvaffaqiyatli yuborildi!")
        except Exception:
            await message.answer("✅ Xabaringiz qabul qilindi.")
    else:
        await message.answer("✅ Xabaringiz qabul qilindi.")
    await state.clear()

# --- UMUMIY TUGMALAR ---

@dp.message(F.text == "📊 Natijalarni ko'rish")
async def show_results_msg(message: types.Message):
    await message.answer(get_results_text(), parse_mode="Markdown")

@dp.message(F.text == "ℹ️ Qoidalar")
async def show_rules(message: types.Message):
    rules = (
        "ℹ️ **So'rovnoma qoidalari:**\n\n"
        f"1. Ovoz berishdan oldin {CHANNEL_USERNAME} kanaliga obuna bo'lish shart.\n"
        "2. Har bir foydalanuvchi faqat 1 marta ovoz bera oladi.\n"
        "3. Ism-familiya va tug'ilgan yil to'g'ri kiritilishi kerak."
    )
    await message.answer(rules, parse_mode="Markdown")

@dp.message(F.text == "👤 Mening ovozim")
async def show_my_vote(message: types.Message):
    user_id = message.from_user.id
    if user_id in votes_db:
        cand = votes_db[user_id]["candidate"]
        info = votes_db[user_id]
        await message.answer(f"✅ Siz **{cand}** uchun ovoz bergansiz.\n👤 Kiritilgan ism: {info['name']}\n📅 Tug'ilgan yil: {info['birth_year']}", parse_mode="Markdown")
    else:
        await message.answer("❌ Siz hali ovoz bermagansiz.")

# --- ADMIN PANEL ---

@dp.message(F.text == "👑 Admin Panel")
async def admin_panel(message: types.Message):
    if str(message.from_user.id) != str(ADMIN_ID):
        await message.answer("⚠️ Boshqaruv paneli faqat admin uchun.")
        return
    await message.answer("⚙️ **Admin Boshqaruv Paneli:**", reply_markup=get_admin_inline_keyboard(), parse_mode="Markdown")

@dp.callback_query(F.data == "admin_download_excel")
async def download_excel(callback: CallbackQuery):
    if str(callback.from_user.id) != str(ADMIN_ID):
        return
    if not votes_db:
        await callback.answer("⚠️ Hali hech kim ovoz bermadi!", show_alert=True)
        return

    data = []
    for uid, info in votes_db.items():
        data.append({
            "User ID": uid,
            "Ism Familiya": info.get("name"),
            "Tug'ilgan yili": info.get("birth_year"),
            "Username": info.get("username"),
            "Tanlagan nomzodi": info.get("candidate")
        })
        
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Ovozlar')
    output.seek(0)
    
    file = BufferedInputFile(output.read(), filename="ovozlar_natijasi.xlsx")
    await callback.message.answer_document(file, caption="📊 Barcha ovoz berganlar va ularning ma'lumotlari.")
    await callback.answer()

@dp.callback_query(F.data == "admin_toggle_poll")
async def toggle_poll(callback: CallbackQuery):
    global poll_active
    if str(callback.from_user.id) != str(ADMIN_ID):
        return
    poll_active = not poll_active
    status = "ochildi 🟢" if poll_active else "yopildi 🔴"
    await callback.answer(f"So'rovnoma {status}")
    await callback.message.edit_reply_markup(reply_markup=get_admin_inline_keyboard())

@dp.callback_query(F.data == "admin_broadcast")
async def start_broadcast(callback: CallbackQuery, state: FSMContext):
    if str(callback.from_user.id) != str(ADMIN_ID):
        return
    await state.set_state(BroadcastState.waiting_for_message)
    await callback.message.answer("📢 Hammaga yubormoqchi bo'lgan xabaringizni yozib yuboring:")
    await callback.answer()

@dp.message(BroadcastState.waiting_for_message)
async def process_broadcast(message: types.Message, state: FSMContext):
    count = 0
    for uid in all_users:
        try:
            await bot.send_message(uid, message.text)
            count += 1
        except Exception:
            pass
    await message.answer(f"✅ Xabar {count} ta foydalanuvchiga muvaffaqiyatli yuborildi.")
    await state.clear()

@dp.callback_query(F.data == "show_results")
async def handle_show_results(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(get_results_text(), parse_mode="Markdown")

# --- RENDER WEB SERVER ---

async def handle_ping(request):
    return web.Response(text="Bot runs perfectly!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
