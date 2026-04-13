"""
台灣新聞 RSS 來源列表
"""
import feedparser
from datetime import datetime
import re

NEWS_SOURCES = {
    # ========== 台灣新聞 ==========
    "Yahoo 新聞": {
        "url": "https://tw.news.yahoo.com/rss/",
        "name": "Yahoo 新聞",
        "category": "台灣",
    },
    "TechNews 科技": {
        "url": "https://technews.tw/feed/",
        "name": "科技新報",
        "category": "台灣",
    },
    "上下游新聞": {
        "url": "https://www.newsmarket.com.tw/feed/",
        "name": "上下游",
        "category": "台灣",
    },
    # ========== 幣圈新聞 ==========
    "Cointelegraph": {
        "url": "https://cointelegraph.com/rss",
        "name": "Cointelegraph",
        "category": "幣圈",
    },
    "Decrypt": {
        "url": "https://decrypt.co/feed",
        "name": "Decrypt",
        "category": "幣圈",
    },
    "Blockworks": {
        "url": "https://blockworks.co/feed",
        "name": "Blockworks",
        "category": "幣圈",
    },
    "區塊客": {
        "url": "https://blockcast.it/rss",
        "name": "區塊客",
        "category": "幣圈",
    },
    "CoinDesk": {
        "url": "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "name": "CoinDesk",
        "category": "幣圈",
    },
}

def clean_html(text):
    """移除 HTML 標籤"""
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text).strip()

def fetch_news(source_name, source_info, limit=5):
    """抓取單一來源的新聞"""
    try:
        feed = feedparser.parse(source_info["url"])
        news_list = []

        if not feed.entries:
            print(f"警告 {source_name}: 無任何項目，RSS status={feed.get('status', 'N/A')}")
            return []

        for entry in feed.entries[:limit]:
            title = clean_html(entry.get("title", ""))
            if not title:
                print(f"警告 {source_name}: 有一則新聞缺少標題，已跳過")
                continue
            news = {
                "title": title,
                "link": entry.get("link", ""),
                "source": source_name,
                "category": source_info.get("category", "台灣"),
                "published": entry.get("published", ""),
                "_entry": entry,
            }
            if hasattr(entry, 'summary') and entry.summary:
                news["summary"] = clean_html(entry.summary)[:100] + "..."
            elif hasattr(entry, 'description') and entry.description:
                news["summary"] = clean_html(entry.description)[:100] + "..."
            else:
                news["summary"] = ""

            news_list.append(news)

        print(f"成功 {source_name}: 抓到 {len(news_list)} 條新聞")
        return news_list
    except Exception as e:
        print(f"抓取 {source_name} 失敗: {e}")
        return []

def fetch_all_news(limit_per_source=5):
    """抓取所有來源的新聞"""
    all_news = []

    for source_name, source_info in NEWS_SOURCES.items():
        news = fetch_news(source_name, source_info, limit_per_source)
        all_news.extend(news)

    all_news.sort(key=lambda x: x.get("published", ""), reverse=True)
    return all_news

def format_news_message(news_list, keyword=None):
    """格式化新聞訊息"""
    if not news_list:
        return "目前沒有新聞可以顯示。\n\n請稍後再試。"

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    message = f"📰 台灣即時新聞 {current_time}\n"
    message += "=" * 32 + "\n\n"

    grouped = {}
    for news in news_list[:20]:
        cat = news.get("category", "台灣")
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append(news)

    emoji_map = {"台灣": "🇹🇼", "幣圈": "🪙"}
    for cat, news_items in grouped.items():
        icon = emoji_map.get(cat, "📌")
        message += f"{icon} {cat}新聞\n"
        for news in news_items[:3]:
            title = news["title"]
            link = news["link"]
            message += f"🔹 {title}\n{link}\n\n"

    message += "=" * 32 + "\n"
    message += "🔍 輸入關鍵字搜尋新聞\n"
    message += "⏰ 每30分鐘自動更新\n"

    return message

def search_news(news_list, keyword):
    """搜尋包含關鍵字的新聞"""
    if not keyword:
        return None

    keyword = keyword.lower()
    results = []

    for news in news_list:
        title = news["title"].lower()
        summary = news.get("summary", "").lower()
        if keyword in title or keyword in summary:
            results.append(news)

    if not results:
        return f"🔍 找不到包含「{keyword}」的新聞\n\n嘗試其他關鍵字看看？"

    message = f"🔍 搜尋結果：「{keyword}」\n"
    message += f"找到 {len(results)} 則新聞\n"
    message += "=" * 32 + "\n\n"

    for news in results[:10]:
        message += f"📌 {news['source']}\n"
        message += f"🔹 {news['title']}\n{news['link']}\n\n"

    return message
