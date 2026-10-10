"""待办：ONES 上分配给我的未关闭工单，加上 GitLab 上等我处理和我发起的合并请求。"""
import collections
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
    closed = ", ".join(f"'{s['uuid']}'" for s in mcp.call(server, "get_issue_status")["data"] if s["name"] in ignore)
    where = f"field004 = '{me}'" + (f" AND field005 NOT IN ({closed})" if closed else "")

    today, types, cursor = str(datetime.date.today()), collections.defaultdict(list), ""
    for _ in range(20):  # 按最近更新排序翻页，最多 1000 张
        page = mcp.call(server, "query_issues_by_onesql", query=(
            "SELECT uuid, field001, field903, field005.name, field007.name, TODATE(field013) FROM issue "
            f"WHERE v$cursor > '{cursor}' AND {where} ORDER BY field010 DESC LIMIT 1000, 50"))
        for row in page["data"]:
            issue = row["item"]
            due = issue.get("field013")
            due = f" · {'已逾期' if due < today else '截止'} {due[5:]}" if due else ""
            title = issue["field001"]
            title = title[:60] + "…" if len(title) > 60 else title
            types[issue["field007"]["name"]].append(
                f"- **{issue['field903']}** {title}（{issue['field005']['name']}{due}）")
        cursor = page["page_info"]["end_cursor"]
        if not page["page_info"]["has_next_page"]:
            break

    # 数量少的类型排前面：成批自动生成的工单往往最多，也最不需要逐条看
    ordered = sorted(types.items(), key=lambda kv: len(kv[1]))
    sections = [
        f"## {name} · {len(lines)} 张\n" + "\n".join(lines[:5])
        + (f"\n- 另有 {len(lines) - 5} 张更早更新的" if len(lines) > 5 else "")
        for name, lines in ordered]
    total = sum(len(lines) for lines in types.values())
    by_type = "、".join(f"{name} {len(lines)}" for name, lines in ordered)
    return (f"- 未关闭工单 {total} 张：{by_type}" if total else "- 没有未关闭的工单"), sections


def mr_sections(cfg):
    lines = {}
    for scope, label in (("assigned-to-me", "等我处理"), ("created-by-me", "我发起的")):
        found = gitlab.api(cfg["gitlab"], f"/merge_requests?state=opened&scope={scope}&per_page=100")
        lines[label] = [
            f"- [{mr['web_url'].split('/', 3)[3].replace('/merge_requests/', '!')}]({mr['web_url']}) {mr['title']}"
            for mr in found]
    overview = "- 合并请求：" + "、".join(f"{label} {len(l)}" for label, l in lines.items())
    return overview, [
        f"## 合并请求 · {label} · {len(l)} 个\n" + "\n".join(l[:5])
        + (f"\n- 另有 {len(l) - 5} 个更早更新的" if len(l) > 5 else "")
        for label, l in lines.items() if l]


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
