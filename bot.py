import os
from telegram.ext import Application

TOKEN = os.getenv("BOT_TOKEN")

app = Application.builder().token(TOKEN).build()

print("Bot started...")
app.run_polling()
