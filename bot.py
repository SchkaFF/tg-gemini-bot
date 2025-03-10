import os
import logging
import asyncio
import google.generativeai as genai
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.enums.chat_action import ChatAction
from dotenv import load_dotenv

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

GEMINI_FAST_MODEL = os.getenv("GEMINI_FAST_MODEL", "models/gemini-2.0-pro-exp-02-05")
GEMINI_SMART_MODEL = os.getenv("GEMINI_SMART_MODEL", "models/gemini-2.0-flash-thinking-exp-1219")

genai.configure(api_key=GEMINI_API_KEY)
logging.basicConfig(level=logging.INFO)

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

start_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔄 Задать вопрос AI")],
        [KeyboardButton(text="⚡ Быстрая модель"), KeyboardButton(text="🧠 Умная модель")]
    ],
    resize_keyboard=True
)

user_model_choice = GEMINI_FAST_MODEL
user_requests = {}  # Словарь для хранения запросов по user_id
MAX_REQUESTS = 10

def get_gemini_response(prompt: str, model_name: str) -> str:
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        return response.text if response.text else "Ошибка: AI не вернул текстовый ответ."
    except Exception as e:
        logging.error(f"Ошибка при запросе к Gemini ({model_name}): {e}, Запрос: {prompt}")
        return "Произошла ошибка при обработке запроса. Попробуйте позже."

@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    await message.answer("Привет! Я бот с AI Gemini. Выберите модель или просто напишите сообщение!", reply_markup=start_keyboard)

@dp.message(lambda message: message.text in ["⚡ Быстрая модель", "🧠 Умная модель"])
async def choose_model(message: types.Message):
    global user_model_choice
    user_model_choice = GEMINI_FAST_MODEL if message.text == "⚡ Быстрая модель" else GEMINI_SMART_MODEL
    await message.answer(f"Выбрана {message.text}.")

@dp.message(Command("history"))
async def send_history(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("У тебя нет доступа к этой команде.")
        return

    history = user_requests.get(message.from_user.id, [])
    history_text = "\n".join(history) or "История пуста."
    await message.answer(f"Последние запросы:\n{history_text}")

@dp.message()
async def handle_message(message: types.Message):
    if message.text.startswith("/"):
        return  # Игнорируем команды, чтобы не передавать их в AI

    user_id = message.from_user.id
    user_requests.setdefault(user_id, []).append(message.text)

    if len(user_requests[user_id]) > MAX_REQUESTS:
        user_requests[user_id].pop(0)

    await bot.send_chat_action(message.chat.id, action=ChatAction.TYPING)
    ai_response = get_gemini_response(message.text, user_model_choice)
    await message.answer(ai_response)

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
