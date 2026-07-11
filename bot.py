from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import requests
import pandas as pd
from datetime import datetime, timedelta

TOKEN = "8807056466:AAH8g7hz1n3i9DTeePDAALiM-yRV6z7PCnc"

active_prediction = None

stats = {
    "total": 0,
    "correct": 0,
    "incorrect": 0,
    "neutral": 0
}


def now_kz():
    return datetime.utcnow() + timedelta(hours=5)


def get_btc_price():
    url = (
        "https://api.coingecko.com/api/v3/"
        "simple/price?ids=bitcoin&vs_currencies=usd"
    )

    response = requests.get(
        url,
        timeout=20,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    response.raise_for_status()

    data = response.json()

    return float(data["bitcoin"]["usd"])


def get_market_data():
    url = (
        "https://api.coingecko.com/api/v3/"
        "coins/bitcoin/market_chart"
        "?vs_currency=usd&days=1&interval=hourly"
    )

    response = requests.get(
        url,
        timeout=20,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    response.raise_for_status()

    data = response.json()

    prices = []

    for item in data["prices"]:
        prices.append(float(item[1]))

    return pd.Series(prices)


def calculate_rsi(prices, period=14):
    delta = prices.diff()

    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return float(rsi.iloc[-1])


def ai_predict():
    prices = get_market_data()

    current_price = float(prices.iloc[-1])

    ema20 = float(
        prices.ewm(span=20).mean().iloc[-1]
    )

    ema50 = float(
        prices.ewm(span=50).mean().iloc[-1]
    )

    rsi = calculate_rsi(prices)

    up_score = 0
    down_score = 0

    reasons = []

    if ema20 > ema50:
        up_score += 2
        reasons.append("EMA20 > EMA50")
    else:
        down_score += 2
        reasons.append("EMA20 < EMA50")

    if rsi < 30:
        up_score += 2
        reasons.append("RSI Oversold")
    elif rsi > 70:
        down_score += 2
        reasons.append("RSI Overbought")

    if prices.iloc[-1] > prices.iloc[-2]:
        up_score += 1
        reasons.append("Price Momentum UP")
    else:
        down_score += 1
        reasons.append("Price Momentum DOWN")

    if up_score > down_score:
        prediction = "🟢 UP"
    elif down_score > up_score:
        prediction = "🔴 DOWN"
    else:
        prediction = "🟡 SIDEWAYS"

    total = up_score + down_score

    if total == 0:
        up = 50
        down = 50
    else:
        up = round(up_score / total * 100)
        down = round(down_score / total * 100)

    sideways = max(
        0,
        100 - up - down
    )

    return {
        "prediction": prediction,
        "price": current_price,
        "ema20": round(ema20, 2),
        "ema50": round(ema50, 2),
        "rsi": round(rsi, 2),
        "up": up,
        "down": down,
        "sideways": sideways,
        "reasons": reasons
    }


async def start(update: Update,
                context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Deko Trade Predictor Bot\n\n"
        "/price - BTC бағасы\n"
        "/predict - AI болжамы\n"
        "/check - Нәтижені тексеру\n"
        "/stats - Статистика"
    )


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
        result = ai_predict()

        now = now_kz()

        end_time = (
            now
            + timedelta(minutes=1)
        )

        active_prediction = {
            "prediction":
                result["prediction"],
            "start_price":
                result["price"],
            "end_time":
                end_time
        }

        reasons = "\n".join(
            result["reasons"]
        )

        text = (
            f"₿ BTC/USDT\n\n"
            f"Current Price: "
            f"${result['price']:,.2f}\n\n"
            f"EMA20: {result['ema20']}\n"
            f"EMA50: {result['ema50']}\n"
            f"RSI: {result['rsi']}\n\n"
            f"UP: {result['up']}%\n"
            f"DOWN: {result['down']}%\n"
            f"SIDEWAYS: {result['sideways']}%\n\n"
            f"Prediction:\n"
            f"{result['prediction']}\n\n"
            f"AI Analysis:\n"
            f"{reasons}\n\n"
            f"Valid Until:\n"
            f"{end_time.strftime('%H:%M:%S')}"
        )

        await update.message.reply_text(text)

    except Exception as e:
        if "429" in str(e):
            await update.message.reply_text(
                "⏳ CoinGecko уақытша шектеді.\n"
                "1-2 минуттан кейін қайта көріңіз."
            )
        else:
            await update.message.reply_text(
                f"Қате:\n{e}"
            )


async def check(update: Update,
                context: ContextTypes.DEFAULT_TYPE):
    global active_prediction
    global stats

    if active_prediction is None:
        await update.message.reply_text(
            "Белсенді болжам жоқ."
        )
        return

    now = now_kz()

    if now < active_prediction["end_time"]:
        remaining = int(
            (
                active_prediction["end_time"]
                - now
            ).total_seconds()
        )

        await update.message.reply_text(
            f"⏳ Қалған уақыт:\n"
            f"{remaining} секунд"
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

        await update.message.reply_text(
            f"Prediction: {prediction}\n"
            f"Actual: {actual}\n\n"
            f"Start Price: ${start_price:,.2f}\n"
            f"End Price: ${end_price:,.2f}\n\n"
            f"Result: {result}"
        )

        active_prediction = None

    except Exception as e:
        await update.message.reply_text(
            f"Қате:\n{e}"
        )


async def stats_command(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    total = stats["total"]

    accuracy = 0

    if total > 0:
        accuracy = round(
            stats["correct"]
            / total
            * 100,
            2
        )

    await update.message.reply_text(
        "📊 Statistics\n\n"
        f"Total: {stats['total']}\n"
        f"Correct: {stats['correct']}\n"
        f"Incorrect: {stats['incorrect']}\n"
        f"Neutral: {stats['neutral']}\n"
        f"Accuracy: {accuracy}%"
    )


app = (
    Application.builder()
    .token(TOKEN)
    .build()
)

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("price", price))
app.add_handler(CommandHandler("predict", predict))
app.add_handler(CommandHandler("check", check))
app.add_handler(CommandHandler("stats", stats_command))

print("Bot started...")
app.run_polling()
