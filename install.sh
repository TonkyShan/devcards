#!/bin/bash
# 用法: ./install.sh <仓库所在目录>...
# 编译桌面卡片应用，并安装三个 LaunchAgent：每天 9 点和 18 点（后者可用 HOUR=17 覆盖）生成周报、站会与工时、
# 每 15 分钟刷新仓库状态、用量、待办与发布，登录时启动卡片。
set -euo pipefail

DATA="$HOME/Library/Application Support/WeeklyReport"
CONFIG="$DATA/config.json"
mkdir -p "$DATA"
if [ $# -gt 0 ]; then
  # 只更新 roots，保留配置里的其他项
  python3 -c 'import json, os, sys
path = sys.argv[1]
cfg = json.load(open(path)) if os.path.exists(path) else {"authors": []}
cfg["roots"] = [os.path.abspath(p) for p in sys.argv[2:]]
json.dump(cfg, open(path, "w"), indent=2, ensure_ascii=False)' "$CONFIG" "$@"
elif [ ! -f "$CONFIG" ]; then
  echo "用法: $0 <仓库所在目录>..." >&2
  exit 1
fi

cd "$(dirname "$0")"

APP="$PWD/build/WeeklyReport.app"
AGENTS="$HOME/Library/LaunchAgents"
LOG="$HOME/Library/Logs/WeeklyReport.log"
GEN=weeklyreport.generate
LOCAL=weeklyreport.local
CARD=weeklyreport.app

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources" "$AGENTS"
swiftc -O main.swift -o "$APP/Contents/MacOS/WeeklyReport"
cp -R widgets "$APP/Contents/Resources/"
cat > "$APP/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleIdentifier</key><string>$CARD</string>
  <key>CFBundleName</key><string>WeeklyReport</string>
  <key>CFBundleExecutable</key><string>WeeklyReport</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>LSUIElement</key><true/>
</dict></plist>
EOF

cat > "$AGENTS/$GEN.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$GEN</string>
  <key>ProgramArguments</key><array>
    <string>/usr/bin/python3</string>
    <string>$APP/Contents/Resources/widgets/run.py</string>
    <string>weekly</string>
    <string>standup</string>
    <string>hours</string>
  </array>
  <key>StartCalendarInterval</key><array>
    <dict><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Hour</key><integer>${HOUR:-18}</integer><key>Minute</key><integer>0</integer></dict>
  </array>
  <key>StandardOutPath</key><string>$LOG</string>
  <key>StandardErrorPath</key><string>$LOG</string>
</dict></plist>
EOF

cat > "$AGENTS/$LOCAL.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LOCAL</string>
  <key>ProgramArguments</key><array>
    <string>/usr/bin/python3</string>
    <string>$APP/Contents/Resources/widgets/run.py</string>
    <string>repos</string>
    <string>usage</string>
    <string>todo</string>
    <string>releases</string>
  </array>
  <key>StartInterval</key><integer>900</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$LOG</string>
  <key>StandardErrorPath</key><string>$LOG</string>
</dict></plist>
EOF

cat > "$AGENTS/$CARD.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$CARD</string>
  <key>ProgramArguments</key><array>
    <string>$APP/Contents/MacOS/WeeklyReport</string>
  </array>
  <key>RunAtLoad</key><true/>
</dict></plist>
EOF

for label in $GEN $LOCAL $CARD; do
  launchctl bootout "gui/$UID/$label" 2>/dev/null || true
  # bootout 是异步的，旧服务没卸载完就 bootstrap 会报 I/O error
  while launchctl print "gui/$UID/$label" &>/dev/null; do sleep 0.2; done
  launchctl bootstrap "gui/$UID" "$AGENTS/$label.plist"
done
echo "已安装：$APP"
echo "配置文件：$CONFIG"
