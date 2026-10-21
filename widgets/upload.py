#!/usr/bin/python3
"""上传：把拖到卡片上的文件传到服务器共享盘，并列出共享盘上最近的文件。
用法: upload.py <文件>...   上传；不带参数（刷新按钮）时只列文件。
配置里 upload.hosts 是能挂到共享盘的几台机器（ssh 目标），依次尝试，传到第一台连得上的；upload.dir 是共享盘上的目录。"""
import os
import shlex
import subprocess
import sys

from common import config, write

SSH = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5"]


def ssh(host, command, **kwargs):
    return subprocess.run(SSH + [host, command], capture_output=True, **kwargs)


def send(host, folder, files):
    """打 tar 流过去解开；umask 022 让其他机器上 uid 不同的同名账号也读得到。"""
    args = []
    for f in files:
        args += ["-C", os.path.dirname(f), os.path.basename(f)]
    # COPYFILE_DISABLE 防止 macOS tar 带上 ._ 资源文件
    tar = subprocess.Popen(["tar", "-cf", "-", *args], stdout=subprocess.PIPE,
                           env={**os.environ, "COPYFILE_DISABLE": "1"})
    q = shlex.quote(folder)
    result = ssh(host, f"umask 022 && mkdir -p {q} && tar -xf - -C {q} --no-same-owner --no-same-permissions",
                 stdin=tar.stdout)
    tar.stdout.close()
    return tar.wait() == 0 and result.returncode == 0


def listing(host, folder):
    """共享盘上最近 20 个文件：(修改时间, 大小, 名字)。"""
    result = ssh(host, f"cd {shlex.quote(folder)} 2>/dev/null && ls -t --time-style=+%m-%d\\ %H:%M -lhA | head -21",
                 text=True)
    rows = []
    for line in result.stdout.splitlines()[1:]:
        parts = line.split(None, 7)
        if len(parts) == 8:
            rows.append((parts[5] + " " + parts[6], parts[4], parts[7]))
    return result.returncode == 0, rows


def main(files=()):
    cfg = config().get("upload")
    if not cfg:
        write("upload", "上传", "## 概览\n- 没有配置 `upload`，见 README")
        return
    folder = cfg["dir"]
    sections = []
    for host in cfg["hosts"]:
        if files and not send(host, folder, files):
            continue
        ok, rows = listing(host, folder)
        if ok or files:
            break
    else:
        raise RuntimeError("服务器都连不上：" + "、".join(cfg["hosts"]))

    overview = [f"- 把文件拖到卡片上就会传到 `{folder}/`，几台服务器都能读到"]
    if files:
        paths = [f"{folder}/{os.path.basename(f)}" for f in files]
        subprocess.run(["pbcopy"], input="\n".join(paths), text=True)
        overview.insert(0, f"- 刚传了 {len(files)} 个（经 {host}），路径已复制到剪贴板")
    sections.append("## 概览\n" + "\n".join(overview))
    sections.append("## 最近的文件\n" + ("\n".join(
        f"- `{name}` {size}，{time}" for time, size, name in rows) or "- 还没有文件"))
    write("upload", "上传", "\n\n".join(sections))


if __name__ == "__main__":
    main([os.path.abspath(f) for f in sys.argv[1:]])
