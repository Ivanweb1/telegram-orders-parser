import os
import sqlite3
from dotenv import load_dotenv
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes
from datetime import datetime
import asyncio

# Загружаем переменные окружения
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN', '8468131759:AAGtDyDlFrt3Q0GfdjMjWIoLXhyrV6goMoE')

# Инициализируем БД
def init_db():
    conn = sqlite3.connect('orders.db')
    cursor = conn.cursor()
    
    # Таблица заказов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_name TEXT,
            message_text TEXT,
            sender_id INTEGER,
            sender_username TEXT,
            timestamp DATETIME,
            sent BOOLEAN DEFAULT 0
        )
    ''')
    
    # Таблица подписчиков
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscribers (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            subscribed BOOLEAN DEFAULT 1,
            subscribed_at DATETIME
        )
    ''')
    
    conn.commit()
    conn.close()

# Получаем новые заказы (не отправленные)
def get_new_orders():
    conn = sqlite3.connect('orders.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, group_name, message_text, sender_username, timestamp
        FROM orders
        WHERE sent = 0
        ORDER BY timestamp DESC
    ''')
    orders = cursor.fetchall()
    conn.close()
    return orders

# Получаем все заказы
def get_all_orders(limit=20):
    conn = sqlite3.connect('orders.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, group_name, message_text, sender_username, timestamp
        FROM orders
        ORDER BY timestamp DESC
        LIMIT ?
    ''', (limit,))
    orders = cursor.fetchall()
    conn.close()
    return orders

# Отмечаем заказ как отправленный
def mark_order_sent(order_id):
    conn = sqlite3.connect('orders.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE orders SET sent = 1 WHERE id = ?', (order_id,))
    conn.commit()
    conn.close()

