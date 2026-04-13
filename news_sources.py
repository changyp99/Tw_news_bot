"""
台灣新聞 RSS 來源列表
"""
import feedparser
from datetime import datetime
import re

NEWS_SOURCES = {
    "Yahoo 新聞": {
        "url": "https://tw.news.yahoo.com/rss/",
        "name": "Yahoo 新聞",
    },
    "TechNews 科技": {
        "url": "https://technews.tw/feed/",
        "name": "科技新報",
    },
    "上下游新聞": {
        "url": "https://www.newsmarket.com.tw/feed/",
        "name": "上下游",
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
        
        # 除錯：檢查 RSS 狀態
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
                "published": entry.get("published", ""),
                "_entry": entry,  # 保留原始 entry 給 broadcast.py 取圖片用
            }
            # 嘗試取得摘要
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
    
    # 按時間排序（最新的在前）
    all_news.sort(key=lambda x: x.get("published", ""), reverse=True)
    
    return all_news

def format_news_message(news_list, keyword=None):
    """格式化新聞訊息"""
    if not news_list:
        return "目前沒有新聞可以顯示。\n\n請稍後再試。"
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    message = f"📰 台灣即時新聞 {current_time}\n"
    message += "=" * 32 + "\n\n"
    
    # 按來源分組顯示
    grouped = {}
    for news in news_list[:20]:  # 最多顯示20條
        source = news["source"]
        if source not in grouped:
            grouped[source] = []
        grouped[source].append(news)
    
    for source, news_items in grouped.items():
        message += f"📌 {source}\n"
        for news in news_items[:3]:  # 每個來源最多3條
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
    
    for news in results[:10]:  # 最多顯示10條
        message += f"📌 {news['source']}\n"
        message += f"🔹 {news['title']}\n{news['link']}\n\n"
    
    return message
