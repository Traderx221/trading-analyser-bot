import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, InputMediaPhoto
import yfinance as yf
import matplotlib.pyplot as plt
import pandas as pd
import pandas_ta as ta
import numpy as np
import io
import warnings
import os
import threading
from flask import Flask

warnings.filterwarnings('ignore')

# Get token from environment variables or use the provided one
BOT_TOKEN = os.getenv('BOT_TOKEN', '8851924440:AAHDMyHQ24L9LtV5Pz4HXzmfIABB9ueLDjQ')
bot = telebot.TeleBot(BOT_TOKEN)

# Categories including Forex
CATEGORIES = {
    "forex": ("💱 Forex & Currencies", ["EURUSD=X", "USDJPY=X", "GBPUSD=X", "AUDUSD=X", "USDCAD=X", "USDCHF=X", "NZDUSD=X", "USDAED=X", "EURAED=X", "USDPKR=X", "USDINR=X", "DX-Y.NYB"]),
    "tech": ("📱 Tech & Telecom", ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "NFLX", "ADBE", "CRM", "AMD", "INTC", "CSCO", "ORCL", "QCOM", "IBM", "TXN", "AVGO", "SHOP", "SNOW", "UBER", "ABNB", "PYPL", "SQ", "ROKU", "ZM", "PLTR", "U", "DOCU", "NET"]),
    "fin": ("🏦 Finance & Banking", ["JPM", "BAC", "WFC", "V", "MA", "GS", "MS", "AXP", "C", "BLK", "CB", "CME", "PGR", "USB", "PNC", "TFC", "COF", "SCHW", "SPGI", "MCO", "ICE"]),
    "health": ("🏥 Healthcare & Biotech", ["JNJ", "UNH", "PFE", "ABBV", "MRK", "TMO", "ABT", "DHR", "LLY", "BMY", "AMGN", "CVS", "GILD", "ISRG", "MDT", "ZTS", "REGN", "VRTX", "HUM", "CI"]),
    "cons": ("🛒 Consumer & Retail", ["WMT", "PG", "KO", "PEP", "COST", "MCD", "NKE", "SBUX", "TGT", "HD", "LOW", "PM", "MO", "DIS", "CMCSA", "EL", "CL", "KHC"]),
    "energy": ("⚡ Energy & Oil", ["XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "KMI", "WMB", "HAL", "HES", "BKR"]),
    "ind": ("🏭 Industrials & Auto", ["CAT", "DE", "UNP", "HON", "UPS", "FDX", "BA", "LMT", "RTX", "GE", "MMM", "EMR", "ETN", "GM", "F", "RIVN", "LCID"]),
    "crypto": ("🪙 Cryptocurrency", ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD", "ADA-USD", "DOGE-USD", "AVAX-USD", "DOT-USD", "LINK-USD", "MATIC-USD", "LTC-USD", "BCH-USD", "ATOM-USD"]),
    "etf": ("📊 Market Indices & ETFs", ["SPY", "QQQ", "DIA", "IWM", "VTI", "VOO", "ARKK", "TQQQ", "SQQQ", "UVXY", "GLD", "SLV", "USO", "TLT"])
}

def get_permanent_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("📋 Main Menu"), KeyboardButton("📊 Fast Live Quotes"))
    return markup

def get_main_menu_markup():
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = [InlineKeyboardButton(data[0], callback_data=f"cat_{cat_id}") for cat_id, data in CATEGORIES.items()]
    markup.add(*buttons)
    return markup

def get_category_markup(cat_id, page=0):
    markup = InlineKeyboardMarkup(row_width=3)
    cat_name, stocks = CATEGORIES[cat_id]
    items_per_page = 9
    start = page * items_per_page
    end = start + items_per_page
    current_stocks = stocks[start:end]

    buttons = [InlineKeyboardButton(ticker.replace('=X', ''), callback_data=f"st_{ticker}_{cat_id}") for ticker in current_stocks]
    markup.add(*buttons)

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"pg_{cat_id}_{page-1}"))
    nav_buttons.append(InlineKeyboardButton("🏠 Menu", callback_data="main_menu"))
    if end < len(stocks):
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"pg_{cat_id}_{page+1}"))

    markup.row(*nav_buttons)
    return markup

