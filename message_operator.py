import sys
import configparser
import data_handler
import json
import datetime
import subprocess

class MessageOperator:
    def __init__(self, log, bot, gpt, home_path, config_path):
        self.log = log
        self.bot = bot
        self.gpt = gpt
        
        config = configparser.ConfigParser()
        config.read(config_path)
        
        self.SAVED_VOICES_FOLDER_PATH = str(home_path)+config["Paths"]["downloaded_voices"].replace('"', "")
        self.MP3_VOICES_FOLDER_PATH = str(home_path)+config["Paths"]["converted_voices"].replace('"', "")
        self.MAX_MESSAGES_LENGTH = int(config["SQLiteDatabase"]["messages_max_size"].replace('"', ""))
        self.GENERATED_IMG_FOLDER_PATH = str(home_path)+config["Paths"]["generated_images"].replace('"', "")
        self.SAVED_IMG_FOLDER_PATH = str(home_path)+config["Paths"]["saved_images"].replace('"', "")
        
    #Обработка сообщений------------------------------------------------------------------
    def message(self, message, thread_id):
        """Обрабатывает сообщение

        Args:
            message (telebot.message): класс сообщения
            thread_id (int): id потока
        """        
        id = message.from_user.id #получение id пользователя
        base = data_handler.Speaker(thread_id, self.log)
        
        try:
            is_registered = base.has_user(id) #проверка зарегестрирован ли пользователь
            
            if (is_registered == 0 and (message.content_type == "text" and message.text != "/start")): 
                self.bot.send_message(id, "Для начала введите /start")
                
                self.log.log(thread_id, f"close thread")
                return
            
            if (message.content_type == "text"):
                if (message.text == "/start"): #если сообщение /start
                    if (is_registered != 0):
                        self.bot.send_message(id, "Приветствую вас снова!")
                    else:
                        base.create_new_user(id) #создание нового пользователя с id
                        
                        self.bot.send_message(id, "Приветствую вас")
                elif (message.text[:6] == "/model"):
                    if (len(message.text.split(" ")) == 1): #если только /model
                        self.bot.send_message(id, f"Ваша текущая модель: {base.get_user_model(id)}")
                    else:
                        if (self.gpt.has_model(message.text.split(" ")[1])): #проверка существует ли модель
                            base.set_user_model(id, message.text[7:]) #установка модели
                            
                            base.clear_messages(id) #очистка истории сообщений
                            self.bot.send_message(id, f"Ваша текущая модель: {base.get_user_model(id)}")
                        else:
                            if (message.text.split(" ")[1] == "all"): #если после стоит all
                                self.bot.send_message(id, "Вот модели которые можно использовать: " + ", ".join(gpt.all_models()))
                            else:
                                self.bot.send_message(id, f"Такой модели не существует!")
                                self.bot.send_message(id, f"Ваша текущая модель: {base.get_user_model(id)}")
                elif (message.text == "/clear"):
                    if (base.is_busy(id) == 0): #проверка идет ли сейчас обработка запроса
                        base.clear_messages(id)
                        
                        self.bot.send_message(id, "История успешно очищена")
                    else:
                        self.bot.send_message(id, "Вы не можете очистить историю во время выполнения запроса")
                else:
                    if (base.is_busy(id) == 0): #проверка идет ли сейчас обработка запроса
                        model = base.get_user_model(id) #получение текущей модели
                        
                        if (model == "DALL-E"): #если генерация изображений
                            base.set_busy(id, 1) #установка статуса занят
                            self.bot.send_message(id, "Генерация изображения...")
                            self.log.log(thread_id, "LOG {0}: generate image".format(id))
                            
                            name = str(datetime.datetime.now()).replace(":", ".")+".png" #имя состоящее из даты+расширения
                            
                            self.gpt.create_img(message.text, self.GENERATED_IMG_FOLDER_PATH+name) #делаем запрос на генерацию
                            
                            self.bot.send_photo(id, photo=open(self.GENERATED_IMG_FOLDER_PATH+name, 'rb')) #открываем и отправляем фото
                            base.set_busy(id, 0)
                        else: #если генерация текста
                            messages = base.get_messages(id) #получаем историю сообщений
                            
                            messages.append({"role": 'user', "content": message.text}) #добавляем запрос пользователя в историю
                            
                            base.set_busy(id, 1)
                            ask = self.gpt.ask(model, question=message.text, messages=messages) #делаем запрос
                            
                            messages.append({"role": 'system', "content": ask}) #добавляем ответ gpt в историю
                            
                            self.bot.send_message(id, ask)
                            
                            weight = len(json.dumps(messages).encode('utf-8')) #проверка веса файла
                            if (weight > self.MAX_MESSAGES_LENGTH):
                                base.clear_messages(id)
                                self.log.log(thread_id, "MEMORY OVERFLOW {0}: messages forcibly cleared (weight: {1})".format(id, weight))
                                self.bot.send_message(id, "Ваша история сообщений была принудительно удалена для предотвращения переполнения")
                            elif (weight > self.MAX_MESSAGES_LENGTH*0.90):
                                base.set_messages(id, messages)
                                self.log.log(thread_id, "MEMORY OVERFLOW {0}: less than 10per of free space left (weight: {1})".format(id, weight))
                                self.bot.send_message(id, "Советуем вам очистить историю сообщений командой /clear (так как у вас осталось меньше 10% свободного места), иначе, при переполнении, она будет удалена принудительно")
                            else:
                                base.set_messages(id, messages)
                            
                            base.set_busy(id, 0)
                    else:
                        self.bot.send_message(id, "Ваш запрос обрабатывается...")
            elif (message.content_type == "voice"):
                if (base.is_busy(id) == 0):
                    base.set_busy(id, 1)
                    #--------------------------------------------------------------------------------------------
                    
                    file_info = self.bot.get_file(message.voice.file_id) #получение ссылки на файл
                    downloaded_file = self.bot.download_file(file_info.file_path) #скачивание файла
                    name = str(datetime.datetime.now()).replace(":", ".").replace(" ", "_")+f"id{id}"+".ogg"
                    
                    self.log.log(thread_id, "LOG {0}: audio downloaded".format(id))
                    #--------------------------------------------------------------------------------------------
                    
                    with open(self.SAVED_VOICES_FOLDER_PATH+name, 'wb') as new_file:
                        new_file.write(downloaded_file) #сохранение файла
                    
                    self.log.log(thread_id, "LOG {0}: audio saved".format(id))
                    #--------------------------------------------------------------------------------------------
                    
                    src_filename = self.SAVED_VOICES_FOLDER_PATH+name
                    dest_filename = self.MP3_VOICES_FOLDER_PATH+str(datetime.datetime.now()).replace(":", ".").replace(" ", "_")+f"id{id}"+".wav"
                    
                    process = subprocess.run(f"ffmpeg.exe -i {src_filename} {dest_filename}") #преобразование в mp3 при помощи ffmpeg
                    #--------------------------------------------------------------------------------------------
                    
                    self.log.log(thread_id, "LOG {0}: audio converted".format(id))
                    
                    self.bot.send_message(id, "Декодирование аудио...")
                    self.log.log(thread_id, "LOG {0}: decode audio".format(id))
                    
                    text = self.gpt.decode_voice(open(dest_filename, 'rb')) #декодирование аудио
                    #--------------------------------------------------------------------------------------------
                    
                    self.bot.send_message(id, text)
                    base.set_busy(id, 0)
                else:
                    self.bot.send_message(id, "Ваш запрос обрабатывается...")
            elif (message.content_type == "photo"):
                if (base.is_busy(id) == 0):
                    model = base.get_user_model(id)
                    
                    if (model == "DALL-E"):
                        base.set_busy(id, 1)
                        
                        raw = str(datetime.datetime.now()).replace(":", ".").replace(" ", "_")+f"id{id}"
                        name = self.SAVED_IMG_FOLDER_PATH+raw+".png"
                        output_name = self.GENERATED_IMG_FOLDER_PATH+raw+".png"
                        file_info = self.bot.get_file(message.photo[2].file_id)
                        downloaded_file = self.bot.download_file(file_info.file_path)
                        with open(name,'wb') as new_file:
                            new_file.write(downloaded_file)
                        
                        self.gpt.edit_image(message.caption, name, output_name)
                        
                        self.bot.send_photo(id, photo=open(output_name, 'rb')) #открываем и отправляем фото
                        base.set_busy(id, 0)
                    else:
                        self.bot.send_message(id, "Текущая модель не может обрабатывать фотографии")
                else:
                    self.bot.send_message(id, "Ваш запрос обрабатывается...")
        except BaseException as e:
            self.log.log(thread_id, "ERROR {0}: {1}".format(id, e))
            
            base.set_busy(id, 0)
            
            if (str(e).find("That model is currently overloaded with other requests") != -1):
                self.bot.send_message(id, "Извините но сейчас сервера OpenAI перегружены. Попробуйте позже")
            else: 
                self.bot.send_message(id, "Извините произошла ошибка. Свяжитесь со мной: @makar_ts")
        
        self.log.log(thread_id, f"close thread")   