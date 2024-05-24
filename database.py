import sqlite3
import os
from docx import Document

DB_NAME = 'lessons.db'

class Database:
    def __init__(self, db_name=DB_NAME):
        self.db_name = db_name
        self.init_db()

    def init_db(self):
        if os.path.exists(self.db_name):
            os.remove(self.db_name)
        
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            language TEXT NOT NULL,
            lesson_number INTEGER NOT NULL,
            lesson_title TEXT NOT NULL,
            lesson_content TEXT NOT NULL
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            user_name TEXT NOT NULL
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS quizzes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            language TEXT NOT NULL,
            quiz_link TEXT NOT NULL
        )
        ''')
        
        conn.commit()
        conn.close()

    def load_lessons_from_files(self, base_path):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM lessons')
        
        lessons_data = {
            "Java": [
                "Знайомство з мовою Java",
                "Основи мови Java: Типи даних, змінні, масиви",
                "Операції",
                "Оператори",
                "ООП мовою Java",
                "Класи",
                "Ієрархія класів"
            ],
            "JavaScript": [
                "Що треба знати?",
                "Змінні та коментарі",
                "Оператори",
                "Умови",
                "Функції",
                "Події",
                "Зміна зображення"
            ],
            "Python": [
                "Знайомство з мовою Python",
                "Основи мови",
                "Числові дані",
                "Винятки",
                "Організація розгалужень",
                "Циклічні оператори",
                "Структури даних",
                "Функції",
                "Файли"
            ],
            "C#": [
                "Ознайомлення",
                "Коментарі",
                "Розміщення екземплярів у пам’яті",
                "Змінні",
                "Типізація",
                "Оператори та вирази",
                "Пріоритетність операторів",
                "Оператори для умов",
                "Інструкції"
            ],
            "C++": [
                "Знайомство з мовою",
                "Типи даних",
                "Константи",
                "Змінні величини",
                "Поняття потоку",
                "Операції",
                "Умови",
                "Функції",
                "Циклічні алгоритми",
                "Рекурсія",
                "Обробка послідовностей",
                "Структурна організація програм"
            ],
            "SQL": [
                "Ознайомлення",
                "Типи даних",
                "Прості запити",
                "Статичні функції",
                "Внесення змін",
                "Зміна визначення таблиці"
            ]
        }
        
        for language, lessons in lessons_data.items():
            lang_path = os.path.join(base_path, language)
            if os.path.isdir(lang_path):
                for lesson_number, lesson_title in enumerate(lessons, start=1):
                    lesson_file = f"{lesson_number}.docx"
                    lesson_path = os.path.join(lang_path, lesson_file)
                    if os.path.exists(lesson_path):
                        lesson_content = self.read_docx(lesson_path)
                        cursor.execute('''
                        INSERT INTO lessons (language, lesson_number, lesson_title, lesson_content)
                        VALUES (?, ?, ?, ?)
                        ''', (language, lesson_number, lesson_title, lesson_content))
        
        conn.commit()
        conn.close()

    def read_docx(self, filepath):
        doc = Document(filepath)
        return '\n'.join([para.text for para in doc.paragraphs])

    def split_text(self, text, max_length=4096):
        words = text.split()
        parts = []
        current_part = ''
        for word in words:
            if len(current_part) + len(word) + 1 > max_length:
                parts.append(current_part)
                current_part = word
            else:
                current_part += ' ' + word
        parts.append(current_part)
        return parts

    def get_lesson_list(self, language):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('SELECT lesson_number, lesson_title FROM lessons WHERE language=? ORDER BY lesson_number', (language,))
        lessons = cursor.fetchall()
        conn.close()
        return [(lesson[0], lesson[1]) for lesson in lessons]

    def get_lesson(self, language, lesson_index):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('SELECT lesson_content FROM lessons WHERE language=? AND lesson_number=?', (language, lesson_index))
        lesson = cursor.fetchone()
        conn.close()
        return self.split_text(lesson[0]) if lesson else None

    def save_user_name(self, user_id, user_name):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO users (user_id, user_name) VALUES (?, ?)', (user_id, user_name))
        conn.commit()
        conn.close()

    def get_user_name(self, user_id):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('SELECT user_name FROM users WHERE user_id=?', (user_id,))
        user_name = cursor.fetchone()
        conn.close()
        return user_name[0] if user_name else None

    def load_quizzes(self, quiz_links):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM quizzes')
        
        for language, link in quiz_links.items():
            cursor.execute('''
            INSERT INTO quizzes (language, quiz_link)
            VALUES (?, ?)
            ''', (language, link))
        
        conn.commit()
        conn.close()

    def get_quiz(self, language):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('SELECT quiz_link FROM quizzes WHERE language=?', (language,))
        quiz = cursor.fetchone()
        conn.close()
        return quiz[0] if quiz else None
