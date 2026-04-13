# 📰 台灣即時新聞 Bot

一個每 30 分鐘自動推播台灣新聞的 Telegram Bot！

## 功能

- 📡 每 30 分鐘自動更新最新新聞到你的 Telegram
- 🔍 關鍵字搜尋新聞
- 📌 整理來自多家媒體的新聞
- 🤖 即時回覆互動

## 新聞來源

- 中央社
- 聯合報
- Yahoo 新聞
- TVBS
- 東森新聞

---

## 免費架設方式（GitHub Actions）

### 需要準備

1. ✅ GitHub 帳號
2. ✅ Telegram Bot Token（@BotFather 取得）
3. ✅ 你的 Telegram Chat ID（@userinfobot 取得）

### 步驟 1：建立 GitHub Repo

1. 登入 GitHub
2. 點擊右上角 **+** → **New repository**
3. Repository name: `tw-news-bot`
4. 選擇 **Public** 或 **Private** 都可以
5. 點擊 **Create repository**

### 步驟 2：上傳檔案

把這個資料夾的檔案上傳到 Repo：
- `bot.py`
- `broadcast.py`
- `news_sources.py`
- `requirements.txt`
- `.github/workflows/news-bot.yml`
- `README.md`

### 步驟 3：設定 Secrets

1. 進入 Repo → **Settings** → **Secrets and variables** → **Actions**
2. 點擊 **New repository secret**，新增：

| Name | Value |
|------|-------|
| `BOT_TOKEN` | 你的 Telegram Bot Token |
| `TELEGRAM_CHAT_ID` | 你的 Telegram Chat ID |

### 如何取得這些資料？

**取得 Bot Token：**
1. 在 Telegram 搜尋 **@BotFather**
2. 發送 `/newbot`
3. 輸入 Bot 名稱和用戶名（結尾要有 bot）
4. BotFather 會給你一串 Token

**取得 Chat ID：**
1. 在 Telegram 搜尋 **@userinfobot**
2. 點擊 Start
3. 它會回傳你的 ID（如 `123456789`）

### 步驟 4：啟動自動化

1. 進入 Repo → **Actions** 頁面
2. 點擊左側「News Bot」
3. 點擊 **Run workflow** → **Run workflow**
4. 看見 ✅ 表示成功！

### 步驟 5：開始使用

1. 在 Telegram 找到你的 Bot
2. 點擊 **Start**
3. 每 30 分鐘你就會收到最新新聞！

---

## 模式說明

### 目前設定：廣播模式（免費）

Bot 每 30 分鐘會自動推播新聞給你
- ✅ 完全免費
- ✅ 不用開著電腦
- ✅ 24 小時自動運行

### 如果想要完整互動模式

需要付費主機（約 100-300 元/月）：
- Railway（railway.app）
- PythonAnywhere
- 24 小時運行，所有指令都能用

---

## 調整推播頻率

編輯 `.github/workflows/news-bot.yml`：

```yaml
on:
  schedule:
    # 每30分鐘
    - cron: '*/30 * * * *'
    
    # 每小時
    # - cron: '0 * * * *'
    
    # 每天早上8點和晚上8點
    # - cron: '0 8,20 * * *'
```

---

## 新增更多新聞來源

編輯 `news_sources.py`，在 `NEWS_SOURCES` 字典中新增：

```python
"你的來源名稱": {
    "url": "RSS 連結",
    "name": "顯示名稱",
},
```

常見 RSS 格式：
- 中央社：`https://www.cna.com.tw/rss_home.aspx`
- UDN：`https://udn.com/rssfeed/news/2`
- Yahoo：`https://tw.news.yahoo.com/rss/`

---

## 常見問題

**Q: GitHub Actions 額度夠用嗎？**
A: 每月 2000 分鐘，每 30 分鐘推播約用 1440 分鐘，夠用！

**Q: Bot 會漏接新聞嗎？**
A: 不會，每次推播都會抓最新新聞

**Q: 可以分享給朋友用嗎？**
A: 目前是單一 Chat ID 推播，多人使用需要另外設定

---

## License

MIT
