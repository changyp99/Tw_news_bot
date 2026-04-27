#!/usr/bin/env python3
"""News Bot 健康檢查：每3小時檢查一次，沒發布就主動查修"""
import os
import sys
import json
import requests
import subprocess
from datetime import datetime, timezone, timedelta

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO = "changyp99/Tw_news_bot"
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}

CHANNEL_ID = "7454171162"  # 備用通知（目前由 News Bot 本身發報，這裡只負責除錯）

def get_last_workflow_run():
    url = f"https://api.github.com/repos/{REPO}/actions/runs?per_page=5"
    r = requests.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()
    data = r.json()
    return data.get("workflow_runs", [])[0] if data.get("workflow_runs") else None

def check_bot_health():
    run = get_last_workflow_run()
    if not run:
        return "❌ 無法取得 GitHub Actions 資料"

    run_id = run["id"]
    status = run["status"]
    conclusion = run["conclusion"]
    created = run["created_at"]
    name = run["name"]

    now = datetime.now(timezone.utc)
    run_time = datetime.fromisoformat(created.replace("Z", "+00:00"))
    age_hours = (now - run_time).total_seconds() / 3600

    conclusion_text = f"結論={conclusion}" if conclusion else f"狀態={status}"

    # 檢查：是否成功？是否太舊（>3.5小時）？
    is_success = conclusion == "success"
    is_stale = age_hours > 3.5

    if is_success and not is_stale:
        return f"✅ 正常｜{name} #{run_id}｜{conclusion_text}｜{age_hours:.1f}小時前"

    # 抓 log 查原因
    problem = []
    if not is_success:
        problem.append(f"⚠️ 最後一次執行失敗：{conclusion_text}")
    if is_stale:
        problem.append(f"⚠️ 太長時間沒執行：{age_hours:.1f}小時（>3.5小時）")

    # 嘗試取 log
    try:
        log_url = f"https://api.github.com/repos/{REPO}/actions/runs/{run_id}/logs"
        lr = requests.get(log_url, headers=HEADERS, timeout=15)
        if lr.status_code == 200:
            # logs 是 zip，下載麻煩，改抓 job log
            job_url = f"https://api.github.com/repos/{REPO}/actions/runs/{run_id}/jobs"
            jr = requests.get(job_url, headers=HEADERS, timeout=10)
            if jr.ok:
                jobs = jr.json().get("jobs", [])
                for job in jobs:
                    for log in job.get("logs", []):
                        # 找錯誤關鍵字
                        if any(k in str(log).lower() for k in ["error", "exception", "traceback", "fail"]):
                            problem.append(f"🔍 log片段: {str(log)[-200:]}")
                            break
        else:
            problem.append(f"🔍 無法取得 log（HTTP {lr.status_code}）")
    except Exception as e:
        problem.append(f"🔍 取log失敗: {e}")

    return "\n".join(problem) + f"\n📋 Run #{run_id} {created}"

def self_heal():
    """萬一壞掉，試著修復 broadcast.py"""
    import subprocess, shutil, os

    local_path = os.path.dirname(os.path.abspath(__file__))
    broadcast_path = os.path.join(local_path, "broadcast.py")

    # 從 origin/master 還原 broadcast.py
    try:
        result = subprocess.run(
            ["git", "fetch", "origin", "master"],
            cwd=local_path, capture_output=True, text=True, timeout=15
        )
        result = subprocess.run(
            ["git", "checkout", "origin/master", "--", "broadcast.py"],
            cwd=local_path, capture_output=True, text=True, timeout=15
        )
        result = subprocess.run(
            ["git", "diff", "--stat", "broadcast.py"],
            cwd=local_path, capture_output=True, text=True
        )
        restored = result.stdout.strip()
        # push 回去
        if restored and restored != "broadcast.py":
            subprocess.run(["git", "add", "broadcast.py"], cwd=local_path)
            subprocess.run(
                ["git", "commit", "-m", "Auto-fix: restore broadcast.py from origin"],
                cwd=local_path, capture_output=True, text=True
            )
            subprocess.run(
                ["git", "push", "origin", "master"],
                cwd=local_path, capture_output=True, text=True, timeout=20
            )
            return "✅ 已自動還原 broadcast.py 並 push"
        else:
            return "broadcast.py 沒問題（無需修復）"
    except Exception as e:
        return f"⚠️ 自動修復失敗: {e}"

def main():
    report = check_bot_health()

    if report.startswith("✅"):
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')} GMT+8] {report}")
        return 0

    # 有問題 → 印出報告並嘗試自修復
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')} GMT+8] 🚨 News Bot 異常!")
    print(report)
    print("→ 嘗試自修復...")
    heal_result = self_heal()
    print(heal_result)
    return 1

if __name__ == "__main__":
    sys.exit(main())