def get_chart_controls_markup(ticker, cat_id, tf_code, ctype, indicator):
    markup = InlineKeyboardMarkup(row_width=3)

    tfs = [("1min", "1 Min"), ("3min", "3 Min"), ("1D", "1 Day"), 
           ("1W", "1 Week"), ("1M", "1 Month"), ("1Y", "1 Year")]
    tf_buttons = [InlineKeyboardButton(f"✅ {label}" if code == tf_code else label, callback_data=f"ch_{ticker}_{cat_id}_{code}_{ctype}_{indicator}") for code, label in tfs]
    markup.add(*tf_buttons[:3])
    markup.add(*tf_buttons[3:])

    types = [("candlestick", "🕯️ Candlestick"), ("line", "📈 Line"), ("bar", "📊 Bar")]
    type_buttons = [InlineKeyboardButton(f"✅ {label}" if t == ctype else label, callback_data=f"ch_{ticker}_{cat_id}_{tf_code}_{t}_{indicator}") for t, label in types]
    markup.add(*type_buttons)

    inds = [("none", "🚫 No Ind."), ("sma", "📈 SMA 20"), ("ema", "📉 EMA 20"), ("bb", "📊 Bollinger"), ("rsi", "⚡ RSI 14")]
    ind_buttons = [InlineKeyboardButton(f"✅ {label}" if ind == indicator else label, callback_data=f"ch_{ticker}_{cat_id}_{tf_code}_{ctype}_{ind}") for ind, label in inds]
    markup.add(*ind_buttons[:3])
    markup.add(*ind_buttons[3:])
    
    # --- Deep Analysis Button ---
    markup.add(InlineKeyboardButton("🤖 Get Deep Signal Analysis", callback_data=f"analyze_{ticker}"))

    markup.add(InlineKeyboardButton(f"🔙 Back to {CATEGORIES[cat_id][0]}", callback_data=f"pg_{cat_id}_0"))
    return markup

# --- Advanced Technical Analysis (Signal) ---
def get_advanced_signal(symbol):
    try:
        df = yf.download(symbol, period='1y', interval='1d', progress=False)
        if df.empty:
            return "⚠️ Symbol not found or data unavailable."

        # Fix for MultiIndex Error
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)

        df.ta.rsi(length=14, append=True)
        df.ta.macd(fast=12, slow=26, signal=9, append=True)
        df.ta.sma(length=50, append=True)
        df.ta.sma(length=200, append=True)
        df.ta.bbands(length=20, std=2, append=True)

        latest = df.iloc[-1]
        try:
            latest_price = float(latest['Close'].iloc[0]) if isinstance(latest['Close'], pd.Series) else float(latest['Close'])
        except:
            latest_price = float(latest['Close'])

        rsi = latest['RSI_14']
        macd = latest['MACD_12_26_9']
        macd_signal = latest['MACDs_12_26_9']
        sma_50 = latest['SMA_50']
        sma_200 = latest['SMA_200']
        bb_lower = latest['BBL_20_2.0']
        bb_upper = latest['BBU_20_2.0']

        buy_score = sum([rsi < 30, macd > macd_signal, sma_50 > sma_200, latest_price < bb_lower])
        sell_score = sum([rsi > 70, macd < macd_signal, sma_50 < sma_200, latest_price > bb_upper])
        total_score = buy_score - sell_score
        
        if total_score >= 2: final_signal = "🟢 STRONG BUY"
        elif total_score == 1: final_signal = "🟢 BUY"
        elif total_score <= -2: final_signal = "🔴 STRONG SELL"
        elif total_score == -1: final_signal = "🔴 SELL"
        else: final_signal = "🟡 HOLD (Neutral)"

        display_symbol = symbol.replace('=X', '')
        result = f"📊 **{display_symbol.upper()} Advanced Analysis**\n"
        result += f"💰 Current Price: ${latest_price:.4f}\n\n"
        result += f"📈 **Indicators Breakdown:**\n"
        result += f"🔹 **RSI (14):** {rsi:.2f} ({'Oversold' if rsi < 30 else 'Overbought' if rsi > 70 else 'Neutral'})\n"
        result += f"🔹 **MACD:** {'Bullish 🟢' if macd > macd_signal else 'Bearish 🔴'}\n"
        result += f"🔹 **Trend (SMA):** {'Uptrend 🟢' if sma_50 > sma_200 else 'Downtrend 🔴'}\n"
        result += f"🔹 **Bollinger Bands:** {'Undervalued 🟢' if latest_price < bb_lower else 'Overvalued 🔴' if latest_price > bb_upper else 'Normal 🟡'}\n\n"
        result += f"🤖 **FINAL SIGNAL:** {final_signal}"
        return result
    except Exception as e:
        return f"Error in analysis: {e}"

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = "Welcome to *Professional Trading Bot* 📈\n\nAdvanced Candlestick charts & indicators are now active. Select from the menu:"
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_permanent_keyboard(), parse_mode="Markdown")
    bot.send_message(message.chat.id, "👇 *Main Menu:*\nChoose a category:", reply_markup=get_main_menu_markup(), parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "📋 Main Menu" or message.text == "/menu")
