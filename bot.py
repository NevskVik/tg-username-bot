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

TOKEN = os.getenv('BOT_TOKEN')

if not TOKEN:
    raise ValueError("Не найден токен бота! Проверь переменную окружения BOT_TOKEN на Render.")

bot = telebot.TeleBot(TOKEN)

DB_FILE = "telegram_tracker_db.json"

# Большая база из 100+ крутых, стильных и премиальных слов и корней для ников
DEFAULT_COOL_WORDS = [
    "nexus", "zenith", "shadow", "blitz", "apex", "phantom", "titan", "storm", "crying", "lost",
    "cyber", "ghost", "king", "lord", "vibe", "chill", "god", "pro", "dark", "moon",
    "angel", "demon", "devil", "saints", "rebel", "sniper", "hunter", "matrix", "vector", "orbit",
    "pulsar", "quasar", "cosmos", "astral", "nova", "eclipse", "frost", "flame", "smoke", "toxic",
    "acid", "neon", "laser", "pulse", "core", "node", "byte", "sync", "flow", "drift",
    "speed", "turbo", "nitro", "alpha", "beta", "omega", "sigma", "delta", "prime", "zero",
    "one", "infinity", "chaos", "order", "void", "abyss", "1337", "hacker", "coder", "script",
    "bug", "glitch", "fatal", "crash", "root", "admin", "guest", "user", "bot", "ai",
    "neural", "synth", "retro", "classic", "vintage", "epic", "legend", "myth", "godlike", "immortal",
    "eternal", "unknown", "hidden", "secret", "private", "public", "local", "global", "net",
    "web", "link", "hub", "station", "base", "origin", "source", "target", "flash", "spark"
]

# Красивые комбинации цифр
NICE_NUM_PATTERNS = [
    "101", "1010", "1100", "111", "000", "777", "007", "666", "999", "13", "99", "2026", "024"
]

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                formatted_data = {}
                for k, v in data.items():
                    chat_id = int(k)
                    if 'custom_words' not in v:
                        v['custom_words'] = []
                    if 'itog_saved' not in v:
                        v['itog_saved'] = []
                    if 'colvo_min' not in v:
                        v['colvo_min'] = 5
                    if 'colvo_max' not in v:
                        v['colvo_max'] = 10
                    formatted_data[chat_id] = v
                return formatted_data
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
            'colvo_min': 5,
            'colvo_max': 10,
            'use_words': 'yes',
            'numbers': 'yes',
            'stylish': 'yes',
            'nice_nums': 'yes',
            'memes': 'yes',
            'mode': 'fast',
            'is_searching': False,
            'found_nicks': [],      
            'checked_history': [],  
            'itog_saved': [],       
            'custom_words': [],     
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
    url = f"https://t.me/{username}"
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    try:
        time.sleep(random.uniform(0.2, 0.5))
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 404:
            return True
        elif response.status_code == 200:
            if "If you have Telegram, you can contact" in response.text or "open in Telegram" not in response.text:
                return False
    except:
        pass
    return False

def generate_telegram_username(settings):
    min_l = settings.get('colvo_min', 5)
    max_l = settings.get('colvo_max', 10)
    length = random.randint(min_l, max_l)
    
    custom = settings.get('custom_query')
    already_checked = set(settings['checked_history'])
    
    all_words = DEFAULT_COOL_WORDS + settings['custom_words']

    for _ in range(150):
        nick = ""
        if custom and random.random() > 0.3:
            base = custom.strip().lower()
            num_part = random.choice(NICE_NUM_PATTERNS) if random.random() > 0.4 else ""
            if random.random() > 0.5:
                nick = base + num_part
            else:
                nick = num_part + base
        elif all_words and random.random() > 0.3:
            word = random.choice(all_words)
            num = random.choice(NICE_NUM_PATTERNS)
            if random.random() > 0.5:
                nick = num + word
            else:
                nick = word + num
        else:
            chars = string.ascii_lowercase + string.digits
            nick = "".join(random.choice(chars) for _ in range(length))

        nick = nick.strip().lower()
        if len(nick) > max_l:
            nick = nick[:max_l]

        if len(nick) >= min_l and nick not in already_checked:
            return nick
            
    return "".join(random.choice(string.ascii_lowercase) for _ in range(length))

