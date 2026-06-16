# -*- coding: utf-8 -*-
import os
import json
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ==============================
# ВСТАВЬ СЮДА СВОИ КЛЮЧИ
# ==============================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
# ==============================

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Системный промпт — личность тренера
SYSTEM_PROMPT = """Ты — Виктор Петрович, персональный фитнес-тренер с 40-летним стажем. 
Ты тренируешь Алёну, её цель — похудеть и сжечь жир. Она тренируется дома и в зале.

Твой характер:
- Строгий, но справедливый и заботливый
- Говоришь по-русски, как живой человек — без канцелярщины
- Иногда немного ворчишь если она пропускает тренировки, но всегда поддерживаешь
- Знаешь имя своей ученицы — Алёна
- Помнишь всё что она тебе говорила в этом разговоре

Что ты делаешь:
- Составляешь персональные планы тренировок (зал + дом) под цель похудения
- Даёшь конкретные упражнения с подходами, повторениями и отдыхом
- Консультируешь по питанию — просто и понятно, без сложных терминов
- Отслеживаешь прогресс — спрашиваешь как прошла тренировка, записываешь результаты
- Сам периодически пишешь первым (напоминаешь, спрашиваешь об отчёте)
- Мотивируешь, но не сюсюкаешь — как настоящий тренер

Когда Алёна пишет первый раз — познакомься, узнай её параметры (вес, рост, возраст, есть ли ограничения по здоровью) и составь план на первую неделю.

Отвечай живо, по-человечески. Ты не робот — ты тренер с опытом и характером."""

# Хранение истории разговора (в памяти, пока бот работает)
user_histories = {}

def get_history(user_id):
    if user_id not in user_histories:
        user_histories[user_id] = []
    return user_histories[user_id]

def add_to_history(user_id, role, content):
    history = get_history(user_id)
    history.append({"role": role, "content": content})
    # Храним последние 30 сообщений чтобы не перегружать
    if len(history) > 30:
        history.pop(0)

async def ask_groq(user_id, user_message):
    import urllib.request
    
    add_to_history(user_id, "user", user_message)
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + get_history(user_id)
    
    payload = json.dumps({
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "max_tokens": 1000,
        "temperature": 0.8
    }).encode("utf-8")
    
    req = urllib.request.Request(
        GROQ_API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
    )
    
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode("utf-8"))
    
    reply = result["choices"][0]["message"]["content"]
    add_to_history(user_id, "assistant", reply)
    return reply

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_histories[user_id] = []  # Сбрасываем историю
    
    reply = await ask_groq(user_id, "Привет! Я готова начать тренироваться.")
    await update.message.reply_text(reply)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text
    
    # Показываем что бот печатает
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        reply = await ask_groq(user_id, user_message)
        await update.message.reply_text(reply)
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await update.message.reply_text("Что-то пошло не так, попробуй ещё раз.")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_histories[user_id] = []
    await update.message.reply_text("История сброшена. Начинаем заново!")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Бот запущен! Нажми Ctrl+C чтобы остановить.")
    app.run_polling()

if __name__ == "__main__":
    main()
