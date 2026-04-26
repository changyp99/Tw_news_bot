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


def _split_by_image(news_list):
    """把新聞清單分成 有圖 / 無圖 兩組"""
    has_img = []
    no_img = []
    for n in news_list:
        img = extract_image_from_entry(n.get('_entry', {}))
        if img:
            has_img.append(n)
        else:
            no_img.append(n)
    return has_img, no_img


def _send_one_news(bot, chat_id, news):
    """發送一條新聞，有圖發 photo，没圖發 text。"""
    title = news['title']
    source = news['source']
    image_url = extract_image_from_entry(news.get('_entry', {}))

    if image_url:
        text = f"📌 {source}\n\n🔹 {title}"
        bot.send_photo(
            chat_id=chat_id,
            photo=image_url,
            caption=text[:1024],
            parse_mode='HTML'
        )
    else:
        text = f"📌 {source}\n\n🔹 {title}"
        bot.send_message(
            chat_id=chat_id,
            text=text[:4096],
            parse_mode='HTML'
        )


def send_all_news(bot_token, chat_id, limit_per_cat=2):
    """發送所有分類的新聞，規則：
    - 有圖片的新聞：全部發送
    - 無圖片的新聞：每家最多 limit_per_cat 則
    - 若該來源完全無圖，則放寬抓取數量直到找到有圖的新聞
    - 自動去除已發送過的文章
    """
    bot = Bot(token=bot_token)
    from news_sources import NEWS_SOURCES, fetch_news

    total_sent = 0
    sent_articles = []

    for source_name, source_info in NEWS_SOURCES.items():
        # 先抓 limit_per_cat * 3 篇來評估
        news_list = fetch_news(source_name, source_info, limit=limit_per_cat * 3)
        if not news_list:
            continue

        # 過濾掉已發送的
        new_articles, history = filter_new_articles(news_list)
        if not new_articles:
            continue

        # 分有圖 / 無圖
        has_img, no_img = _split_by_image(new_articles)

        if has_img:
            # 有圖：全部發，再補無圖最多 limit_per_cat 則
            to_send = has_img + no_img[:limit_per_cat]
        else:
            # 完全無圖：放寬抓取數量（最多20篇），直到找到有圖的
            logger.info(f"[{source_name}] 沒有找到圖片新聞，主動放寬搜尋...")
            expanded = fetch_news(source_name, source_info, limit=20)
            expanded_new, _ = filter_new_articles(expanded)
            has_img2, no_img2 = _split_by_image(expanded_new)
            if has_img2:
                to_send = has_img2 + no_img2[:limit_per_cat]
                logger.info(f"[{source_name}] 放寬後找到 {len(has_img2)} 張圖片")
            else:
                # 真的完全沒圖，只發1篇
                to_send = new_articles[:1]
                logger.warning(f"[{source_name}] 該來源完全無圖片，只發1篇純文字")

        # 發送分類標題
        emoji = CATEGORIES.get(f"{CATEGORIES.get(source_name, {}).get('emoji', '📌')} {source_name}", {}).get('emoji', '📌')
        try:
            bot.send_message(
                chat_id=chat_id,
                text=f"{emoji} ====== {source_info.get('name', source_name)} ======",
                parse_mode='HTML'
            )
        except:
            pass

        for news in to_send:
            try:
                _send_one_news(bot, chat_id, news)
                total_sent += 1
                sent_articles.append(news)
            except Exception as e:
                logger.warning(f"發送失敗: {e}")

    # 更新已發送歷史
    if sent_articles:
        # 所有 history 來自各 source 的最後一次 filter_new_articles
        from sent_history import filter_new_articles as fh, mark_as_sent as ms
        _, history = fh(sent_articles)
        ms(sent_articles, history)

    return total_sent


def send_news_for_category(bot_token, chat_id, source_name, limit=5):
    """發送指定分類的新聞"""
    bot = Bot(token=bot_token)
    from news_sources import NEWS_SOURCES, fetch_news
    from sent_history import filter_new_articles, mark_as_sent

    source_info = NEWS_SOURCES.get(source_name)
    if not source_info:
        bot.send_message(chat_id=chat_id, text="找不到這個分類")
        return

    news_list = fetch_news(source_name, source_info, limit=limit)
    new_articles, history = filter_new_articles(news_list)
    logger.info(f"[{source_name}] 本次新文章: {len(new_articles)} 篇")

    if not new_articles:
        bot.send_message(chat_id=chat_id, text=f"目前 {source_name} 沒有新文章")
        return 0

    has_img, no_img = _split_by_image(new_articles)
    if has_img:
        to_send = has_img + no_img[:limit]
    else:
        to_send = new_articles[:1]

    sent = 0
    sent_articles = []
    for news in to_send:
        try:
            _send_one_news(bot, chat_id, news)
            sent += 1
            sent_articles.append(news)
        except Exception as e:
            logger.warning(f"發送失敗: {e}")

    if sent_articles:
        mark_as_sent(sent_articles, history)

    return sent


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
        for news in news_list:
            img = extract_image_from_entry(news.get('_entry', {}))
            icon = "HAS IMG" if img else "NO IMG"
            print(f"[{icon}] {news['source']} | {news['title'][:50]}")


if __name__ == "__main__":
    main()
