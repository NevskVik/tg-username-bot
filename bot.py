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

# База из 100+ крутых, стильных и премиальных слов
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

# Мемные и хайповые слова
MEME_WORDS = [
    "sigma", "gigachad", "rizz", "skibidi", "ohio", "mewing", "alpha", "beta", "pudge", "invoker",
    "shadowfiend", "ez", "clutch", "boost", "boosted", "taunt", "toxic", "cringe", "based", "chad"
]

# Красивые цифровые паттерны
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
                    if 'checked_words_base' not in v:
                        v['checked_words_base'] = []
                    if 'colvo_min' not in v:
                        v['colvo_min'] = 5
                    if 'colvo_max' not in v:
                        v['colvo_max'] = 10
                    if 'use_words' not in v:
                        v['use_words'] = 'yes'
                    if 'numbers' not in v:
                        v['numbers'] = 'yes'
                    if 'stylish' not in v:
                        v['stylish'] = 'yes'
                    if 'nice_nums' not in v:
                        v['nice_nums'] = 'yes'
                    if 'memes' not in v:
                        v['memes'] = 'yes'
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
            'checked_words_base': [], 
            'custom_words': [],     
            'custom_query': None
        }
        save_db()
    return persistent_db[chat_id]

def save_checked_word(chat_id, word):
    settings = get_user(chat_id)
    clean_word = word.strip().lower()
    if clean_word and clean_word not in settings['checked_words_base']:
        settings['checked_words_base'].append(clean_word)
        save_db()
        return True
    return False

# --- УМНЫЙ ИИ-АНАЛИЗАТОР НИКОВ ДЛЯ /itog ---
def smart_evaluate_and_save(chat_id, username):
    """
    Интеллектуальная функция: оценивает ник по качеству, наличию крутых слов 
    и красивых цифр. Если ник хороший — гарантированно добавляет в /itog.
    """
    settings = get_user(chat_id)
    u = username.lower()
    
    score = 0
    
    # 1. Проверяем наличие слов из баз (стандартные, мемные, кастомные)
    all_words = DEFAULT_COOL_WORDS + MEME_WORDS + settings.get('custom_words', [])
    has_word = any(w in u for w in all_words)
    if has_word:
        score += 5
        
    # 2. Проверяем наличие крутых цифровых комбинаций
    has_nice_num = any(num in u for num in NICE_NUM_PATTERNS)
    if has_nice_num:
        score += 4
        
    # 3. Оценка длины (короткие ценятся выше)
    if len(u) <= 6:
        score += 3
    elif len(u) <= 8:
        score += 2
    else:
        score += 1
        
    # 4. Если задан кастомный запрос через /search и он есть в нике — жирный плюс
    custom = settings.get('custom_query')
    if custom and custom in u:
        score += 6

    # Умный порог: если итоговый балл >= 5, ник считается достаточно красивым для /itog
    if score >= 5:
        if u not in settings['itog_saved']:
            settings['itog_saved'].append(u)
            save_db()
            return True
    return False

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
    
    active_word_pool = []
    if settings.get('use_words') == 'yes':
        active_word_pool.extend(DEFAULT_COOL_WORDS)
    if settings.get('memes') == 'yes':
        active_word_pool.extend(MEME_WORDS)
    active_word_pool.extend(settings.get('custom_words', []))

    for _ in range(150):
        nick = ""
        if custom and random.random() > 0.3:
            base = custom.strip().lower()
            num_part = random.choice(NICE_NUM_PATTERNS) if (settings.get('nice_nums') == 'yes' and random.random() > 0.4) else ""
            if random.random() > 0.5:
                nick = base + num_part
            else:
                nick = num_part + base
        elif active_word_pool and random.random() > 0.25:
            word = random.choice(active_word_pool)
            if settings.get('nice_nums') == 'yes' and random.random() > 0.2:
                num = random.choice(NICE_NUM_PATTERNS)
                nick = (num + word) if random.random() > 0.5 else (word + num)
            else:
                nick = word
        elif settings.get('nice_nums') == 'yes' and random.random() > 0.5:
            nick = random.choice(NICE_NUM_PATTERNS) + "".join(random.choice(string.ascii_lowercase) for _ in range(random.randint(1, 3)))
        else:
            chars = string.ascii_lowercase
            if settings.get('numbers') == 'yes':
                chars += string.digits
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

    beauty_score = 7
    all_known_words = DEFAULT_COOL_WORDS + MEME_WORDS + [w for chat in persistent_db.values() for w in chat.get('custom_words', [])]
    if any(m in username for m in all_known_words):
        beauty_score = 10

    return {
        'beauty': beauty_score,
        'numbers': num_score,
        'length_score': len_score,
        'similar': [username + "bot", "the_" + username, username + "_1", "club_" + username]
    }

