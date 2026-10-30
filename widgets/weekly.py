"""周报：本周一以来（或卡片上选的时间段内）我在各仓库的提交，用 claude 整理成周会用的周报。

用法: weekly.py [开始日期 结束日期 | reset]  选定时间段 / 回到本周；定时任务经 run.py 调用时不带参数。
"""
import datetime
import json
import os
import sys

from common import DATA, ask_claude, commits, config, write

# 卡片上选的时间段，到下周一失效，免得被定时任务盖回本周
RANGE = os.path.join(DATA, "weekly_range.json")

PROMPT = """下面是我{label}（{start} ~ {end}）在各个 git 仓库里的提交记录，请帮我整理成周会用的中文周报。

要求：
- 开头用 `## {label}概览` 写 2~4 条最重要的进展
- 之后每个仓库一个 `## 仓库名`，紧跟一行 `分支：xxx`，再按 `**新功能**`、`**修复**`、`**其他**` 分组列要点（没有内容的分组省略）
- 合并同类提交，用周会汇报的口吻概括做了什么、解决了什么问题，不要逐条照抄 commit
- 只依据提交记录，不要编造
- 只输出 Markdown 正文，格式只用 `## ` 标题、`- ` 列表和 `**加粗**`，不要代码块、表格和开场白

提交记录（每条格式：日期 [分支] 标题，缩进行是提交说明）：

{commits}
"""


def pinned(monday):
    """本周选过的时间段 (开始, 结束)；没选过或已过期返回 None。"""
    try:
        with open(RANGE, encoding="utf-8") as f:
            saved = json.load(f)
    except FileNotFoundError:
        return None
    if saved["pinned_on"] >= str(monday):
        return saved["since"], saved["until"]
    os.remove(RANGE)
    return None


def main():
    today = datetime.date.today()
    monday = today - datetime.timedelta(days=today.weekday())
    saved = pinned(monday)
    start, end = saved if saved else (str(monday), str(today))
    label = "这段时间" if saved else "本周"
    log = commits(config(), f"{start} 00:00", f"{end} 23:59:59")
    body = ask_claude(PROMPT.format(label=label, start=start, end=end, commits=log)) if log else f"{label}暂无提交。"
    write("weekly", f"周报 {start[5:]} ~ {end[5:]}", body)


if __name__ == "__main__":
    if sys.argv[1:] == ["reset"]:
        if os.path.exists(RANGE):
            os.remove(RANGE)
    elif len(sys.argv) == 3:
        with open(RANGE, "w", encoding="utf-8") as f:
            json.dump({"since": sys.argv[1], "until": sys.argv[2], "pinned_on": str(datetime.date.today())}, f)
    main()
