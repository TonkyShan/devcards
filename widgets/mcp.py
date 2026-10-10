"""直接调用 Claude Code 里已配置的 HTTP MCP 服务（复用它的地址和鉴权），不经过模型。"""
import json
import os
import subprocess
import urllib.request

_servers = {}


def _server(name):
    if name not in _servers:
        with open(os.path.expanduser("~/.claude.json"), encoding="utf-8") as f:
            cfg = json.load(f)["mcpServers"][name]
        headers = dict(cfg.get("headers", {}))
        if cfg.get("headersHelper"):
            helper = subprocess.run(cfg["headersHelper"], shell=True, capture_output=True, text=True, check=True)
            headers.update(json.loads(helper.stdout))
        _servers[name] = (cfg["url"], headers)
    return _servers[name]


def call(server, tool, **arguments):
    url, headers = _server(server)
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": tool, "arguments": arguments}}
    request = urllib.request.Request(url, data=json.dumps(body).encode(), headers={
        "Content-Type": "application/json", "Accept": "application/json, text/event-stream", **headers})
    with urllib.request.urlopen(request, timeout=30) as response:
        text = response.read().decode()
    # 响应可能是纯 JSON，也可能是 SSE（data: 开头的行）
    payload = json.loads(next((l[5:] for l in text.splitlines() if l.startswith("data:")), text))
    if "error" in payload or payload["result"].get("isError"):
        raise RuntimeError(f"{tool} 调用失败: {text[:500]}")
    return json.loads(payload["result"]["content"][0]["text"])
