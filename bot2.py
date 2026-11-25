import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder

BOT_TOKEN = "9196836533:AAGXXDB3gzfaUVDQjZrP5iAcwfZFVnr6LmQ"
CHANNEL_USERNAME = "@uchnuqta_1"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Ovoz bergan foydalanuvchilar ro'yxati (qayta ovoz bermaslik uchun)
voted_users = set()

# Ovozlar sonini hisoblash uchun lug'at (27 nafar o'qituvchi)
votes = {
    "Boltayeva Gulruh": 0,
    "Radjabova Dinora": 0,
    "Istamova Sitora": 0,
    "Fazliddinova Nazokat": 0,
    "Shodiyev Azizbek": 0,
    "Rasulov Hamro": 0,
    "Olimova Ruxshona": 0,
    "Saidov Jamol": 0,
    "Moʻminova Dildora": 0,
    "Poʻlatova Maftuna": 0,
    "Temirova Gulhayo": 0,
    "Toʻxtamurodov Lazizbek": 0,
    "Qudratov Najmiddin": 0,
    "Abdullayeva Nargiza": 0,
    "Aliyeva Mohinabonu": 0,
    "Hikmatova Feruza": 0,
    "Nizomova Mehriniso": 0,
    "Kamolov Asliddin": 0,
    "Qudratova Nigora": 0,
    "Jalilova Mashhura": 0,
    "Moʻminova Dilnoza": 0,
    "Nurmatov Azizbek": 0,
    "Saʼdullayeva Sabina": 0,
    "Tosheva Nilufar": 0,
    "Neʼmatova Surayyo": 0,
    "Zohirova Nigina": 0,
    "Shodiyeva Orzigul": 0
}

# Kanalga a'zolikni tekshirish funksiyasi
async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ["creator", "administrator", "member"]
    except Exception as e:
        logging.error(f"A'zolikni tekshirishda xatolik: {e}")
        return False

# Klaviatura yaratish funksiyasi
def get_main_keyboard():
    builder = InlineKeyboardBuilder()
    for candidate, count in votes.items():
        builder.button(text=f"🗳 {candidate} ({count} ovoz)", callback_data=f"vote_{candidate}")
    builder.button(text="🔄 A'zolikni tekshirish", callback_data="check_sub")
    builder.adjust(1)
    return builder.as_markup()

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    is_subscribed = await check_subscription(message.from_user.id)
    if is_subscribed:
        await message.answer(
            "<b>Sizningcha, eng mahoratli va talabchan oʻqituvchi kim?</b>\n\nOvoz berish uchun quyidagi nomzodlardan birini tanlang:",
            reply_markup=get_main_keyboard(),
            parse_mode="HTML"
        )
    else:
        builder = InlineKeyboardBuilder()
        builder.button(text="📢 Kanalga a'zo bo'lish", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")
        builder.button(text="✅ A'zo bo'ldim / Tekshirish", callback_data="check_sub")
        builder.adjust(1)
        await message.answer(
            f"Ovoz berish uchun avval <b>{CHANNEL_USERNAME}</b> kanaliga a'zo bo'lishingiz kerak!",
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )

@dp.callback_query(F.data == "check_sub")
async def process_check_sub(callback: types.CallbackQuery):
    is_subscribed = await check_subscription(callback.from_user.id)
    if is_subscribed:
        await callback.message.edit_text(
            "<b>A'zolik tasdiqlandi!</b>\n\n<b>Sizningcha, eng mahoratli va talabchan oʻqituvchi kim?</b>\n\nOvoz berish uchun quyidagi nomzodlardan birini tanlang:",
            reply_markup=get_main_keyboard(),
            parse_mode="HTML"
        )
    else:
        await callback.answer("Siz hali kanalga a'zo bo'lmadingiz!", show_alert=True)

@dp.callback_query(F.data.startswith("vote_"))
async def process_vote(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    is_subscribed = await check_subscription(user_id)
    
    if not is_subscribed:
        await callback.answer("Ovoz berish uchun avval kanalga a'zo bo'ling!", show_alert=True)
        return
        
    if user_id in voted_users:
        await callback.answer("Siz allaqachon ovoz bergansiz!", show_alert=True)
        return
        
    candidate = callback.data.replace("vote_", "")
    if candidate in votes:
        votes[candidate] += 1
        voted_users.add(user_id)
        
        await callback.message.edit_reply_markup(reply_markup=get_main_keyboard())
        await callback.answer(f"Ovozingiz {candidate} uchun qabul qilindi!", show_alert=True)

async def main():
    logging.basicConfig(level=logging.INFO)
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())