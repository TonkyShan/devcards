"""Claude Code 用量：从本机会话记录统计今天和本周的 token 用量。"""
import collections
import datetime
import json
import os
import pathlib

from common import write

PROJECTS = pathlib.Path(os.path.expanduser(os.environ.get("CLAUDE_CONFIG_DIR", "~/.claude"))) / "projects"
WEEKDAYS = "一二三四五六日"


def fmt(n):
    return f"{n / 1e6:.1f}M" if n >= 1e6 else f"{n / 1e3:.0f}K" if n >= 1e3 else str(n)


def line(name, total):
    out, inp, hit = total
    cached = f"（缓存命中 {hit * 100 // inp}%）" if inp else ""
    return f"- **{name}**：输出 {fmt(out)} · 输入 {fmt(inp)}{cached}"


def main():
    today = datetime.date.today()
    monday = today - datetime.timedelta(days=today.weekday())
    since = datetime.datetime.combine(monday, datetime.time()).timestamp()

    messages = {}  # 同一条回复在流式过程中会写多行，按消息 id 取最后一行
    for path in PROJECTS.rglob("*.jsonl"):
        if path.stat().st_mtime < since:
            continue
        with open(path, encoding="utf-8", errors="replace") as f:
            for raw in f:
                if '"usage"' not in raw:
                    continue
                try:
                    entry = json.loads(raw)
                    message = entry["message"]
                    usage = message["usage"]
                    day = datetime.datetime.fromisoformat(
                        entry["timestamp"].replace("Z", "+00:00")).astimezone().date()
                    messages[message["id"]] = (
                        day, os.path.basename(entry.get("cwd") or "?"), message.get("model", "?"),
                        usage.get("output_tokens", 0),
                        usage.get("input_tokens", 0) + usage.get("cache_creation_input_tokens", 0)
                        + usage.get("cache_read_input_tokens", 0),
                        usage.get("cache_read_input_tokens", 0))
                except (ValueError, KeyError, TypeError):
                    continue

    # 每项是 [输出, 输入(含缓存), 其中缓存命中]
    days, projects, models = (collections.defaultdict(lambda: [0, 0, 0]) for _ in range(3))
    for day, project, model, *tokens in messages.values():
        if day < monday or not any(tokens):
            continue
        for bucket in (days[day], projects[project], models[model]):
            for i, n in enumerate(tokens):
                bucket[i] += n

    week = [sum(d[i] for d in days.values()) for i in range(3)]
    by_output = lambda item: -item[1][0]
    write("usage", "Claude Code 用量", "\n\n".join([
        "## 概览\n" + line("今天", days.get(today, [0, 0, 0])) + "\n" + line("本周", week),
        "## 每天\n" + "\n".join(
            line(f"{d:%m-%d} 周{WEEKDAYS[d.weekday()]}", t) for d, t in sorted(days.items())),
        "## 按项目（本周）\n" + "\n".join(line(p, t) for p, t in sorted(projects.items(), key=by_output)[:8]),
        "## 按模型（本周）\n" + "\n".join(line(m, t) for m, t in sorted(models.items(), key=by_output)),
    ]))
