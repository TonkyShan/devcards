#!/usr/bin/python3
"""用法: run.py <组件名>...  依次生成各卡片内容，某个失败不影响其余。"""
import importlib
import sys
import traceback

failed = False
for name in sys.argv[1:]:
    try:
        importlib.import_module(name).main()
    except Exception:
        traceback.print_exc()
        failed = True
sys.exit(failed)