def evaluate_username(username):
    length = len(username)
    if length <= 5: len_score = 10
    elif length == 6: len_score = 8
    elif length == 7: len_score = 6
    else: len_score = 4

    num_score = 5
    has_digits = any(c.isdigit() for c in username)
    if has_digits:
        if any(seq in username for seq in NICE_NUM_PATTERNS):
            num_score = 10
        else:
            num_score = 6
    else:
        num_score = 8

    vowels = sum(1 for c in username if c in 'aeiou')
    beauty_score = 7 if vowels > 0 else 4
    
    all_words = DEFAULT_COOL_WORDS + [w for chat in persistent_db.values() for w in chat.get('custom_words', [])]
    if any(m in username for m in all_words):
        beauty_score = 10

    return {
        'beauty': beauty_score,
        'numbers': num_score,
        'length_score': len_score,
        'similar': [username + "bot", "the_" + username, username + "_1", "club_" + username]
    }

def get_markup(settings):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_len = types.InlineKeyboardButton(f"Длина (/colvo): {settings.get('colvo_min', 5)}-{settings.get('colvo_max', 10)}", callback_data="set_len")
    mode_text = "⚡ Полная сила" if settings['mode'] == 'full_power' else "🏃‍♂️ Быстрый"
    btn_mode = types.InlineKeyboardButton(f"Режим: {mode_text}", callback_data="toggle_mode")
    btn_search = types.InlineKeyboardButton("🚀 Запустить поиск юзеров", callback_data="start_search")
    btn_itog = types.InlineKeyboardButton("🏆 Топ ники (/itog)", callback_data="btn_itog")
    markup.add(btn_len, btn_mode, btn_search, btn_itog)
    return markup

@bot.message_handler(commands=['start'])
def cmd_start(message):
    chat_id = message.chat.id
    settings = get_user(chat_id)
    bot.send_message(
        chat_id,
        "🔥 **Telegram Rare Username Tracker & Generator**\n\n"
        "Бот готов искать крутые ники с красивыми цифрами и словами!\n"
        "Введите `/help`, чтобы посмотреть список всех доступных команд.",
        parse_mode="Markdown",
        reply_markup=get_markup(settings)
    )

@bot.message_handler(commands=['help'])
def cmd_help(message):
    help_text = (
        "📖 **Справка по командам бота:**\n\n"
        "🚀 `/start` — Главное меню и запуск бота.\n"
        "🛑 `/stop` — Остановить поиск юзернеймов.\n"
        "⚙️ `/colvo Мин, Макс` — Задать диапазон длины (например: `/colvo 5, 10`).\n"
        "🎯 `/search Слово` — Искать ники по конкретному шаблону/слову.\n"
        "🔄 `/noseach` — Отключить текущий шаблон поиска.\n"
        "🏆 `/itog` — Выдать от 1 до 7 самых красивых свободных юзернеймов.\n"
        "📁 `/allitog` — Получить файл со ВСЕМИ крутыми никами, которые нашел бот.\n"
        "💬 `/slovo Слово` — Добавить свое слово в базу красивых слов.\n"
        "📜 `/allslovo` — Посмотреть все добавленные вами слова.\n"
        "❌ `/dellslovo Слово` — Удалить слово из вашего списка.\n"
        "📊 `/info` — Статистика и выгрузка базы проверенных ников."
    )
    bot.send_message(message.chat.id, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['stop'])
def cmd_stop(message):
    chat_id = message.chat.id
    settings = get_user(chat_id)
    settings['is_searching'] = False
    save_db()
    bot.send_message(chat_id, "🛑 Поиск юзернеймов остановлен!")

