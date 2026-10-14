import telebot
import sqlite3
import os
import time
from telebot import types

# ==== НАСТРОЙКИ ====
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')  # Токен берем из переменных Railway
ADMIN_ID = int(os.environ.get('BOT_ADMIN_ID', 0))  # Твой ID тоже из переменных

if not BOT_TOKEN:
    print("ОШИБКА: TELEGRAM_BOT_TOKEN не установлен!")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

# ==== БАЗА ДАННЫХ ====
def init_db():
    conn = sqlite3.connect('subscribers.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (chat_id INTEGER PRIMARY KEY)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS answers (
        user_id INTEGER, 
        username TEXT, 
        answer TEXT, 
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

def add_user(chat_id):
    conn = sqlite3.connect('subscribers.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (chat_id) VALUES (?)', (chat_id,))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect('subscribers.db')
    cursor = conn.cursor()
    cursor.execute('SELECT chat_id FROM users')
    users = cursor.fetchall()
    conn.close()
    return users

# ==== КОМАНДЫ ====
@bot.message_handler(commands=['start'])
def start(message):
    add_user(message.chat.id)
    bot.send_message(
        message.chat.id,
        "🔥 Ты подписан на афиши ОРСК ПАТИ 14+!\n\nТеперь ты будешь получать все анонсы тусовок первым. 🎉"
    )

@bot.message_handler(commands=['send'])
def send_broadcast(message):
    if message.from_user.id != ADMIN_ID:
        return
    
    text_to_send = message.text.replace('/send ', '').strip()
    if not text_to_send:
        bot.send_message(message.chat.id, "Напиши текст афиши после команды /send")
        return

    markup = types.InlineKeyboardMarkup(row_width=3)
    btn_yes = types.InlineKeyboardButton("✅ Приду", callback_data="answer_yes")
    btn_maybe = types.InlineKeyboardButton("🤔 Подумаю", callback_data="answer_maybe")
    btn_no = types.InlineKeyboardButton("❌ Не смогу", callback_data="answer_no")
    markup.add(btn_yes, btn_maybe, btn_no)

    users = get_all_users()
    success = 0
    for user in users:
        try:
            bot.send_message(user[0], text_to_send, reply_markup=markup)
            success += 1
            time.sleep(0.05)
        except Exception as e:
            print(f"Ошибка у {user[0]}: {e}")

    bot.send_message(message.chat.id, f"✅ Рассылка отправлена {success} из {len(users)}.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('answer_'))
def handle_answer(call):
    answer = call.data.replace('answer_', '')
    user_id = call.from_user.id
    username = call.from_user.username or call.from_user.first_name

    conn = sqlite3.connect('subscribers.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO answers (user_id, username, answer) VALUES (?, ?, ?)', 
                   (user_id, username, answer))
    conn.commit()
    conn.close()

    answers = {'yes': '✅ Ты придёшь!', 'maybe': '🤔 Ты подумаешь.', 'no': '❌ Ты не сможешь.'}
    bot.answer_callback_query(call.id, answers.get(answer, 'Ответ учтён'))
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)

@bot.message_handler(commands=['stats'])
def stats(message):
    if message.from_user.id != ADMIN_ID:
        return
    
    conn = sqlite3.connect('subscribers.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM answers WHERE answer='yes'")
    yes = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM answers WHERE answer='maybe'")
    maybe = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM answers WHERE answer='no'")
    no = cursor.fetchone()[0]
    conn.close()
    
    bot.send_message(
        message.chat.id,
        f"📊 СТАТИСТИКА\n\n👥 Подписчиков: {total_users}\n\n✅ Приду: {yes}\n🤔 Подумаю: {maybe}\n❌ Не смогу: {no}"
    )

# ==== ЗАПУСК ====
if __name__ == '__main__':
    init_db()
    print("Бот запущен...")
    bot.polling(none_stop=True)