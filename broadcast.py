"""
Telegram 新聞 Bot - 推播版
專門用於 GitHub Actions 定時推播
"""
import os
import logging
from telegram import Bot
from news_sources import fetch_all_news, format_news_message

# 設定日誌
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """主程式 - 抓取新聞並發送"""
    bot_token = os.getenv("BOT_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token:
        logger.error("請設定 BOT_TOKEN 環境變數！")
        exit(1)
    
    logger.info("開始抓取新聞...")
    
    # 抓取新聞
    news_list = fetch_all_news(limit_per_source=5)
    
    # 格式化訊息
    message = format_news_message(news_list)
    
    logger.info(f"抓到 {len(news_list)} 條新聞")
    
    # 如果有指定 Chat ID，直接推播
    if telegram_chat_id:
        logger.info(f"推播到 Chat ID: {telegram_chat_id}")
        bot = Bot(token=bot_token)
        bot.send_message(
            chat_id=telegram_chat_id,
            text=message,
            parse_mode='HTML'
        )
        logger.info("推播成功！")
    else:
        # 沒有 Chat ID，印出訊息（用於測試）
        logger.info("沒有設定 TELEGRAM_CHAT_ID，只顯示訊息：")
        print(message)

if __name__ == "__main__":
    main()
