"""工时：按本周提交里出现的 ONES 工单号估算每天每张工单的工时，等你在卡片上确认后再登记。

估算规则：每天按 8 小时算，按当天各工单的提交数占比分摊，取 0.5 小时的整数倍。
只是给个初值，git 里没有真实耗时。
"""
import collections
import datetime
import json
import os
import re

import mcp
from common import DATA, config, my_commits, write

PENDING = os.path.join(DATA, "hours_pending.json")  # 本次估算出、还没登记的条目
LOGGED = os.path.join(DATA, "hours_logged.json")    # 已由本工具登记过的 [工单, 日期]，防止重复登记
KEY = re.compile(r"\b[A-Z][A-Z0-9]{1,9}-\d+\b")
WEEKDAYS = "一二三四五六日"


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def main():
    cfg = config()
    if not cfg.get("ones_mcp"):
        write("hours", "工时", "## 概览\n- 还没配置数据源：在 config.json 里填 `ones_mcp`")
        return
    today = datetime.date.today()
    monday = today - datetime.timedelta(days=today.weekday())

    days = collections.defaultdict(list)  # 日期 -> [(仓库, 标题, 提到的编号)]
    for repo, date, branch, subject, body in my_commits(cfg, f"{monday} 00:00"):
        days[date].append((repo, subject, set(KEY.findall(f"{branch} {subject} {body}"))))

    # 形如 ABC-123 的不一定是 ONES 工单号，逐个到 ONES 里确认
    issues = {}
    for key in sorted({k for commits in days.values() for _, _, keys in commits for k in keys}):
        found = mcp.call(cfg["ones_mcp"], "query_issues_by_onesql", query=(
            f"SELECT uuid, field001 FROM issue WHERE v$cursor > '' AND field903 = '{key}' LIMIT 1000, 50"))["data"]
        if found:
            issues[key] = found[0]["item"]

    logged = {tuple(entry) for entry in load(LOGGED)}
    pending, sections, unlinked = [], [], 0
    for date in sorted(days):
        commits = days[date]
        per_issue = collections.defaultdict(list)
        for repo, subject, keys in commits:
            linked = [k for k in keys if k in issues]
            unlinked += not linked
            for key in linked:
                per_issue[key].append(subject)
        lines = []
        for key, subjects in per_issue.items():
            hours = max(0.5, round(8 * len(subjects) / len(commits) * 2) / 2)
            done = (key, date) in logged
            lines.append(f"- **{key}** {issues[key]['field001'][:50]}：{hours:g} 小时"
                         f"（当天 {len(commits)} 个提交中的 {len(subjects)} 个）{' · 已登记' if done else ''}")
            if not done:
                pending.append({"key": key, "issue": issues[key]["uuid"], "date": date, "hours": hours,
                                "description": "；".join(subjects)[:200]})
        if lines:
            day = datetime.date.fromisoformat(date)
            sections.append(f"## {day:%m-%d} 周{WEEKDAYS[day.weekday()]}\n" + "\n".join(lines))

    with open(PENDING, "w", encoding="utf-8") as f:
        json.dump(pending, f, ensure_ascii=False, indent=2)
    overview = [
        f"- 待登记 {sum(p['hours'] for p in pending):g} 小时，共 {len(pending)} 条；点右上角的对勾登记到 ONES"
        if pending else "- 没有待登记的工时",
        f"- 本周 {unlinked} 个提交没有关联到 ONES 工单（提交说明或分支名里没有工单号）",
    ]
    write("hours", f"工时 {monday:%m-%d} ~ {today:%m-%d}", "\n\n".join(["## 概览\n" + "\n".join(overview)] + sections))
