# 📰 台灣即時新聞 Bot

> 一個每 30 分鐘自動推播台灣新聞的 Telegram Bot，24小時免費運行！

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-24%2F7%20Automation-orange.svg)](https://github.com/features/actions)

## 🎯 專案展示

這是一個已上線運行的真實專案，展示以下技能：

| 技能 | 應用 |
|------|------|
| Python | 主程式開發 |
| Telegram Bot API | 訊息推播系統 |
| RSS 聚合 | 新聞資料擷取 |
| GitHub Actions | 24/7 自動化排程 |
| 第三方 API 整合 | 新聞來源串接 |

## ⚡ 功能

- 📡 **每 30 分鐘自動推播** - 無需主機，完全免費運行
- 🔍 **關鍵字搜尋** - 快速找新聞
- 📌 **多家媒體聚合** - 台灣重點新聞來源
- 🤖 **按鈕互動** - 使用者友善的 UI 設計
- 🔄 **24小時自動化** - GitHub Actions 驅動

## 📰 新聞來源

| 類別 | 來源 |
|------|------|
| 台灣新聞 | Yahoo 新聞、科技新報、上下游 |
| 幣圈中文 | 區塊客 |

## 🛠 技術棧

```
Python          # 主程式語言
python-telegram-bot  # Telegram Bot SDK
feedparser      # RSS 解析
GitHub Actions  # CI/CD + 自動化排程
```

## 📂 專案結構

```
tw-news-bot/
├── bot.py           # Bot 主程式
├── broadcast.py     # 廣播訊息模組
├── handler.py       # 訊息處理（含按鈕功能）
├── news_sources.py  # RSS 來源設定
├── requirements.txt  # 依賴套件
└── .github/workflows/
    └── news-bot.yml # GitHub Actions 排程
```

## 🚀 快速架設（免費）

### 步驟 1：Fork 此專案
點擊右上角 **Fork** 複製到你的 GitHub

### 步驟 2：取得 Telegram Bot Token
1. Telegram 搜尋 **@BotFather**
2. 發送 `/newbot`
3. 取得 Token

### 步驟 3：設定 Secrets
進入 Repo → **Settings** → **Secrets and variables** → **Actions**

| Name | Value |
|------|-------|
| `BOT_TOKEN` | 你的 Telegram Bot Token |
| `TELEGRAM_CHAT_ID` | 你的 Telegram Chat ID |

### 步驟 4：啟動自動化
1. 進入 **Actions** 頁面
2. 點擊 **Enable Actions**
3. 每 30 分鐘自動推播新聞！

## 💼 聯絡與服務

這個 Bot 是我的作品集之一。如果你需要：
- LINE Bot 開發
- Telegram Bot 客製化
- 自動化系統建置

歡迎聯絡我！

- 📧 **GitHub**: [github.com/changyp99](https://github.com/changyp99)
- 💬 **PRO360**: [pro360.com.tw](https://www.pro360.com.tw)（搜尋：changyp99）

---

*用技術解決問題，用自動化創造價值！*
