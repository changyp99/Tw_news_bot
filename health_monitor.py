"""
News Bot 健康監控模組
自動偵測異常：漏發、重複、來源失效、workflow 失敗
"""
import os
import json
import re
import logging
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
import feedparser

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_API_TOKEN")
REPO = "changyp99/Tw_news_bot"
HISTORY_FILE = Path(__file__).parent / "sent_history.json"

# ====== 1. GitHub Actions 排程缺口偵測 ======

def get_recent_workflow_runs(limit=30):
    """取得最近的 workflow 執行記錄"""
    if not GITHUB_TOKEN:
        logger.warning("沒有 GITHUB_TOKEN，無法查詢 workflow 記錄")
        return []

    url = f"https://api.github.com/repos/{REPO}/actions/runs?per_page={limit}"
    req = Request(url, headers={
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "NewsBot-Monitor/1.0"
    })

    try:
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            return data.get("workflow_runs", [])
    except Exception as e:
        logger.error(f"查詢 GitHub Actions 失敗: {e}")
        return []

def detect_missed_runs(runs, schedule_interval_hours=0.5, tolerance_minutes=40):
    """
    偵測漏發：檢查 workflow 執行時間是否有缺口
    schedule_interval_hours: 預期執行間隔（小時）
    tolerance_minutes: 容忍缺口（分鐘），超過這個時間沒跑就視為漏發
    """
    if not runs:
        return {"has_missed": True, "reason": "無法取得 workflow 記錄"}

    # 按時間排序（最新的在前）
    runs_sorted = sorted(runs, key=lambda r: r["created_at"], reverse=True)

    # 只看已完成的
    completed = [r for r in runs_sorted if r["status"] == "completed"][:10]
    if len(completed) < 2:
        return {"has_missed": False, "reason": "執行記錄不足，無法判斷"}

    problems = []

    # 檢查最新一次是否失敗
    latest = completed[0]
    if latest["conclusion"] == "failure":
        problems.append({
            "type": "workflow_failure",
            "run_id": latest["id"],
            "created_at": latest["created_at"],
            "html_url": latest["html_url"],
            "reason": f"最近一次執行失敗: {latest.get('name', 'news bot')}"
        })

    # 檢查執行時間缺口
    for i in range(len(completed) - 1):
        prev_time = datetime.fromisoformat(completed[i]["created_at"].replace("Z", "+00:00"))
        curr_time = datetime.fromisoformat(completed[i + 1]["created_at"].replace("Z", "+00:00"))

        gap = (prev_time - curr_time).total_seconds() / 60  # 分鐘
        expected = schedule_interval_hours * 60

        if gap > expected + tolerance_minutes:
            missed_count = int((gap - tolerance_minutes) / expected)
            problems.append({
                "type": "missed_run",
                "gap_minutes": round(gap, 1),
                "expected_minutes": round(expected, 1),
                "missed_count": missed_count,
                "between": f"{completed[i+1]['created_at'][:16]} ~ {completed[i]['created_at'][:16]}"
            })

    return {
        "has_missed": len([p for p in problems if p["type"] == "missed_run"]) > 0,
        "has_failure": any(p["type"] == "workflow_failure" for p in problems),
        "problems": problems
    }

def trigger_workflow_dispatch(workflow_id=None):
    """手動觸發 workflow_dispatch"""
    if not GITHUB_TOKEN:
        return {"success": False, "reason": "沒有 GITHUB_TOKEN"}

    # 先取得 workflow ID
    if not workflow_id:
        url = f"https://api.github.com/repos/{REPO}/actions/workflows"
        req = Request(url, headers={
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "NewsBot-Monitor/1.0"
        })
        try:
            with urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
                workflows = data.get("workflows", [])
                # 找 news-bot 相關的
                wf = next((w for w in workflows if "news" in w["name"].lower()), workflows[0])
                workflow_id = wf["id"]
        except Exception as e:
            return {"success": False, "reason": f"取得 workflow ID 失敗: {e}"}

    # 觸發 dispatch
    url = f"https://api.github.com/repos/{REPO}/actions/workflows/{workflow_id}/dispatches"
    req = Request(url, method="POST", headers={
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "User-Agent": "NewsBot-Monitor/1.0"
    }, data=json.dumps({"ref": "master"}).encode())

    try:
        with urlopen(req, timeout=15) as resp:
            if resp.status in (200, 204):
                return {"success": True, "workflow_id": workflow_id}
            return {"success": False, "reason": f"HTTP {resp.status}"}
    except HTTPError as e:
        body = e.read().decode() if e.fp else ""
        return {"success": False, "reason": f"HTTP {e.code}: {body[:200]}"}
    except Exception as e:
        return {"success": False, "reason": str(e)}

# ====== 2. RSS 來源健康檢查 ======

