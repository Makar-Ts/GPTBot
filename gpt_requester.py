MODELS_ENDPOINTS = {#"gpt-4":"ChatCompletion", "gpt-4-0314":"ChatCompletion", 
                    #"gpt-4-32k":"ChatCompletion", "gpt-4-32k-0314":"ChatCompletion", 
                    "gpt-3.5-turbo":"ChatCompletion", "gpt-3.5-turbo-0301":"ChatCompletion", 
                    "davinci":"Completion", "code-davinci-edit-001":"Edit", 
                    "text-davinci-edit-001":"Edit", "DALL-E":"Image"} #Доступные модели модель:режим обработки

import openai
import urllib

class GPTRequester:
    def __init__(self, openai_api_key):
        openai.api_key = openai_api_key #задаем api ключ
    
    def ask(self, model, question=None, messages=None, text=None) -> str:
        """Генерация текста по запросу или истории сообщений
           |    model    - модель которая используется в генерации (функция all_models())
           |   *question - запрос (нужен только для моделей с режимом Completion или Edit)
           |   *messages - история запросов (нужен только для моделей с режимом ChatCompletion)
           |   *text     - тект для изменения (нужен только для моделей с режимом Edit)"""
        
        mode = MODELS_ENDPOINTS[model]
        answer = "nothing generated"
        
        if (mode == "ChatCompletion"):
            response = openai.ChatCompletion.create(
                model = model,
                messages = messages,
                temperature = 0  
            )
            answer = response['choices'][0]['message']['content'] #выуживаем ответ
        elif (mode == "Completion"):
            response = openai.Completion.create(
                engine=model,
                prompt=question,
                temperature=0
            )
            answer = response.choices[0].text #выуживаем ответ
        elif (mode == "Edit"):
            response = openai.Edit.create(
                model=model,
                input=text,
                instruction=question
            )
            answer = response['choices'][0]['text']
        
        return answer
    
    def create_img(self, promt, img_path) -> None:
        """Генерация изображения по запросу
           |    promt    - запрос
           |    img_path - путь для сохранения изображения"""
        
        response = openai.Image.create(
            prompt=promt,
            n=1,
            size="1024x1024"
        )
        image_url = response['data'][0]['url'] #получаем url картинки
        
        resource = urllib.request.urlopen(image_url) #открываем картинку
        out = open(img_path, 'wb') 
        out.write(resource.read()) #скачиваем и записываем на компьютер
        out.close()
    
    def edit_image(self, promt, input_img_path, output_img_path) -> None:
        """Генерация изображения по запросу
           |    promt           - запрос
           |    input_img_path  - путь до входного изображения
           |    output_img_path - путь для сохранения изображения"""
        
        openai.Image.create_edit(
            image=open(input_img_path, "rb"),
            prompt=promt,
            size="1024x1024"
        )
        image_url = response['data'][0]['url'] #получаем url картинки
        
        resource = urllib.request.urlopen(image_url) #открываем картинку
        out = open(output_img_path, 'wb') 
        out.write(resource.read()) #скачиваем и записываем на компьютер
        out.close()
    
    def decode_voice(self, file) -> str:
        """Декодирование голоса в текст
           |    file - файл mp3 или wav для декодирования"""
        
        transcript = openai.Audio.transcribe("whisper-1", 
                                             file) #запрашиваем транскрипцию
        
        return transcript['text']
    
    def has_model(self, model) -> bool:
        """Проверка есть ли данная модель в списке доступных
           |    model - модель для проверки"""
        
        if model in MODELS_ENDPOINTS:
            return True
        
        return False
    
    def all_models(self) -> list:
        """Возвращает названия всех доступных моделей"""
        
        return MODELS_ENDPOINTS.keys()
    
                