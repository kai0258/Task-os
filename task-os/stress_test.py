#!/usr/bin/env python3
"""
Task OS v0.1.1 — Stress Test

自动生成100个任务，连续执行，输出统计报告。

用法：
  python3 stress_test.py              # 默认100个任务
  python3 stress_test.py --count 10   # 跑10个（快速验证）
  python3 stress_test.py --count 1    # 跑1个（调试）
"""

import os
import sys
import time
import json
import shutil
import random
import argparse
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
os.environ["TASK_ROOT"] = os.path.dirname(__file__)

from dispatcher import Dispatcher, TaskSpec, Registry, SPECS_DIR, REGISTRY_PATH


# ═══════════════════════════════════════════
# 生成测试数据
# ═══════════════════════════════════════════

SAMPLE_TEXTS = [
    "人工智能是计算机科学的一个分支，致力于创建能够执行通常需要人类智能的系统。深度学习是其中最重要的技术之一。",
    "量子计算利用量子力学原理进行信息处理。与经典计算机使用比特不同，量子计算机使用量子比特，可以同时处于0和1的叠加态。",
    "区块链是一种分布式账本技术，通过密码学保证数据不可篡改。比特币是第一个成功应用区块链技术的加密货币。",
    "基因编辑技术CRISPR-Cas9使科学家能够精确修改DNA序列。这项技术在医学、农业和生物研究领域有广泛应用。",
    "太空探索是人类认识宇宙的重要手段。从1961年加加林首次进入太空，到如今的火星探测计划，太空事业不断发展。",
    "可再生能源包括太阳能、风能、水能等。全球正在加速向清洁能源转型，以应对气候变化挑战。",
    "经济学研究资源的稀缺性和选择。微观经济学关注个体决策，宏观经济学研究整体经济运行。",
    "哲学探讨存在、知识、价值等根本问题。从苏格拉底到现代分析哲学，人类对这些问题的思考从未停止。",
    "音乐是人类最古老的艺术形式之一。从古典音乐到流行音乐，每种风格都反映了特定时代的精神面貌。",
    "心理学研究人类行为和心理过程。认知心理学、社会心理学、发展心理学等分支帮助我们理解自己和他人。",
]


def generate_test_data(count: int, work_dir: Path):
    """生成count个测试输入文件和对应的Task Spec定义。"""
    input_dir = work_dir / "test_inputs"
    output_dir = work_dir / "test_outputs"
    input_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)

    tasks = []
    for i in range(count):
        # 随机选一段文本，加上唯一标识
        text = random.choice(SAMPLE_TEXTS)
        unique_text = f"[任务#{i:03d}] {text}\n\n生成时间：{datetime.now().isoformat()}\n随机种子：{random.randint(1000,9999)}"

        input_file = input_dir / f"input_{i:03d}.txt"
        output_file = output_dir / f"output_{i:03d}.txt"

        input_file.write_text(unique_text, encoding="utf-8")

        tasks.append({
            "task_type": "summarize",
            "title": f"压力测试#{i:03d}：一句话摘要",
            "input_source": str(input_file),
            "output_target": str(output_file),
            "requirements": [
                "用一句话（不超过30字）概括输入文件的核心内容",
                "只输出摘要文本，不要加标题或格式",
            ],
            "acceptance_hard": [
                {"check": "file_exists"},
                {"check": "min_bytes", "value": 10},
                {"check": "max_bytes", "value": 500},
            ],
        })

    return tasks


# ═══════════════════════════════════════════
# 统计收集
# ═══════════════════════════════════════════

