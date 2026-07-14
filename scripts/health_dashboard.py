#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ClawTeam 健康检查 Dashboard v2.0
支持 HTTP serve / export / Prometheus metrics / 熔断器可视化 / 失败聚合。
"""
__version__ = "2.0.0"

import http.server
import json
import pathlib
import datetime
import socket
import sys
import os
import io
import collections
import time
from typing import Optional

from scripts._paths import (
    TEAMS_DIR as _TEAMS_DIR, CB_DIR as _CB_DIR,
    REPAIR_DIR as _REPAIR_DIR, SKILL_DIR as _SKILL_DIR,
)

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

SKILL_DIR = _SKILL_DIR
TEAMS_DIR = _TEAMS_DIR
CB_DIR = _CB_DIR
REPAIR_DIR = _REPAIR_DIR
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


def load_circuit_breakers() -> list[dict]:
    """读取所有熔断器状态"""
    result = []
    if not CB_DIR.exists():
        return result
    for f in sorted(CB_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            data["_file"] = f.name
            result.append(data)
        except Exception:
            pass
    return result


def load_repair_records() -> list[dict]:
    """读取所有修复记录"""
    result = []
    if not REPAIR_DIR.exists():
        return result
    for f in sorted(REPAIR_DIR.glob("*.json")):
        try:
            records = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(records, list):
                for r in records:
                    r["_source"] = f.name
                result.extend(records)
        except Exception:
            pass
    return result


def _prom_label(v: str) -> str:
    """转义 Prometheus label value（反斜杠、引号、换行）"""
    return v.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def build_metrics(teams: list[dict]) -> str:
    """生成 Prometheus 文本格式指标"""
    lines = []
    now = time.time()
    lines.append('# HELP clawteam_team_total 团队总数')
    lines.append('# TYPE clawteam_team_total gauge')
    lines.append(f'clawteam_team_total {len(teams)}')
    total_agents = 0
    alive_agents = 0
    for t in teams:
        agents = t.get("agents", [])
        total_agents += len(agents)
        alive_agents += sum(1 for a in agents if a.get("status") != "dead")
    lines.append('# HELP clawteam_agent_total Agent 总数')
    lines.append('# TYPE clawteam_agent_total gauge')
    lines.append(f'clawteam_agent_total {total_agents}')
    lines.append('# HELP clawteam_agent_alive 活跃 Agent 数')
    lines.append('# TYPE clawteam_agent_alive gauge')
    lines.append(f'clawteam_agent_alive {alive_agents}')
    lines.append('# HELP clawteam_agent_dead 死亡 Agent 数')
    lines.append('# TYPE clawteam_agent_dead gauge')
    lines.append(f'clawteam_agent_dead {total_agents - alive_agents}')
    for t in teams:
        name = t.get("name", "?")
        agents = t.get("agents", [])
        alive = sum(1 for a in agents if a.get("status") != "dead")
        lines.append(f'# HELP clawteam_team_health 团队健康状态')
        lines.append(f'# TYPE clawteam_team_health gauge')
        lines.append(f'clawteam_team_health{{team="{_prom_label(name)}"}} {alive}')
    cbs = load_circuit_breakers()
    for cb in cbs:
        state = cb.get("state", "CLOSED")
        state_val = {"CLOSED": 0, "HALF_OPEN": 1, "OPEN": 2}.get(state, 0)
        failure_count = cb.get("failure_count", 0)
        lines.append(f'# HELP clawteam_circuit_breaker 熔断器状态')
        lines.append(f'# TYPE clawteam_circuit_breaker gauge')
        cb_name = _prom_label(cb.get("name", "?"))
        lines.append(f'clawteam_circuit_breaker{{name="{cb_name}",state="{state}"}} {state_val}')
        lines.append(f'# HELP clawteam_circuit_breaker_failures 熔断器失败计数')
        lines.append(f'# TYPE clawteam_circuit_breaker_failures counter')
        lines.append(f'clawteam_circuit_breaker_failures{{name="{cb_name}"}} {failure_count}')
    records = load_repair_records()
    by_type = collections.Counter(r.get("fault_type", "unknown") for r in records)
    for ft, count in by_type.items():
        lines.append(f'# HELP clawteam_repairs_total 修复次数按故障类型')
        lines.append(f'# TYPE clawteam_repairs_total counter')
        lines.append(f'clawteam_repairs_total{{fault_type="{_prom_label(ft)}"}} {count}')
    lines.append(f'# HELP clawteam_repairs_total_all 总修复次数')
    lines.append(f'# TYPE clawteam_repairs_total_all counter')
    lines.append(f'clawteam_repairs_total_all {len(records)}')
    lines.append(f'# HELP clawteam_up 服务存活 1=正常')
    lines.append(f'# TYPE clawteam_up gauge')
    lines.append(f'clawteam_up 1')
    lines.append(f'# EOF clawteam_metrics')
    return '\n'.join(lines) + '\n'


def escape_html(text: str) -> str:
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;"))


def _cb_state_icon(state: str) -> tuple[str, str]:
    m = {"CLOSED": ("🟢", "closed"), "OPEN": ("🔴", "open"), "HALF_OPEN": ("🟡", "half-open")}
    return m.get(state, ("⚪", "unknown"))


def build_html(teams: list[dict], title: str = "ClawTeam 健康检查 Dashboard") -> str:
    """生成 HTML 页面（含熔断器和失败聚合）"""
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

    # 熔断器区
    cbs = load_circuit_breakers()
    cb_rows = ""
    for cb in cbs:
        name = escape_html(cb.get("name", "?"))
        state = cb.get("state", "CLOSED")
        icon, cls = _cb_state_icon(state)
        fails = cb.get("failure_count", 0)
        cb_rows += f"""<tr>
            <td>{icon} {name}</td>
            <td class="cb-{cls}">{state}</td>
            <td>{fails}</td>
            <td>{cb.get("success_count", 0)}</td>
            <td>{cb.get("failure_threshold", 3)}</td>
        </tr>"""

    # 失败类型聚合
    records = load_repair_records()
    by_type = collections.Counter(r.get("fault_type", "unknown") for r in records)
    by_action = collections.Counter(r.get("action", "unknown") for r in records)
    top_types = by_type.most_common(10)
    ft_rows = "".join(
        f'<tr><td>{escape_html(ft)}</td><td>{cnt}</td></tr>'
        for ft, cnt in top_types
    )
    top_actions = by_action.most_common(10)
    act_rows = "".join(
        f'<tr><td>{escape_html(a)}</td><td>{cnt}</td></tr>'
        for a, cnt in top_actions
    )

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{escape_html(title)}</title>
<style>
body {{ font-family: system-ui, sans-serif; background: #0d1117; color: #c9d1d9; margin: 0; padding: 20px; }}
h1 {{ color: #58a6ff; }} h2 {{ color: #58a6ff; margin-top: 30px; }}
.summary {{ display: flex; gap: 20px; margin: 20px 0; }}
.card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; flex: 1; }}
.card .num {{ font-size: 2em; font-weight: bold; color: #58a6ff; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
th, td {{ text-align: left; padding: 10px; border-bottom: 1px solid #30363d; }}
th {{ color: #8b949e; }}
.agent {{ display: inline-block; padding: 2px 8px; border-radius: 4px; margin: 2px; font-size: 0.9em; }}
.alive {{ background: #1b4721; color: #3fb950; }}
.dead {{ background: #47211b; color: #f85149; }}
.cb-closed {{ color: #3fb950; }} .cb-open {{ color: #f85149; font-weight: bold; }}
.cb-half-open {{ color: #d29922; }}
.footer {{ margin-top: 30px; color: #8b949e; font-size: 0.85em; }}
.dual-col {{ display: flex; gap: 20px; }}
.dual-col > div {{ flex: 1; }}
</style>
</head>
<body>
<h1>{escape_html(title)}</h1>
<div class="summary">
    <div class="card"><div class="num">{total_teams}</div>团队</div>
    <div class="card"><div class="num">{total_agents}</div>Agent</div>
    <div class="card"><div class="num">{alive_agents}</div>活跃</div>
</div>
<h2>团队状态</h2>
<table>
<tr><th>团队</th><th>健康</th><th>Agent</th></tr>
{rows}
</table>
<h2>熔断器</h2>
<table>
<tr><th>名称</th><th>状态</th><th>失败</th><th>成功</th><th>阈值</th></tr>
{cb_rows if cb_rows else '<tr><td colspan="5">无熔断器数据</td></tr>'}
</table>
<h2>失败聚合</h2>
<div class="dual-col">
<div>
<h3>按故障类型</h3>
<table><tr><th>类型</th><th>次数</th></tr>{ft_rows if ft_rows else '<tr><td colspan="2">无记录</td></tr>'}</table>
</div>
<div>
<h3>按恢复动作</h3>
<table><tr><th>动作</th><th>次数</th></tr>{act_rows if act_rows else '<tr><td colspan="2">无记录</td></tr>'}</table>
</div>
</div>
<div class="footer">
  更新于 {now} | v{__version__} |
  <a href="/metrics" style="color: #58a6ff;">Prometheus /metrics</a> |
  <a href="/api/teams" style="color: #58a6ff;">API teams</a> |
  <a href="/api/circuit-breakers" style="color: #58a6ff;">API circuit-breakers</a> |
  <a href="/api/failures" style="color: #58a6ff;">API failures</a>
</div>
</body>
</html>"""
    return html


class DashboardHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        teams = load_teams()

        if self.path == "/metrics":
            body = build_metrics(teams).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/api/teams":
            body = json.dumps([{
                "name": t.get("name"), "phase": t.get("phase"),
                "agents": len(t.get("agents", [])),
                "alive": sum(1 for a in t.get("agents", []) if a.get("status") != "dead"),
            } for t in teams], ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/api/circuit-breakers":
            cbs = load_circuit_breakers()
            body = json.dumps(cbs, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/api/failures":
            records = load_repair_records()
            by_type = dict(collections.Counter(r.get("fault_type", "unknown") for r in records).most_common(20))
            by_action = dict(collections.Counter(r.get("action", "unknown") for r in records).most_common(20))
            body = json.dumps({"total": len(records), "by_fault_type": by_type,
                               "by_action": by_action}, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

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
