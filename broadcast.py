"""
Telegram 新聞 Bot - 推播版 v2
增強：自動抓取新聞圖片，有圖的新聞用 send_photo 發送
"""
import os
import re
import logging
import requests
from telegram import Bot
from news_sources import fetch_all_news, clean_html

# 設定日誌
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendPhoto"


def extract_image_from_entry(entry):
    """從 RSS 條目中提取圖片網址"""
    # 1. 先試 enclosures（最準確）
    if hasattr(entry, 'enclosures') and entry.enclosures:
        for enc in entry.enclosures:
            if enc.get('type', '').startswith('image/'):
                href = enc.get('href', '')
                if href:
                    return href
    
    # 2. 試 media_thumbnail
    if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
        return entry.media_thumbnail[0].get('url', '')
    
    # 3. 試 media_content
    if hasattr(entry, 'media_content') and entry.media_content:
        for mc in entry.media_content:
            if mc.get('type', '').startswith('image/'):
                return mc.get('url', '')
    
    # 4. 從 summary/description/content 的 HTML 裡找第一張圖
    raw = str(entry.get('summary', '')) + str(entry.get('description', ''))
    for content in entry.get('content', []):
        raw += content.value if hasattr(content, 'value') else str(content)
    
    # 找 src="..." 或 src='...'
    imgs = re.findall(r'src=["\']([^"\']+)["\']', raw)
    for img in imgs:
        if img.startswith('http') and not img.endswith('.gif'):
            return img
    
    return ''


def send_news_with_photos(bot_token, chat_id, news_list):
    """發送新聞，有圖的新聞傳送照片"""
    bot = Bot(token=bot_token)
    sent_count = 0
    
    for news in news_list[:15]:  # 最多15條
        try:
            image_url = news.get('image_url', '')
            title = news['title']
            link = news['link']
            source = news['source']
            
            if image_url:
                # 有圖：用 sendPhoto + caption
                text = f"📌 {source}\n🔹 {title}\n🔗 {link}"
                bot.send_photo(
                    chat_id=chat_id,
                    photo=image_url,
                    caption=text[:1024],  # caption 最長 1024
                    parse_mode='HTML'
                )
                logger.info(f"📷 發送有圖新聞：{title[:40]}")
            else:
                # 沒圖：用文字訊息
                text = f"📌 {source}\n🔹 {title}\n🔗 {link}"
                bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode='HTML'
                )
                logger.info(f"📄 發送文字新聞：{title[:40]}")
            
            sent_count += 1
            
        except Exception as e:
            logger.warning(f"發送失敗: {e}")
            # 如果 send_photo 失敗，降級成文字
            try:
                text = f"📌 {news['source']}\n🔹 {news['title']}\n🔗 {news['link']}"
                bot.send_message(chat_id=chat_id, text=text, parse_mode='HTML')
            except:
                pass
    
    return sent_count


def main():
    """主程式"""
    bot_token = os.getenv("BOT_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token:
        logger.error("請設定 BOT_TOKEN 環境變數！")
        exit(1)
    
    logger.info("開始抓取新聞...")
    
    # 抓取新聞（增強版，帶圖片資訊）
    news_list = fetch_all_news(limit_per_source=5)
    
    # 為每條新聞提取圖片
    for news in news_list:
        img = extract_image_from_entry(news.get('_entry', news))
        news['image_url'] = img
    
    logger.info(f"抓到 {len(news_list)} 條新聞")
    
    if telegram_chat_id:
        logger.info(f"推播到 Chat ID: {telegram_chat_id}")
        sent = send_news_with_photos(bot_token, telegram_chat_id, news_list)
        logger.info(f"推播完成！共發送 {sent} 條")
    else:
        # 沒有 Chat ID，印出訊息
        for news in news_list:
            img = news.get('image_url', '')
            print(f"[{'📷' if img else '📄'}] {news['source']} | {news['title'][:40]} | {img[:50] if img else '無圖'}")


if __name__ == "__main__":
    main()
