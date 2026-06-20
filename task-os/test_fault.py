#!/usr/bin/env python3
"""Task OS v0.2 — 故障注入测试。"""

import os
import sys
import yaml
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(__file__))
os.environ["TASK_ROOT"] = os.path.dirname(__file__)

from dispatcher import (
    Dispatcher, TaskSpec, Registry, REGISTRY_PATH, SPECS_DIR,
    STATUS_FAILED, STATUS_DONE, STATUS_DOING, STATUS_TODO,
    _parse_claude_output,
)

WORK_DIR = Path(os.environ["TASK_ROOT"])
FAULT_DIR = WORK_DIR / "test_fault"
FAULT_DIR.mkdir(exist_ok=True)


def clean_fault_dir():
    for f in FAULT_DIR.glob("*"):
        f.unlink()
    # 不清理 SPECS_DIR 和 REGISTRY —— 让每个测试独立管理


def clean_all():
    for f in FAULT_DIR.glob("*"):
        f.unlink()
    for f in SPECS_DIR.glob("*.yaml"):
        f.unlink()
    if REGISTRY_PATH.exists():
        REGISTRY_PATH.unlink()
    tmp = REGISTRY_PATH.with_suffix(".tmp")
    if tmp.exists():
        tmp.unlink()


def test_robust_json_parse():
    """测试1：脏JSON输出解析。"""
    print("\n" + "=" * 60)
    print("TEST 1: Robust JSON parsing")
    print("=" * 60)

    cases = [
        ('{"status": "success", "session_id": "abc123"}', "abc123"),
        ('好的，我来处理。\n{"status": "success", "session_id": "def456"}', "def456"),
        ('Warning: something\n{"status": "success", "session_id": "ghi789"}\nWarning: more', "ghi789"),
        ("这不是JSON", None),
        ("", None),
    ]

    for stdout, expected_sid in cases:
        result = _parse_claude_output(stdout)
        if expected_sid is None:
            assert result is None or result.get("session_id") is None, f"预期None，实际{result}"
        else:
            assert result is not None and result.get("session_id") == expected_sid, f"预期{expected_sid}，实际{result}"
        print(f"  '{stdout[:40]}...' -> sid={expected_sid} ✓")

    print("\n[RESULT] TEST 1: PASSED ✓")


def test_crash_recovery_review():
    """测试2：crash recovery 处理 review 状态任务。"""
    print("\n" + "=" * 60)
    print("TEST 2: Crash Recovery (review → done)")
    print("=" * 60)
    clean_all()

    # 创建输出文件（模拟Claude已经写完）
    output_file = FAULT_DIR / "crash_output.md"
    output_file.write_text("这是一段测试摘要，包含图灵和深度学习。", encoding="utf-8")

    # 创建任务
    spec = TaskSpec.create(
        task_type="summarize",
        title="崩溃恢复测试",
        input_source=str(WORK_DIR / "demo_input.md"),
        output_target=str(output_file),
        acceptance_hard=[
            {"check": "file_exists"},
            {"check": "min_bytes", "value": 10},
        ],
    )
    task_id = spec.task_id

    # 第一个Dispatcher：注册并设置为review状态
    d1 = Dispatcher()
    d1.registry.register(spec)  # 必须先注册
    d1.registry.update(task_id, {"status": "review", "session_id": "fake-sid"})

    # 第二个Dispatcher：模拟重启，crash recovery 应该自动处理
    d2 = Dispatcher()
    entry = d2.registry.get(task_id)
    assert entry is not None, f"任务不存在：{task_id}"
    assert entry["status"] == STATUS_DONE, f"预期done，实际{entry['status']}"
    print(f"[验证] review → done ✓")

    print("\n[RESULT] TEST 2: PASSED ✓")
    clean_all()


def test_crash_recovery_stale_doing():
    """测试3：crash recovery 处理 stale doing。"""
    print("\n" + "=" * 60)
    print("TEST 3: Crash Recovery (stale doing → failed)")
    print("=" * 60)
    clean_all()

    spec = TaskSpec.create(
        task_type="summarize",
        title="stale doing测试",
        input_source=str(WORK_DIR / "demo_input.md"),
        output_target=str(FAULT_DIR / "stale_output.md"),
    )
    task_id = spec.task_id

    # 手动设置为 doing，started_at 设为 2 小时前
    d1 = Dispatcher()
    d1.registry.register(spec)  # 必须先注册
    two_hours_ago = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    d1.registry.update(task_id, {
        "status": "doing",
        "started_at": two_hours_ago,
    })

    # 新Dispatcher → crash recovery
    d2 = Dispatcher()
    entry = d2.registry.get(task_id)
    assert entry is not None
    assert entry["status"] == STATUS_FAILED, f"预期failed，实际{entry['status']}"
    assert "stale" in (entry.get("error") or ""), f"错误信息应包含stale，实际：{entry.get('error')}"
    print(f"[验证] stale doing → failed ✓")

    print("\n[RESULT] TEST 3: PASSED ✓")
    clean_all()