def show_main_menu(message):
    bot.send_message(message.chat.id, "👇 *Main Menu:*\nChoose a category:", reply_markup=get_main_menu_markup(), parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "📊 Fast Live Quotes")
def show_quick_quotes(message):
    bot.reply_to(message, "Select any asset from the menu to view its professional candlestick chart and indicators.")

def generate_professional_chart(ticker, tf_code, chart_type, indicator):
    if tf_code == '1min': period, interval = "1d", "1m"
    elif tf_code == '3min': period, interval = "1d", "1m"
    elif tf_code == '1D': period, interval = "1d", "5m"
    elif tf_code == '1W': period, interval = "5d", "15m"
    elif tf_code == '1M': period, interval = "1mo", "1d"
    elif tf_code == '1Y': period, interval = "1y", "1d"
    else: period, interval = "1d", "5m"

    try:
        data = yf.download(ticker, period=period, interval=interval, progress=False)
    except Exception as e:
        print(f"yfinance download error for {ticker}: {e}")
        return None, None, None, None, None

    if data is None or data.empty:
        return None, None, None, None, None

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.droplevel(1)

    if tf_code == '3min':
        try:
            data = data.resample('3T').agg({
                'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
            }).dropna()
        except Exception:
            pass

    if data.empty or 'Close' not in data.columns:
        return None, None, None, None, None

    close = data['Close']
    curr_price = float(close.iloc[-1])
    first_price = float(close.iloc[0])
    pct_change = ((curr_price - first_price) / first_price) * 100

    plt.style.use('dark_background')

    has_rsi = (indicator == 'rsi')
    has_vol = ('Volume' in data.columns and data['Volume'].sum() > 0)

    nrows = 1
    height_ratios = [4]
    if has_vol:
        nrows += 1
        height_ratios.append(1)
    if has_rsi:
        nrows += 1
        height_ratios.append(1.2)

    fig, axes = plt.subplots(nrows=nrows, ncols=1, figsize=(11, 7), sharex=True, gridspec_kw={'height_ratios': height_ratios})
    if nrows == 1:
        axes = [axes]

    ax1 = axes[0]
    ax_idx = 1

    if chart_type == "candlestick":
        up = data[data['Close'] >= data['Open']]
        down = data[data['Close'] < data['Open']]
        width = 0.0006 if tf_code in ['1min', '3min', '1D'] else (0.4 if tf_code in ['1W', '1M', '1Y'] else 0.003)

        if not up.empty:
            ax1.vlines(up.index, up['Low'], up['High'], color='#26a69a', linewidth=1)
            ax1.bar(up.index, up['Close'] - up['Open'], bottom=up['Open'], color='#26a69a', width=width, alpha=0.9)
        if not down.empty:
            ax1.vlines(down.index, down['Low'], down['High'], color='#ef5350', linewidth=1)
            ax1.bar(down.index, down['Open'] - down['Close'], bottom=down['Close'], color='#ef5350', width=width, alpha=0.9)
    elif chart_type == "bar":
        width = 0.001 if tf_code in ['1min', '3min', '1D'] else 0.6
        ax1.bar(data.index, close, color=['#26a69a' if c >= o else '#ef5350' for c, o in zip(data['Close'], data['Open'])], alpha=0.8, width=width)
    else:
        ax1.plot(data.index, close, color='#29b6f6', linewidth=2, label="Close")
        ax1.fill_between(data.index, close, close.min(), color='#29b6f6', alpha=0.1)

    ind_label = "Clean Chart"
    if indicator == 'sma':
        sma = close.rolling(window=20).mean()
        ax1.plot(data.index, sma, color='#ff9800', linewidth=1.5, label="SMA 20")
        ax1.legend(loc="upper left", fontsize=9, frameon=False)
        ind_label = "SMA 20"
    elif indicator == 'ema':
        ema = close.ewm(span=20, adjust=False).mean()
        ax1.plot(data.index, ema, color='#ab47bc', linewidth=1.5, label="EMA 20")
        ax1.legend(loc="upper left", fontsize=9, frameon=False)
        ind_label = "EMA 20"
    elif indicator == 'bb':
        sma20 = close.rolling(window=20).mean()
        std20 = close.rolling(window=20).std()
        upper = sma20 + (std20 * 2)
        lower = sma20 - (std20 * 2)
        ax1.plot(data.index, sma20, color='#78909c', linewidth=1, label="SMA 20")
        ax1.plot(data.index, upper, color='#ab47bc', linestyle='--', linewidth=1, label="Upper BB")
        ax1.plot(data.index, lower, color='#ab47bc', linestyle='--', linewidth=1, label="Lower BB")
        ax1.fill_between(data.index, upper, lower, color='#ab47bc', alpha=0.04)
        ax1.legend(loc="upper left", fontsize=9, frameon=False)
        ind_label = "Bollinger Bands"

    display_ticker = ticker.replace('=X', '')
    ax1.set_title(f"{display_ticker} | {tf_code.upper()} | {ind_label} | Price: ${curr_price:.4f} ({'+' if pct_change>0 else ''}{pct_change:.2f}%)", fontsize=12, fontweight='bold', color='white')
    ax1.grid(True, linestyle=':', alpha=0.3, color='gray')
    ax1.set_ylabel("Price ($)", color='lightgray', fontsize=10)

    if has_vol:
        ax_vol = axes[ax_idx]
        ax_idx += 1
        vol_colors = ['#26a69a' if c >= o else '#ef5350' for c, o in zip(data['Close'], data['Open'])]
        ax_vol.bar(data.index, data['Volume'], color=vol_colors, alpha=0.7, width=0.001 if tf_code in ['1min', '3min', '1D'] else 0.6)
        ax_vol.set_ylabel("Volume", color='lightgray', fontsize=9)
        ax_vol.grid(True, linestyle=':', alpha=0.2, color='gray')

    if has_rsi:
        ax_rsi = axes[ax_idx]
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        ax_rsi.plot(data.index, rsi, color='#ab47bc', linewidth=1.5)
        ax_rsi.axhline(70, color='#ef5350', linestyle='--', alpha=0.5, linewidth=1)
        ax_rsi.axhline(30, color='#26a69a', linestyle='--', alpha=0.5, linewidth=1)
        ax_rsi.fill_between(data.index, rsi, 70, where=(rsi >= 70), color='#ef5350', alpha=0.2)
        ax_rsi.fill_between(data.index, rsi, 30, where=(rsi <= 30), color='#26a69a', alpha=0.2)
        ax_rsi.set_ylabel("RSI (14)", color='lightgray', fontsize=9)
        ax_rsi.set_ylim(0, 100)
        ax_rsi.grid(True, linestyle=':', alpha=0.2, color='gray')

    fig.autofmt_xdate()
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=120, bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
    buf.seek(0)
    plt.close('all')

    plt.style.use('default')

    change_text = f"🟩 +{pct_change:.2f}%" if pct_change > 0 else f"🟥 {pct_change:.2f}%"
    return buf, curr_price, change_text, tf_code.upper(), ind_label