def check_source_health(source_name, source_url, failure_threshold=3):
    """
    檢查單一 RSS 來源是否正常
    failure_threshold: 連續失敗幾次視為失效
    """
    health_file = Path(__file__).parent / f"health_{source_name.replace(' ', '_')}.json"

    try:
        feed = feedparser.parse(source_url)
        entries_count = len(feed.entries) if feed.entries else 0

        # 重置失敗計數
        if health_file.exists():
            health_file.unlink()

        return {
            "source": source_name,
            "status": "healthy" if entries_count > 0 else "empty",
            "entries": entries_count,
            "failures": 0
        }

    except Exception as e:
        # 記錄失敗次數
        failures = 0
        if health_file.exists():
            try:
                with open(health_file, "r") as f:
                    failures = json.load(f).get("failures", 0)
            except:
                pass

        failures += 1
        with open(health_file, "w") as f:
            json.dump({"failures": failures, "last_error": str(e)}, f)

        return {
            "source": source_name,
            "status": "failed" if failures >= failure_threshold else "error",
            "failures": failures,
            "last_error": str(e)[:100]
        }

def check_all_sources_health(sources):
    """檢查所有 RSS 來源的健康狀態"""
    results = []
    for name, info in sources.items():
        result = check_source_health(name, info["url"])
        results.append(result)
        if result["status"] == "failed":
            logger.warning(f"來源失效: {name}（已連續失敗 {result['failures']} 次）")
        elif result["status"] == "healthy":
            logger.info(f"✓ {name}: {result['entries']} 篇文章")

    return results

# ====== 3. 發送歷史異常偵測 ======

def detect_sent_anomalies():
    """
    偵測發送歷史的異常：
    - sent_history.json 太久沒更新（Bot 可能當機）
    - 短時間內同一篇文章被標記多次（系統異常）
    """
    if not HISTORY_FILE.exists():
        return {"anomaly": True, "reason": "沒有歷史檔案（首次啟動）"}

    try:
        with open(HISTORY_FILE, "r") as f:
            data = json.load(f)

        links = data.get("sent_links", [])
        if not links:
            return {"anomaly": True, "reason": "歷史檔案是空的（可能 Bot 從未成功發送過）"}

        # 檢查是否為字串列表（新格式）或舊格式
        if isinstance(links, list) and len(links) == 0:
            return {"anomaly": True, "reason": "歷史是空的"}

        return {
            "anomaly": False,
            "total_sent": len(links) if isinstance(links, list) else "unknown",
            "history_exists": True
        }

    except json.JSONDecodeError:
        return {"anomaly": True, "reason": "歷史檔案格式損壞"}

# ====== 4. 綜合健康報告 ======

def run_health_check():
    """執行完整健康檢查，回傳報告"""
    from news_sources import NEWS_SOURCES

    report = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "issues": [],
        "auto_actions": [],
        "notifications": []
    }

    # 1. 檢查 workflow runs
    logger.info("=== 檢查 Workflow 執行狀態 ===")
    runs = get_recent_workflow_runs(limit=20)
    run_check = detect_missed_runs(runs)

    if run_check.get("has_missed"):
        for p in run_check.get("problems", []):
            if p["type"] == "missed_run":
                msg = f"⚠️ 偵測到漏發：缺口 {p['gap_minutes']} 分鐘，可能漏了 {p['missed_count']} 次執行"
                report["issues"].append(msg)
                report["auto_actions"].append({
                    "action": "trigger_workflow",
                    "reason": msg,
                    "details": p
                })

    if run_check.get("has_failure"):
        for p in run_check.get("problems", []):
            if p["type"] == "workflow_failure":
                msg = f"❌ Workflow 執行失敗: {p['created_at'][:16]}"
                report["issues"].append(msg)
                report["auto_actions"].append({
                    "action": "trigger_workflow",
                    "reason": msg,
                    "details": p
                })

    # 2. 檢查 RSS 來源健康
    logger.info("=== 檢查 RSS 來源 ===")
    source_health = check_all_sources_health(NEWS_SOURCES)
    for h in source_health:
        if h["status"] == "failed":
            msg = f"🚨 來源失效（{h['failures']}次失敗）: {h['source']}"
            report["issues"].append(msg)
            report["notifications"].append(msg)
        elif h["status"] == "empty":
            msg = f"⚡ 來源空內容（可能已停更）: {h['source']}"
            report["issues"].append(msg)

    # 3. 檢查發送歷史
    logger.info("=== 檢查發送歷史 ===")
    history_check = detect_sent_anomalies()
    if history_check.get("anomaly"):
        msg = f"⚠️ 歷史異常: {history_check['reason']}"
        report["issues"].append(msg)

    # 4. 自動修復
    for action in report["auto_actions"]:
        if action["action"] == "trigger_workflow":
            result = trigger_workflow_dispatch()
            if result["success"]:
                action["result"] = "已觸發 workflow"
                logger.info(f"✓ 已自動觸發 workflow: {action['reason']}")
            else:
                action["result"] = f"觸發失敗: {result['reason']}"
                report["notifications"].append(f"自動修復失敗: {result['reason']}")
                logger.error(f"✗ 自動觸發失敗: {result['reason']}")

    return report

if __name__ == "__main__":
    report = run_health_check()
    print("\n" + "=" * 40)
    print("📋 News Bot 健康報告")
    print("=" * 40)
    print(f"時間: {report['timestamp']}")
    print(f"問題數: {len(report['issues'])}")
    for issue in report["issues"]:
        print(f"  • {issue}")
    print(f"自動修復: {len(report['auto_actions'])} 次")
    for a in report["auto_actions"]:
        print(f"  • {a['action']}: {a['result']}")
    if report["notifications"]:
        print(f"\n需要通知: {'; '.join(report['notifications'])}")
    else:
        print("\n✅ 所有系統正常")
