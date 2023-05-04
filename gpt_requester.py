MODELS_ENDPOINTS = {#"gpt-4":"ChatCompletion", "gpt-4-0314":"ChatCompletion", 
                    #"gpt-4-32k":"ChatCompletion", "gpt-4-32k-0314":"ChatCompletion", 
                    "gpt-3.5-turbo":"ChatCompletion", "gpt-3.5-turbo-0301":"ChatCompletion", 
                    "davinci":"Completion", "text-babbage-001":"Completion", 
                    "text-ada-001":"Completion", "DALL-E":"Image"} #Доступные модели модель:режим обработки

import openai
import urllib

class GPTRequester:
    def __init__(self, openai_api_key):
        openai.api_key = openai_api_key #задаем api ключ
    
    def ask(self, question, model, messages):
        mode = MODELS_ENDPOINTS[model]
        answer = "nothing generated"
        
        if (mode == "ChatCompletion"):
            completion = openai.ChatCompletion.create(
                model = model,
                messages = messages,
                temperature = 0  
            )
            answer = completion['choices'][0]['message']['content'] #выуживаем ответ
        elif (mode == "Completion"):
            response = openai.Completion.create(
                engine=model,
                prompt=question,
                temperature=0
            )
            answer = response.choices[0].text #выуживаем ответ
        
        return answer
    
    def create_img(self, promt, img_path):
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
    
    def decode_voice(self, file):
        transcript = openai.Audio.transcribe("whisper-1", 
                                             file)
        
        return transcript['text']
    
    def has_model(self, model):
        if model in MODELS_ENDPOINTS:
            return True
        
        return False
    
    def all_models(self):
        return MODELS_ENDPOINTS.keys()
    
                