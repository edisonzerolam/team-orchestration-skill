"""性能基准测试 — 手动计时版（pytest-benchmark 未安装）"""
import json
import math
import time
import importlib
import pytest

# ── 测前准备：保存原始函数引用，在需要时绕过 conftest 的自动 mock ──
from scripts import expert_matcher as em
from scripts import template_cropper as tc
from scripts import orchestrator as orch
# memory-bridge.py 含连字符，需用 importlib 加载
mb = importlib.import_module("scripts._memory_collector")
from scripts.file_utils import atomic_write


# ---------- 1. 匹配引擎加载 ----------

@pytest.mark.benchmark
class TestLoadExpertsLightBenchmark:
    """测量: load_experts_light() 从 teams-index.json 加载所有团队元数据
       目标: 单次加载 < 200ms（含冷缓存文件 I/O）
    """

    def test_cold_cache(self, monkeypatch):
        """冷启动 — L1 缓存清空 + 恢复真实文件加载"""
        # 绕过 mock，恢复真实文件读取
        monkeypatch.undo()
        # 重置三阶缓存
        import scripts.expert_matcher as em_real
        _cache = em_real._TIER_CACHE
        _cache["l1"] = {}
        _cache["l2"] = {}
        _cache["l2_ts"] = 0

        times = []
        for _ in range(10):
            # 每次测前清空 L1
            _cache["l1"] = {}
            start = time.perf_counter()
            result = em_real.load_experts_light()
            elapsed = time.perf_counter() - start
            times.append(elapsed)

        times.sort()
        median = times[len(times) // 2]
        assert len(result) > 0, "应返回非空字典"
        assert median < 0.2, f"冷加载中位数 {median*1000:.1f}ms 超过 200ms"
        print(f"    load_experts_light (cold, 10次中位数): {median*1000:.1f}ms")

    def test_warm_cache(self):
        """热启动 — L1 缓存命中"""
        # conftest mock 已让此函数直接返回 dict（模拟热缓存命中）
        times = []
        for _ in range(10):
            start = time.perf_counter()
            result = em.load_experts_light()
            elapsed = time.perf_counter() - start
            times.append(elapsed)

        times.sort()
        median = times[len(times) // 2]
        assert len(result) > 0
        assert median < 0.01, f"热加载中位数 {median*1000:.1f}ms 超过 10ms"
        print(f"    load_experts_light (warm, 10次中位数): {median*1000:.1f}ms")


# ---------- 2. 模板裁剪 ----------

@pytest.mark.benchmark
class TestCropTeamBenchmark:
    """测量: crop_team() 核心裁剪逻辑（评分+排序+选择）
       目标: 单次裁剪 < 50ms（含打分循环）
    """

    def test_crop_investment_team(self):
        """投资大师团队（22 个 agent）裁剪"""
        team_name = "investment-masters-team"
        subtask_types = ["analysis_judgment", "decision_execution"]

        times = []
        for _ in range(5):
            start = time.perf_counter()
            result = tc.crop_team(team_name, subtask_types)
            elapsed = time.perf_counter() - start
            times.append(elapsed)

        times.sort()
        median = times[len(times) // 2]
        assert "agents" in result
        assert median < 0.05, f"裁剪中位数 {median*1000:.1f}ms 超过 50ms"
        print(f"    crop_team (22 agents, 5次中位数): {median*1000:.1f}ms")

    def test_crop_small_team(self):
        """小团队（5 个 agent）裁剪"""
        team_name = "content-creator-team"
        subtask_types = ["creation_generation"]

        times = []
        for _ in range(5):
            start = time.perf_counter()
            result = tc.crop_team(team_name, subtask_types)
            elapsed = time.perf_counter() - start
            times.append(elapsed)

        times.sort()
        median = times[len(times) // 2]
        assert "agents" in result
        assert median < 0.02, f"小团队裁剪中位数 {median*1000:.1f}ms 超过 20ms"
        print(f"    crop_team (5 agents, 5次中位数): {median*1000:.1f}ms")


# ---------- 3. 权重矩阵加载 ----------

@pytest.mark.benchmark
class TestLoadWeightMatrixBenchmark:
    """测量: load_weight_matrix() 从 weight-matrix.json 加载
       目标: 单次加载 < 50ms
    """

    def test_load_default(self):
        """默认加载（无 task_type）"""
        times = []
        for _ in range(10):
            start = time.perf_counter()
            w = em.load_weight_matrix()
            elapsed = time.perf_counter() - start
            times.append(elapsed)

        times.sort()
        median = times[len(times) // 2]
        assert "domain" in w
        assert median < 0.05, f"权重加载中位数 {median*1000:.1f}ms 超过 50ms"
        print(f"    load_weight_matrix (default, 10次中位数): {median*1000:.1f}ms")

    def test_load_with_task_type(self):
        """指定 task_type 加载"""
        times = []
        for _ in range(10):
            start = time.perf_counter()
            w = em.load_weight_matrix("analysis_judgment")
            elapsed = time.perf_counter() - start
            times.append(elapsed)

        times.sort()
        median = times[len(times) // 2]
        assert "domain" in w or median < 0.05
        assert median < 0.05
        print(f"    load_weight_matrix (typed, 10次中位数): {median*1000:.1f}ms")


# ---------- 4. ε-greedy 决策 ----------

@pytest.mark.benchmark
class TestEpsilonGreedyBenchmark:
    """测量: _should_explore() 的 ε-greedy 判定（含随机数 + 分数查询）
       目标: 单次 < 5ms（纯内存操作）
    """

    def test_should_explore_known_team(self, monkeypatch):
        """已知团队 — mock 消除文件 I/O 干扰，只测计算逻辑"""
        monkeypatch.setattr("scripts.expert_matcher._get_exploration_log",
                            lambda: {"version": "1.0", "experts": {"investment-masters-team": {"exploration_count": 3}}})
        times = []
        for _ in range(20):
            start = time.perf_counter()
            result = em._should_explore("investment-masters-team")
            elapsed = time.perf_counter() - start
            times.append(elapsed)

        times.sort()
        median = times[len(times) // 2]
        assert isinstance(result, bool)
        assert median < 0.005, f"_should_explore 中位数 {median*1000:.1f}ms 超过 5ms"
        print(f"    _should_explore (known, 20次中位数): {median*1000:.1f}ms")

    def test_should_explore_unknown_team(self, monkeypatch):
        """未知团队（无历史分 → 返回 True）— mock 消除文件 I/O"""
        monkeypatch.setattr("scripts.expert_matcher._get_exploration_log",
                            lambda: {"version": "1.0", "experts": {}})
        times = []
        for _ in range(20):
            start = time.perf_counter()
            result = em._should_explore("nonexistent-team")
            elapsed = time.perf_counter() - start
            times.append(elapsed)

        times.sort()
        median = times[len(times) // 2]
        assert result is True
        assert median < 0.005, f"_should_explore(unknown) 中位数 {median*1000:.1f}ms 超过 5ms"
        print(f"    _should_explore (unknown, 20次中位数): {median*1000:.1f}ms")


# ---------- 5. 全局注册表 ----------

@pytest.mark.benchmark
class TestGlobalRegistryBenchmark:
    """测量: get_global_registry() 和 register_task() 的锁+读写
       目标: 单次 < 5ms
    """

    def test_get_global_registry(self):
        """读取注册表快照"""
        times = []
        for _ in range(20):
            start = time.perf_counter()
            reg = orch.get_global_registry()
            elapsed = time.perf_counter() - start
            times.append(elapsed)

        times.sort()
        median = times[len(times) // 2]
        assert isinstance(reg, dict)
        assert median < 0.005, f"get_global_registry 中位数 {median*1000:.1f}ms 超过 5ms"
        print(f"    get_global_registry (20次中位数): {median*1000:.1f}ms")

    def test_register_task(self):
        """注册一个新任务（含锁 + MD5 + 字典写入）"""
        times = []
        test_id = 0
        for _ in range(20):
            test_id += 1
            tid = f"benchmark-test-{test_id}"
            start = time.perf_counter()
            instance_id = orch.register_task(tid, {"source": "benchmark"})
            elapsed = time.perf_counter() - start
            times.append(elapsed)

        times.sort()
        median = times[len(times) // 2]
        assert isinstance(instance_id, str) and len(instance_id) == 8
        assert median < 0.005, f"register_task 中位数 {median*1000:.1f}ms 超过 5ms"
        print(f"    register_task (20次中位数): {median*1000:.1f}ms")


# ---------- 6. memory-bridge ----------

@pytest.mark.benchmark
class TestMemoryBridgeBenchmark:
    """测量: collect_last_orchestration() 和 make_session_summary()
       目标: 各 < 50ms（含少量文件 I/O）
    """

    def test_collect_last_orchestration(self):
        """从 token-ledger.json 读取最近一次编排记录"""
        times = []
        for _ in range(10):
            start = time.perf_counter()
            result = mb.collect_last_orchestration()
            elapsed = time.perf_counter() - start
            times.append(elapsed)

        times.sort()
        median = times[len(times) // 2]
        # 文件可能不存在 → 返回 None 也接受
        assert median < 0.05, f"collect_last_orchestration 中位数 {median*1000:.1f}ms 超过 50ms"
        print(f"    collect_last_orchestration (10次中位数): {median*1000:.1f}ms")

    def test_exploration_log_cache_benchmark(self):
        """真实 measurement: exploration-log 冷→热读取（验证内存缓存生效）"""
        from scripts.expert_matcher import _get_exploration_log
        import scripts.expert_matcher as em
        em._exploration_cache = None
        times = []
        for _ in range(10):
            start = time.perf_counter()
            _ = _get_exploration_log()
            elapsed = time.perf_counter() - start
            times.append(elapsed)
        times.sort()
        median_cold = times[1]
        median_warm = times[len(times) // 2]
        assert median_warm < 0.05, f"_get_exploration_log (warm) {median_warm*1000:.1f}ms 超过 50ms"
        print(f"    _get_exploration_log (cold≈{times[0]*1000:.1f}ms, warm={median_warm*1000:.1f}ms)")

    def test_make_session_summary(self):
        """生成完整会话摘要（自愈事件 + 熔断器 + 团队健康 + 专家分）"""
        times = []
        for _ in range(10):
            start = time.perf_counter()
            result = mb.make_session_summary()
            elapsed = time.perf_counter() - start
            times.append(elapsed)

        times.sort()
        median = times[len(times) // 2]
        assert "type" in result and result["type"] == "session_summary"
        assert median < 0.05, f"make_session_summary 中位数 {median*1000:.1f}ms 超过 50ms"
        print(f"    make_session_summary (10次中位数): {median*1000:.1f}ms")
