"""待办：ONES 上分配给我的未关闭工单，加上 GitLab 上等我处理和我发起的合并请求。"""
import datetime

import gitlab
import mcp
from common import config, write

# 这些状态的工单不算待办；可在配置里用 ones_ignore_states 覆盖
IGNORE_STATES = ["已完成", "已拒绝", "关闭", "已关闭", "挂起"]


def ones_sections(cfg):
    server = cfg["ones_mcp"]
    ignore = set(cfg.get("ones_ignore_states", IGNORE_STATES))
    me = mcp.call(server, "who_am_i")["uuid"]

    counts = mcp.call(server, "query_issues_by_onesql", query=(
        f"SELECT field005.name, COUNT() AS n FROM issue WHERE field004 = '{me}' GROUP BY field005"))
    states = {g["field005"]["name"]: g["n"] for g in counts["data"][0]["group_aggregate"]}
    states = {name: n for name, n in states.items() if name not in ignore}
    by_count = "、".join(f"{name} {n}" for name, n in sorted(states.items(), key=lambda kv: -kv[1]))

    today, items, cursor = str(datetime.date.today()), [], ""
    for _ in range(4):  # 最多翻 4 页，凑够最近更新的 12 张未关闭工单
        page = mcp.call(server, "query_issues_by_onesql", query=(
            "SELECT uuid, field001, field903, field005.name, TODATE(field013) FROM issue "
            f"WHERE v$cursor > '{cursor}' AND field004 = '{me}' ORDER BY field010 DESC LIMIT 1000, 50"))
        for row in page["data"]:
            issue = row["item"]
            if issue["field005"]["name"] in ignore or len(items) >= 12:
                continue
            due = issue.get("field013")
            due = f" · {'已逾期' if due < today else '截止'} {due[5:]}" if due else ""
            title = issue["field001"]
            title = title[:60] + "…" if len(title) > 60 else title
            items.append(f"- **{issue['field903']}** {title}（{issue['field005']['name']}{due}）")
        cursor = page["page_info"]["end_cursor"]
        if len(items) >= 12 or not page["page_info"]["has_next_page"]:
            break

    overview = f"- 未关闭工单 {sum(states.values())} 张：{by_count}" if states else "- 没有未关闭的工单"
    return overview, ["## 工单（最近更新）\n" + "\n".join(items)] if items else []


def mr_sections(cfg):
    lines = {}
    for scope, label in (("assigned-to-me", "等我处理"), ("created-by-me", "我发起的")):
        found = gitlab.api(cfg["gitlab"], f"/merge_requests?state=opened&scope={scope}&per_page=10")
        lines[label] = [
            f"- [{mr['web_url'].split('/', 3)[3].replace('/merge_requests/', '!')}]({mr['web_url']}) {mr['title']}"
            for mr in found]
    overview = "- 合并请求：" + "、".join(f"{label} {len(l)}" for label, l in lines.items())
    return overview, [f"## 合并请求 · {label}\n" + "\n".join(l) for label, l in lines.items() if l]


def main():
    cfg = config()
    overview, sections = [], []
    for key, build in (("ones_mcp", ones_sections), ("gitlab", mr_sections)):
        if cfg.get(key):
            line, more = build(cfg)
            overview.append(line)
            sections += more
    if not overview:
        overview = ["- 还没配置数据源：在 config.json 里填 `ones_mcp` 或 `gitlab`"]
    write("todo", "我的待办", "\n\n".join(["## 概览\n" + "\n".join(overview)] + sections))
