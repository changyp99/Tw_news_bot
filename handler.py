"""
Telegram 新聞 Bot - 按鈕版
用 Inline Keyboard 呈現分類按鈕
用戶點按鈕 -> 回覆該分類的新聞
"""
import os
import re
import logging
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, Updater, MessageHandler, Filters
from news_sources import NEWS_SOURCES, fetch_news

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("請設定 BOT_TOKEN 環境變數！")
    exit(1)

# ============================================================
# 分類按鈕定義
# ============================================================
CATEGORIES = {
    "📰 頭條": "Yahoo 新聞",
    "💻 科技": "TechNews 科技",
    "🌱 生活": "上下游新聞",
    "🪙 幣圈": "區塊客",
    "🏥 健康": "元氣網健康",
    "🌍 國際": "BBC中文",
}

def build_category_keyboard():
    """建立分類按鈕選單"""
    keyboard = []
    row = []
    for i, (cat_name, source_name) in enumerate(CATEGORIES.items(), 1):
        row.append(InlineKeyboardButton(cat_name, callback_data=f"cat_{source_name}"))
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


def send_category_news(update, context, source_name, limit=5):
    """發送指定分類的新聞"""
    query = update.callback_query
    chat_id = query.message.chat_id

    source_info = NEWS_SOURCES.get(source_name)
    if not source_info:
        query.edit_message_text(text="找不到這個分類")
        return

    news_list = fetch_news(source_name, source_info, limit=limit)
    if not news_list:
        query.edit_message_text(text=f"目前沒有 {source_name} 的新聞，稍後再試")
        return

    # 回覆「載入中」避免按鈕卡住
    query.answer(text="載入中...")

    for news in news_list[:limit]:
        try:
            image_url = extract_image_from_entry(news.get('_entry', {}))
            title = news['title']
            link = news['link']
            source = news['source']
            text = f"📌 {source}\n🔹 {title}\n👉 <a href=\"{link}\">點我看全文</a>"

            if image_url:
                context.bot.send_photo(
                    chat_id=chat_id,
                    photo=image_url,
                    caption=text[:1024],
                    parse_mode='HTML',
                    disable_web_page_preview=False
                )
            else:
                context.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode='HTML',
                    disable_web_page_preview=False
                )
        except Exception as e:
            logger.warning(f"發送失敗: {e}")

    # 重新顯示按鈕
    try:
        query.edit_message_text(
            text="👇 選擇分類看更多新聞 👇",
            reply_markup=build_category_keyboard()
        )
    except:
        pass


def send_all_news(update, context, limit_per_cat=3):
    """發送所有分類的新聞"""
    query = update.callback_query
    chat_id = query.message.chat_id
    query.answer(text="載入全部新聞...")

    emoji_map = {
        "Yahoo 新聞": "📰",
        "TechNews 科技": "💻",
        "上下游新聞": "🌱",
        "區塊客": "🪙",
        "元氣網健康": "🏥",
        "BBC中文": "🌍",
    }

    for source_name, source_info in NEWS_SOURCES.items():
        news_list = fetch_news(source_name, source_info, limit=limit_per_cat)
        if not news_list:
            continue

        emoji = emoji_map.get(source_name, "📌")
        try:
            context.bot.send_message(
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
                text = f"📌 {source}\n🔹 {title}\n👉 <a href=\"{link}\">點我看全文</a>"

                if image_url:
                    context.bot.send_photo(
                        chat_id=chat_id,
                        photo=image_url,
                        caption=text[:1024],
                        parse_mode='HTML',
                        disable_web_page_preview=False
                    )
                else:
                    context.bot.send_message(
                        chat_id=chat_id,
                        text=text,
                        parse_mode='HTML',
                        disable_web_page_preview=False
                    )
            except Exception as e:
                logger.warning(f"發送失敗: {e}")

    # 重新顯示按鈕
    try:
        query.edit_message_text(
            text="👇 選擇分類看更多新聞 👇",
            reply_markup=build_category_keyboard()
        )
    except:
        pass


# ============================================================
# Handler 函式
# ============================================================

def handle_start(update, context):
    """/start 命令"""
    update.message.reply_text(
        "👋 歡迎回來！\n\n👇 點按鈕選擇想看的新聞分類 👇",
        reply_markup=build_category_keyboard()
    )


def handle_help(update, context):
    """說明"""
    update.message.reply_text(
        "📋 使用方式：\n\n"
        "👉 點上面的按鈕切換新聞分類\n"
        "📋 全部新聞 - 看所有最新消息\n\n"
        "⏰ 不想一直點？\n"
        "→ 綁定後每30分鐘自動推播！"
    )


def handle_button(update, context):
    """處理按鈕點擊"""
    query = update.callback_query
    data = query.data

    if data == "cat_all":
        send_all_news(update, context)
    elif data.startswith("cat_"):
        source_name = data[4:]
        send_category_news(update, context, source_name)
    else:
        query.answer(text="未知指令")


def handle_text(update, context):
    """處理文字輸入（關鍵字搜尋）"""
    text = update.message.text.strip()
    if not text:
        return

    # 搜尋所有來源
    all_news = []
    for source_name, source_info in NEWS_SOURCES.items():
        news_list = fetch_news(source_name, source_info, limit=10)
        all_news.extend(news_list)

    # 簡單關鍵字過濾
    keyword = text.lower()
    results = [
        n for n in all_news
        if keyword in n['title'].lower() or keyword in n.get('summary', '').lower()
    ]

    if not results:
        update.message.reply_text(f"找不到包含「{text}」的新聞")
        return

    update.message.reply_text(f"🔍 找到 {len(results)} 條相關新聞：")

    for news in results[:10]:
        image_url = extract_image_from_entry(news.get('_entry', {}))
        title = news['title']
        link = news['link']
        source = news['source']
        text_msg = f"📌 {source}\n🔹 {title}\n👉 <a href=\"{link}\">點我看全文</a>"

        try:
            if image_url:
                context.bot.send_photo(
                    chat_id=update.message.chat_id,
                    photo=image_url,
                    caption=text_msg[:1024],
                    parse_mode='HTML',
                    disable_web_page_preview=False
                )
            else:
                context.bot.send_message(
                    chat_id=update.message.chat_id,
                    text=text_msg,
                    parse_mode='HTML',
                    disable_web_page_preview=False
                )
        except Exception as e:
            logger.warning(f"發送失敗: {e}")


def error_handler(update, context):
    """錯誤處理"""
    logger.warning(f"Error: {context.error}")


# ============================================================
# 主程式（Bot 持續運行模式）
# ============================================================

def main():
    logger.info("啟動按鈕版新聞 Bot...")
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # 指令處理
    dp.add_handler(CommandHandler("start", handle_start))
    dp.add_handler(CommandHandler("help", handle_help))

    # 按鈕處理
    dp.add_handler(CallbackQueryHandler(handle_button))

    # 文字處理（關鍵字搜尋）
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

    # 錯誤處理
    dp.add_error_handler(error_handler)

    # 啟動 Bot（長駐模式）
    logger.info("Bot 啟動完成，按 Ctrl+C 停止")
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
