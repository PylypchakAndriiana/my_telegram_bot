import telebot
from config import TOKEN
from database import Database
import time
import logging
import sys
import io

# Примусове встановлення UTF-8 для stdout/stderr
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Налаштування логування з виводом у консоль
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

class TelegramBot:
    def __init__(self, token):
        logging.debug("Ініціалізація TelegramBot")
        self.bot = telebot.TeleBot(token)
        self.db = Database()
        self.user_data = {}
        self.languages = ["Java", "JavaScript", "Python", "C++", "C#", "SQL"]
        self.register_handlers()

    def send_message_with_retry(self, chat_id, text, retries=5):
        for i in range(retries):
            try:
                self.bot.send_message(chat_id, text)
                logging.debug(f"Повідомлення надіслано на {chat_id}")
                return
            except Exception as e:
                logging.error(f"Помилка при надсиланні повідомлення: {e}. Спроба {i+1} з {retries}")
                time.sleep(5)
        logging.error(f"Не вдалося надіслати повідомлення після {retries} спроб")

    def send_welcome(self, message):
        logging.debug("Надсилаю привітальне повідомлення")
        self.bot.send_message(
            message.chat.id,
            'Вітаю! Я Ваш персональний довідник з програмування. '
            'Перш ніж розпочати, давайте познайомимось! Як до Вас звертатися?'
        )
        self.bot.register_next_step_handler(message, self.get_user_name)

    def get_user_name(self, message):
        user_name = message.text
        self.user_data[message.chat.id] = {'name': user_name}
        self.db.save_user_name(message.chat.id, user_name)
        logging.debug(f"Ім’я користувача {user_name} збережено в базі даних")
        self.bot.send_message(
            message.chat.id,
            f'{user_name}, пропоную ознайомитись із опціями боту, у цьому Вам допоможе команда /help.'
        )

    def send_help(self, message):
        logging.debug("Надсилаю інструкції користувачу")
        self.bot.send_message(message.chat.id, (
            'Щоб нам з тобою поладнати потрібно правила завчати та інструкції читати! \n'
            'Отож:\n'
            '/languages - обрати мову програмування\n'
            '/lesson - матеріали для вивчення мов\n'
            '/quiz - тести до теми\n'
            '/exit - завершити роботу з ботом'
        ))

    def list_languages(self, message):
        logging.debug("Надсилаю список мов")
        markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
        for lang in self.languages:
            markup.add(lang)
        self.bot.send_message(message.chat.id, 'Оберіть мову програмування:', reply_markup=markup)
        self.bot.register_next_step_handler(message, self.choose_language)

    def choose_language(self, message):
        chosen_language = message.text
        if chosen_language in self.languages:
            self.user_data[message.chat.id]['language'] = chosen_language
            self.bot.send_message(
                message.chat.id,
                f'Ви обрали {chosen_language}. Для перегляду уроків скористайтесь командою /lesson.'
            )
        else:
            self.bot.send_message(
                message.chat.id,
                'Такої мови немає в списку. Будь ласка, спробуйте знову.'
            )
            self.list_languages(message)

    def choose_lesson(self, message):
        if message.chat.id not in self.user_data or 'language' not in self.user_data[message.chat.id]:
            self.bot.send_message(
                message.chat.id,
                'Будь ласка, спочатку оберіть мову програмування за допомогою /languages.'
            )
            return
        lang = self.user_data[message.chat.id]['language']
        self.show_lesson_list(message, lang)

    def show_lesson_list(self, message, lang):
        logging.debug(f"Завантажую список уроків для {lang}")
        lessons = self.db.get_lesson_list(lang)
        if not lessons:
            self.bot.send_message(message.chat.id, f'Наразі немає уроків для мови {lang}.')
            return
        lesson_list = "\n".join([f"{i+1}. {lesson[1]}" for i, lesson in enumerate(lessons)])
        self.bot.send_message(
            message.chat.id,
            f'Уроки для {lang}:\n{lesson_list}\nВведіть номер уроку, який хочете переглянути.'
        )
        self.bot.register_next_step_handler(message, self.show_lesson, lessons, lang)

    def show_lesson(self, message, lessons, lang):
        try:
            lesson_index = int(message.text) - 1
            if 0 <= lesson_index < len(lessons):
                lesson_parts = self.db.get_lesson(lang, lesson_index + 1)
                if lesson_parts:
                    for part in lesson_parts:
                        self.send_message_with_retry(message.chat.id, part)
                    self.bot.send_message(
                        message.chat.id,
                        'Щоб продовжити натисніть /continue. Для тесту /quiz. Щоб вийти /exit.'
                    )
                    self.user_data[message.chat.id]['lesson_index'] = lesson_index
                else:
                    self.bot.send_message(message.chat.id, 'Урок не знайдено.')
            else:
                self.bot.send_message(message.chat.id, 'Неправильний номер уроку. Спробуйте ще раз.')
                self.bot.register_next_step_handler(message, self.show_lesson, lessons, lang)
        except ValueError:
            self.bot.send_message(message.chat.id, 'Введіть цифру уроку:')
            self.bot.register_next_step_handler(message, self.show_lesson, lessons, lang)

    def continue_lesson(self, message):
        data = self.user_data.get(message.chat.id, {})
        if 'language' not in data or 'lesson_index' not in data:
            self.bot.send_message(message.chat.id, 'Спочатку оберіть мову за допомогою /languages.')
            return
        lang = data['language']
        index = data['lesson_index'] + 1
        lessons = self.db.get_lesson_list(lang)
        if index < len(lessons):
            parts = self.db.get_lesson(lang, index + 1)
            for part in parts:
                self.send_message_with_retry(message.chat.id, part)
            self.bot.send_message(
                message.chat.id,
                'Щоб продовжити натисніть /continue. Для тесту /quiz. Щоб вийти /exit.'
            )
            self.user_data[message.chat.id]['lesson_index'] = index
        else:
            self.bot.send_message(
                message.chat.id,
                'Це був останній урок. Для тесту натисніть /quiz, для виходу /exit.'
            )

    def start_quiz(self, message):
        lang = self.user_data.get(message.chat.id, {}).get('language')
        if not lang:
            self.bot.send_message(message.chat.id, 'Спочатку оберіть мову за допомогою /languages.')
            return
        quiz_link = self.db.get_quiz(lang)
        if quiz_link:
            self.bot.send_message(message.chat.id, f'Ось ваше посилання на тест:\n{quiz_link}')
        else:
            self.bot.send_message(message.chat.id, f'Тестів для {lang} наразі немає.')

    def exit_bot(self, message):
        self.bot.send_message(message.chat.id, 'Дякуємо за використання! До нових зустрічей.')

    def register_handlers(self):
        self.bot.message_handler(commands=['start'])(self.send_welcome)
        self.bot.message_handler(commands=['help'])(self.send_help)
        self.bot.message_handler(commands=['languages'])(self.list_languages)
        self.bot.message_handler(commands=['lesson'])(self.choose_lesson)
        self.bot.message_handler(commands=['continue'])(self.continue_lesson)
        self.bot.message_handler(commands=['quiz'])(self.start_quiz)
        self.bot.message_handler(commands=['exit'])(self.exit_bot)

    def run(self):
        logging.debug("Ініціалізація бази даних")
        self.db.init_db()

        logging.debug("Завантаження уроків і тестів")
        self.db.load_lessons_from_files("/lessons")
        self.db.load_quizzes({
            "JavaScript": "https://itproger.com/test/javascript#google_vignette",
            "Java": "https://itproger.com/practice/java",
            "Python": "https://itproger.com/practice/python",
            "C++": "https://itproger.com/practice/cpp",
            "C#": "https://itproger.com/practice/csharp",
            "SQL": "https://itproger.com/practice/sql",
        })

        self.bot.delete_webhook()
        logging.debug("Запуск polling")
        self.bot.polling(none_stop=True)

if __name__ == "__main__":
    logging.debug("Запуск Telegram бота")
    telegram_bot = TelegramBot(TOKEN)
    telegram_bot.run()
