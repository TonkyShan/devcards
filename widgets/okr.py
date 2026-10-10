"""月度 OKR：按仓库整理上月实现的功能，并起草本月 OKR（存成文件，可以手改）。"""
import datetime
import os

from common import DATA, ask_claude, commits, config, write

REVIEW = """下面是我上个月（{month}）在各个 git 仓库里的提交记录，请按仓库整理出上个月实现的功能。

要求：
- 每个仓库独占一行 `**仓库名**`，其下用 `- ` 列出实现的功能和解决的问题，每个仓库不超过 5 条
- 合并同类提交，概括做成了什么功能、解决了什么问题，不要逐条照抄 commit
- 只依据提交记录，不要编造
- 只输出 Markdown 正文，格式只用 `- ` 列表和 `**加粗**`，不要标题、代码块、表格和开场白

提交记录（每条格式：日期 [分支] 标题，缩进行是提交说明）：

{commits}
"""

DRAFT = """请帮我起草这个月（{month}）的 OKR 初稿，我会在此基础上再改。从各个项目上个月实现的功能和这个月到目前为止的提交出发，推出每个项目这个月在设计和优化上该做什么。

要求：
- 3~5 个目标，按项目或方向划分，只覆盖主要项目；每个目标独占一行 `**O1 目标内容**`，其下 2~4 条 `- KR1 关键结果`
- 设计类 KR：接着已有实现要新做或补齐的方案、能力；优化类 KR：性能、稳定性、可维护性，以及上月没收尾的事
- KR 写明涉及的仓库，要具体，月底能对照提交判断是否完成
- 只依据下面的材料推导，不要编造材料里看不出来的方向
- 只输出 Markdown 正文，格式只用 `- ` 列表和 `**加粗**`，不要标题、代码块、表格、开场白和结尾的补充说明

上月实现的功能：

{review}

本月提交记录（每条格式：日期 [分支] 标题，缩进行是提交说明）：

{commits}
"""


def plan_path(month):
    return os.path.join(DATA, "okr", f"{month:%Y-%m}.md")


def read(path):
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8") as f:
        return f.read().strip()


def main():
    cfg = config()
    this = datetime.date.today().replace(day=1)
    last = (this - datetime.timedelta(days=1)).replace(day=1)

    last_log = commits(cfg, f"{last} 00:00", f"{this} 00:00")
    review = ask_claude(REVIEW.format(month=f"{last:%Y-%m}", commits=last_log)) if last_log else "上月暂无提交。"

    # 本月 OKR 只起草一次，之后以文件为准，手改的内容不会被覆盖
    path = plan_path(this)
    plan = read(path)
    if not plan:
        this_log = commits(cfg, f"{this} 00:00")
        if not (last_log or this_log):
            plan = "暂无提交，无从起草。"
        else:
            plan = ask_claude(DRAFT.format(
                month=f"{this:%Y-%m}", review=review, commits=this_log or "（暂无）"))
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(plan + "\n")

    write("okr", f"OKR {this:%Y-%m}",
          f"## 上月完成（{last:%Y-%m}）\n{review}\n\n## 本月规划（{this:%Y-%m}）\n{plan}")
