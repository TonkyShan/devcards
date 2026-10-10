#!/usr/bin/python3
"""汇总本周一以来各仓库中我的提交，用 claude 生成周报 Markdown。"""
import datetime
import json
import os
import shutil
import subprocess
import sys

DATA = os.path.expanduser("~/Library/Application Support/WeeklyReport")
CONFIG = os.path.join(DATA, "config.json")
OUT = os.path.join(DATA, "report.md")
# launchd 环境的 PATH 里没有 ~/.local/bin
CLAUDE = shutil.which("claude") or os.path.expanduser("~/.local/bin/claude")

PROMPT = """下面是我本周（{start} ~ {end}）在各个 git 仓库里的提交记录，请帮我整理成周会用的中文周报。

要求：
- 开头用 `## 本周概览` 写 2~4 条最重要的进展
- 之后每个仓库一个 `## 仓库名`，紧跟一行 `分支：xxx`，再按 `**新功能**`、`**修复**`、`**其他**` 分组列要点（没有内容的分组省略）
- 合并同类提交，用周会汇报的口吻概括做了什么、解决了什么问题，不要逐条照抄 commit
- 只依据提交记录，不要编造
- 只输出 Markdown 正文，格式只用 `## ` 标题、`- ` 列表和 `**加粗**`，不要代码块、表格和开场白

提交记录（每条格式：日期 [分支] 标题，缩进行是提交说明）：

{commits}
"""


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True).stdout


def collect(since, config):
    sections = []
    repos = sorted(
        os.path.join(root, name)
        for root in map(os.path.expanduser, config["roots"])
        for name in os.listdir(root)
        if os.path.isdir(os.path.join(root, name, ".git")))
    for repo in repos:
        # 仓库自己的 user.email（没配则回落到全局），外加配置里追加的身份
        authors = {git(repo, "config", "user.email").strip(), *config.get("authors", [])} - {""}
        if not authors:
            continue
        log = git(
            repo, "log", "--branches", "--remotes", "--source", "--no-merges",
            "--since", since, "--date=format:%m-%d", "--format=%x1e%ad%x1f%S%x1f%s%x1f%b",
            *[f"--author={a}" for a in authors])
        lines, seen = [], set()
        for record in log.split("\x1e"):
            if not record.strip():
                continue
            date, branch, subject, body = record.split("\x1f", 3)
            if subject in seen:  # 同一提交被 cherry-pick 到多个分支
                continue
            seen.add(subject)
            lines.append(f"{date} [{branch}] {subject}")
            lines += ["    " + l for l in body.strip()[:500].splitlines() if l.strip()]
        if lines:
            sections.append(f"### {os.path.basename(repo)}\n" + "\n".join(lines))
    return "\n\n".join(sections)


def main():
    today = datetime.date.today()
    monday = today - datetime.timedelta(days=today.weekday())
    with open(CONFIG, encoding="utf-8") as f:
        config = json.load(f)
    commits = collect(f"{monday} 00:00", config)
    if commits:
        prompt = PROMPT.format(start=monday, end=today, commits=commits)
        result = subprocess.run(
            [CLAUDE, "-p", "--model", "sonnet", "--tools", "", "--strict-mcp-config",
             "--disable-slash-commands", "--no-session-persistence"],
            input=prompt, capture_output=True, text=True, timeout=600,
            cwd=DATA)
        if result.returncode != 0 or not result.stdout.strip():
            sys.exit(f"claude 调用失败: {result.stderr or result.stdout}")
        body = result.stdout.strip()
    else:
        body = "本周暂无提交。"

    now = datetime.datetime.now().strftime("%m-%d %H:%M")
    report = f"# 周报 {monday:%m-%d} ~ {today:%m-%d}\n更新于 {now}\n\n{body}\n"
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(report)
    os.replace(tmp, OUT)


if __name__ == "__main__":
    main()
