import sys
import os
import configparser

config = configparser.ConfigParser()
config.read(sys.path[0] + "\\settings.ini")

TOKEN = config["Keys"]["telegram_bot_token"].replace('"', "")
OPENAI_API_KEY = config["Keys"]["open_ai_api_key"].replace('"', "")
GENERATED_IMG_FOLDER_PATH = str(sys.path[0])+config["Paths"]["generated_images"].replace('"', "")
SAVED_VOICES_FOLDER_PATH = str(sys.path[0])+config["Paths"]["downloaded_voices"].replace('"', "")
MP3_VOICES_FOLDER_PATH = str(sys.path[0])+config["Paths"]["converted_voices"].replace('"', "")
MAX_MESSAGES_LENGTH = int(config["SQLiteDatabase"]["messages_max_size"].replace('"', ""))

import telebot
import data_handler
import gpt_requester
import logger
import atexit
import json
import datetime
import time
from threading import Thread
import subprocess

bot = telebot.TeleBot(TOKEN)
gpt = gpt_requester.GPTRequester(OPENAI_API_KEY)
log = logger.Logger()
thread_counter = 0

#Обработка сообщений------------------------------------------------------------------
def message_operator(message, thread_id):
    id = message.from_user.id #получение id пользователя
    base = data_handler.Speaker(thread_id, log)
    
    try:
        is_registered = base.has_user(id) #проверка зарегестрирован ли пользователь
        
        if (message.text == "/start"): #если сообщение /start
            if (is_registered != 0):
                bot.send_message(id, "Приветствую вас снова!")
            else:
                base.create_new_user(id) #создание нового пользователя с id
                
                bot.send_message(id, "Приветствую вас")
        elif (message.text[:6] == "/model" and is_registered != 0):
            if (len(message.text.split(" ")) == 1): #если только /model
                bot.send_message(id, f"Ваша текущая модель: {base.get_user_model(id)}")
            else:
                if (gpt.has_model(message.text.split(" ")[1])): #проверка существует ли модель
                    base.set_user_model(id, message.text[7:]) #установка модели
                    
                    base.clear_messages(id) #очистка истории сообщений
                    bot.send_message(id, f"Ваша текущая модель: {base.get_user_model(id)}")
                else:
                    if (message.text.split(" ")[1] == "all"): #если после стоит all
                        bot.send_message(id, "Вот модели которые можно использовать: " + ", ".join(gpt.all_models()))
                    else:
                        bot.send_message(id, f"Такой модели не существует!")
                        bot.send_message(id, f"Ваша текущая модель: {base.get_user_model(id)}")
        elif (message.text == "/clear" and is_registered != 0):
            if (base.is_busy(id) == 0): #проверка идет ли сейчас обработка запроса
                base.clear_messages(id)
                
                bot.send_message(id, "История успешно очищена")
            else:
                bot.send_message(id, "Вы не можете очистить историю во время выполнения запроса")
        elif (is_registered != 0):
            if (base.is_busy(id) == 0): #проверка идет ли сейчас обработка запроса
                model = base.get_user_model(id) #получение текущей модели
                
                if (model == "DALL-E"): #если генерация изображений
                    base.set_busy(id, 1) #установка статуса занят
                    bot.send_message(id, "Генерация изображения...")
                    log.log(thread_id, "LOG {0}: generate image".format(id))
                    
                    name = str(datetime.datetime.now()).replace(":", ".")+".png" #имя состоящее из даты+расширения
                    
                    gpt.create_img(message.text, GENERATED_IMG_FOLDER_PATH+name) #делаем запрос на генерацию
                    
                    bot.send_photo(id, photo=open(GENERATED_IMG_FOLDER_PATH+name, 'rb')) #открываем и отправляем фото
                    base.set_busy(id, 0)
                else: #если генерация текста
                    messages = base.get_messages(id) #получаем историю сообщений
                    
                    messages.append({"role": 'user', "content": message.text}) #добавляем запрос пользователя в историю
                    
                    base.set_busy(id, 1)
                    ask = gpt.ask(model, question=message.text, messages=messages) #делаем запрос
                    
                    messages.append({"role": 'system', "content": ask}) #добавляем ответ gpt в историю
                    
                    bot.send_message(id, ask)
                    
                    weight = len(json.dumps(messages).encode('utf-8')) #проверка веса файла
                    if (weight > MAX_MESSAGES_LENGTH):
                        base.clear_messages(id)
                        log.log(thread_id, "MEMORY OVERFLOW {0}: messages forcibly cleared (weight: {1})".format(id, weight))
                        bot.send_message(id, "Ваша история сообщений была принудительно удалена для предотвращения переполнения")
                    elif (weight > MAX_MESSAGES_LENGTH*0.90):
                        base.set_messages(id, messages)
                        log.log(thread_id, "MEMORY OVERFLOW {0}: less than 10per of free space left (weight: {1})".format(id, weight))
                        bot.send_message(id, "Советуем вам очистить историю сообщений командой /clear (так как у вас осталось меньше 10% свободного места), иначе, при переполнении, она будет удалена принудительно")
                    else:
                        base.set_messages(id, messages)
                    
                    base.set_busy(id, 0)
            else:
                bot.send_message(id, "Ваш запрос обрабатывается...")
        else:
            bot.send_message(id, "Для начала введите /start")
    except BaseException as e:
        log.log(thread_id, "ERROR {0}: {1}".format(id, e))
        
        base.set_busy(id, 0)
        
        if (str(e).find("That model is currently overloaded with other requests") != -1):
            bot.send_message(id, "Извините но сейчас сервера OpenAI перегружены. Попробуйте позже")
        else: 
            bot.send_message(id, "Извините произошла ошибка. Свяжитесь со мной: @makar_ts")
    
    log.log(thread_id, f"close thread")   


