import random
import string
import time
import threading
import concurrent.futures
import io
import json
import os
import telebot
from telebot import types
import requests

TOKEN = '8800397883:AAGt84fFANusGrcTyqEGgUntT3LTS_w6aOU'
bot = telebot.TeleBot(TOKEN)

DB_FILE = "telegram_tracker_db.json"

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {int(k): v for k, v in data.items()}
        except:
            pass
    return {}

def save_db():
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(persistent_db, f, ensure_ascii=False, indent=4)
    except:
        pass

persistent_db = load_db()

def get_user(chat_id):
    if chat_id not in persistent_db:
        persistent_db[chat_id] = {
            'min_len': 5,
            'max_len': 7,
            'use_words': 'yes',
            'numbers': 'yes',
            'stylish': 'yes',
            'nice_nums': 'yes',
            'memes': 'yes',
            'mode': 'fast', # fast или full_power
            'is_searching': False,
            'found_nicks': [],      # Найденные и оцененные свободные юзеры
            'checked_history': [],  # База проверенных (нет повторов)
            'custom_query': None
        }
        save_db()
    return persistent_db[chat_id]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0"
]

def check_telegram_username(username):
    # Проверка доступности юзернейма в Telegram через публичный профиль
    url = f"https://t.me/{username}"
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    try:
        time.sleep(random.uniform(0.3, 0.7))
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 404:
            # Если страница 404, велика вероятность, что юзернейм свободен или удален
            return True
        elif response.status_code == 200:
            # Если 200, страница существует (ник занят)
            # Проверяем текст страницы на предмет того, свободен ли аккаунт
            if "If you have Telegram, you can contact" in response.text or "open in Telegram" not in response.text:
                # Дополнительная проверка на заброшенный/удаленный юзернейм
                return False
    except:
        pass
    return False

# Словари для генерации умных ников
MEME_WORDS = ["bro", "cat", "dog", "vibe", "chill", "god", "pro", "dark", "moon", "cyber", "ghost", "king", "lord"]
COOL_ROOTS = ["nexus", "zenith", "shadow", "blitz", "apex", "phantom", "titan", "storm", "crying", "lost"]

def generate_telegram_username(settings):
    min_l = settings['min_len']
    max_l = settings['max_len']
    length = random.randint(min_l, max_l)
    
    use_words = settings['use_words'] == 'yes'
    use_nums = settings['numbers'] == 'yes'
    stylish = settings['stylish'] == 'yes'
    nice_nums = settings['nice_nums'] == 'yes'
    memes = settings['memes'] == 'yes'
    custom = settings['custom_query']
    
    already_checked = set(settings['checked_history'])

    for _ in range(150):
        nick = ""
        if custom and random.random() > 0.3:
            base = custom.strip().lower()
            filler_len = max(0, length - len(base))
            filler = "".join(random.choice(string.ascii_lowercase) for _ in range(filler_len))
            nick = (base + filler)[:length]
        elif memes and random.random() > 0.5:
            word = random.choice(MEME_WORDS)
            if len(word) < length and use_nums:
                num = str(random.randint(10, 999)) if not nice_nums else random.choice(["777", "007", "666", "13", "99"])
                nick = (word + num)[:length]
            else:
                nick = word[:length]
        elif stylish and random.random() > 0.4:
            root = random.choice(COOL_ROOTS)
            nick = root[:length]
        else:
            chars = string.ascii_lowercase
            if use_nums:
                chars += string.digits
            nick = "".join(random.choice(chars) for _ in range(length))

        # Очистка и проверка на уникальность
        nick = nick.strip().lower()
        if len(nick) >= min_l and len(nick) <= max_l and nick not in already_checked:
            return nick
            
    # Запасной вариант
    return "".join(random.choice(string.ascii_lowercase) for _ in range(length))

def evaluate_username(username):
    # Оценка юзернейма от 1 до 10
    length = len(username)
    
    # 1. Оценка длины (чем короче, тем круче)
    if length <= 5: len_score = 10
    elif length == 6: len_score = 8
    elif length == 7: len_score = 6
    else: len_score = 4

    # 2. Оценка цифр (красивые цифры поднимают оценку)
    num_score = 5
    has_digits = any(c.isdigit() for c in username)
    if has_digits:
        if any(seq in username for seq in ["777", "007", "111", "999", "666", "2026"]):
            num_score = 10
        else:
            num_score = 6
    else:
        num_score = 8 # Чистые буквы — это круто

    # 3. Общая красота и благозвучие (наличие гласных/согласных)
    vowels = sum(1 for c in username if c in 'aeiou')
    beauty_score = 7 if vowels > 0 else 4
    if any(m in username for m in MEME_WORDS + COOL_ROOTS):
        beauty_score = 9

    return {
        'beauty': beauty_score,
        'numbers': num_score,
        'length_score': len_score,
        'similar': [username + "bot", "the_" + username, username + "_1", "club_" + username]
    }

