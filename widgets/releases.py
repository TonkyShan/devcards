"""发布：从 GitOps 部署仓库读出各服务在每个环境的当前版本，以及源码仓库最新的发布分支和流水线状态。

约定部署仓库里每个服务一个目录、其下每个环境一个子目录；环境目录最近一次提交就是最近一次发布。
环境目录里如果有 SOURCE_COMMIT 文件，取它作为版本号。显示的是期望状态，不保证集群已经跑到这一版。

config.json:
  "gitlab": "http://gitlab.example.com",
  "releases": {
    "deploy_project": "ops/deploy", "ref": "master",
    "services": [{"name": "shop-api", "path": "shop-api-k8s", "project": "backend/shop-api"}]
  }
service 的 project（源码仓库）可省略，省略则不显示发布分支。
"""
import datetime
import urllib.error
import urllib.parse

import gitlab
from common import config, write

quote = lambda s: urllib.parse.quote(s, safe="")


def environments(base, deploy, ref, path):
    versioned, plain = [], []
    tree = gitlab.api(base, f"/projects/{deploy}/repository/tree?path={quote(path)}&ref={ref}&per_page=100")
    for env in sorted(item["name"] for item in tree if item["type"] == "tree"):
        directory = f"{path}/{env}"
        last = gitlab.api(
            base, f"/projects/{deploy}/repository/commits?path={quote(directory)}&ref_name={ref}&per_page=1")[0]
        try:
            source = gitlab.api(
                base, f"/projects/{deploy}/repository/files/{quote(directory + '/SOURCE_COMMIT')}/raw?ref={ref}",
                raw=True).strip()[:8]
        except urllib.error.HTTPError:
            source = ""
        when = datetime.datetime.fromisoformat(last["committed_date"].replace("Z", "+00:00")).astimezone()
        # 有版本号时提交标题基本是重复信息，只在没有版本号时显示
        if source:
            versioned.append(f"- **{env}** `{source}` · {when:%m-%d %H:%M}")
        else:
            plain.append(f"- **{env}** {when:%m-%d %H:%M} {last['title']}")
    # 只要有目录带 SOURCE_COMMIT，没带的就当作不是环境（比如公共的基础设施目录）
    return versioned or plain


def latest_release(base, project, prefix):
    """源码仓库里最新的发布分支及其流水线状态，没有则返回空串。"""
    project = quote(project)
    branches = gitlab.api(base, f"/projects/{project}/repository/branches?search={quote(prefix)}&per_page=100")
    branches = [b for b in branches if b["name"].startswith(prefix)]
    if not branches:
        return ""
    branch = max(branches, key=lambda b: b["commit"]["committed_date"])
    pipelines = gitlab.api(base, f"/projects/{project}/pipelines?ref={quote(branch['name'])}&per_page=1")
    status = f"（流水线 {pipelines[0]['status']}）" if pipelines else ""
    return f"分支：{branch['name']} `{branch['commit']['short_id']}`{status}"


def main():
    cfg = config()
    releases = cfg.get("releases")
    if not (cfg.get("gitlab") and releases):
        write("releases", "发布", "## 概览\n- 还没配置数据源：在 config.json 里填 `gitlab` 和 `releases`")
        return
    base, ref = cfg["gitlab"], releases.get("ref", "master")
    sections = []
    for service in releases["services"]:
        lines = []
        if service.get("project"):
            lines.append(latest_release(base, service["project"], releases.get("branch_prefix", "release-")))
        lines += environments(base, quote(releases["deploy_project"]), ref, service["path"])
        sections.append(f"## {service['name']}\n" + "\n".join(l for l in lines if l))
    write("releases", "发布", "\n\n".join(sections))
