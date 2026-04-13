"""
Telegram 新聞 Bot - 推播版 v4
增強：縮網址讓長連結變一行，版面更乾淨
"""
import os
import re
import logging
from telegram import Bot
from news_sources import fetch_all_news

# 設定日誌
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def extract_image_from_entry(entry):
    """從 RSS 條目中提取圖片網址"""
    if hasattr(entry, 'enclosures') and entry.enclosures:
        for enc in entry.enclosures:
            if enc.get('type', '').startswith('image/'):
                href = enc.get('href', '')
                if href:
                    return href

    if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
        return entry.media_thumbnail[0].get('url', '')

    if hasattr(entry, 'media_content') and entry.media_content:
        for mc in entry.media_content:
            if mc.get('type', '').startswith('image/'):
                return mc.get('url', '')

    raw = str(entry.get('summary', '')) + str(entry.get('description', ''))
    for content in entry.get('content', []):
        raw += content.value if hasattr(content, 'value') else str(content)

    imgs = re.findall(r'src=["\']([^"\']+)["\']', raw)
    for img in imgs:
        if img.startswith('http') and not img.endswith('.gif'):
            return img

    return ''


def send_news_with_photos(bot_token, chat_id, news_list):
    """發送新聞，有圖的新聞傳送照片，沒圖的傳文字"""
    bot = Bot(token=bot_token)

    grouped = {}
    for news in news_list:
        cat = news.get('category', '台灣')
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append(news)

    emoji_map = {'台灣': '🇹🇼', '幣圈': '🪙'}
    total_sent = 0

    for cat in ['台灣', '幣圈']:
        if cat not in grouped:
            continue

        icon = emoji_map.get(cat, '📌')
        try:
            bot.send_message(
                chat_id=chat_id,
                text=f"{icon} ====== {cat}新聞 ======",
                parse_mode='HTML'
            )
        except:
            pass

        for news in grouped[cat][:5]:
            try:
                image_url = extract_image_from_entry(news.get('_entry', news))
                title = news['title']
                source = news['source']

                if image_url:
                    text = f"📌 {source}\n🔹 {title}\n👉 <a href=\"{news['link']}\">點我看全文</a>"
                    bot.send_photo(
                        chat_id=chat_id,
                        photo=image_url,
                        caption=text,
                        parse_mode='HTML',
                        disable_web_page_preview=False
                    )
                    logger.info(f"📷 [{cat}] {title[:40]}")
                else:
                    text = f"📌 {source}\n🔹 {title}\n👉 <a href=\"{news['link']}\">點我看全文</a>"
                    bot.send_message(
                        chat_id=chat_id,
                        text=text,
                        parse_mode='HTML',
                        disable_web_page_preview=False
                    )
                    logger.info(f"📄 [{cat}] {title[:40]}")

                total_sent += 1

            except Exception as e:
                logger.warning(f"發送失敗: {e}")

    return total_sent


def main():
    """主程式"""
    bot_token = os.getenv("BOT_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token:
        logger.error("請設定 BOT_TOKEN 環境變數！")
        exit(1)

    logger.info("開始抓取新聞...")

    news_list = fetch_all_news(limit_per_source=5)
    logger.info(f"抓到 {len(news_list)} 條新聞")

    if telegram_chat_id:
        logger.info(f"推播到 Chat ID: {telegram_chat_id}")
        sent = send_news_with_photos(bot_token, telegram_chat_id, news_list)
        logger.info(f"推播完成！共發送 {sent} 條")
    else:
        for news in news_list:
            img = extract_image_from_entry(news.get('_entry', news))
            cat = news.get('category', '?')
            print(f"[{cat}] [{'📷' if img else '📄'}] {news['source']} | {news['title'][:50]}")
            print(f"       🔗 {news['link']}")


if __name__ == "__main__":
    main()