@bot.message_handler(commands=['colvo'])
def cmd_colvo(message):
    chat_id = message.chat.id
    settings = get_user(chat_id)
    try:
        parts = message.text.replace('/colvo', '').strip().split(',')
        if len(parts) == 2:
            min_l = int(parts[0].strip())
            max_l = int(parts[1].strip())
            if 3 <= min_l <= max_l <= 15:
                settings['colvo_min'] = min_l
                settings['colvo_max'] = max_l
                save_db()
                bot.send_message(chat_id, f"✅ Успешно! Установлен диапазон длин от `{min_l}` до `{max_l}` символов.", parse_mode="Markdown")
                return
        bot.send_message(chat_id, "⚠️ Ошибка формата! Используйте так: `/colvo 5, 10`", parse_mode="Markdown")
    except:
        bot.send_message(chat_id, "⚠️ Ошибка! Укажите числа правильно, например: `/colvo 5, 10`", parse_mode="Markdown")

@bot.message_handler(commands=['search'])
def cmd_search(message):
    chat_id = message.chat.id
    text = message.text.replace('/search', '').strip().lower()
    settings = get_user(chat_id)
    if len(text) < 2:
        bot.send_message(chat_id, "⚠️ Текст шаблона должен быть не менее 2 символов.")
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
    bot.send_message(chat_id, "🔄 Шаблон поиска отключен.")

@bot.message_handler(commands=['slovo'])
def cmd_slovo(message):
    chat_id = message.chat.id
    word = message.text.replace('/slovo', '').strip().lower()
    settings = get_user(chat_id)
    if len(word) < 2:
        bot.send_message(chat_id, "⚠️ Слово должно содержать минимум 2 символа.")
        return
    if word not in settings['custom_words']:
        settings['custom_words'].append(word)
        save_db()
        bot.send_message(chat_id, f"✨ Слово `{word}` успешно добавлено в вашу базу красивых слов!", parse_mode="Markdown")
    else:
        bot.send_message(chat_id, f"ℹ️ Слово `{word}` уже есть в вашей базе.", parse_mode="Markdown")

@bot.message_handler(commands=['allslovo'])
def cmd_allslovo(message):
    chat_id = message.chat.id
    settings = get_user(chat_id)
    words = settings['custom_words']
    if words:
        words_str = ", ".join([f"`{w}`" for w in words])
        bot.send_message(chat_id, f"💬 **Ваши добавленные слова:**\n{words_str}", parse_mode="Markdown")
    else:
        bot.send_message(chat_id, "ℹ️ Вы еще не добавили ни одного слова. Используйте команду `/slovo ВашеСлово`.")

@bot.message_handler(commands=['dellslovo'])
def cmd_dellslovo(message):
    chat_id = message.chat.id
    word = message.text.replace('/dellslovo', '').strip().lower()
    settings = get_user(chat_id)
    if word in settings['custom_words']:
        settings['custom_words'].remove(word)
        save_db()
        bot.send_message(chat_id, f"🗑 Слово `{word}` удалено из вашей базы.", parse_mode="Markdown")
    else:
        bot.send_message(chat_id, f"⚠️ Слово `{word}` не найдено в вашем списке.")

@bot.message_handler(commands=['itog'])
def cmd_itog(message):
    chat_id = message.chat.id
    settings = get_user(chat_id)
    saved = settings['itog_saved']
    
    if not saved:
        bot.send_message(chat_id, "ℹ️ У бота пока нет накопленных топ-ников. Запустите поиск, чтобы наполнить коллекцию!")
        return
        
    count = min(len(saved), 7)
    top_nicks = saved[-count:]
    
    response = "🏆 **САМЫЕ КРАСИВЫЕ И ТОПОВЫЕ НИКИ (Итог):**\n\n"
    for nick in top_nicks:
        response += f"👉 `t.me/{nick}`\n"
    response += "\n*(Самые лучшие комбинации слов и цифр)*"
    
    bot.send_message(chat_id, response, parse_mode="Markdown")

