import os

TOKEN = os.getenv("BOT_TOKEN")

print("TOKEN:", TOKEN)

from telegram.ext import Application

app = Application.builder().token(TOKEN).build()

print("Bot started...")
app.run_polling()
