"""
Telegram 新聞 Bot - 主程式
"""
import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from news_sources import fetch_all_news, format_news_message, search_news

# 設定日誌
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 取得環境變數
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    logger.error("請設定 BOT_TOKEN 環境變數！")
    exit(1)

# 快取的新聞資料
news_cache = []
last_update = None

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """處理 /start 指令"""
    welcome_message = """
👋 歡迎使用「台灣即時新聞 Bot」！

📰 我可以提供以下服務：
• 每30分鐘自動推播最新新聞
• 輸入關鍵字搜尋新聞
• 整理來自各大媒體的新聞

🔧 可用指令：
/start - 顯示歡迎訊息
/help - 顯示說明
/news - 取得最新新聞
/search [關鍵字] - 搜尋新聞

📌 使用方式：
直接輸入關鍵字即可搜尋！
例如：輸入「颱風」查看相關新聞
"""
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """處理 /help 指令"""
    help_message = """
📖 使用說明

【自動推播】
系統每30分鐘自動更新新聞

【手動查詢】
• 輸入 /news - 取得最新新聞
• 輸入 /search [關鍵字] - 搜尋特定主題

【直接輸入】
直接輸入關鍵字也可以搜尋！
例如：輸入「股票」、「房價」、「地震」等

【新聞來源】
• 中央社
• 聯合報
• Yahoo 新聞
• TVBS
• 東森新聞

⚠️ 注意：新萬物皆可搜尋，但精準度取決於當天新聞內容
"""
    await update.message.reply_text(help_message)

async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """處理 /news 指令"""
    global news_cache
    
    await update.message.reply_text("📡 正在抓取最新新聞...")
    
    news_list = fetch_all_news(limit_per_source=5)
    news_cache = news_list
    
    message = format_news_message(news_list)
    await update.message.reply_text(message)

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """處理 /search 指令"""
    global news_cache
    
    if not context.args:
        await update.message.reply_text(
            "🔍 請輸入搜尋關鍵字！\n\n"
            "例如：/search 颱風\n"
            "或直接輸入關鍵字搜尋"
        )
        return
    
    keyword = " ".join(context.args)
    
    # 如果還沒有快取，先抓新聞
    if not news_cache:
        await update.message.reply_text(f"🔍 正在搜尋「{keyword}」...")
        news_cache = fetch_all_news(limit_per_source=10)
    
    message = search_news(news_cache, keyword)
    await update.message.reply_text(message)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """處理一般文字訊息（當作關鍵字搜尋）"""
    global news_cache
    
    text = update.message.text.strip()
    
    # 忽略指令（以 / 開頭的）
    if text.startswith("/"):
        return
    
    # 空訊息
    if not text:
        return
    
    await update.message.reply_text(f"🔍 正在搜尋「{text}」...")
    
    # 如果還沒有快取，先抓新聞
    if not news_cache:
        news_cache = fetch_all_news(limit_per_source=10)
    
    message = search_news(news_cache, text)
    await update.message.reply_text(message)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """處理錯誤"""
    logger.error(f"更新 {update} 發生錯誤: {context.error}")

def main():
    """主程式"""
    logger.info("啟動新聞 Bot...")
    
    # 建立 Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # 註冊指令處理器
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("news", news_command))
    application.add_handler(CommandHandler("search", search_command))
    
    # 註冊訊息處理器
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # 註冊錯誤處理器
    application.add_error_handler(error_handler)
    
    # 啟動 Bot
    logger.info("Bot 啟動成功！")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
