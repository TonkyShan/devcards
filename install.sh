#!/bin/bash
# 用法: ./install.sh <仓库所在目录>...
# 编译桌面卡片应用，并安装两个 LaunchAgent：每天定时生成周报（默认 18 点，可用 HOUR=9 覆盖）、登录时启动卡片。
set -euo pipefail

DATA="$HOME/Library/Application Support/WeeklyReport"
CONFIG="$DATA/config.json"
mkdir -p "$DATA"
if [ $# -gt 0 ]; then
  python3 -c 'import json, os, sys; json.dump({"roots": [os.path.abspath(p) for p in sys.argv[2:]], "authors": []}, open(sys.argv[1], "w"), indent=2, ensure_ascii=False)' "$CONFIG" "$@"
elif [ ! -f "$CONFIG" ]; then
  echo "用法: $0 <仓库所在目录>..." >&2
  exit 1
fi

cd "$(dirname "$0")"

APP="$PWD/build/WeeklyReport.app"
AGENTS="$HOME/Library/LaunchAgents"
LOG="$HOME/Library/Logs/WeeklyReport.log"
GEN=weeklyreport.generate
CARD=weeklyreport.app

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources" "$AGENTS"
swiftc -O main.swift -o "$APP/Contents/MacOS/WeeklyReport"
cp generate.py "$APP/Contents/Resources/"
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
    <string>$APP/Contents/Resources/generate.py</string>
  </array>
  <key>StartCalendarInterval</key><dict>
    <key>Hour</key><integer>${HOUR:-18}</integer>
    <key>Minute</key><integer>0</integer>
  </dict>
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

for label in $GEN $CARD; do
  launchctl bootout "gui/$UID/$label" 2>/dev/null || true
  launchctl bootstrap "gui/$UID" "$AGENTS/$label.plist"
done
echo "已安装：$APP"
echo "配置文件：$CONFIG"
