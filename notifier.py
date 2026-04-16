"""
News Bot 自主通知模組
發現問題時自動通知用戶
"""
import os
import logging
from datetime import datetime
from pathlib import Path
from telegram import Bot

logger = logging.getLogger(__name__)

def send_telegram_alert(message, chat_id=None):
    """透過 Telegram 發送 alert"""
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        logger.warning("沒有 BOT_TOKEN，無法發送 Telegram 通知")
        return False

    target_chat = chat_id or os.getenv("TELEGRAM_CHAT_ID")
    if not target_chat:
        logger.warning("沒有 TELEGRAM_CHAT_ID，無法發送 Telegram 通知")
        return False

    try:
        bot = Bot(token=bot_token)
        # markdown mode 比較不嚴格
        bot.send_message(
            chat_id=target_chat,
            text=message,
            parse_mode="Markdown"
        )
        logger.info(f"✓ Telegram 通知已發送: {message[:50]}...")
        return True
    except Exception as e:
        logger.error(f"Telegram 通知發送失敗: {e}")
        return False

def format_health_report(report):
    """把健康報告格式化為 Telegram 訊息"""
    lines = [
        "🔔 *News Bot 健康報告*",
        f"🕐 {report['timestamp']}",
        ""
    ]

    if not report["issues"] and not report["notifications"]:
        lines.append("✅ 所有系統正常，沒有發現異常")
        return "\n".join(lines)

    if report["issues"]:
        lines.append("⚠️ *發現以下問題：*")
        for issue in report["issues"]:
            lines.append(f"  • {issue}")
        lines.append("")

    if report["auto_actions"]:
        lines.append("🔧 *自動修復記錄：*")
        for action in report["auto_actions"]:
            lines.append(f"  • {action.get('result', action['action'])}")
        lines.append("")

    if report["notifications"]:
        lines.append("📢 *需要關注：*")
        for n in report["notifications"]:
            lines.append(f"  • {n}")

    return "\n".join(lines)

def notify_issue(issue_type, message, chat_id=None):
    """快速通知單一問題"""
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        return False

    target_chat = chat_id or os.getenv("TELEGRAM_CHAT_ID")
    if not target_chat:
        return False

    emoji_map = {
        "missed_run": "⏰",
        "workflow_failure": "❌",
        "source_down": "🚨",
        "source_empty": "⚡",
        "history_empty": "⚠️",
        "fixed": "✅"
    }

    emoji = emoji_map.get(issue_type, "📢")
    text = f"{emoji} *News Bot 自動偵測*\n\n{message}"

    try:
        bot = Bot(token=bot_token)
        bot.send_message(chat_id=target_chat, text=text, parse_mode="Markdown")
        return True
    except Exception as e:
        logger.error(f"通知發送失敗: {e}")
        return False

# ====== 簡化版：只有問題才發通知 ======

def smart_notify(report):
    """
    智能通知：只有發現問題或自動修復才通知
    正常時安靜不吵
    """
    if not report["issues"] and not report["notifications"] and not report["auto_actions"]:
        # 完全正常，不通知
        logger.info("系統正常，不需要通知")
        return None

    message = format_health_report(report)
    success = send_telegram_alert(message)

    # 同時寫入本地日誌
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"health_{datetime.now().strftime('%Y%m%d')}.log"

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"\n[{datetime.now().strftime('%H:%M:%S')}]\n{message}\n")

    return success
