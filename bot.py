import requests
import pandas as pd
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = "8807056466:AAH8g7hz1n3i9DTeePDAALiM-yRV6z7PCnc"

stats = {
    "total": 0,
    "correct": 0,
    "incorrect": 0
}


def get_btc_price():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
    data = requests.get(url, timeout=10).json()
    return float(data["bitcoin"]["usd"])

def get_market_data():
    url = (
        "https://api.coingecko.com/api/v3/coins/"
        "bitcoin/market_chart"
        "?vs_currency=usd&days=1&interval=minutely"
    )

    data = requests.get(url, timeout=20).json()

    prices = data["prices"]

    closes = []

    for item in prices[-100:]:
        closes.append(float(item[1]))

    return pd.Series(closes)
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

    prices = get_binance_data()

    current_price = float(prices.iloc[-1])

    ema20 = float(prices.ewm(span=20).mean().iloc[-1])
    ema50 = float(prices.ewm(span=50).mean().iloc[-1])

    rsi = calculate_rsi(prices)

    up_score = 0
    down_score = 0

    reasons = []

    if ema20 > ema50:
        up_score += 2
        reasons.append("EMA20 > EMA50 ✅")

    else:
        down_score += 2
        reasons.append("EMA20 < EMA50 ❌")

    if rsi < 30:
        up_score += 2
        reasons.append("RSI Oversold ✅")

    elif rsi > 70:
        down_score += 2
        reasons.append("RSI Overbought ❌")

    else:
        reasons.append(f"RSI = {round(rsi,2)}")

    if prices.iloc[-1] > prices.iloc[-2]:
        up_score += 1
        reasons.append("Price Momentum UP ✅")
    else:
        down_score += 1
        reasons.append("Price Momentum DOWN ❌")

    total = up_score + down_score

    if total == 0:
        up_probability = 50
        down_probability = 50
    else:
        up_probability = round(up_score / total * 100)
        down_probability = round(down_score / total * 100)

    sideways_probability = max(
        0,
        100 - up_probability - down_probability
    )

    if up_score > down_score:
        prediction = "🟢 UP"
    elif down_score > up_score:
        prediction = "🔴 DOWN"
    else:
        prediction = "🟡 SIDEWAYS"

    return {
        "prediction": prediction,
        "price": current_price,
        "rsi": round(rsi, 2),
        "ema20": round(ema20, 2),
        "ema50": round(ema50, 2),
        "up": up_probability,
        "down": down_probability,
        "sideways": sideways_probability,
        "reasons": reasons
    }


async def start(update: Update,
                context: ContextTypes.DEFAULT_TYPE):

    text = (
        "🤖 Deko Trade Predictor Bot\n\n"
        "Командалар:\n"
        "/price - BTC бағасы\n"
        "/predict - AI болжамы\n"
        "/stats - Статистика"
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

    try:
        result = ai_predict()

        reasons = "\n".join(result["reasons"])

        text = (
            f"₿ BTC/USDT\n\n"
            f"Current Price: "
            f"${result['price']:,.2f}\n\n"

            f"EMA20: {result['ema20']}\n"
            f"EMA50: {result['ema50']}\n"
            f"RSI: {result['rsi']}\n\n"

            f"UP Probability: "
            f"{result['up']}%\n"

            f"DOWN Probability: "
            f"{result['down']}%\n"

            f"SIDEWAYS Probability: "
            f"{result['sideways']}%\n\n"

            f"Prediction: "
            f"{result['prediction']}\n\n"

            f"AI Analysis:\n"
            f"{reasons}"
        )

        await update.message.reply_text(text)

    except Exception as e:
        await update.message.reply_text(
            f"Қате:\n{e}"
        )


async def stats_command(update: Update,
                        context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        f"📊 Statistics\n\n"
        f"Total: {stats['total']}\n"
        f"Correct: {stats['correct']}\n"
        f"Incorrect: {stats['incorrect']}"
    )


app = (
    Application.builder()
    .token(TOKEN)
    .build()
)

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("price", price))
app.add_handler(CommandHandler("predict", predict))
app.add_handler(CommandHandler("stats", stats_command))

print("Bot started...")
app.run_polling()
