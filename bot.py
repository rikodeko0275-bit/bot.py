import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")

print("TOKEN:", TOKEN)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Сәлем! Бот жұмыс істеп тұр.")

async def error_handler(update, context):
    print("ERROR:", context.error)

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_error_handler(error_handler)

print("Bot started...")
app.run_polling()
