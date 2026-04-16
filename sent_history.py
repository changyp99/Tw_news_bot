"""
已發送新聞追蹤 - 用連結當 unique key，避免重複發送
"""
import json
import os
from pathlib import Path

HISTORY_FILE = Path(__file__).parent / "sent_history.json"
MAX_HISTORY = 500  # 最多保留 500 筆，太多會拖慢比對

def load_history():
    """載入已發送文章記錄"""
    if not HISTORY_FILE.exists():
        return set()
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return set(data.get("sent_links", []))
    except (json.JSONDecodeError, IOError):
        return set()

def save_history(sent_links):
    """儲存已發送文章記錄"""
    # 只保留最新的 MAX_HISTORY 筆
    links_list = list(sent_links)[-MAX_HISTORY:]
    data = {"sent_links": links_list}
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def filter_new_articles(news_list):
    """過濾掉已發送的文章，只回傳新文章"""
    history = load_history()
    new_articles = []
    for news in news_list:
        link = news.get("link", "")
        if link and link not in history:
            new_articles.append(news)
        # 如果沒有 link（備援機制），就看 title + source 當 key
        elif not link:
            key = f"{news.get('source', '')}|{news.get('title', '')}"
            if key not in history:
                news["_dedup_key"] = key
                new_articles.append(news)
    
    return new_articles, history

def mark_as_sent(news_list, history):
    """將文章標記為已發送並儲存"""
    for news in news_list:
        link = news.get("link", "")
        if link:
            history.add(link)
        else:
            key = f"{news.get('source', '')}|{news.get('title', '')}"
            history.add(key)
    
    save_history(history)
    return history
