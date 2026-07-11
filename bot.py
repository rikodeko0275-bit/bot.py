import requests
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = "8807056466:AAH8g7hz1n3i9DTeePDAALiM-yRV6z7PCnc"

import os
TOKEN = os.getenv("BOT_TOKEN")

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


def get_klines(interval="1m", limit=100):
    url = (
        f"https://api.binance.com/api/v3/klines"
        f"?symbol=BTCUSDT"
        f"&interval={interval}"
        f"&limit={limit}"
    )

    data = requests.get(url, timeout=10).json()

    closes = []

    for candle in data:
        closes.append(float(candle[4]))

    return closes


def calculate_ema(prices, period):
    multiplier = 2 / (period + 1)
    ema = prices[0]

    for price in prices[1:]:
        ema = (price - ema) * multiplier + ema

    return ema


def calculate_rsi(prices, period=14):
    gains = []
    losses = []

    for i in range(1, len(prices)):
        change = prices[i] - prices[i - 1]

        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi


def analyze_market(interval):
    prices = get_klines(interval)

    ema9 = calculate_ema(prices, 9)
    ema21 = calculate_ema(prices, 21)
    rsi = calculate_rsi(prices)

    up = 50
    down = 50

    if ema9 > ema21:
        up += 20
        down -= 20
    else:
        down += 20
        up -= 20

    if rsi > 60:
        up += 10
        down -= 10
    elif rsi < 40:
        down += 10
        up -= 10

    up = max(0, min(90, up))
    down = max(0, min(90, down))
    sideways = 100 - up - down

    if up >= down and up >= sideways:
        prediction = "🟢 UP"
    elif down >= up and down >= sideways:
        prediction = "🔴 DOWN"
    else:
        prediction = "🟡 SIDEWAYS"

    return prediction, up, down, sideways, ema9, ema21, rsi


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🤖 Deko Trade Predictor Bot\n\n"
        "Командалар:\n"
        "/price - BTC бағасы\n"
        "/predict 1m\n"
        "/predict 5m\n"
        "/predict 15m\n"
        "/check - Нәтижені тексеру\n"
        "/stats - Статистика"
    )

    await update.message.reply_text(text)


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = get_btc_price()

        await update.message.reply_text(
            f"₿ BTC/USDT\n\nPrice: ${price}"
        )

    except Exception as e:
        await update.message.reply_text(f"Қате:\n{e}")


async def predict(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global active_prediction

    try:
        now = datetime.now()

        if (
            active_prediction is not None
            and now < active_prediction["end_time"]
        ):
            remaining = int(
                (active_prediction["end_time"] - now).total_seconds()
            )

            await update.message.reply_text(
                f"⏳ Prediction Active\n\n"
                f"Prediction: {active_prediction['prediction']}\n"
                f"Time Remaining: {remaining} sec"
            )
            return

        timeframe = "1m"

        if len(context.args) > 0:
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

        prediction, up, down, sideways, ema9, ema21, rsi = analyze_market(
            timeframe
        )

        end_time = now + timedelta(seconds=seconds)

        active_prediction = {
            "prediction": prediction,
            "start_price": price,
            "end_time": end_time,
            "timeframe": timeframe
        }

        text = (
            f"₿ BTC/USDT\n\n"
            f"Current Price: ${price}\n\n"
            f"EMA9: {ema9:.2f}\n"
            f"EMA21: {ema21:.2f}\n"
            f"RSI: {rsi:.2f}\n\n"
            f"UP Probability: {up}%\n"
            f"DOWN Probability: {down}%\n"
            f"SIDEWAYS Probability: {sideways}%\n\n"
            f"Prediction: {prediction}\n"
            f"Timeframe: {timeframe}\n"
            f"Valid Until: "
            f"{end_time.strftime('%H:%M:%S')}"
        )

        await update.message.reply_text(text)

    except Exception as e:
        await update.message.reply_text(f"Қате:\n{e}")


async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global active_prediction, stats

    if active_prediction is None:
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
            f"⏳ Prediction Active\n"
            f"Time Remaining: {remaining} sec"
        )
        return

    try:
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
            f"Start Price: ${start_price}\n"
            f"End Price: ${end_price}\n\n"
            f"Result: {result}"
        )

        active_prediction = None

        await update.message.reply_text(text)

    except Exception as e:
        await update.message.reply_text(f"Қате:\n{e}")


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

app.run_polling(
    poll_interval=1,
    timeout=20,
    bootstrap_retries=-1,
    drop_pending_updates=True
    )
