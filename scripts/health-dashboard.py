#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ClawTeam 健康检查 Dashboard v1.0.1
纯 Python 内置库实现，支持 serve 和 export 两种模式。
"""
__version__ = "1.0.1"

import http.server
import json
import pathlib
import datetime
import socket
import sys
import os
import io
from typing import Optional

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

TEAMS_DIR = pathlib.Path(os.environ.get(
    "CLAWTEAM_SHARED",
    pathlib.Path(__file__).parent.parent.parent / "shared" / "team-brain" / "teams"
))
SCRIPT_DIR = pathlib.Path(__file__).parent


def load_teams() -> list[dict]:
    """读取所有团队状态文件"""
    teams = []
    if not TEAMS_DIR.exists():
        return teams
    for f in TEAMS_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            data["_file"] = f.name
            teams.append(data)
        except Exception:
            pass
    return sorted(teams, key=lambda x: x.get("created_at", ""))


def get_health_status(agent_statuses: list) -> tuple[str, str]:
    """根据 agent 状态计算健康状态"""
    if not agent_statuses:
        return "🔴", "无 Agent"
    alive = sum(1 for s in agent_statuses if s.get("status") != "dead")
    total = len(agent_statuses)
    ratio = alive / total
    if ratio >= 0.8:
        return "🟢", f"{alive}/{total} 活跃"
    elif ratio >= 0.5:
        return "🟡", f"{alive}/{total} 活跃"
    else:
        return "🔴", f"{alive}/{total} 活跃"


def escape_html(text: str) -> str:
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;"))


def build_html(teams: list[dict], title: str = "ClawTeam 健康检查 Dashboard") -> str:
    """生成 HTML 页面"""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    total_teams = len(teams)
    total_agents = 0
    alive_agents = 0
    for t in teams:
        agents = t.get("agents", [])
        total_agents += len(agents)
        alive_agents += sum(1 for a in agents if a.get("status") != "dead")

    rows = ""
    for t in teams:
        name = escape_html(t.get("name", "?"))
        agents = t.get("agents", [])
        icon, label = get_health_status(agents)
        agent_list = "".join(
            f'<span class="agent {"dead" if a.get("status")=="dead" else "alive"}">'
            f'{escape_html(a.get("name","?"))}</span> '
            for a in agents
        )
        rows += f"""<tr>
            <td>{icon} {name}</td>
            <td>{label}</td>
            <td>{agent_list}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{escape_html(title)}</title>
<style>
body {{ font-family: system-ui, sans-serif; background: #0d1117; color: #c9d1d9; margin: 0; padding: 20px; }}
h1 {{ color: #58a6ff; }}
.summary {{ display: flex; gap: 20px; margin: 20px 0; }}
.card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; flex: 1; }}
.card .num {{ font-size: 2em; font-weight: bold; color: #58a6ff; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
th, td {{ text-align: left; padding: 10px; border-bottom: 1px solid #30363d; }}
th {{ color: #8b949e; }}
.agent {{ display: inline-block; padding: 2px 8px; border-radius: 4px; margin: 2px; font-size: 0.9em; }}
.alive {{ background: #1b4721; color: #3fb950; }}
.dead {{ background: #47211b; color: #f85149; }}
.footer {{ margin-top: 30px; color: #8b949e; font-size: 0.85em; }}
</style>
</head>
<body>
<h1>{escape_html(title)}</h1>
<div class="summary">
    <div class="card"><div class="num">{total_teams}</div>团队</div>
    <div class="card"><div class="num">{total_agents}</div>Agent</div>
    <div class="card"><div class="num">{alive_agents}</div>活跃</div>
</div>
<table>
<tr><th>团队</th><th>状态</th><th>Agent</th></tr>
{rows}
</table>
<div class="footer">更新于 {now} | v{__version__}</div>
</body>
</html>"""
    return html


class DashboardHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        teams = load_teams()
        html = build_html(teams)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html.encode("utf-8"))))
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def log_message(self, fmt, *args):
        print(f"[DASHBOARD] {args[0] if args else ''}", file=sys.stderr)


def find_free_port(start: int = 8080, end: int = 8100) -> int:
    for port in range(start, end):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("", port))
            s.close()
            return port
        except OSError:
            s.close()
    return 0


def serve(port: Optional[int] = None):
    if port is None:
        port = find_free_port()
    if not port:
        print("ERROR: 未找到可用端口 (8080-8100)", file=sys.stderr)
        sys.exit(1)
    server = http.server.HTTPServer(("", port), DashboardHandler)
    print(f"DASHBOARD: http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDASHBOARD: 已停止")
        server.server_close()


def export(output_path: Optional[str] = None):
    teams = load_teams()
    html = build_html(teams)
    if output_path:
        pathlib.Path(output_path).write_text(html, encoding="utf-8")
        print(f"DASHBOARD: 已导出到 {output_path}")
    else:
        print(html)


def main():
    import argparse
    ap = argparse.ArgumentParser(description="健康检查 Dashboard v" + __version__)
    ap.add_argument("mode", nargs="?", default="serve", choices=["serve", "export"],
                    help="serve: 启动 HTTP 服务 (默认), export: 导出 HTML")
    ap.add_argument("--port", type=int, default=None, help="HTTP 端口 (默认: 8080)")
    ap.add_argument("--output", default=None, help="导出文件路径")
    args = ap.parse_args()

    if args.mode == "serve":
        serve(args.port)
    else:
        export(args.output)


if __name__ == "__main__":
    main()