def get_markup(settings):
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    w_status = "✅ Вкл" if settings.get('use_words') == 'yes' else "❌ Выкл"
    m_status = "✅ Вкл" if settings.get('memes') == 'yes' else "❌ Выкл"
    n_status = "✅ Вкл" if settings.get('nice_nums') == 'yes' else "❌ Выкл"
    num_status = "✅ Вкл" if settings.get('numbers') == 'yes' else "❌ Выкл"
    
    mode_text = "⚡ Турбо" if settings.get('mode') == 'full_power' else "🏃‍♂️ Стандарт"

    markup.add(
        types.InlineKeyboardButton(f"📚 Красивые слова: {w_status}", callback_data="toggle_words"),
        types.InlineKeyboardButton(f"🤪 Мем-слова: {m_status}", callback_data="toggle_memes")
    )
    markup.add(
        types.InlineKeyboardButton(f"🔢 Красивые цифры: {n_status}", callback_data="toggle_nicenums"),
        types.InlineKeyboardButton(f"🔠 Обычные цифры: {num_status}", callback_data="toggle_numbers")
    )
    markup.add(
        types.InlineKeyboardButton(f"⚙️ Длина (/colvo): {settings.get('colvo_min', 5)}-{settings.get('colvo_max', 10)}", callback_data="info_colvo"),
        types.InlineKeyboardButton(f"⚡ Режим: {mode_text}", callback_data="toggle_mode")
    )
    markup.add(
        types.InlineKeyboardButton("🚀 Запустить поиск", callback_data="start_search"),
        types.InlineKeyboardButton("🏆 Топ ники (/itog)", callback_data="btn_itog")
    )
    return markup

@bot.message_handler(commands=['start'])
def cmd_start(message):
    chat_id = message.chat.id
    settings = get_user(chat_id)
    bot.send_message(
        chat_id,
        "🔥 **Telegram Rare Username Dashboard & Generator**\n\n"
        "Умная ИИ-фильтрация активирована: в `/itog` попадают только топовые ники со словами и красивыми цифрами!",
        parse_mode="Markdown",
        reply_markup=get_markup(settings)
    )

@bot.message_handler(commands=['help'])
def cmd_help(message):
    help_text = (
        "📖 **Справка по всем командам бота:**\n\n"
        "🚀 `/start` — Открыть интерактивную GUI-панель.\n"
        "🛑 `/stop` — Остановить активный поиск.\n"
        "⚙️ `/colvo Мин, Макс` — Задать диапазон длины (пример: `/colvo 5, 10`).\n"
        "🎯 `/search Шаблон` — Искать ники по конкретной основе.\n"
        "🔄 `/noseach` — Отключить текущий шаблон поиска.\n"
        "🏆 `/itog` — Выдать от 1 до 7 лучших отобранных ИИ свободных ников.\n"
        "📁 `/allitog` — Получить `.txt` файл со ВСЕМИ крутыми никами.\n"
        "💬 `/slovo Слово` — Добавить слово в личную базу.\n"
        "📜 `/allslovo` — Просмотреть добавленные слова.\n"
        "❌ `/dellslovo Слово` — Удалить слово из базы.\n"
        "📊 `/info` — Статистика и показатели хранилища."
    )
    bot.send_message(message.chat.id, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['stop'])
def cmd_stop(message):
    chat_id = message.chat.id
    settings = get_user(chat_id)
    settings['is_searching'] = False
    save_db()
    bot.send_message(chat_id, "🛑 Поиск юзернеймов успешно остановлен!")

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
                bot.send_message(chat_id, f"✅ Успешно! Установлена длина: от `{min_l}` до `{max_l}` символов.", parse_mode="Markdown", reply_markup=get_markup(settings))
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
        bot.send_message(chat_id, f"✨ Слово `{word}` успешно добавлено в вашу базу!", parse_mode="Markdown")
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
        bot.send_message(chat_id, "ℹ️ Вы еще не добавили ни одного слова через `/slovo`.")

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
        bot.send_message(chat_id, "ℹ️ ИИ еще не отобрал достаточно премиальных ников. Запустите поиск, чтобы ИИ наполнил коллекцию лучшими вариантами!")
        return
        
    count = min(len(saved), 7)
    top_nicks = saved[-count:]
    
    response = "🏆 **ИИ-ОБЗОР: ЛУЧШИЕ ОТОБРАННЫЕ НИКИ (Итог):**\n\n"
    for nick in top_nicks:
        response += f"👉 `t.me/{nick}`\n"
    response += "\n*(Проверено ИИ-фильтром на красивые словосочетания и цифры)*"
    
    bot.send_message(chat_id, response, parse_mode="Markdown")

