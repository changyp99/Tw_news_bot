#!/usr/bin/env python3
"""
News Bot 自主健康管理腳本
每天定時執行：健康檢查 → 自動修復 → 主動通知

使用方式：
  python self_healer.py              # 完整檢查 + 通知
  python self_healer.py --light     # 輕量檢查（只看 workflow）
  python self_healer.py --fix        # 只執行自動修復
  python self_healer.py --notify    # 只發通知測試
"""
import os
import sys
import json
import logging
import argparse
from datetime import datetime
from pathlib import Path

# 設定 logging
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/newsbot_healer.log')
    ]
)
logger = logging.getLogger("self_healer")

# 把 script 目錄加入 path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

def run_health_check():
    """執行健康檢查"""
    from health_monitor import run_health_check as do_check
    return do_check()

def run_source_check():
    """只檢查來源健康"""
    from health_monitor import check_all_sources_health
    from news_sources import NEWS_SOURCES
    return check_all_sources_health(NEWS_SOURCES)

def auto_fix(report):
    """執行自動修復"""
    from health_monitor import trigger_workflow_dispatch
    from notifier import smart_notify

    fixed = []
    for action in report.get("auto_actions", []):
        if action["action"] == "trigger_workflow":
            result = trigger_workflow_dispatch()
            if result["success"]:
                fixed.append(f"✓ 已自動重跑 workflow")
                logger.info(f"自動修復成功: {action['reason']}")
            else:
                fixed.append(f"✗ 自動修復失敗: {result['reason']}")
                logger.error(f"自動修復失敗: {result['reason']}")
                # 修復失敗，加入通知
                report["notifications"].append(f"自動修復失敗，需要人工處理")

    report["fixed"] = fixed
    return report

def send_notification(report):
    """發送通知"""
    from notifier import smart_notify
    return smart_notify(report)

def daily_report():
    """每日深度報告（比輕量檢查更完整）"""
    from health_monitor import get_recent_workflow_runs, detect_missed_runs, check_all_sources_health
    from news_sources import NEWS_SOURCES

    lines = [
        "📊 *News Bot 每日深度報告*",
        f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        ""
    ]

    # 1. Workflow 執行摘要
    runs = get_recent_workflow_runs(limit=48)  # 最近48次（約24小時）
    if runs:
        completed = [r for r in runs if r["status"] == "completed"]
        failed = [r for r in completed if r["conclusion"] == "failure"]
        success_rate = f"{len(completed) - len(failed)}/{len(completed)}" if completed else "N/A"

        lines.append(f"📨 *Workflow 執行*：{len(completed)} 次完成，成功率 {success_rate}")

        if failed:
            lines.append(f"  ❌ 失敗 {len(failed)} 次：")
            for f in failed[:3]:
                lines.append(f"    • {f['created_at'][:16]} - {f.get('name', 'news bot')}")

    # 2. RSS 來源狀態
    health = check_all_sources_health(NEWS_SOURCES)
    healthy = [h for h in health if h["status"] == "healthy"]
    failed = [h for h in health if h["status"] == "failed"]
    empty = [h for h in health if h["status"] == "empty"]

    lines.append(f"📡 *RSS 來源*：{len(healthy)} 正常，{len(empty)} 空內容，{len(failed)} 失效")

    for h in health:
        if h["status"] != "healthy":
            status_icon = "🚨" if h["status"] == "failed" else "⚡"
            lines.append(f"  {status_icon} {h['source']}: {h.get('last_error', '無文章') or '空內容'}")

    # 3. 發送歷史摘要
    from health_monitor import detect_sent_anomalies, HISTORY_FILE
    hist = detect_sent_anomalies()
    if hist.get("history_exists"):
        total = hist.get("total_sent", "?")
        lines.append(f"📬 *已發送文章*：共 {total} 篇（防止重複發送）")
    elif hist.get("anomaly"):
        lines.append(f"⚠️ *歷史異常*：{hist['reason']}")

    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="News Bot 自主健康管理")
    parser.add_argument("--light", action="store_true", help="輕量檢查（只看 workflow 狀態）")
    parser.add_argument("--fix", action="store_true", help="只執行自動修復")
    parser.add_argument("--notify", action="store_true", help="只發通知測試")
    parser.add_argument("--daily", action="store_true", help="每日深度報告模式")
    args = parser.parse_args()

    logger.info("=" * 40)
    logger.info("News Bot 自主健康管理啟動")
    logger.info("=" * 40)

    if args.notify:
        # 通知測試
        from notifier import send_telegram_alert
        test_msg = f"✅ *News Bot 通知測試*\n\n小助理連線測試成功！\n時間：{datetime.now().strftime('%H:%M:%S')}"
        result = send_telegram_alert(test_msg)
        print(f"通知{'成功' if result else '失敗'}")
        return

    if args.light:
        # 輕量檢查：只看 workflow
        from health_monitor import get_recent_workflow_runs, detect_missed_runs
        runs = get_recent_workflow_runs(limit=10)
        check = detect_missed_runs(runs)

        print(f"\n輕量檢查結果：")
        print(f"  漏發：{'是 ⚠️' if check.get('has_missed') else '否 ✅'}")
        print(f"  失敗：{'是 ❌' if check.get('has_failure') else '否 ✅'}")

        if check.get("problems"):
            print(f"  問題：")
            for p in check["problems"]:
                print(f"    • {p}")
        return

    if args.daily:
        # 每日報告模式
        report_text = daily_report()
        from notifier import send_telegram_alert
        send_telegram_alert(report_text)
        print(report_text)
        return

    if args.fix:
        # 只執行修復
        report = run_health_check()
        auto_fix(report)
        print("自動修復執行完畢")
        return

    # 預設：完整檢查 → 自動修復 → 通知
    logger.info("執行完整健康檢查...")
    report = run_health_check()

    logger.info(f"發現 {len(report['issues'])} 個問題")
    for issue in report["issues"]:
        logger.info(f"  • {issue}")

    if report["auto_actions"]:
        logger.info("執行自動修復...")
        report = auto_fix(report)

    # 只有發現問題才發通知（平常安靜）
    if report["issues"] or report["auto_actions"] or report["notifications"]:
        logger.info("發送通知...")
        send_notification(report)
    else:
        logger.info("所有系統正常，不需要通知")

    logger.info("自主健康管理完成")

if __name__ == "__main__":
    main()
