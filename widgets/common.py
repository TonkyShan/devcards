"""各小组件共用：配置、仓库发现与分组、取提交记录、调用 claude、写卡片文件。"""
import collections
import datetime
import json
import os
import re
import shutil
import subprocess

# DEVCARDS_DATA 可换数据目录，录演示时用 docs/demo 的示例数据
DATA = os.path.expanduser(os.environ.get("DEVCARDS_DATA", "~/Library/Application Support/DevCards"))
# launchd 环境的 PATH 里没有 ~/.local/bin
CLAUDE = shutil.which("claude") or os.path.expanduser("~/.local/bin/claude")


def config():
    with open(os.path.join(DATA, "config.json"), encoding="utf-8") as f:
        return json.load(f)


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True).stdout


def repos(config):
    return sorted(
        os.path.join(root, name)
        for root in map(os.path.expanduser, config["roots"])
        for name in os.listdir(root)
        if os.path.isdir(os.path.join(root, name, ".git")))


def groups(config):
    """{组名: [仓库路径]}。配置里的 groups 优先，其余按 origin 地址里的命名空间自动归组。"""
    manual = {name: group for group, names in config.get("groups", {}).items() for name in names}
    result = collections.defaultdict(list)
    for repo in repos(config):
        group = manual.get(os.path.basename(repo))
        if not group:
            # git@host:group/repo.git 或 http(s)://host[:port]/group/sub/repo.git
            m = re.search(r"(?:://[^/]+/|:)(.+)/[^/]+$", git(repo, "remote", "get-url", "origin").strip())
            group = m.group(1) if m else "未归组"
        result[group].append(repo)
    return dict(sorted(result.items()))


def my_commits(config, since, until=None):
    """逐条产出我在 since 之后（until 之前）的提交：(仓库名, 日期 YYYY-MM-DD, 分支, 标题, 说明)。"""
    for repo in repos(config):
        # 仓库自己的 user.email（没配则回落到全局），外加配置里追加的身份
        authors = {git(repo, "config", "user.email").strip(), *config.get("authors", [])} - {""}
        if not authors:
            continue
        log = git(
            repo, "log", "--branches", "--remotes", "--source", "--no-merges",
            "--since", since, *(["--until", until] if until else []),
            "--date=short", "--format=%x1e%ad%x1f%S%x1f%s%x1f%b",
            *[f"--author={a}" for a in authors])
        seen = set()
        for record in log.split("\x1e"):
            if not record.strip():
                continue
            date, branch, subject, body = record.split("\x1f", 3)
            if subject in seen:  # 同一提交被 cherry-pick 到多个分支
                continue
            seen.add(subject)
            yield os.path.basename(repo), date, branch, subject, body.strip()


def commits(config, since, until=None):
    """各仓库里我在 since 之后（until 之前）的提交，整理成给模型看的文本；没有提交返回空串。"""
    sections = collections.defaultdict(list)
    for repo, date, branch, subject, body in my_commits(config, since, until):
        sections[repo].append(f"{date[5:]} [{branch}] {subject}")
        sections[repo] += ["    " + l for l in body[:500].splitlines() if l.strip()]
    return "\n\n".join(f"### {repo}\n" + "\n".join(lines) for repo, lines in sections.items())


def ask_claude(prompt):
    result = subprocess.run(
        [CLAUDE, "-p", "--model", "sonnet", "--tools", "", "--strict-mcp-config",
         "--disable-slash-commands", "--no-session-persistence"],
        input=prompt, capture_output=True, text=True, timeout=600, cwd=DATA)
    if result.returncode != 0 or not result.stdout.strip():
        raise RuntimeError(f"claude 调用失败: {result.stderr or result.stdout}")
    return result.stdout.strip()


def write(name, title, body):
    """写出卡片内容。卡片把 `# ` 当标题、`更新于` 当副标题、每个 `## ` 当一个分块。"""
    now = datetime.datetime.now().strftime("%m-%d %H:%M")
    path = os.path.join(DATA, name + ".md")
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        f.write(f"# {title}\n更新于 {now}\n\n{body}\n")
    os.replace(path + ".tmp", path)
