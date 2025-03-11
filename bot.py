import os
import logging
import asyncio
from typing import Dict, Any, Optional
import google.generativeai as genai
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.enums.chat_action import ChatAction
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Конфигурация
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_FAST_MODEL = os.getenv("GEMINI_FAST_MODEL", "models/gemini-2.0-pro-exp-02-05")
GEMINI_SMART_MODEL = os.getenv("GEMINI_SMART_MODEL", "models/gemini-2.0-flash-thinking-exp-1219")

# Инициализация Google AI
genai.configure(api_key=GEMINI_API_KEY)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаём бота и диспетчер
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# Хранилище для текущей модели пользователя
user_models: Dict[int, str] = {}

# Клавиатура с командами
start_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔄 Задать вопрос AI")],
        [KeyboardButton(text="⚡ Быстрая модель"), KeyboardButton(text="🧠 Умная модель")]
    ],
    resize_keyboard=True
)

# Функция для отправки запроса в Gemini API
async def get_gemini_response(prompt: str, model_name: str) -> str:
    """Асинхронная функция для получения ответа от Gemini API"""
    try:
        logger.info(f"Запрос к Gemini API. Модель: {model_name}, Запрос: {prompt}")
        
        # Используем asyncio для выполнения синхронного вызова в отдельном потоке
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: genai.GenerativeModel(model_name).generate_content(prompt)
        )
        
        if response.text:
            return response.text
        else:
            logger.warning(f"Gemini вернул пустой ответ для модели {model_name} и запроса: {prompt}")
            return "Ошибка: AI не вернул текстовый ответ."
    except Exception as e:
        logger.error(f"Ошибка при запросе к Gemini ({model_name}): {e}, Запрос: {prompt}")
        return f"Произошла ошибка при обработке запроса: {str(e)}"

# Обработчик команды /start
@dp.message(Command(commands=['start']))
async def send_welcome(message: types.Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    user_models[user_id] = GEMINI_FAST_MODEL  # Устанавливаем модель по умолчанию
    
    await message.answer(
        "Привет! Я бот с AI Gemini. Выберите модель или просто напишите сообщение!",
        reply_markup=start_keyboard
    )

# Обработчик команды /help
@dp.message(Command(commands=['help']))
async def send_help(message: types.Message):
    """Обработчик команды /help"""
    help_text = """
    Доступные команды:
    /start - Начать чат
    /help - Показать справку
    """
    await message.answer(help_text)

# Обработчик выбора модели
@dp.message(lambda message: message.text in ["⚡ Быстрая модель", "🧠 Умная модель"])
async def choose_model(message: types.Message):
    """Обработчик выбора модели пользователем"""
    user_id = message.from_user.id
    if message.text == "⚡ Быстрая модель":
        user_models[user_id] = GEMINI_FAST_MODEL
        await message.answer("⚡ Быстрая модель активирована (немного тупее, но отвечает быстрее).")
    else:
        user_models[user_id] = GEMINI_SMART_MODEL
        await message.answer("🧠 Умная модель активирована (отвечает медленнее, но умнее).")
    logger.info(f"Пользователь {user_id} выбрал модель: {user_models[user_id]}")

# Обработчик текстовых сообщений
@dp.message()
async def handle_message(message: types.Message):
    """Основной обработчик текстовых сообщений"""
    user_id = message.from_user.id
    user_text = message.text
    
    # Устанавливаем модель по умолчанию, если пользователь не выбрал
    if user_id not in user_models:
        user_models[user_id] = GEMINI_FAST_MODEL
    
    # Показываем индикатор печати
    await bot.send_chat_action(message.chat.id, action=ChatAction.TYPING)
    
    # Получаем ответ от AI
    ai_response = await get_gemini_response(user_text, user_models[user_id])
    
    # Отправляем ответ пользователю
    await message.answer(ai_response)

# Запуск бота
async def main():
    """Основная функция для запуска бота"""
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())