@bot.message_handler(commands=['allitog'])
def cmd_allitog(message):
    chat_id = message.chat.id
    settings = get_user(chat_id)
    saved = settings['itog_saved']
    
    if not saved:
        bot.send_message(chat_id, "ℹ️ База отборных ников пока пуста.")
        return
        
    file_content = "\n".join(saved)
    file_bytes = io.BytesIO(file_content.encode('utf-8'))
    file_bytes.name = "telegram_ai_top_usernames.txt"
    bot.send_document(
        chat_id, 
        file_bytes, 
        caption="📁 Файл со ВСЕМИ отборными премиальными никами, одобренными ИИ!"
    )

@bot.message_handler(commands=['info'])
def cmd_info(message):
    chat_id = message.chat.id
    st = get_user(chat_id)
    found_str = ", ".join(st['found_nicks'][-5:]) if st['found_nicks'] else "Пока нет"
    info_text = (
        f"📊 **Статистика трейкера:**\n\n"
        f"⚙️ **Длина ников:** от `{st.get('colvo_min', 5)}` до `{st.get('colvo_max', 10)}`\n"
        f"📝 **В базе проверенных слов:** `{len(st['checked_words_base'])}`\n"
        f"🤖 **Одобрено ИИ для `/itog`:** `{len(st['itog_saved'])}` ников\n"
        f"🎉 **Последние находки:** `{found_str}`\n"
        f"🔍 **Всего проверено:** `{len(st['checked_history'])}`"
    )
    bot.send_message(chat_id, info_text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id
    settings = get_user(chat_id)
    
    if call.data == "toggle_words":
        settings['use_words'] = 'no' if settings.get('use_words') == 'yes' else 'yes'
    elif call.data == "toggle_memes":
        settings['memes'] = 'no' if settings.get('memes') == 'yes' else 'yes'
    elif call.data == "toggle_nicenums":
        settings['nice_nums'] = 'no' if settings.get('nice_nums') == 'yes' else 'yes'
    elif call.data == "toggle_numbers":
        settings['numbers'] = 'no' if settings.get('numbers') == 'yes' else 'yes'
    elif call.data == "toggle_mode":
        settings['mode'] = 'fast' if settings.get('mode') == 'full_power' else 'full_power'
    elif call.data == "info_colvo":
        bot.answer_callback_query(call.id, "Используй команду /colvo Мин, Макс для изменения (например: /colvo 5, 10)", show_alert=True)
        return
    elif call.data == "btn_itog":
        saved = settings['itog_saved']
        if not saved:
            bot.answer_callback_query(call.id, "ИИ еще не отобрал топ ники!", show_alert=True)
        else:
            count = min(len(saved), 7)
            top_str = "\n".join([f"t.me/{n}" for n in saved[-count:]])
            bot.answer_callback_query(call.id, f"Топ ники:\n{top_str}", show_alert=True)
        return
    elif call.data == "start_search":
        if settings['is_searching']:
            bot.answer_callback_query(call.id, "Поиск уже запущен!")
            return
        bot.answer_callback_query(call.id, "Запуск сканирования...")
        settings['is_searching'] = True
        status_msg = bot.send_message(chat_id, "🔎 ИИ сканирует сеть Telegram и фильтрует лучшие варианты...")
        threading.Thread(target=run_search_loop, args=(chat_id, status_msg.message_id)).start()
        return

    save_db()
    try:
        bot.edit_message_text(
            "🔥 **Telegram Rare Username Dashboard & Generator**\n\nПараметры успешно обновлены:",
            chat_id=chat_id,
            message_id=call.message.message_id,
            parse_mode="Markdown",
            reply_markup=get_markup(settings)
        )
    except:
        pass

def run_search_loop(chat_id, msg_id):
    settings = get_user(ch
