import sys

TOKEN = '6180393695:AAEVa0QP6FSDSAWPeANU2_20O8YJCyMuw8Q'
OPENAI_API_KEY = "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"
GENERATED_IMG_FOLDER_PATH = str(sys.path[0])+"\\images\\"
MAX_MESSAGES_LENGTH = 40000

import telebot
import data_handler
import gpt_requester
import atexit
import json
import datetime


bot = telebot.TeleBot(TOKEN)
base = data_handler.Speaker()
gpt = gpt_requester.GPTRequester(OPENAI_API_KEY)


@bot.message_handler(content_types=['text'])
def get_text_messages(message): #при получении сообщения
    id = message.from_user.id #получение id пользователя
    
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
                    base.log("LOG {0}: generate image".format(id))
                    
                    name = str(datetime.datetime.now()).replace(":", ".")+".png" #имя состоящее из даты+расширения
                    
                    gpt.create_img(message.text, GENERATED_IMG_FOLDER_PATH+name) #делаем запрос на генерацию
                    
                    bot.send_photo(id, photo=open(GENERATED_IMG_FOLDER_PATH+name, 'rb'))
                    base.set_busy(id, 0)
                else:
                    messages = base.get_messages(id)
                    
                    messages.append({"role": 'user', "content": message.text})
                    
                    base.set_busy(id, 1)
                    ask = gpt.ask(message.text, model, messages)
                    
                    messages.append({"role": 'system', "content": ask})
                    
                    bot.send_message(id, ask)
                    
                    weight = len(json.dumps(messages).encode('utf-8'))
                    if (weight > MAX_MESSAGES_LENGTH):
                        base.clear_messages(id)
                        base.log("MEMORY OVERFLOW {0}: messages forcibly cleared (weight: {1})".format(id, weight))
                        bot.send_message(id, "Ваша история сообщений была принудительно удалена для предотвращения переполнения")
                    elif (weight > MAX_MESSAGES_LENGTH*0.90):
                        base.set_messages(id, messages)
                        base.log("MEMORY OVERFLOW {0}: less than 10per of free space left (weight: {1})".format(id, weight))
                        bot.send_message(id, "Советуем вам очистить историю сообщений командой /clear (так как у вас осталось меньше 10% свободного места), иначе, при переполнении, она будет удалена принудительно")
                    else:
                        base.set_messages(id, messages)
                    
                    base.set_busy(id, 0)
            else:
                bot.send_message(id, "Ваш запрос обрабатывается...")
        else:
            bot.send_message(id, "Для начала введите /start")
    except BaseException as e:
        base.log("ERROR {0}: {1}".format(id, e))
        
        base.set_busy(id, 0)
        
        if (str(e).find("That model is currently overloaded with other requests") != -1):
            bot.send_message(id, "Извините но сейчас сервера OpenAI перегружены. Попробуйте позже")
        else: 
            bot.send_message(id, "Извините произошла ошибка. Свяжитесь со мной: @makar_ts")
            

atexit.register(base.close_log)
bot.polling(none_stop=True, interval=0)