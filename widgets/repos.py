"""仓库状态：按组列出有未提交改动或未推送提交的仓库，其余只在概览里提一句。只看本地，不 fetch。"""
import os
import re

from common import config, git, groups, write


def attention(repo):
    """返回 (当前分支, [需要处理的事项])。"""
    head, behind, dirty, untracked = "", 0, 0, 0
    for line in git(repo, "status", "--porcelain=v2", "--branch").splitlines():
        if line.startswith("# branch.head "):
            head = line.split(" ", 2)[2]
        elif line.startswith("# branch.ab "):
            behind = -int(line.split()[3])
        elif line.startswith("?"):
            untracked += 1
        elif not line.startswith("#"):
            dirty += 1
    notes = [f"{dirty} 个文件未提交"] if dirty else []
    if untracked:
        notes.append(f"{untracked} 个未跟踪")
    unpushed = []
    tracks = git(repo, "for-each-ref", "--format=%(refname:short)\t%(upstream:track)", "refs/heads")
    for line in tracks.splitlines():
        branch, _, track = line.partition("\t")
        ahead = re.search(r"ahead (\d+)", track)
        if ahead:
            unpushed.append(f"`{branch}` {ahead.group(1)} 个")
    if unpushed:
        more = f" 等 {len(unpushed)} 个分支" if len(unpushed) > 3 else ""
        notes.append("未推送：" + "、".join(unpushed[:3]) + more)
    if behind:
        notes.append(f"落后远端 {behind} 个提交")
    return head, notes


def main():
    total, minor, by_group = 0, [], {}
    for group, paths in groups(config()).items():
        for repo in paths:
            total += 1
            head, notes = attention(repo)
            name = os.path.basename(repo)
            if not notes:
                continue
            if not any("未提交" in note or note.startswith("未推送") for note in notes):
                minor.append(name)  # 没有本地工作，只是有未跟踪文件或没拉最新，不值得单列
            else:
                by_group.setdefault(group, []).append(f"- **{name}** `{head}`：" + "；".join(notes))

    # 只有一个仓库的组并到"其他"，免得一组一行
    merged = {group: lines for group, lines in by_group.items() if len(lines) > 1}
    rest = [line for lines in by_group.values() if len(lines) == 1 for line in lines]
    if rest:
        merged["其他"] = rest
    flagged = sum(len(lines) for lines in merged.values())
    overview = [f"- 共 {total} 个仓库，" + (f"{flagged} 个有本地改动或未推送的提交" if flagged else "没有未提交或未推送的内容")]
    if minor:
        overview.append(f"- 另有 {len(minor)} 个只有未跟踪文件或落后远端：" + "、".join(minor))
    write("repos", "仓库状态", "\n\n".join(
        ["## 概览\n" + "\n".join(overview)] + [f"## {group}\n" + "\n".join(lines) for group, lines in merged.items()]))
