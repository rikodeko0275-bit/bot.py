import random
import requests
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes
)

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
    url = (
        "https://api.coingecko.com/api/v3/"
        "simple/price?ids=bitcoin&vs_currencies=usd"
    )

    data = requests.get(url, timeout=10).json()

    return float(data["bitcoin"]["usd"])


async def start(update: Update,
                context: ContextTypes.DEFAULT_TYPE):

    text = (
        "🤖 Deko Trade Predictor Bot\n\n"
        "Командалар:\n"
        "/price - BTC бағасы\n"
        "/predict\n"
        "/predict 1m\n"
        "/predict 5m\n"
        "/predict 15m\n"
        "/stats"
    )

    await update.message.reply_text(text)


async def price(update: Update,
                context: ContextTypes.DEFAULT_TYPE):

    try:
        price = get_btc_price()

        await update.message.reply_text(
            f"₿ BTC/USDT\n\n"
            f"Price: ${price:,.2f}"
        )

    except Exception as e:
        await update.message.reply_text(
            f"Қате:\n{e}"
        )


async def predict(update: Update,
                  context: ContextTypes.DEFAULT_TYPE):

    global active_prediction

    try:
        now = datetime.now()

        if (
            active_prediction is not None
            and now < active_prediction["end_time"]
        ):

            remaining = int(
                (
                    active_prediction["end_time"]
                    - now
                ).total_seconds()
            )

            await update.message.reply_text(
                f"⏳ Белсенді болжам бар\n\n"
                f"Prediction: "
                f"{active_prediction['prediction']}\n"
                f"Қалған уақыт: "
                f"{remaining} сек"
            )
            return

        timeframe = "1m"

        if context.args:
            timeframe = context.args[0].lower()

        if timeframe not in TIMEFRAMES:
            await update.message.reply_text(
                "/predict\n"
                "/predict 1m\n"
                "/predict 5m\n"
                "/predict 15m"
            )
            return

        seconds = TIMEFRAMES[timeframe]

        price = get_btc_price()

        up = random.randint(40, 75)
        down = random.randint(10, 50)

        if up + down > 95:
            down = 95 - up

        sideways = 100 - up - down

        if up >= down and up >= sideways:
            prediction = "🟢 UP"
        elif down >= up and down >= sideways:
            prediction = "🔴 DOWN"
        else:
            prediction = "🟡 SIDEWAYS"

        end_time = now + timedelta(
            seconds=seconds
        )

        active_prediction = {
            "prediction": prediction,
            "start_price": price,
            "end_time": end_time,
            "timeframe": timeframe
        }

        text = (
            f"₿ BTC/USDT\n\n"
            f"Current Price: "
            f"${price:,.2f}\n\n"
            f"UP: {up}%\n"
            f"DOWN: {down}%\n"
            f"SIDEWAYS: {sideways}%\n\n"
            f"Prediction: "
            f"{prediction}\n"
            f"Timeframe: "
            f"{timeframe}\n"
            f"Valid Until:\n"
            f"{end_time.strftime('%H:%M:%S')}"
        )

        await update.message.reply_text(text)

        context.job_queue.run_once(
            auto_check,
            seconds,
            chat_id=update.effective_chat.id
        )

    except Exception as e:
        await update.message.reply_text(
            f"Қате:\n{e}"
        )


async def auto_check(
        context: ContextTypes.DEFAULT_TYPE
):

    global active_prediction
    global stats

    if active_prediction is None:
        return

    try:
        start_price = (
            active_prediction["start_price"]
        )

        end_price = get_btc_price()

        if end_price > start_price:
            actual = "🟢 UP"
        elif end_price < start_price:
            actual = "🔴 DOWN"
        else:
            actual = "🟡 SIDEWAYS"

        prediction = (
            active_prediction["prediction"]
        )

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
            "⏰ Prediction Finished\n\n"
            f"Prediction: "
            f"{prediction}\n"
            f"Actual: "
            f"{actual}\n\n"
            f"Start Price: "
            f"${start_price:,.2f}\n"
            f"End Price: "
            f"${end_price:,.2f}\n\n"
            f"Result: {result}"
        )

        await context.bot.send_message(
            chat_id=context.job.chat_id,
            text=text
        )

        active_prediction = None

    except Exception as e:
        await context.bot.send_message(
            chat_id=context.job.chat_id,
            text=f"Қате:\n{e}"
        )


async def stats_command(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
):

    total = stats["total"]

    accuracy = 0

    if total > 0:
        accuracy = round(
            stats["correct"]
            / total
            * 100,
            2
        )

    text = (
        "📊 Statistics\n\n"
        f"Total: {stats['total']}\n"
        f"Correct: {stats['correct']}\n"
        f"Incorrect: {stats['incorrect']}\n"
        f"Neutral: {stats['neutral']}\n"
        f"Accuracy: {accuracy}%"
    )

    await update.message.reply_text(text)


app = (
    Application.builder()
    .token(TOKEN)
    .build()
)

app.add_handler(
    CommandHandler("start", start)
)
app.add_handler(
    CommandHandler("price", price)
)
app.add_handler(
    CommandHandler("predict", predict)
)
app.add_handler(
    CommandHandler("stats", stats_command)
)

print("Bot started...")
app.run_polling()
