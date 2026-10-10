"""GitLab API：用 git 已保存的凭据换取临时访问令牌，不需要单独建 token。"""
import json
import subprocess
import urllib.parse
import urllib.request

_tokens = {}
# 走密码换令牌的都是内网自建 GitLab，经代理反而连不上
_open = urllib.request.build_opener(urllib.request.ProxyHandler({})).open


def _token(base):
    if base not in _tokens:
        url = urllib.parse.urlsplit(base)
        filled = subprocess.run(
            ["git", "credential", "fill"], input=f"protocol={url.scheme}\nhost={url.netloc}\n\n",
            capture_output=True, text=True, check=True, env={"GIT_TERMINAL_PROMPT": "0", "PATH": "/usr/bin:/bin"}).stdout
        cred = dict(line.split("=", 1) for line in filled.splitlines() if "=" in line)
        body = json.dumps({"grant_type": "password", "username": cred["username"], "password": cred["password"]})
        request = urllib.request.Request(
            base + "/oauth/token", data=body.encode(), headers={"Content-Type": "application/json"})
        with _open(request, timeout=20) as response:
            _tokens[base] = json.load(response)["access_token"]
    return _tokens[base]


def api(base, path, raw=False):
    """GET /api/v4<path>。raw=True 返回原始文本（读仓库文件用），否则解析 JSON。"""
    base = base.rstrip("/")
    request = urllib.request.Request(base + "/api/v4" + path, headers={"Authorization": "Bearer " + _token(base)})
    with _open(request, timeout=20) as response:
        return response.read().decode() if raw else json.load(response)
