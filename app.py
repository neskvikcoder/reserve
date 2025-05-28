import os
import asyncio
import random
import json
from telethon import TelegramClient, errors
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument

# Укажи свои значения здесь
api_id = 28969912  # <-- ВСТАВЬ СВОЙ API ID
api_hash = '69e174b8c3b90bc6885ee41bb803dd19'  # <-- ВСТАВЬ СВОЙ API HASH

SESSIONS_DIR = 'Sessions'
LAST_MSG_FILE = 'last_message.json'
BATCH_SIZE = 30  # Размер партии сообщений для пересылки

async def create_new_session(session_name, phone_number):
    session_path = os.path.join(SESSIONS_DIR, session_name)
    client = TelegramClient(session_path, api_id, api_hash)
    await client.start(phone=phone_number)
    print('Сессия успешно сохранена!')
    await client.disconnect()

async def forward_media_messages(session_file):
    print("Начинаем работу скрипта...")
    client = TelegramClient(session_file, api_id, api_hash)
    await client.start()

    dialogs = await client.get_dialogs()
    source = None
    target = None

    for dialog in dialogs:
        if dialog.name == 'New ':  # <-- откуда пересылать
            source = dialog.entity
        if dialog.name == 'Reserve':  # <-- куда пересылать
            target = dialog.entity

    if not source:
        print('Канал "New" не найден.')
        await client.disconnect()
        return

    if not target:
        print('Канал "Reserve" не найден.')
        await client.disconnect()
        return

    last_message_id = 0
    if os.path.exists(LAST_MSG_FILE):
        try:
            with open(LAST_MSG_FILE, 'r') as f:
                content = f.read().strip()
                if content:
                    data = json.loads(content)
                    last_message_id = data.get('last_id', 0)
                else:
                    print(f"Файл {LAST_MSG_FILE} пуст. Инициализируем last_message_id как 0.")
        except json.JSONDecodeError as e:
            print(f"Ошибка чтения {LAST_MSG_FILE}: {e}. Инициализируем last_message_id как 0.")
        except Exception as e:
            print(f"Неожиданная ошибка при чтении {LAST_MSG_FILE}: {e}. Инициализируем last_message_id как 0.")

    print(f"Последний сохраненный ID сообщения: {last_message_id}")

    batch = []
    async for message in client.iter_messages(source, reverse=True, min_id=last_message_id):
        if message.media and isinstance(message.media, (MessageMediaPhoto, MessageMediaDocument)):
            batch.append(message)
            print(f"Добавлено сообщение ID {message.id} в партию (размер партии: {len(batch)})")

            if len(batch) >= BATCH_SIZE:
                try:
                    await client.forward_messages(target, batch)
                    last_message_id = max(m.id for m in batch)  # Обновляем последний ID
                    print(f"Переслано {len(batch)} сообщений, последний ID: {last_message_id}")

                    with open(LAST_MSG_FILE, 'w') as f:
                        json.dump({'last_id': last_message_id}, f)

                    batch = []  # Очищаем партию
                    await asyncio.sleep(random.uniform(5, 10))  # Задержка между партиями
                except errors.FloodWaitError as e:
                    print(f"Поймали FLOOD_WAIT. Ждем {e.seconds} секунд...")
                    await asyncio.sleep(e.seconds + 5)
                except Exception as e:
                    print(f"Ошибка при пересылке партии сообщений: {e}")
                    await asyncio.sleep(random.uniform(10, 20))

    # Пересылаем оставшиеся сообщения, если партия неполная
    if batch:
        try:
            await client.forward_messages(target, batch)
            last_message_id = max(m.id for m in batch)
            print(f"Переслано {len(batch)} оставшихся сообщений, последний ID: {last_message_id}")

            with open(LAST_MSG_FILE, 'w') as f:
                json.dump({'last_id': last_message_id}, f)
        except errors.FloodWaitError as e:
            print(f"Поймали FLOOD_WAIT. Ждем {e.seconds} секунд...")
            await asyncio.sleep(e.seconds + 5)
        except Exception as e:
            print(f"Ошибка при пересылке оставшейся партии: {e}")
            await asyncio.sleep(random.uniform(10, 20))

    print('Пересылка завершена.')
    await client.disconnect()

def main():
    if not os.path.exists(SESSIONS_DIR):
        os.makedirs(SESSIONS_DIR)
        print(f'Папка "{SESSIONS_DIR}" была создана.')

    session_files = [f for f in os.listdir(SESSIONS_DIR) if f.endswith('.session')]

    if not session_files:
        print('Сессий нет. Создаем новую.')
        session_name = input('Введите имя новой сессии: ').strip()
        phone_number = input('Введите номер телефона (+380...): ').strip()
        asyncio.run(create_new_session(session_name, phone_number))
        session_files = [f for f in os.listdir(SESSIONS_DIR) if f.endswith('.session')]
        if not session_files:
            print('Не удалось создать сессию. Проверьте данные и попробуйте снова.')
            return

    print('Сессия найдена. Начинаем работу...')
    session_name = session_files[0].replace('.session', '')
    session_path = os.path.join(SESSIONS_DIR, session_name)
    asyncio.run(forward_media_messages(session_path))

if __name__ == '__main__':
    main()
