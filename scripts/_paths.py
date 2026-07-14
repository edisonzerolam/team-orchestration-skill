# -*- coding: utf-8 -*-
"""共享路径常量模块

所有模块从此处导入团队状态目录路径，消除硬编码不一致。
"""
import os
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent

STATE_DIR = SKILL_DIR / "shared" / "team-brain"
STATE_DIR.mkdir(parents=True, exist_ok=True)

CB_DIR = STATE_DIR / "circuit-breakers"
REPAIR_DIR = STATE_DIR / "repair-records"
TEAMS_DIR = Path(os.environ.get(
    "CLAWTEAM_SHARED",
    STATE_DIR / "teams"
))
SNAPSHOT_DIR = SKILL_DIR / "shared" / "snapshots"
SCORES_FILE = SKILL_DIR / "shared" / "expert-scores.json"
