import data_handler

bot = data_handler.Speaker(-1, None)

while True:
    inp = int(input())
    
    if inp == 0: break
    
    print(bot.get_messages(inp))