def get_markup(settings):
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    btn_len = types.InlineKeyboardButton(f"Длина: от {settings['min_len']} до {settings['max_len']}", callback_data="set_len")
    btn_words = types.InlineKeyboardButton(f"Слова: {'Да' if settings['use_words']=='yes' else 'Нет'}", callback_data="toggle_words")
    btn_nums = types.InlineKeyboardButton(f"Цифры: {'Да' if settings['numbers']=='yes' else 'Нет'}", callback_data="toggle_nums")
    btn_style = types.InlineKeyboardButton(f"Красивые ники: {'Да' if settings['stylish']=='yes' else 'Нет'}", callback_data="toggle_style")
    btn_nn = types.InlineKeyboardButton(f"Красивые цифры: {'Да' if settings['nice_nums']=='yes' else 'Нет'}", callback_data="toggle_nn")
    btn_memes = types.InlineKeyboardButton(f"Мемы/Шутки: {'Да' if settings['memes']=='yes' else 'Нет'}", callback_data="toggle_memes")
    
    mode_text = "⚡ Полная сила" if settings['mode'] == 'full_power' else "🏃‍♂️ Быстрый"
    btn_mode = types.InlineKeyboardButton(f"Режим: {mode_text}", callback_data="toggle_mode")
    
    btn_search = types.InlineKeyboardButton("🚀 Запустить поиск юзеров", callback_data="start_search")
    
    markup.add(btn_len, btn_words, btn_nums, btn_style, btn_nn, btn_memes, btn_mode, btn_search)
    return markup

@bot.message_handler(commands=['start'])
def cmd_start(message):
    chat_id = message.chat.id
    settings = get_user(chat_id)
    bot.send_message(
        chat_id,
        "🔥 **Telegram Rare Username Tracker & Generator**\n\nВсе параметры и база загружены. Настройте параметры ниже:",
        parse_mode="Markdown",
        reply_markup=get_markup(settings)
    )

@bot.message_handler(commands=['stop'])
def cmd_stop(message):
    chat_id = message.chat.id
    settings = get_user(chat_id)
    settings['is_searching'] = False
    save_db()
    bot.send_message(chat_id, "🛑 Поиск юзернеймов остановлен!")

@bot.message_handler(commands=['search'])
def cmd_search(message):
    chat_id = message.chat.id
    text = message.text.replace('/search', '').strip().lower()
    settings = get_user(chat_id)
    
    if len(text) < 3:
        bot.send_message(chat_id, "⚠️ Текст шаблона должен быть не менее 3 символов.", parse_mode="Markdown")
        return
        
    settings['custom_query'] = text
    save_db()
    bot.send_message(chat_id, f"🎯 Шаблон ключевого слова сохранен: `{text}`.", parse_mode="Markdown")

@bot.message_handler(commands=['noseach'])
def cmd_noseach(message):
    chat_id = message.chat.id
    settings = get_user(chat_id)
    settings['custom_query'] = None
    save_db()
    bot.send_message(chat_id, "🔄 Шаблон отключен.")