@bot.message_handler(commands=['allitog'])
def cmd_allitog(message):
    chat_id = message.chat.id
    settings = get_user(chat_id)
    saved = settings['itog_saved']
    
    if not saved:
        bot.send_message(chat_id, "ℹ️ База крутых ников пока пуста.")
        return
        
    file_content = "\n".join(saved)
    file_bytes = io.BytesIO(file_content.encode('utf-8'))
    file_bytes.name = "telegram_all_top_usernames.txt"
    bot.send_document(
        chat_id, 
        file_bytes, 
        caption="📁 Полный файл со ВСЕМИ крутыми и красивыми никами!"
    )

@bot.message_handler(commands=['info'])
def cmd_info(message):
    chat_id = message.chat.id
    st = get_user(chat_id)
    found_str = ", ".join(st['found_nicks'][-5:]) if st['found_nicks'] else "Пока не найдены"
    info_text = (
        f"📊 **Ваше хранилище трейкера:**\n\n"
        f"⚙️ **Диапазон длины:** от `{st.get('colvo_min', 5)}` до `{st.get('colvo_max', 10)}` симв.\n"
        f"🎉 **Последние найденные:** `{found_str}`\n"
        f"🏆 **Сохранено в итоги (`/itog`):** `{len(st['itog_saved'])}` ников\n"
        f"🔍 **Всего проверено за всё время:** `{len(st['checked_history'])}`"
    )
    bot.send_message(chat_id, info_text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id
    settings = get_user(chat_id)
    
    if call.data == "toggle_mode":
        settings['mode'] = 'fast' if settings['mode'] == 'full_power' else 'full_power'
    elif call.data == "btn_itog":
        saved = settings['itog_saved']
        if not saved:
            bot.answer_callback_query(call.id, "Топ ники пока не найдены!", show_alert=True)
        else:
            count = min(len(saved), 7)
            top_str = "\n".join([f"t.me/{n}" for n in saved[-count:]])
            bot.answer_callback_query(call.id, f"Топ ники:\n{top_str}", show_alert=True)
        return
    elif call.data == "start_search":
        if settings['is_searching']:
            bot.answer_callback_query(call.id, "Поиск уже запущен!")
            return
        bot.answer_callback_query(call.id, "Поиск активирован!")
        settings['is_searching'] = True
        status_msg = bot.send_message(chat_id, "🔎 Бот ищет крутые редкие комбинации (слово + цифры)...")
        threading.Thread(target=run_search_loop, args=(chat_id, status_msg.message_id)).start()
        return

    save_db()
    try:
        bot.edit_message_text(
            "🔥 **Telegram Rare Username Tracker & Generator**\n\nПараметры обновлены:",
            chat_id=chat_id,
            message_id=call.message.message_id,
            parse_mode="Markdown",
            reply_markup=get_markup(settings)
        )
    except:
        pass

def run_search_loop(chat_id, msg_id):
    settings = get_user(chat_id)
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
            if found_username not in settings['itog_saved']:
                settings['itog_saved'].append(found_username)

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
            f"🎉 **НАЙДЕН КРУТОЙ СВОБОДНЫЙ НИК!** 🎉\n\n"
            f"👉 Ссылка: `t.me/{found_username}`\n\n"
            f"📊 **Оценка бота:**\n"
            f"✨ Красота/Слово: `{evals['beauty']}/10`\n"
            f"🔢 Цифры: `{evals['numbers']}/10`\n"
            f"📏 Длина ({len(found_username)} симв.): `{evals['length_score']}/10`\n\n"
            f"🔗 **Подобные варианты:**\n{similar_str}\n\n"
            f"*(Ник сохранен в команды `/itog` и `/allitog`)*"
        )
        bot.send_message(chat_id, report, parse_mode="Markdown")
        bot.send_message(
            chat_id,
            "🔄 **Продолжить поиск?**",
            reply_markup=get_markup(settings)
        )
    else:
        bot.send_message(
            chat_id,
            "🛡 Порция сканирования завершена. Все варианты проверены и занесены в базу без повторов!",
            reply_markup=get_markup(settings)
        )

print("Telegram Трейкер и Генератор юзернеймов запущен...")
bot.infinity_polling()
