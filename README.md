# WeeklyReport

macOS 桌面开发者卡片：一张贴在桌面上的卡片，用标签页切换几个小组件，数据都来自你本机的 git 仓库和 [Claude Code](https://claude.com/claude-code)。

| 标签 | 内容 | 刷新 |
|---|---|---|
| 周报 | 本周一以来你在各仓库的提交，由 claude 整理成周会用的周报（功能、分支、修复） | 每天 9 点、18 点 |
| 站会 | 上一个工作日到现在的提交，整理成站会发言要点 | 每天 9 点、18 点 |
| 仓库 | 按组列出有未提交改动、未推送提交或落后远端的仓库 | 每 15 分钟 |
| 用量 | Claude Code 今天和本周的 token 用量，按天、项目、模型拆分 | 每 15 分钟 |

<img src="docs/screenshot.png" width="460" alt="桌面周报卡片效果（示例数据）">

## 依赖

- macOS 13+，Xcode Command Line Tools（`xcode-select --install`，提供 `swiftc`、`git`、`/usr/bin/python3`）
- 已登录的 `claude` 命令行

## 安装

```bash
./install.sh ~/code            # 参数是存放各仓库的目录，可以传多个
HOUR=17 ./install.sh ~/code    # 傍晚那次改到 17 点，默认 18 点
```

脚本会编译 `build/WeeklyReport.app`，并安装三个 LaunchAgent：

- `weeklyreport.generate`：每天 9 点和 18 点生成周报与站会
- `weeklyreport.local`：每 15 分钟刷新仓库状态与用量
- `weeklyreport.app`：登录时启动桌面卡片

卡片可拖动、可拉伸，右上角三个按钮分别是立即重新生成当前标签、复制 Markdown、退出。

## 配置

`~/Library/Application Support/WeeklyReport/config.json`：

```json
{
  "roots": ["/Users/me/code"],
  "authors": [],
  "groups": {"后端": ["shop-api", "pay-service"]}
}
```

- `roots`：存放仓库的目录，扫描其下一层带 `.git` 的子目录
- `authors`：额外的提交身份（邮箱或名字）。默认已按每个仓库的 `git config user.email` 识别你的提交，只有用过别的邮箱提交时才需要填
- `groups`：可选，手动指定仓库分组（组名 → 仓库目录名）。没指定的仓库按 `origin` 地址里的命名空间自动归组，比如 `git@host:backend/shop-api.git` 归到 `backend`

修改 `widgets/` 下的脚本（比如提示词）后重新执行 `./install.sh` 生效。

## 加一个小组件

每个小组件是 `widgets/` 下的一个 Python 脚本，只做一件事：把 Markdown 写到数据目录。卡片负责渲染，`# ` 是标题，每个 `## ` 是一个分块，支持 `- ` 列表、`**加粗**` 和行内代码。

1. 新建 `widgets/foo.py`，实现 `main()`，最后调用 `common.write("foo", "标题", body)`
2. 在 `main.swift` 的 `widgets` 列表里加一行
3. 在 `install.sh` 里把 `foo` 加到某个定时任务的参数里

手动运行：`python3 widgets/run.py foo`。

## 说明

- 统计本地分支和已拉取的远端分支，不含 merge 提交，不会主动 `git fetch`
- 周报和站会会把提交记录发送给 Claude 用于生成摘要；仓库状态和用量只在本机计算
- 仓库状态里的"落后远端"以上次 `git fetch` 的结果为准
- 各标签内容：`~/Library/Application Support/WeeklyReport/<组件名>.md`，日志：`~/Library/Logs/WeeklyReport.log`

## 卸载

```bash
launchctl bootout gui/$UID/weeklyreport.generate
launchctl bootout gui/$UID/weeklyreport.local
launchctl bootout gui/$UID/weeklyreport.app
rm ~/Library/LaunchAgents/weeklyreport.*.plist
rm -r ~/Library/Application\ Support/WeeklyReport
```
