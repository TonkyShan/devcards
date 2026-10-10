"""站会：上一个工作日到现在的提交，用 claude 整理成站会发言要点。"""
import datetime

from common import ask_claude, commits, config, write

PROMPT = """下面是我从上一个工作日（{prev}）到今天（{today}）的 git 提交记录，请整理成每日站会发言用的中文要点。

要求：
- `## 上个工作日（{prev:%m-%d}）`：今天之前完成的工作
- `## 今天（{today:%m-%d}）`：今天已经有的进展；今天没有提交就省略这一节
- 每条一句话，以 `**仓库名**` 开头，说清做了什么或解决了什么问题；合并同类提交，每节不超过 6 条
- 只依据提交记录，不要编造
- 只输出 Markdown 正文，格式只用 `## ` 标题、`- ` 列表和 `**加粗**`，不要代码块、表格和开场白

提交记录（每条格式：日期 [分支] 标题，缩进行是提交说明）：

{commits}
"""


def main():
    today = datetime.date.today()
    prev = today - datetime.timedelta(days=1)
    while prev.weekday() >= 5:
        prev -= datetime.timedelta(days=1)
    log = commits(config(), f"{prev} 00:00")
    body = ask_claude(PROMPT.format(prev=prev, today=today, commits=log)) if log else "上个工作日以来暂无提交。"
    write("standup", f"站会 {today:%m-%d}", body)
