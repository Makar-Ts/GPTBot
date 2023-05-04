import datetime
import sys

class Logger:
    def __init__(self):
        date = str(datetime.datetime.now()).replace(":", ".")
        
        self.logfile = open(sys.path[0] + f"\\logs\\log {date}.txt", "w")
    def log(self, thread_id, message):
        print(f"THREAD {thread_id} {message}")
        
        self.logfile.write(f"THREAD {thread_id} {datetime.datetime.now()} {message}\n")
    def close_log(self):
        self.logfile.close()