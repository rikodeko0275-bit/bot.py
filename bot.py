import os
import time

TOKEN = os.getenv("BOT_TOKEN")

print("TOKEN =", TOKEN)
print("Bot started!")

while True:
    print("Working...")
    time.sleep(30)
