from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = "8807056466:AAH8g7hz1n3i9DTeePDAALiM-yRV6z7PCnc"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Сәлем! Бот жұмыс істеп тұр.")

app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))

print("Bot started...")
app.run_polling()
