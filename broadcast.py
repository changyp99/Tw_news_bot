"""
台灣新聞分類按鈕版
每個按鈕對應一個 RSS 來源
"""
import os
import re
import logging
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from news_sources import fetch_all_news
from sent_history import filter_new_articles, mark_as_sent

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# 分類按鈕設定（名稱翻譯+對應RSS）
# ============================================================
CATEGORIES = {
    "📰 頭條": {
        "emoji": "📰",
        "label": "頭條",
        "source": "Yahoo 新聞",
    },
    "💻 科技": {
        "emoji": "💻",
        "label": "科技",
        "source": "TechNews 科技",
    },
    "🌱 生活": {
        "emoji": "🌱",
        "label": "生活",
        "source": "上下游新聞",
    },
    "🪙 幣圈": {
        "emoji": "🪙",
        "label": "幣圈",
        "source": "區塊客",
    },
    "🏥 健康": {
        "emoji": "🏥",
        "label": "健康",
        "source": "元氣網健康",
    },
    "🌍 國際": {
        "emoji": "🌍",
        "label": "國際",
        "source": "BBC中文",
    },
}

def get_category_keyboard():
    """產生分類按鈕"""
    keyboard = []
    row = []
    for i, (cat_name, info) in enumerate(CATEGORIES.items(), 1):
        row.append(InlineKeyboardButton(cat_name, callback_data=f"cat_{info['source']}"))
        if i % 2 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    # 最後一行：全部新聞
    keyboard.append([InlineKeyboardButton("📋 全部新聞", callback_data="cat_all")])
    return InlineKeyboardMarkup(keyboard)


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


def send_news_for_category(bot_token, chat_id, source_name, limit=5):
    """發送指定分類的新聞，自動去除已發送過的"""
    bot = Bot(token=bot_token)

    # 從 news_sources 取得特定來源的新聞
    from news_sources import NEWS_SOURCES, fetch_news
    from sent_history import filter_new_articles, mark_as_sent
    source_info = NEWS_SOURCES.get(source_name)
    if not source_info:
        bot.send_message(chat_id=chat_id, text="找不到這個分類")
        return

    news_list = fetch_news(source_name, source_info, limit=limit)

    # 去重
    new_articles, history = filter_new_articles(news_list)
    logger.info(f"[{source_name}] 本次新文章: {len(new_articles)} 篇")

    if not new_articles:
        bot.send_message(chat_id=chat_id, text=f"目前 {source_name} 沒有新文章")
        return 0

    sent = 0
    sent_articles = []
    for news in new_articles[:limit]:
        try:
            image_url = extract_image_from_entry(news.get('_entry', {}))
            title = news['title']
            link = news['link']
            source = news['source']

            if image_url:
                text = f"📌 {source}\n🔹 {title}\n👉 <a href=\"{link}\">點我看全文</a>"
                bot.send_photo(
                    chat_id=chat_id,
                    photo=image_url,
                    caption=text[:1024],
                    parse_mode='HTML',
                    disable_web_page_preview=False
                )
            else:
                text = f"📌 {source}\n🔹 {title}\n👉 <a href=\"{link}\">點我看全文</a>"
                bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode='HTML',
                    disable_web_page_preview=False
                )
            sent += 1
            sent_articles.append(news)
        except Exception as e:
            logger.warning(f"發送失敗: {e}")

    if sent_articles:
        mark_as_sent(sent_articles, history)

    return sent


def send_all_news(bot_token, chat_id, limit_per_cat=3):
    """發送所有分類的新聞（每分類3條），自動去除已發送過的"""
    bot = Bot(token=bot_token)
    from news_sources import NEWS_SOURCES, fetch_news

    # 先抓所有新聞
    all_news = fetch_all_news(limit_per_source=limit_per_cat * 3)

    # 過濾掉已發送的文章
    new_articles, history = filter_new_articles(all_news)
    logger.info(f"本次新文章: {len(new_articles)} 篇（已發送過: {len(all_news) - len(new_articles)} 篇）")

    if not new_articles:
        logger.info("沒有新文章要發送")
        return 0

    # 按分類群組
    grouped = {}
    for news in new_articles:
        src = news.get("source", "其他")
        if src not in grouped:
            grouped[src] = []
        grouped[src].append(news)

    total_sent = 0
    sent_articles = []  # 收集本次成功發送的文章

    for source_name, source_info in NEWS_SOURCES.items():
        if source_name not in grouped or not grouped[source_name]:
            continue

        news_list = grouped[source_name][:limit_per_cat]

        # 分類標題
        emoji = CATEGORIES.get(f"{CATEGORIES.get(source_name, {}).get('emoji', '📌')} {source_name}", {}).get('emoji', '📌')
        try:
            bot.send_message(
                chat_id=chat_id,
                text=f"{emoji} ====== {source_info.get('name', source_name)} ======",
                parse_mode='HTML'
            )
        except:
            pass

        for news in news_list:
            try:
                image_url = extract_image_from_entry(news.get('_entry', {}))
                title = news['title']
                link = news['link']
                source = news['source']

                if image_url:
                    text = f"📌 {source}\n🔹 {title}\n👉 <a href=\"{link}\">點我看全文</a>"
                    bot.send_photo(
                        chat_id=chat_id,
                        photo=image_url,
                        caption=text[:1024],
                        parse_mode='HTML',
                        disable_web_page_preview=False
                    )
                else:
                    text = f"📌 {source}\n🔹 {title}\n👉 <a href=\"{link}\">點我看全文</a>"
                    bot.send_message(
                        chat_id=chat_id,
                        text=text,
                        parse_mode='HTML',
                        disable_web_page_preview=False
                    )
                total_sent += 1
                sent_articles.append(news)
            except Exception as e:
                logger.warning(f"發送失敗: {e}")

    # 更新已發送歷史
    if sent_articles:
        mark_as_sent(sent_articles, history)

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
        sent = send_all_news(bot_token, telegram_chat_id)
        logger.info(f"推播完成！共發送 {sent} 條")
    else:
        # 沒有 Chat ID，印出新聞列表
        from news_sources import clean_html
        for news in news_list:
            img = extract_image_from_entry(news.get('_entry', {}))
            print(f"[{'📷' if img else '📄'}] {news['source']} | {news['title'][:50]}")


if __name__ == "__main__":
    main()