class Stats:
    def __init__(self):
        self.start_time = time.time()
        self.task_durations = []
        self.task_results = []  # (task_id, status, elapsed, error)
        self.registry_snapshots = []  # 定期快照

    def record(self, task_id: str, status: str, elapsed: float, error: str = None):
        self.task_results.append((task_id, status, elapsed, error))
        self.task_durations.append(elapsed)

    def snapshot_registry(self, registry: Registry):
        """保存registry快照，用于检测损坏。"""
        import yaml
        snap_path = REGISTRY_PATH.with_suffix(f".snap.{len(self.registry_snapshots)}")
        with open(snap_path, "w", encoding="utf-8") as f:
            yaml.dump(registry.data, f, allow_unicode=True, default_flow_style=False)
        self.registry_snapshots.append(str(snap_path))

    def report(self, registry: Registry):
        total = len(self.task_results)
        done = sum(1 for _, s, _, _ in self.task_results if s == "done")
        failed = sum(1 for _, s, _, _ in self.task_results if s == "failed")
        retries = sum(r.get("retry_count", 0) for r in registry.data["tasks"].values())
        total_elapsed = time.time() - self.start_time

        # 检查registry是否可正常读取
        try:
            verify = Registry()
            registry_ok = True
            registry_note = "Registry可正常读取"
        except Exception as e:
            registry_ok = False
            registry_note = f"Registry损坏：{e}"

        print("\n" + "=" * 60)
        print("STRESS TEST REPORT")
        print("=" * 60)
        print(f"总任务数:       {total}")
        print(f"成功(done):     {done} ({done/total*100:.1f}%)" if total else "")
        print(f"失败(failed):   {failed} ({failed/total*100:.1f}%)" if total else "")
        print(f"总重试次数:     {retries}")
        print(f"总耗时:         {total_elapsed:.1f}s ({total_elapsed/60:.1f}min)")

        if self.task_durations:
            avg = sum(self.task_durations) / len(self.task_durations)
            mn = min(self.task_durations)
            mx = max(self.task_durations)
            print(f"平均任务耗时:   {avg:.1f}s")
            print(f"最短任务耗时:   {mn:.1f}s")
            print(f"最长任务耗时:   {mx:.1f}s")

        print(f"\nRegistry状态:   {'✓ 正常' if registry_ok else '✗ 损坏'}")
        print(f"  {registry_note}")

        # 检查是否有卡死任务
        stale_doing = sum(1 for t in registry.data["tasks"].values() if t["status"] == "doing")
        print(f"卡死(doing):    {stale_doing}")

        # 失败详情
        failures = [(tid, err) for tid, s, _, err in self.task_results if s == "failed" and err]
        if failures:
            print(f"\n失败详情（前10条）：")
            for tid, err in failures[:10]:
                print(f"  {tid}: {err[:100]}")

        # 保存报告到文件
        report = {
            "total_tasks": total,
            "done": done,
            "failed": failed,
            "success_rate": f"{done/total*100:.1f}%" if total else "N/A",
            "total_retries": retries,
            "total_elapsed_s": round(total_elapsed, 1),
            "avg_task_s": round(sum(self.task_durations) / len(self.task_durations), 1) if self.task_durations else 0,
            "min_task_s": round(min(self.task_durations), 1) if self.task_durations else 0,
            "max_task_s": round(max(self.task_durations), 1) if self.task_durations else 0,
            "registry_ok": registry_ok,
            "stale_doing": stale_doing,
        }
        report_path = Path(os.environ["TASK_ROOT"]) / "stress_test_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n报告已保存: {report_path}")

        # 清理快照
        for snap in self.registry_snapshots:
            try:
                os.remove(snap)
            except Exception:
                pass

        return report


# ═══════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════

def run_stress_test(count: int):
    work_dir = Path(os.environ["TASK_ROOT"])
    print(f"[Stress Test] 生成 {count} 个测试任务...")

    # 清理旧数据
    if REGISTRY_PATH.exists():
        REGISTRY_PATH.unlink()
    for f in (SPECS_DIR).glob("*.yaml"):
        f.unlink()

    # 生成测试数据
    task_defs = generate_test_data(count, work_dir)
    print(f"[Stress Test] 已生成 {len(task_defs)} 个任务")

    # 初始化Dispatcher
    dispatcher = Dispatcher()
    stats = Stats()

    # 提交所有任务
    task_ids = []
    for td in task_defs:
        spec = TaskSpec.create(
            task_type=td["task_type"],
            title=td["title"],
            input_source=td["input_source"],
            output_target=td["output_target"],
            requirements=td["requirements"],
            acceptance_hard=td["acceptance_hard"],
            worker_hint="claude",
        )
        dispatcher.submit(spec)
        task_ids.append(spec.task_id)

    print(f"\n[Stress Test] 开始执行 {len(task_ids)} 个任务...\n")

    # 逐个执行，记录统计
    for i, task_id in enumerate(task_ids):
        t0 = time.time()

        # 记录执行前状态
        entry_before = dispatcher.registry.get(task_id)
        status_before = entry_before["status"] if entry_before else "unknown"

        # 执行
        try:
            dispatcher._execute(task_id)
        except Exception as e:
            dispatcher.registry.update(task_id, {
                "status": "failed",
                "error": f"Dispatcher异常：{str(e)[:200]}",
            })

        elapsed = time.time() - t0

        # 记录执行后状态
        entry_after = dispatcher.registry.get(task_id)
        status_after = entry_after["status"] if entry_after else "unknown"
        error = entry_after.get("error") if entry_after else None

        stats.record(task_id, status_after, elapsed, error)

        # 每10个任务做一次registry快照
        if (i + 1) % 10 == 0:
            stats.snapshot_registry(dispatcher.registry)
            done_count = sum(1 for _, s, _, _ in stats.task_results if s == "done")
            print(f"\n[进度] {i+1}/{count} 完成，成功率 {done_count/(i+1)*100:.0f}%\n")

    # 最终报告
    stats.report(dispatcher.registry)


def main():
    parser = argparse.ArgumentParser(description="Task OS Stress Test")
    parser.add_argument("--count", type=int, default=100, help="任务数量（默认100）")
    args = parser.parse_args()

    run_stress_test(args.count)


if __name__ == "__main__":
    main()
