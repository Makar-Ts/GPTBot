import sys
import configparser

CONFIG_PATH = sys.path[0] + "\\settings.ini"

config = configparser.ConfigParser()
config.read(CONFIG_PATH)

TOKEN = config["Keys"]["telegram_bot_token"].replace('"', "")
OPENAI_API_KEY = config["Keys"]["open_ai_api_key"].replace('"', "")

import telebot
import message_operator
import gpt_requester
import logger
import atexit
import time
from threading import Thread

bot = telebot.TeleBot(TOKEN)
gpt = gpt_requester.GPTRequester(OPENAI_API_KEY)
log = logger.Logger()
thread_counter = 0

operator = message_operator.MessageOperator(log, bot, gpt, sys.path[0], CONFIG_PATH)

#События получения сообщений-----------------------------------------------------------------
@bot.message_handler(content_types=['text', 'voice', 'photo'])
def get_messages(message): #при получении сообщения
    global thread_counter
    thread_counter += 1
    
    log.log(thread_counter, f"new thread with user id {message.from_user.id}")
    mes_thread = Thread(target=operator.message, args=(message,thread_counter,)) #запуск оператора сообщений в отдельном потоке
    mes_thread.start()

atexit.register(log.close_log) #при закрытии процесса

while True:
    try:
        bot.polling(none_stop=True) #запрос к телеграму о новых сообщениях
    except Exception as _ex:
        log.log(-1, f"Update connection")
        time.sleep(1)