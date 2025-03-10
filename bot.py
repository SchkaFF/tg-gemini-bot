import os
import logging
import asyncio
import google.generativeai as genai
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv
from aiogram.filters import Command
from aiogram.enums.chat_action import ChatAction

# Загружаем переменные окружения
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_FAST_MODEL = os.getenv("GEMINI_FAST_MODEL", "models/gemini-2.0-pro-exp-02-05")
GEMINI_SMART_MODEL = os.getenv("GEMINI_SMART_MODEL", "models/gemini-2.0-flash-thinking-exp-1219")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID"))  # Добавим ваш Telegram ID

# Инициализация Google AI
genai.configure(api_key=GEMINI_API_KEY)

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Создаём бота и диспетчер
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# Клавиатура команд
start_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔄 Задать вопрос AI")],
        [KeyboardButton(text="⚡ Быстрая модель"), KeyboardButton(text="🧠 Умная модель")]
    ],
    resize_keyboard=True
)

# Глобальная переменная для хранения текущей модели
user_model_choice = GEMINI_FAST_MODEL

# Переменная для хранения последних запросов
last_requests = []

# Функция для отправки запроса в Gemini API
def get_gemini_response(prompt: str, model_name: str) -> str:
    try:
        print(f"Запрос к Gemini API. Модель: {model_name}, Запрос: {prompt}")
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        if response.text:
            return response.text
        else:
            logging.warning(f"Gemini вернул пустой ответ для модели {model_name} и запроса: {prompt}")
            return "Ошибка: AI не вернул текстовый ответ."
    except Exception as e:
        logging.error(f"Ошибка при запросе к Gemini ({model_name}): {e}, Запрос: {prompt}, Ошибка: {e}")
        return "Произошла ошибка при обработке запроса. Попробуйте позже."

# Обработчик команды /start
@dp.message(Command(commands=['start']))
async def send_welcome(message: types.Message):
    await message.answer("Привет! Я бот с AI Gemini. Выберите модель или просто напишите сообщение!", reply_markup=start_keyboard)

# Обработчик выбора модели
@dp.message(lambda message: message.text in ["⚡ Быстрая модель", "🧠 Умная модель"])
async def choose_model(message: types.Message):
    global user_model_choice
    if message.text == "⚡ Быстрая модель":
        user_model_choice = GEMINI_FAST_MODEL
        await message.answer("Вы выбрали ⚡ Быструю модель (немного тупее, но отвечает быстрее).")
    else:
        user_model_choice = GEMINI_SMART_MODEL
        await message.answer("Вы выбрали 🧠 Умную модель (отвечает медленнее, но умнее).")
    print(f"Выбрана модель: {user_model_choice}")

# Обработчик текстовых сообщений
@dp.message()
async def handle_message(message: types.Message):
    print("Функция handle_message вызвана")
    user_text = message.text
    await bot.send_chat_action(message.chat.id, action=ChatAction.TYPING)
    
    # Добавляем запрос в список
    last_requests.append(f"Запрос от {message.from_user.full_name}: {user_text}")
    
    # Ограничиваем размер списка, чтобы не хранить слишком много данных
    if len(last_requests) > 10:
        last_requests.pop(0)

    ai_response = get_gemini_response(user_text, user_model_choice)
    await message.answer(ai_response)

# Обработчик команды для просмотра последних запросов
@dp.message(Command(commands=['last_requests']))
async def show_last_requests(message: types.Message):
    if message.from_user.id == ADMIN_USER_ID:
        if last_requests:
            response = "\n".join(last_requests)
        else:
            response = "Нет последних запросов."
        await message.answer(f"Последние запросы:\n{response}")
    else:
        await message.answer("У вас нет прав для просмотра последних запросов.")

# Запуск бота
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
