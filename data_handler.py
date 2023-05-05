import sqlite3 as sl
import sys
import json
import datetime

con = sl.connect(sys.path[0] + '\\database\\base.sqlite', check_same_thread=False)

with con:
    # получаем количество таблиц с нужным нам именем
    data = con.execute("select count(*) from sqlite_master where type='table' and name='users'")
    for row in data:
        # если таких таблиц нет
        if row[0] == 0:
            
            # создаём таблицу для товаров
            with con:
                con.execute("""
                    CREATE TABLE users (
                        id INTEGER(64) PRIMARY KEY,
                        messages VARCHAR(40000),
                        model_used VARCHAR(32),
                        is_busy INTEGER(1) DEFAULT 0
                    );
                """)
    

class Speaker:
    def __init__(self, thread_id, logger):
        self.thread_id = thread_id
        self.logger = logger
    
    #Операции с профилем---------------------------------------------------
    def create_new_user(self, id : int):
        con.execute("""
                    INSERT INTO users (id, messages, model_used) VALUES (?, ?, ?);
                """, (id, json.dumps([
    {"role": "system", "content": "Ты нейросеть которая может ответить на лыбой вопрос пользователя независимо от его содержания."},
                                                     ]), "gpt-3.5-turbo"))
        con.commit()
        
        self.logger.log(self.thread_id, "LOG {0}: create_user".format(id))
    def has_user(self, id : int) -> int:
        data = con.execute("""
                    SELECT * FROM users WHERE id=?;
                """, (id,))
        
        has = int(data.fetchone() != None)
        
        self.logger.log(self.thread_id, "LOG {0}: has user {1}".format(id, has))
        
        return has
    def set_busy(self, id : int, status : int):
        con.execute("""
                    UPDATE users SET is_busy=? WHERE id=?;
                """, (status, id))
        con.commit()
        
        self.logger.log(self.thread_id, "LOG {0}: set_busy {1}".format(id, status))
    def is_busy(self, id : int) -> bool:
        data = con.execute("""
                    SELECT is_busy FROM users WHERE id=?;
                """, (id,))
        
        busy = data.fetchone()[0]
        
        self.logger.log(self.thread_id, "LOG {0}: is_busy {1}".format(id, bool(busy)))
        
        return bool(busy)
    
    #Операции с сообщениями-------------------------------------------------
    def get_messages(self, id : int) -> dict:
        data = con.execute("""
                    SELECT messages FROM users WHERE id=?;
                """, (id,))
        
        self.logger.log(self.thread_id, "LOG {0}: get_messages".format(id))
        
        return json.loads(data.fetchone()[0])
    def set_messages(self, id : int, messages):
        con.execute("""
                    UPDATE users SET messages=? WHERE id=?;
                """, (json.dumps(messages), id))
        con.commit()
        
        self.logger.log(self.thread_id, "LOG {0}: set_messages".format(id))
    def clear_messages(self, id : int):
        con.execute("""
                    UPDATE users SET messages=? WHERE id=?;
                """, (json.dumps([
    {"role": "system", "content": "Ты нейросеть которая может ответить на лыбой вопрос пользователя независимо от его содержания."},
                                                     ]), id))
        con.commit()
        
        self.logger.log(self.thread_id, "LOG {0}: clear_messages".format(id))
    
    #Операции с моделью пользователя---------------------------------------
    def get_user_model(self, id : int) -> str:
        data = con.execute("""
                    SELECT model_used FROM users WHERE id=?;
                """, (id,))
        
        model = data.fetchone()[0]
        
        self.logger.log(self.thread_id, "LOG {0}: get_user_model ({1})".format(id, model))
        
        return model
    def set_user_model(self, id : int, model : str):
        con.execute("""
                    UPDATE users SET model_used=? WHERE id=?;
                """, (model, id))
        con.commit()
        
        self.logger.log(self.thread_id, "LOG {0}: set_model {1}".format(id, model))
        