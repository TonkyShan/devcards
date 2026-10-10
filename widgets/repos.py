"""仓库状态：按组列出有未提交改动、未推送提交或落后远端的仓库。只看本地，不 fetch。"""
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
    total, flagged, sections = 0, 0, []
    for group, paths in groups(config()).items():
        lines = []
        for repo in paths:
            total += 1
            head, notes = attention(repo)
            if notes:
                lines.append(f"- **{os.path.basename(repo)}** `{head}`：" + "；".join(notes))
        if lines:
            flagged += len(lines)
            sections.append(f"## {group}\n" + "\n".join(lines))
    summary = f"{flagged} 个需要处理" if flagged else "全部干净"
    write("repos", "仓库状态", "\n\n".join([f"## 概览\n- 共 {total} 个仓库，{summary}"] + sections))
