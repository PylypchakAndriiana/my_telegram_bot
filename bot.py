import telebot
from config import TOKEN
from database import Database
import time

class TelegramBot:
    def __init__(self, token):
        self.bot = telebot.TeleBot(token)
        self.db = Database()
        self.user_data = {}
        self.languages = ["Java", "JavaScript", "Python", "C++", "C#", "SQL"]
        self.register_handlers()

    def send_message_with_retry(self, chat_id, text, retries=5):
        for i in range(retries):
            try:
                self.bot.send_message(chat_id, text)
                return
            except Exception as e:
                print(f"Помилка при надсиланні повідомлення: {e}. Спроба {i+1} з {retries}")
                time.sleep(5)  # Зачекати перед наступною спробою
        print(f"Не вдалося надіслати повідомлення після {retries} спроб")

    def send_welcome(self, message):
        self.bot.send_message(message.chat.id, 'Вітаю! Я Ваш персональний довідник з програмування. '
                                               'Перш ніж розпочати, давайте познайомитись! Як до Вас звертатися?')
        self.bot.register_next_step_handler(message, self.get_user_name)

    def get_user_name(self, message):
        user_name = message.text
        self.user_data[message.chat.id] = {'name': user_name}
        self.db.save_user_name(message.chat.id, user_name)
        self.bot.send_message(message.chat.id, f'{user_name}, пропоную ознайомитись із опціями боту, у цьому Вам допоможе команда /help.')

    def send_help(self, message):
        self.bot.send_message(message.chat.id, 'Щоб нам з тобою поладнати потрібно правила завчати та інструкції читати! \n'
                                               'Отож:\n'
                                               '/languages - дає можливість обрати мову з якою хочете працювати далі\n'
                                               '/lesson - надає відео та текстові матеріали для вивчення мов\n'
                                               '/quiz - тести до обраної теми для кращого освоєння вивченого\n'
                                               '/exit - завершує роботу з ботом')

    def list_languages(self, message):
        markup =telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
        for lang in self.languages:
            markup.add(lang)
        self.bot.send_message(message.chat.id, 'Оберіть мову програмування:', reply_markup=markup)
        self.bot.register_next_step_handler(message, self.choose_language)

    def choose_language(self, message):
        chosen_language = message.text
        if chosen_language in self.languages:
            self.user_data[message.chat.id]['language'] = chosen_language
            self.bot.send_message(message.chat.id, f'Ви обрали {chosen_language}. Тепер ви можете переглянути доступні уроки за допомогою /lesson.')
        else:
            self.bot.send_message(message.chat.id, 'Вибачте, такої мови немає в списку. Будь ласка, спробуйте знову.')
            self.list_languages(message)

    def choose_lesson(self, message):
        if message.chat.id not in self.user_data or 'language' not in self.user_data[message.chat.id]:
            self.bot.send_message(message.chat.id, 'Будь ласка, спочатку оберіть мову програмування за допомогою /languages.')
            return
        lang = self.user_data[message.chat.id]['language']
        self.show_lesson_list(message, lang)

    def show_lesson_list(self, message, lang):
        lessons = self.db.get_lesson_list(lang)
        if not lessons:
            self.bot.send_message(message.chat.id, f'Вибачте, але наразі немає уроків для мови {lang}.')
            return
        lesson_list = "\n".join([f"{i+1}. {lesson[1]}" for i, lesson in enumerate(lessons)])
        self.bot.send_message(message.chat.id, f'Перелік уроків для {lang}:\n{lesson_list}\n'
                                               'Оберіть потрібну Вам тему і введіть, будь ласка, цифру відповідного уроку.')
        self.bot.register_next_step_handler(message, self.show_lesson, lessons, lang)

    def show_lesson(self, message, lessons, lang):
        try:
            lesson_index = int(message.text) - 1
            if 0 <= lesson_index < len(lessons):
                lesson_parts = self.db.get_lesson(lang, lesson_index + 1)
                if lesson_parts:
                    for part in lesson_parts:
                        self.send_message_with_retry(message.chat.id, part)
                    self.bot.send_message(message.chat.id, f'Щоб продовжити вивчення і перейти до наступного уроку натисніть /continue.\n'
                                                          'Щоб почати тренування /quiz.\n'
                                                          'Щоб вийти /exit.')
                    self.user_data[message.chat.id]['lesson_index'] = lesson_index
                else:
                    self.bot.send_message(message.chat.id, 'Вибачте, урок не знайдено.')
            else:
                self.bot.send_message(message.chat.id, 'Вибачте, Ви помилилися під час введення, такого уроку не існує, спробуйте ще раз.')
                self.bot.register_next_step_handler(message, self.show_lesson, lessons, lang)
        except ValueError:
            self.bot.send_message(message.chat.id, 'Будь ласка, введіть коректну цифру уроку:')
            self.bot.register_next_step_handler(message, self.show_lesson, lessons, lang)

    def continue_lesson(self, message):
        if message.chat.id not in self.user_data or 'language' not in self.user_data[message.chat.id] or 'lesson_index' not in self.user_data[message.chat.id]:
            self.bot.send_message(message.chat.id, 'Будь ласка, спочатку оберіть мову програмування за допомогою /languages.')
            return

        lang = self.user_data[message.chat.id]['language']
        lesson_index = self.user_data[message.chat.id]['lesson_index']
        lessons = self.db.get_lesson_list(lang)
        next_lesson_index = lesson_index + 1
        if next_lesson_index < len(lessons):
            lesson_parts = self.db.get_lesson(lang, next_lesson_index + 1)
            for part in lesson_parts:
                self.send_message_with_retry(message.chat.id, part)
            self.bot.send_message(message.chat.id, f'Щоб продовжити вивчення і перейти до наступного уроку натисніть /continue.\n'
                                                  'Щоб почати тренування /quiz.\n'
                                                  'Щоб вийти /exit.')
            self.user_data[message.chat.id]['lesson_index'] = next_lesson_index
        else:
            self.bot.send_message(message.chat.id, 'Це був останній урок з цієї мови програмування.\n'
                                                  'Щоб почати тренування /quiz.\n'
                                                  'Щоб вийти /exit.')

    def start_quiz(self, message):
        if message.chat.id not in self.user_data or 'language' not in self.user_data[message.chat.id]:
            self.bot.send_message(message.chat.id, 'Будь ласка, спочатку оберіть мову програмування за допомогою /languages.')
            return
        lang = self.user_data[message.chat.id]['language']
        quiz_link = self.db.get_quiz(lang)
        if quiz_link:
            self.bot.send_message(message.chat.id, f'Ось ваше посилання на тест для {lang}:\n{quiz_link}')
        else:
            self.bot.send_message(message.chat.id, f'Вибачте, наразі немає тестів для мови {lang}.')

    def exit_bot(self, message):
        self.bot.send_message(message.chat.id, 'Дякуємо за використання бота. До побачення!')

    def register_handlers(self):
        self.bot.message_handler(commands=['start'])(self.send_welcome)
        self.bot.message_handler(commands=['help'])(self.send_help)
        self.bot.message_handler(commands=['languages'])(self.list_languages)
        self.bot.message_handler(commands=['lesson'])(self.choose_lesson)
        self.bot.message_handler(commands=['continue'])(self.continue_lesson)
        self.bot.message_handler(commands=['quiz'])(self.start_quiz)
        self.bot.message_handler(commands=['exit'])(self.exit_bot)

    def run(self):
        self.db.init_db()
        base_path = "D:/Курсова/lessons"
        self.db.load_lessons_from_files(base_path)
        quiz_links = {
            "JavaScript":"https://itproger.com/test/javascript#google_vignette",
            "Java": "https://itproger.com/practice/java",
            "Python": "https://itproger.com/practice/python",
            "C++": "https://itproger.com/practice/cpp",
            "C#": "https://itproger.com/practice/csharp",
            "SQL": "https://itproger.com/practice/sql",
        }
        self.db.load_quizzes(quiz_links)
        self.bot.polling(none_stop=True)

if __name__ == "__main__":
    telegram_bot = TelegramBot(TOKEN)
    telegram_bot.run()

