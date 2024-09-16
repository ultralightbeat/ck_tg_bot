import telebot
import json
import datetime
import subprocess
import re
import logging
from openai import OpenAI
import gspread
from oauth2client.service_account import ServiceAccountCredentials


TOKEN = "YO"
bot = telebot.TeleBot(TOKEN)

# Определение клавиатуры с кнопкой "Начать"
def start_keyboard():
    start_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    start_keyboard.add(telebot.types.KeyboardButton("Начать ▶️"))
    start_keyboard.add(telebot.types.KeyboardButton("Задать вопрос тренеру ❓"))
    return start_keyboard

# Определение клавиатуры с кнопками "Назад" и "Задать вопрос тренеру"
def back_keyboard():
    back_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    back_keyboard.add(telebot.types.KeyboardButton("Назад 🚪"))
    back_keyboard.add(telebot.types.KeyboardButton("Задать вопрос тренеру ❓"))
    return back_keyboard

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message,
                 "Рады приветствовать, я помогу тебе подобрать тренинг по твоему запросу.\nНажми кнопку Начать",
                 reply_markup=start_keyboard())
def analyze_events(user_input, target_word):
    # Используйте OpenAI GPT-3 для анализа ключевых слов и генерации более точных запросов
    openai = OpenAI(
        api_key="YOUR_API_KEY",
        base_url="https://api.deepinfra.com/v1/openai",
    )

    chat_completion = openai.chat.completions.create(
        model="mistralai/Mixtral-8x7B-Instruct-v0.1",
        messages=[{"role": "user", "content": f"Есть тренинги и мастер-классы Саморазвитие, "
               f"Лидерство, "
               f"Креативность, "
               f"Ораторское искусство, "
               f"Импровизация, Гибкость и адаптация, "
               f"Эмоциональный интеллект, "
               f"Интерактивная игра Мозг Студента, "
               f"Резюме,"
               f"Собеседование, "
               f"Адаптация на новом месте работы, "
               f"Планирование и организация, "
               f"Выбор, моя траектория жизни, "
               f"Эффективная коммуникация, посоветуй мне один из этих треннигов если я хочу: {user_input}. Приведи только один треннинг. Напиши ответ на русском языке в формате: Рекомендую тренинг ..."}],
    )
    response = chat_completion.choices[0].message.content
    print(response)

    match = re.search(r'\bтренинг\b', response, re.IGNORECASE)

    if match:
        # Если "тренинг" найден, находим следующее слово после него
        next_word_match = re.search(r'\b\w+\b', response[match.end():])

        if next_word_match:
            next_word = next_word_match.group()
            print(next_word)
            return next_word
    else:
        print("Я ничего не смог найти по вашему запросы, проверьте корректность запроса и  попрубейте еще раз")
def add_question_to_google_sheet(user_id, username, question):
    # Подключение к Google Sheets
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('YOUR_JSON', scope)

    client = gspread.authorize(creds)

    # Открытие таблицы
    sheet = client.open('CK_APPEALS').sheet1

    # Добавление вопроса в таблицу
    row = [user_id, username, question]
    sheet.append_row(row)

def collect_posts(channel):
    with open(f"{channel}.txt") as file:
        file = file.readlines()
    posts = []
    for n, line in enumerate(file):
        file[n] = json.loads(file[n])
        # Список ссылок в каждом сообщении в котором нет ссылок на авторский канал
        links = [link for link in file[n]['outlinks'] if channel not in link]
        # Пост
        p = str(file[n]['content']) + "\n\n" + str("\n".join(links))
        posts.append(p)
    return posts
def clear_data(channel):
    with open(f"{channel}.txt", 'w') as file:
        pass
def upload_posts(channel):
    today = datetime.date.today()
    start_of_month = today.replace(day=1)
    command = f'snscrape --since {start_of_month} --jsonl telegram-channel {channel} > {channel}.txt'
    subprocess.run(command, shell=True)
def find_posts_by_keyword(keyword, channel):
    # Получите все посты из канала
    posts = collect_posts(channel)
    # Поиск постов, содержащих только ключевое слово
    found_posts = [post for post in posts if keyword.lower() in post.lower()]
    return found_posts


@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_text(message):
    if message.text == "Начать ▶️":
        bot.send_message(message.chat.id, "Введите чему бы вы хотели научиться\nНапример: Я хочу успешно проходить собеседования")
        bot.register_next_step_handler(message, search_posts)
    elif message.text == "Назад 🚪":
        bot.send_message(message.chat.id,
                         "Вы в главном меню.", reply_markup=start_keyboard())
    elif message.text == "Задать вопрос тренеру ❓":
        bot.send_message(message.chat.id,
                         "Пожалуйста, отправьте дополнительную информацию или вопрос.", reply_markup=back_keyboard())
        bot.register_next_step_handler(message, process_feedback_text)  # Заменено на process_feedback_text

def search_posts(message):
    try:
        user_input = message.text
        target_word=""
        target_word = analyze_events(user_input, target_word)
        print(target_word)
        channel = 'guapck'
        upload_posts(channel)
        found_posts = find_posts_by_keyword(target_word, channel)
        if found_posts:
            bot.send_message(message.chat.id, "Вот что мне удалось найти:")
            for post in found_posts:
                bot.send_message(message.chat.id, post)
        else:
            logging.error("Поиск не дал результатов.")
            bot.send_message(message.chat.id,
                             "Извините, я не смог найти ничего подходящего.",
                             reply_markup=back_keyboard())
        clear_data(channel)

    except Exception as e:
        logging.exception(f"Произошла ошибка: {str(e)}")
        bot.reply_to(message, f"Произошла ошибка: {str(e)}")

    bot.send_message(message.chat.id, f"Поиск завершен, если хотите найти новое мероприятие нажмите кнопку Начать")


def process_feedback_text(message):  # Новая функция для обработки текстового ввода
    try:
        add_question_to_google_sheet(message.from_user.id, message.from_user.username, message.text)
        bot.reply_to(message, "Спасибо за ваш вопрос! В скором времени с вами свяжуться.")
    except Exception as e:
        logging.exception(f"Произошла ошибка при обработке обратной связи: {str(e)}")
        bot.reply_to(message, "Произошла ошибка при обработке вашего вопроса. Пожалуйста, попробуйте еще раз позже.")

if __name__ == "__main__":
    bot.polling()