#Расшифровка голосовых-----------------------------------------------------------------------
def voice_operator(message, thread_id):
    id = message.from_user.id #получение id пользователя
    base = data_handler.Speaker(thread_id, log)
    
    try:
        is_registered = base.has_user(id)
        
        if (is_registered):
            if (base.is_busy(id) == 0):
                base.set_busy(id, 1)
                #--------------------------------------------------------------------------------------------
                
                file_info = bot.get_file(message.voice.file_id) #получение ссылки на файл
                downloaded_file = bot.download_file(file_info.file_path) #скачивание файла
                name = str(datetime.datetime.now()).replace(":", ".").replace(" ", "_")+f"id{id}"+".ogg"
                
                log.log(thread_id, "LOG {0}: audio downloaded".format(id))
                #--------------------------------------------------------------------------------------------
                
                with open(SAVED_VOICES_FOLDER_PATH+name, 'wb') as new_file:
                    new_file.write(downloaded_file) #сохранение файла
                
                log.log(thread_id, "LOG {0}: audio saved".format(id))
                #--------------------------------------------------------------------------------------------
                
                src_filename = SAVED_VOICES_FOLDER_PATH+name
                dest_filename = MP3_VOICES_FOLDER_PATH+str(datetime.datetime.now()).replace(":", ".").replace(" ", "_")+f"id{id}"+".wav"
                
                process = subprocess.run(f"ffmpeg.exe -i {src_filename} {dest_filename}") #преобразование в mp3 при помощи ffmpeg
                #--------------------------------------------------------------------------------------------
                
                log.log(thread_id, "LOG {0}: audio converted".format(id))
                
                bot.send_message(id, "Декодирование аудио...")
                log.log(thread_id, "LOG {0}: decode audio".format(id))
                
                text = gpt.decode_voice(open(dest_filename, 'rb')) #декодирование аудио
                #--------------------------------------------------------------------------------------------
                
                bot.send_message(id, text)
                base.set_busy(id, 0)
            else:
                bot.send_message(id, "Ваш запрос обрабатывается...")
        else:
            bot.send_message(id, "Для начала введите /start")
    except BaseException as e:
        log.log(thread_id, "ERROR {0}: {1}".format(id, e))
        
        base.set_busy(id, 0)
        
        if (str(e).find("That model is currently overloaded with other requests") != -1):
            bot.send_message(id, "Извините но сейчас сервера OpenAI перегружены. Попробуйте позже")
        else: 
            bot.send_message(id, "Извините произошла ошибка. Свяжитесь со мной: @makar_ts")
    
    log.log(thread_id, f"close thread") 


#События получения сообщений-----------------------------------------------------------------
@bot.message_handler(content_types=['text'])
def get_text_messages(message): #при получении сообщения
    global thread_counter
    thread_counter += 1
    
    log.log(thread_counter, f"new thread with user id {message.from_user.id}")
    mes_thread = Thread(target=message_operator, args=(message,thread_counter,)) #запуск оператора сообщений в отдельном потоке
    mes_thread.start()

@bot.message_handler(content_types=['voice'])
def voice_handler(message):
    global thread_counter
    thread_counter += 1
    
    log.log(thread_counter, f"new thread with user id {message.from_user.id}")
    mes_thread = Thread(target=voice_operator, args=(message,thread_counter,)) #запуск оператора сообщений в отдельном потоке
    mes_thread.start()


atexit.register(log.close_log) #при закрытии процесса

while True:
    try:
        bot.polling(none_stop=True) #запрос к телеграму о новых сообщениях
    except Exception as _ex:
        log.log(-1, f"Update connection")
        time.sleep(1)