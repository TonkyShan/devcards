# WeeklyReport

macOS 桌面周报卡片：每天自动汇总本周一以来你在本地各 git 仓库的提交，用 [Claude Code](https://claude.com/claude-code) 整理成周会可用的周报（做了什么功能、在哪些分支、修了什么问题），显示在一张贴在桌面上的卡片里。

<img src="docs/screenshot.png" width="460" alt="桌面周报卡片效果（示例数据）">

## 依赖

- macOS 13+，Xcode Command Line Tools（`xcode-select --install`，提供 `swiftc`、`git`、`/usr/bin/python3`）
- 已登录的 `claude` 命令行

## 安装

```bash
./install.sh ~/code            # 参数是存放各仓库的目录，可以传多个
HOUR=9 ./install.sh ~/code     # 改成每天 9 点生成，默认 18 点
```

脚本会编译 `build/WeeklyReport.app`，并安装两个 LaunchAgent：

- `weeklyreport.generate`：每天定时生成周报
- `weeklyreport.app`：登录时启动桌面卡片

卡片可拖动、可拉伸，右上角三个按钮分别是立即重新生成、复制 Markdown、退出。

## 配置

`~/Library/Application Support/WeeklyReport/config.json`：

```json
{
  "roots": ["/Users/me/code"],
  "authors": []
}
```

- `roots`：存放仓库的目录，扫描其下一层带 `.git` 的子目录
- `authors`：额外的提交身份（邮箱或名字）。默认已按每个仓库的 `git config user.email` 识别你的提交，只有用过别的邮箱提交时才需要填

修改 `generate.py`（比如提示词）后重新执行 `./install.sh` 生效。

## 说明

- 统计本地分支和已拉取的远端分支，不含 merge 提交，不会主动 `git fetch`
- 提交记录会发送给 Claude 用于生成摘要
- 周报文件：`~/Library/Application Support/WeeklyReport/report.md`，日志：`~/Library/Logs/WeeklyReport.log`

## 卸载

```bash
launchctl bootout gui/$UID/weeklyreport.generate
launchctl bootout gui/$UID/weeklyreport.app
rm ~/Library/LaunchAgents/weeklyreport.*.plist
rm -r ~/Library/Application\ Support/WeeklyReport
```