def test_done_output_missing():
    """测试4：done状态但输出文件丢失。"""
    print("\n" + "=" * 60)
    print("TEST 4: Done but output missing → failed")
    print("=" * 60)
    clean_all()

    missing_file = FAULT_DIR / "will_be_deleted.md"
    missing_file.write_text("临时内容", encoding="utf-8")

    spec = TaskSpec.create(
        task_type="summarize",
        title="输出丢失测试",
        input_source=str(WORK_DIR / "demo_input.md"),
        output_target=str(missing_file),
    )
    task_id = spec.task_id

    d1 = Dispatcher()
    d1.registry.register(spec)  # 必须先注册
    d1.registry.update(task_id, {"status": "done"})

    # 删除输出文件
    missing_file.unlink()

    # 新Dispatcher → crash recovery
    d2 = Dispatcher()
    entry = d2.registry.get(task_id)
    assert entry is not None
    assert entry["status"] == STATUS_FAILED, f"预期failed，实际{entry['status']}"
    assert "missing" in (entry.get("error") or "")
    print(f"[验证] done + 输出丢失 → failed ✓")

    print("\n[RESULT] TEST 4: PASSED ✓")
    clean_all()


def test_retry_resume():
    """测试5：retry 保留 session_id，Renderer 生成 --resume 命令。"""
    print("\n" + "=" * 60)
    print("TEST 5: Retry + Resume")
    print("=" * 60)
    clean_all()

    # 创建一个初始输出文件（Claude会覆盖写入）
    output_file = FAULT_DIR / "resume_output.md"
    output_file.write_text("初始内容", encoding="utf-8")

    # 创建一个会失败的任务（contains_all 用不可能出现的关键词）
    spec = TaskSpec.create(
        task_type="summarize",
        title="故障注入：验收必失败",
        input_source=str(WORK_DIR / "demo_input.md"),
        output_target=str(output_file),
        requirements=["用一句话摘要"],
        acceptance_hard=[
            {"check": "file_exists"},
            {"check": "contains_all", "values": ["这个关键词永远不可能出现XYZ123"]},
        ],
    )
    task_id = spec.task_id

    dispatcher = Dispatcher()
    dispatcher.submit(spec)

    # Step 1: 第一次执行（预期失败）
    print("\n--- Step 1: 第一次执行（预期失败）---")
    dispatcher.run_once()
    entry = dispatcher.registry.get(task_id)
    assert entry["status"] == STATUS_FAILED, f"预期failed，实际{entry['status']}"
    assert entry["session_id"] is not None, "session_id应该已保存"
    session1 = entry["session_id"]
    print(f"[验证] status=failed ✓, session_id={session1[:12]}... ✓")

    # Step 2: retry
    print("\n--- Step 2: retry ---")
    dispatcher.retry(task_id)
    entry = dispatcher.registry.get(task_id)
    assert entry["status"] == STATUS_TODO
    assert entry["session_id"] == session1, "session_id应该保留"
    assert entry["retry_count"] == 1
    print(f"[验证] status=todo ✓, session_id保留 ✓, retry_count=1 ✓")

    # Step 3: 验证 Renderer 生成 --resume 命令
    print("\n--- Step 3: 验证Renderer生成resume命令 ---")
    from dispatcher import ClaudeRenderer
    renderer = ClaudeRenderer()
    render_result = renderer.render(spec, registry_entry=entry)
    cmd = render_result["command"]
    has_resume = "--resume" in cmd and session1 in cmd
    print(f"[验证] 命令包含--resume: {has_resume} ✓" if has_resume else f"[失败] 命令不包含--resume")
    assert has_resume

    # Step 4: 修改验收条件让它通过，然后执行resume
    print("\n--- Step 4: 修改验收条件，执行resume ---")
    spec.data["acceptance"]["hard"] = [{"check": "file_exists"}, {"check": "min_bytes", "value": 5}]
    spec.save()
    dispatcher.run_once()
    entry = dispatcher.registry.get(task_id)
    assert entry["status"] == STATUS_DONE, f"预期done，实际{entry['status']}"
    assert entry["session_id"] == session1, "session_id应该不变"
    print(f"[验证] status=done ✓, session_id不变 ✓")

    print("\n[RESULT] TEST 5: PASSED ✓")
    clean_all()


def main():
    print("Task OS v0.2 — Fault Injection Tests")
    print("=" * 60)

    tests = [
        test_robust_json_parse,
        test_crash_recovery_review,
        test_crash_recovery_stale_doing,
        test_done_output_missing,
        test_retry_resume,
    ]

    passed = 0
    failed = 0
    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            print(f"\n[RESULT] {test_fn.__name__}: FAILED ✗")
            print(f"  Error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"SUMMARY: {passed} passed, {failed} failed, {passed + failed} total")
    print("=" * 60)

    clean_all()
    return failed == 0


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
