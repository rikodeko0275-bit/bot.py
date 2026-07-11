import random
import requests
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = "8807056466:AAH8g7hz1n3i9DTeePDAALiM-yRV6z7PCnc"

active_prediction = None

stats = {
    "total": 0,
    "correct": 0,
    "incorrect": 0,
    "neutral": 0
}

TIMEFRAMES = {
    "1m": 60,
    "5m": 300,
    "15m": 900
}


def get_btc_price():
    url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
    data = requests.get(url, timeout=10).json()
    return float(data["price"])


def generate_prediction():
    up = random.randint(35, 65)
    down = random.randint(20, 50)

    if up + down > 90:
        down = 90 - up

    sideways = 100 - up - down

    if up >= down and up >= sideways:
        prediction = "🟢 UP"
    elif down >= up and down >= sideways:
        prediction = "🔴 DOWN"
    else:
        prediction = "🟡 SIDEWAYS"

    return prediction, up, down, sideways


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🤖 Deko Trade Predictor\n\n"
        "/price - BTC бағасы\n"
        "/predict 1m\n"
        "/predict 5m\n"
        "/predict 15m\n"
        "/check - нәтижені тексеру\n"
        "/stats - статистика"
    )
    await update.message.reply_text(text)


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = get_btc_price()
        await update.message.reply_text(
            f"₿ BTC/USDT\n\n"
            f"Current Price: ${price:,.2f}"
        )
    except Exception as e:
        await update.message.reply_text(f"Қате:\n{e}")


async def predict(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global active_prediction

    now = datetime.now()

    if active_prediction:
        if now < active_prediction["end_time"]:
            remaining = int(
                (active_prediction["end_time"] - now).total_seconds()
            )

            await update.message.reply_text(
                f"⏳ Болжам әлі белсенді\n\n"
                f"Prediction: {active_prediction['prediction']}\n"
                f"Қалды: {remaining} сек"
            )
            return

    timeframe = "1m"

    if context.args:
        timeframe = context.args[0].lower()

    if timeframe not in TIMEFRAMES:
        await update.message.reply_text(
            "Қолдану:\n"
            "/predict 1m\n"
            "/predict 5m\n"
            "/predict 15m"
        )
        return

    seconds = TIMEFRAMES[timeframe]
    price = get_btc_price()

    prediction, up, down, sideways = generate_prediction()

    end_time = now + timedelta(seconds=seconds)

    active_prediction = {
        "prediction": prediction,
        "start_price": price,
        "end_time": end_time,
        "timeframe": timeframe
    }

    text = (
        f"₿ BTC/USDT\n\n"
        f"Price: ${price:,.2f}\n\n"
        f"🟢 UP: {up}%\n"
        f"🔴 DOWN: {down}%\n"
        f"🟡 SIDEWAYS: {sideways}%\n\n"
        f"Prediction: {prediction}\n"
        f"Timeframe: {timeframe}\n"
        f"Valid Until: "
        f"{end_time.strftime('%H:%M:%S')}"
    )

    await update.message.reply_text(text)


async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global active_prediction
    global stats

    if not active_prediction:
        await update.message.reply_text(
            "Белсенді болжам жоқ."
        )
        return

    now = datetime.now()

    if now < active_prediction["end_time"]:
        remaining = int(
            (active_prediction["end_time"] - now).total_seconds()
        )

        await update.message.reply_text(
            f"⏳ Әлі аяқталған жоқ\n"
            f"Қалды: {remaining} сек"
        )
        return

    start_price = active_prediction["start_price"]
    end_price = get_btc_price()

    if end_price > start_price:
        actual = "🟢 UP"
    elif end_price < start_price:
        actual = "🔴 DOWN"
    else:
        actual = "🟡 SIDEWAYS"

    prediction = active_prediction["prediction"]

    stats["total"] += 1

    if prediction == actual:
        result = "✅ Correct"
        stats["correct"] += 1
    elif actual == "🟡 SIDEWAYS":
        result = "⚪ Neutral"
        stats["neutral"] += 1
    else:
        result = "❌ Incorrect"
        stats["incorrect"] += 1

    text = (
        f"Prediction: {prediction}\n"
        f"Actual: {actual}\n\n"
        f"Start Price: ${start_price:,.2f}\n"
        f"End Price: ${end_price:,.2f}\n\n"
        f"Result: {result}"
    )

    active_prediction = None

    await update.message.reply_text(text)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total = stats["total"]

    accuracy = 0
    if total > 0:
        accuracy = round(
            stats["correct"] / total * 100,
            2
        )

    text = (
        f"📊 Statistics\n\n"
        f"Total: {stats['total']}\n"
        f"Correct: {stats['correct']}\n"
        f"Incorrect: {stats['incorrect']}\n"
        f"Neutral: {stats['neutral']}\n"
        f"Accuracy: {accuracy}%"
    )

    await update.message.reply_text(text)


app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("price", price))
app.add_handler(CommandHandler("predict", predict))
app.add_handler(CommandHandler("check", check))
app.add_handler(CommandHandler("stats", stats_command))

print("Bot started...")
app.run_polling()
