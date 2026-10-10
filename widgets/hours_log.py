"""把工时卡片上待登记的条目写入 ONES。只在用户点卡片上的登记按钮并确认后运行。"""
import datetime
import json

import hours
import mcp
from common import config


def main():
    server = config()["ones_mcp"]
    mode = mcp.call(server, "get_manhour_mode")["result"]  # simple 或 summary
    logged = hours.load(hours.LOGGED)
    try:
        for entry in hours.load(hours.PENDING):
            start = datetime.datetime.fromisoformat(entry["date"] + "T09:00:00").astimezone().isoformat()
            mcp.call(server, f"add_workhour_in_{mode}_mode", issueID=entry["issue"], hours=entry["hours"],
                     startTime=start, description=entry["description"])
            logged.append([entry["key"], entry["date"]])
    finally:
        # 中途失败也要记下已经登记成功的，避免重试时重复登记
        with open(hours.LOGGED, "w", encoding="utf-8") as f:
            json.dump(logged, f, ensure_ascii=False, indent=2)
        hours.main()