@bot.message_handler(commands=['info'])
def cmd_info(message):
    chat_id = message.chat.id
    st = get_user(chat_id)
    
    found_str = ", ".join(st['found_nicks']) if st['found_nicks'] else "Пока не найдены"
    
    info_text = (
        f"📊 **Ваше хранилище трейкера:**\n\n"
        f"⚙️ **Диапазон длины:** от `{st['min_len']}` до `{st['max_len']}` симв.\n"
        f"🎉 **Найденные крутые юзернеймы:** `{found_str}`\n"
        f"🔍 **Всего проверено за всё время (база):** `{len(st['checked_history'])}`"
    )
    
    bot.send_message(chat_id, info_text, parse_mode="Markdown")
    
    if st['checked_history']:
        file_content = "\n".join(st['checked_history'])
        file_bytes = io.BytesIO(file_content.encode('utf-8'))
        file_bytes.name = "telegram_checked_usernames.txt"
        bot.send_document(
            chat_id, 
            file_bytes, 
            caption="📄 Полный файл со всеми проверенными Telegram-никами (защита от повторов)."
        )

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id
    settings = get_user(chat_id)
    
    if call.data == "set_len":
        # Циклически меняем диапазоны длин
        if settings['min_len'] == 5 and settings['max_len'] == 7:
            settings['min_len'], settings['max_len'] = 5, 10
        elif settings['min_len'] == 5 and settings['max_len'] == 10:
            settings['min_len'], settings['max_len'] = 4, 6
        else:
            settings['min_len'], settings['max_len'] = 5, 7
    elif call.data == "toggle_words":
        settings['use_words'] = 'no' if settings['use_words'] == 'yes' else 'yes'
    elif call.data == "toggle_nums":
        settings['numbers'] = 'no' if settings['numbers'] == 'yes' else 'yes'
    elif call.data == "toggle_style":
        settings['stylish'] = 'no' if settings['stylish'] == 'yes' else 'yes'
    elif call.data == "toggle_nn":
        settings['nice_nums'] = 'no' if settings['nice_nums'] == 'yes' else 'yes'
    elif call.data == "toggle_memes":
        settings['memes'] = 'no' if settings['memes'] == 'yes' else 'yes'
    elif call.data == "toggle_mode":
        settings['mode'] = 'fast' if settings['mode'] == 'full_power' else 'full_power'
    elif call.data == "start_search":
        if settings['is_searching']:
            bot.answer_callback_query(call.id, "Поиск уже запущен!")
            return
            
        bot.answer_callback_query(call.id, "Поиск активирован!")
        settings['is_searching'] = True
        
        status_msg = bot.send_message(chat_id, "🔎 Бот сканирует Telegram на наличие свободных редких юзеров...")
        threading.Thread(target=run_search_loop, args=(chat_id, status_msg.message_id)).start()
        return

    save_db()
    try:
        bot.edit_message_text(
            "🔥 **Telegram Rare Username Tracker & Generator**\n\nПараметры обновлены и сохранены:",
            chat_id=chat_id,
            message_id=call.message.message_id,
            parse_mode="Markdown",
            reply_markup=get_markup(settings)
        )
    except:
        pass

def run_search_loop(chat_id, msg_id):
    settings = get_user(chat_id)
    # Выбор порции в зависимости от режима (полная сила или быстрый)
    batch_size = 25 if settings['mode'] == 'full_power' else 10
    
    found_username = None
    checked_local = 0
    
    def worker():
        nonlocal found_username
        if not settings['is_searching'] or found_username:
            return
            
        candidate = generate_telegram_username(settings)
        if not settings['is_searching'] or found_username:
            return
            
        if candidate not in settings['checked_history']:
            settings['checked_history'].append(candidate)
            
        if check_telegram_username(candidate):
            found_username = candidate
            if found_username not in settings['found_nicks']:
                settings['found_nicks'].append(found_username)

    while not found_username and settings['is_searching'] and checked_local < batch_size:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(worker) for _ in range(4)]
            concurrent.futures.wait(futures)
        checked_local += 4

    save_db()
    settings['is_searching'] = False
    
    try:
        bot.delete_message(chat_id, msg_id)
    except:
        pass
        
    if found_username:
        evals = evaluate_username(found_username)
        similar_str = ", ".join([f"`@{s}`" for s in evals['similar']])
        
        report = (
            f"🎉 **НАЙДЕН СВОБОДНЫЙ TELEGRAM ЮЗЕР!** 🎉\n\n"
            f"👉 Ссылка: `t.me/{found_username}`\n\n"
            f"📊 **Оценка бота:**\n"
            f"✨ Красота: `{evals['beauty']}/10`\n"
            f"🔢 Цифры: `{evals['numbers']}/10`\n"
            f"📏 Длина ({len(found_username)} симв.): `{evals['length_score']}/10`\n\n"
            f"🔗 **Подобные юзернеймы:**\n{similar_str}\n\n"
            f"*(Сохранено в хранилище бота)*"
        )
        bot.send_message(chat_id, report, parse_mode="Markdown")
        bot.send_message(
            chat_id,
            "🔄 **Продолжить поиск новых редких юзеров?**",
            reply_markup=get_markup(settings)
        )
    else:
        bot.send_message(
            chat_id,
            "🛡 Порция сканирования завершена. Все проверенные варианты занесены в базу данных, повторов не будет!",
            reply_markup=get_markup(settings)
        )

print("Telegram Трейкер и Генератор юзернеймов запущен...")
bot.infinity_polling()