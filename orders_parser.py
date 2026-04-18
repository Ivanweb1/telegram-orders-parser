from telethon.sync import TelegramClient
from telethon import events
import sqlite3
from datetime import datetime
import os
from dotenv import load_dotenv
import time

# Загружаем переменные окружения
load_dotenv()

PHONE_NUMBER = os.getenv('PHONE_NUMBER', '+79161591110')
API_ID = 12345
API_HASH = '0123456789abcdef0123456789abcdef'

# Группы для парсинга
TARGET_GROUPS = [
    'marketplaceone',
    'TOPSELLERAPP',
    'marketplace_pro',
    'ozon_wildberries_yandex',
    'wildberries_marketplace_chats',
    'wildberries_mplace'
]

# Ключевые слова для фильтрации
KEYWORDS = [
    'дизайн', 'логотип', 'баннер', 'инфографика', 'дизайнер',
    'макет', 'карточка товара', 'вёрстка', 'оформление',
    'оформить', 'нужен', 'ищу', 'требуется', 'услуга'
]

# Инициализируем БД
def init_db():
    conn = sqlite3.connect('orders.db')
    cursor = conn.cursor()
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
    conn.commit()
    conn.close()

# Сохраняем заказ в БД
def save_order(group_name, message_text, sender_id, sender_username):
    conn = sqlite3.connect('orders.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO orders (group_name, message_text, sender_id, sender_username, timestamp)
        VALUES (?, ?, ?, ?, ?)
    ''', (group_name, message_text, sender_id, sender_username, datetime.now()))
    conn.commit()
    conn.close()

# Проверяем, содержит ли сообщение ключевые слова
def has_keywords(text):
    if not text:
        return False
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in KEYWORDS)

# Создаём клиент Telethon (синхронный)
client = TelegramClient('session_name', API_ID, API_HASH)

@client.on(events.NewMessage(chats=TARGET_GROUPS))
def handler(event):
    """Обработчик новых сообщений в целевых группах"""
    
    message_text = event.message.text
    
    # Пропускаем пустые сообщения
    if not message_text:
        return
    
    # Проверяем наличие ключевых слов
    if not has_keywords(message_text):
        return
    
    # Получаем информацию об отправителе
    sender = event.message.from_id
    sender_username = event.message.sender.username if hasattr(event.message.sender, 'username') and event.message.sender.username else f"user_{sender}"
    
    # Получаем название группы
    chat = event.chat
    group_name = chat.title if hasattr(chat, 'title') else (chat.username if hasattr(chat, 'username') else str(chat.id))
    
    print(f"\n[{datetime.now()}] ✅ Найден заказ!")
    print(f"📍 Группа: {group_name}")
    print(f"👤 От: @{sender_username}")
    print(f"📝 Сообщение: {message_text[:100]}...")
    
    # Сохраняем в БД
    save_order(group_name, message_text, sender, sender_username)

def main():
    """Основная функция"""
    print("🚀 Запуск парсера заказов...")
    print(f"📌 Целевые группы: {', '.join(TARGET_GROUPS)}")
    print(f"🔑 Ключевые слова: {', '.join(KEYWORDS[:5])}...")
    
    init_db()
    
    print("\n⏳ Подключение к Telegram...")
    
    try:
        with client:
            print("✓ Подключен к Telegram")
            print("🔍 Слушаю сообщения в группах...")
            print("=" * 50)
            
            # Запускаем обработчик событий
            client.run_until_disconnected()
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        print("Убедись, что номер телефона в .env правильный")
        time.sleep(5)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⛔ Парсер остановлен пользователем")
    except Exception as e:
        print(f"\n\n❌ Ошибка: {e}")
