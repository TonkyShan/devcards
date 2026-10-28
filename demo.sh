#!/bin/bash
# 用法: ./demo.sh
# 用 docs/demo 里的示例数据单独打开一张卡片，录屏、截图用，不碰 ~/Library/Application Support/DevCards。
# 演示版每 2.5 秒自动切换标签；不带刷新脚本，误点刷新只会显示失败，不会用真实数据覆盖示例。
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p build
swiftc -O -D DEMO main.swift -o build/DevCards-demo
DEVCARDS_DATA="$PWD/docs/demo" exec build/DevCards-demo