def send_or_update_chart(chat_id, message_id, ticker, cat_id, tf_code, ctype, indicator, is_update=False):
    display_ticker = ticker.replace('=X', '')
    if not is_update:
        processing_msg = bot.send_message(chat_id, f"⌛ Generating professional trading chart for {display_ticker}...")

    buf, curr_price, change_text, period_str, ind_name = generate_professional_chart(ticker, tf_code, ctype, indicator)

    if buf is None:
        error_msg = f"❌ Data not found for {display_ticker}. The market might be closed or the ticker is invalid."
        if is_update:
            try:
                bot.edit_message_caption(caption=error_msg, chat_id=chat_id, message_id=message_id)
            except Exception:
                bot.send_message(chat_id, error_msg)
        else:
            bot.edit_message_text(error_msg, chat_id=chat_id, message_id=processing_msg.message_id)
        return

    caption = f"🟢 *{display_ticker}* ({period_str})\n🕯️ *Style:* {ctype.capitalize()} | *Ind:* {ind_name}\n💵 *Price:* `${curr_price:.4f}`\n📊 *Change:* {change_text}"
    markup = get_chart_controls_markup(ticker, cat_id, tf_code, ctype, indicator)

    if is_update:
        try:
            media = InputMediaPhoto(buf.getvalue(), caption=caption, parse_mode="Markdown")
            bot.edit_message_media(media=media, chat_id=chat_id, message_id=message_id, reply_markup=markup)
        except Exception as e:
            if "is not modified" not in str(e).lower():
                bot.send_photo(chat_id, photo=buf.getvalue(), caption=caption, reply_markup=markup, parse_mode="Markdown")
    else:
        bot.delete_message(chat_id=chat_id, message_id=processing_msg.message_id)
        bot.send_photo(chat_id, photo=buf.getvalue(), caption=caption, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    data = call.data
    chat_id = call.message.chat.id
    msg_id = call.message.message_id

    try:
        if data == "main_menu":
            bot.edit_message_text("👇 *Main Menu:*\nChoose a category:", chat_id=chat_id, message_id=msg_id, reply_markup=get_main_menu_markup(), parse_mode="Markdown")
            
        elif data.startswith("cat_"):
            cat_id = data.replace("cat_", "")
            cat_name = CATEGORIES[cat_id][0]
            bot.edit_message_text(f"👇 *{cat_name}*\nClick on an asset:", chat_id=chat_id, message_id=msg_id, reply_markup=get_category_markup(cat_id, 0), parse_mode="Markdown")
            
        elif data.startswith("pg_"):
            parts = data.split("_")
            cat_id = parts[1]
            page = int(parts[2])
            cat_name = CATEGORIES[cat_id][0]
            if call.message.content_type == 'photo':
                bot.delete_message(chat_id, msg_id)
                bot.send_message(chat_id, f"👇 *{cat_name}*\nClick on an asset:", reply_markup=get_category_markup(cat_id, page), parse_mode="Markdown")
            else:
                bot.edit_message_text(f"👇 *{cat_name}*\nClick on an asset:", chat_id=chat_id, message_id=msg_id, reply_markup=get_category_markup(cat_id, page), parse_mode="Markdown")
                
        elif data.startswith("st_"):
            parts = data.split("_")
            ticker = parts[1]
            cat_id = parts[2]
            bot.answer_callback_query(call.id, f"Loading {ticker.replace('=X', '')}...")
            send_or_update_chart(chat_id, msg_id, ticker, cat_id, tf_code="1D", ctype="candlestick", indicator="none", is_update=False)
            
        elif data.startswith("ch_"):
            parts = data.split("_")
            ticker = parts[1]
            cat_id, tf_code, ctype = parts[2], parts[3], parts[4]
            indicator = parts[5] if len(parts) > 5 else "none"
            bot.answer_callback_query(call.id, f"Updating chart...")
            send_or_update_chart(chat_id, msg_id, ticker, cat_id, tf_code, ctype, indicator, is_update=True)
            
        # --- Deep Analysis Button Handler ---
        elif data.startswith("analyze_"):
            ticker = data.split("_")[1]
            display_ticker = ticker.replace('=X', '')
            bot.answer_callback_query(call.id, f"Analyzing {display_ticker}...")
            bot.send_message(chat_id, f"⏳ Generating deep technical analysis for {display_ticker}...")
            signal_result = get_advanced_signal(ticker)
            bot.send_message(chat_id, signal_result, parse_mode="Markdown")

    except Exception as e:
        print(f"Callback Error: {e}")
        try:
            bot.answer_callback_query(call.id, "Please wait...")
        except:
            pass

# --- Web Server for Render ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running perfectly!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    threading.Thread(target=run_web_server).start()
    print("Pro Trading Bot with Forex is running...")
    bot.polling(none_stop=True)
