"""周报：本周一以来我在各仓库的提交，用 claude 整理成周会用的周报。"""
import datetime

from common import ask_claude, commits, config, write

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


def main():
    today = datetime.date.today()
    monday = today - datetime.timedelta(days=today.weekday())
    log = commits(config(), f"{monday} 00:00")
    body = ask_claude(PROMPT.format(start=monday, end=today, commits=log)) if log else "本周暂无提交。"
    write("weekly", f"周报 {monday:%m-%d} ~ {today:%m-%d}", body)