# Добавляем подписчика
def add_subscriber(user_id, username):
    conn = sqlite3.connect('orders.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO subscribers (user_id, username, subscribed, subscribed_at)
        VALUES (?, ?, 1, ?)
    ''', (user_id, username, datetime.now()))
    conn.commit()
    conn.close()

# Удаляем подписчика
def remove_subscriber(user_id):
    conn = sqlite3.connect('orders.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE subscribers SET subscribed = 0 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

# Получаем активных подписчиков
def get_subscribers():
    conn = sqlite3.connect('orders.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM subscribers WHERE subscribed = 1')
    subscribers = [row[0] for row in cursor.fetchall()]
    conn.close()
    return subscribers

# Проверяем, подписан ли пользователь
def is_subscriber(user_id):
    conn = sqlite3.connect('orders.db')
    cursor = conn.cursor()
    cursor.execute('SELECT subscribed FROM subscribers WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result and result[0] == 1

# Форматируем заказ для вывода
def format_order(group_name, message_text, sender_username, timestamp):
    """Форматирует заказ в красивое сообщение"""
    text = f"""
📋 **НОВЫЙ ЗАКАЗ**

🏢 Группа: `{group_name}`
👤 От: `@{sender_username}`
⏰ Время: `{timestamp}`

💬 Сообщение:
```
{message_text[:500]}
```

---
"""
    return text

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "unknown"
    
    # Добавляем в подписчики при первом старте
    add_subscriber(user_id, username)
    
    await update.message.reply_text(
        "👋 Привет! Я бот для парсинга заказов дизайна из групп ТГ.\n\n"
        "📋 **Доступные команды:**\n\n"
        "/orders - показать новые заказы\n"
        "/all - последние 20 заказов\n"
        "/stats - статистика по группам\n"
        "/subscribe - подписаться на уведомления (по умолчанию включено)\n"
        "/unsubscribe - отписаться от уведомлений\n\n"
        "🔔 При подписке ты будешь получать уведомления о новых заказах каждые 30 секунд."
    )

# Команда /orders - показать новые заказы
async def orders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    orders = get_new_orders()
    
    if not orders:
        await update.message.reply_text("❌ Новых заказов нет")
        return
    
    message = f"🆕 **НОВЫЕ ЗАКАЗЫ** ({len(orders)} шт.)\n\n"
    
    for order_id, group_name, message_text, sender_username, timestamp in orders[:10]:
        message += format_order(group_name, message_text, sender_username, timestamp)
    
    # Разбиваем на части
    if len(message) > 4096:
        for part in [message[i:i+4096] for i in range(0, len(message), 4096)]:
            await update.message.reply_text(part, parse_mode='Markdown')
    else:
        await update.message.reply_text(message, parse_mode='Markdown')

# Команда /all - все заказы
async def all_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    orders = get_all_orders(20)
    
    if not orders:
        await update.message.reply_text("❌ Заказов нет")
        return
    
    message = f"📋 **Последние {len(orders)} заказов:**\n\n"
    
    for order_id, group_name, message_text, sender_username, timestamp in orders:
        message += format_order(group_name, message_text, sender_username, timestamp)
    
    if len(message) > 4096:
        for part in [message[i:i+4096] for i in range(0, len(message), 4096)]:
            await update.message.reply_text(part, parse_mode='Markdown')
    else:
        await update.message.reply_text(message, parse_mode='Markdown')

# Команда /stats - статистика
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('orders.db')
    cursor = conn.cursor()
    
    # Всего заказов
    cursor.execute('SELECT COUNT(*) FROM orders')
    total = cursor.fetchone()[0]
    
    # Новых заказов
    cursor.execute('SELECT COUNT(*) FROM orders WHERE sent = 0')
    new = cursor.fetchone()[0]
    
    # По группам
    cursor.execute('SELECT group_name, COUNT(*) FROM orders GROUP BY group_name ORDER BY COUNT(*) DESC')
    groups = cursor.fetchall()
    
    # Подписчиков
    cursor.execute('SELECT COUNT(*) FROM subscribers WHERE subscribed = 1')
    subscribers_count = cursor.fetchone()[0]
    
    conn.close()
    
    message = f"""
📊 **СТАТИСТИКА**

📈 Всего заказов: `{total}`
🆕 Новых заказов: `{new}`
👥 Активных подписчиков: `{subscribers_count}`

**По группам:**
"""
    for group_name, count in groups:
        message += f"\n• `{group_name}`: {count}"
    
    await update.message.reply_text(message, parse_mode='Markdown')

# Команда /subscribe
async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "unknown"
    
    add_subscriber(user_id, username)
    await update.message.reply_text(
        "✅ Ты подписан на уведомления!\n\n"
        "Ты будешь получать сообщения о новых заказах каждые 30 секунд."
    )

# Команда /unsubscribe
async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    remove_subscriber(user_id)
    await update.message.reply_text("❌ Ты отписан от уведомлений.")

# Периодически отправляем новые заказы всем подписчикам
async def send_new_orders_periodic(application):
    """Проверяет новые заказы каждые 30 секунд и отправляет подписчикам"""
    while True:
        try:
            orders = get_new_orders()
            
            if orders:
                subscribers = get_subscribers()
                
                if not subscribers:
                    print("⚠️ Нет активных подписчиков")
                    await asyncio.sleep(30)
                    continue
                
                # Форматируем сообщение с заказами
                message = f"🔔 **НОВЫЕ ЗАКАЗЫ** ({len(orders)} шт.)\n\n"
                
                for order_id, group_name, message_text, sender_username, timestamp in orders[:5]:
                    message += format_order(group_name, message_text, sender_username, timestamp)
                    mark_order_sent(order_id)
                
                # Отправляем каждому подписчику
                bot = application.bot
                sent_count = 0
                failed_count = 0
                
                for user_id in subscribers:
                    try:
                        if len(message) > 4096:
                            for part in [message[i:i+4096] for i in range(0, len(message), 4096)]:
                                await bot.send_message(chat_id=user_id, text=part, parse_mode='Markdown')
                        else:
                            await bot.send_message(chat_id=user_id, text=message, parse_mode='Markdown')
                        sent_count += 1
                    except Exception as e:
                        print(f"❌ Ошибка отправки пользователю {user_id}: {e}")
                        failed_count += 1
                
                print(f"✅ Отправлено {sent_count} подписчикам, ошибок: {failed_count}")
        
        except Exception as e:
            print(f"❌ Ошибка при проверке заказов: {e}")
        
        await asyncio.sleep(30)  # Проверяем каждые 30 секунд

async def main():
    """Запуск бота"""
    print("🤖 Запуск бота...")
    
    init_db()
    
    # Инициализируем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("orders", orders_command))
    application.add_handler(CommandHandler("all", all_orders))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("subscribe", subscribe))
    application.add_handler(CommandHandler("unsubscribe", unsubscribe))
    
    # Создаём задачу для периодической проверки заказов
    asyncio.create_task(send_new_orders_periodic(application))
    
    # Запускаем бота
    print("✅ Бот запущен и слушает команды...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

if __name__ == '__main__':
    asyncio.run(main())
