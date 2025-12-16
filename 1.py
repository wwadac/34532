from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
from telegram.error import TelegramError
import json
import os

# ============ НАСТРОЙКИ ============
BOT_TOKEN = "8534057742:AAE1EDuHUmBXo0vxsXR5XorlWgeXe3-4L98"
ARCHIVE_GROUP_ID = -1003606590827  # ID группы с темами (начинается с -100)
TOPICS_FILE = "user_topics.json"   # Хранение связки user_id -> topic_id
# ===================================


def load_topics() -> dict:
    """Загрузка маппинга пользователей к темам"""
    if os.path.exists(TOPICS_FILE):
        with open(TOPICS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_topics(topics: dict):
    """Сохранение маппинга"""
    with open(TOPICS_FILE, "w") as f:
        json.dump(topics, f, indent=2)


async def get_or_create_topic(context: ContextTypes.DEFAULT_TYPE, user_id: int, username: str, first_name: str) -> int:
    """Получить существующую тему или создать новую для пользователя"""
    topics = load_topics()
    user_key = str(user_id)
    
    # Если тема уже есть — возвращаем её ID
    if user_key in topics:
        return topics[user_key]
    
    # Создаём новую тему
    display_name = f"@{username}" if username else first_name or f"User_{user_id}"
    
    try:
        # Создание темы в группе
        forum_topic = await context.bot.create_forum_topic(
            chat_id=ARCHIVE_GROUP_ID,
            name=display_name,
            icon_custom_emoji_id=None  # Можно добавить эмодзи
        )
        
        topic_id = forum_topic.message_thread_id
        
        # Сохраняем связку
        topics[user_key] = topic_id
        save_topics(topics)
        
        # Первое сообщение с инфой о пользователе
        info_text = f"""👤 **Информация о пользователе**

🆔 ID: `{user_id}`
👤 Имя: {first_name or "—"}
📧 Username: @{username or "нет"}

📅 Первое сообщение: сейчас
"""
        await context.bot.send_message(
            chat_id=ARCHIVE_GROUP_ID,
            message_thread_id=topic_id,
            text=info_text,
            parse_mode="Markdown"
        )
        
        print(f"✅ Создана тема для {display_name}")
        return topic_id
        
    except TelegramError as e:
        print(f"❌ Ошибка создания темы: {e}")
        return None


async def forward_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пересылка текстовых сообщений"""
    message = update.message
    user = message.from_user
    
    topic_id = await get_or_create_topic(context, user.id, user.username, user.first_name)
    if not topic_id:
        return
    
    # Формируем сообщение с меткой времени
    text = f"💬 {message.text}"
    
    await context.bot.send_message(
        chat_id=ARCHIVE_GROUP_ID,
        message_thread_id=topic_id,
        text=text
    )


async def forward_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пересылка фото"""
    message = update.message
    user = message.from_user
    
    topic_id = await get_or_create_topic(context, user.id, user.username, user.first_name)
    if not topic_id:
        return
    
    caption = f"📷 Фото"
    if message.caption:
        caption += f"\n\n{message.caption}"
    
    await context.bot.send_photo(
        chat_id=ARCHIVE_GROUP_ID,
        message_thread_id=topic_id,
        photo=message.photo[-1].file_id,
        caption=caption
    )


async def forward_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пересылка голосовых"""
    message = update.message
    user = message.from_user
    
    topic_id = await get_or_create_topic(context, user.id, user.username, user.first_name)
    if not topic_id:
        return
    
    await context.bot.send_voice(
        chat_id=ARCHIVE_GROUP_ID,
        message_thread_id=topic_id,
        voice=message.voice.file_id,
        caption=f"🎤 Голосовое ({message.voice.duration} сек)"
    )


async def forward_video_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пересылка кружков"""
    message = update.message
    user = message.from_user
    
    topic_id = await get_or_create_topic(context, user.id, user.username, user.first_name)
    if not topic_id:
        return
    
    await context.bot.send_video_note(
        chat_id=ARCHIVE_GROUP_ID,
        message_thread_id=topic_id,
        video_note=message.video_note.file_id
    )
    
    # Подпись отдельным сообщением (у кружков нет caption)
    await context.bot.send_message(
        chat_id=ARCHIVE_GROUP_ID,
        message_thread_id=topic_id,
        text=f"⭕ Видео-кружок ({message.video_note.duration} сек)"
    )


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветствие"""
    await update.message.reply_text(
        "👋 Привет! Я сохраняю сообщения.\n\n"
        "Отправь мне:\n"
        "💬 Текст\n"
        "📷 Фото\n"
        "🎤 Голосовое\n"
        "⭕ Кружок"
    )


async def cmd_my_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать ссылку на свою тему"""
    topics = load_topics()
    user_key = str(update.effective_user.id)
    
    if user_key in topics:
        topic_id = topics[user_key]
        # Формируем ссылку на тему
        group_id_str = str(ARCHIVE_GROUP_ID).replace("-100", "")
        link = f"https://t.me/c/{group_id_str}/{topic_id}"
        await update.message.reply_text(f"📁 Твоя тема: {link}")
    else:
        await update.message.reply_text("📭 У тебя пока нет сохранённых сообщений")


def main():
    """Запуск бота"""
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Команды
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("mytopic", cmd_my_topic))
    
    # Обработчики сообщений (только нужные типы!)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, forward_text))
    app.add_handler(MessageHandler(filters.PHOTO, forward_photo))
    app.add_handler(MessageHandler(filters.VOICE, forward_voice))
    app.add_handler(MessageHandler(filters.VIDEO_NOTE, forward_video_note))
    
    # Остальное (стикеры, гифки, файлы) — игнорируется автоматически
    
    print("🤖 Бот запущен!")
    print(f"📁 Архив: {ARCHIVE_GROUP_ID}")
    app.run_polling()


if __name__ == "__main__":
    main()

