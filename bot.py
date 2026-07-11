import os

TOKEN = os.getenv("BOT_TOKEN")
print("TOKEN =", TOKEN)
print("Bot started...")
app.run_polling()
