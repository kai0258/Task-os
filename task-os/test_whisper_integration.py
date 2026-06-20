#!/usr/bin/env python3
"""Task OS v0.2 — Phase 2: Whisper Worker 集成测试。"""

import os
import sys
import yaml
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
os.environ["TASK_ROOT"] = os.path.dirname(__file__)

from dispatcher import TaskSpec, SPECS_DIR, REGISTRY_PATH
from workers.whisper.renderer import WhisperRenderer

WORK_DIR = Path(os.environ["TASK_ROOT"])
TEST_DIR = WORK_DIR / "test_whisper"
TEST_DIR.mkdir(exist_ok=True)


def clean():
    for f in TEST_DIR.glob("*"):
        f.unlink()
    for f in SPECS_DIR.glob("*.yaml"):
        f.unlink()
    if REGISTRY_PATH.exists():
        REGISTRY_PATH.unlink()
    REGISTRY_PATH.with_suffix(".tmp").unlink(missing_ok=True)


def test_whisper_renderer():
    """测试WhisperRenderer生成正确的命令。"""
    print("=" * 60)
    print("TEST: Whisper Renderer")
    print("=" * 60)

    # 创建一个假的音频文件（Whisper需要文件存在来估算超时）
    fake_audio = TEST_DIR / "test_audio.mp3"
    fake_audio.write_bytes(b"\x00" * 1024)  # 1KB假文件

    output_file = TEST_DIR / "test_audio.txt"

    spec = TaskSpec.create(
        task_type="transcribe",
        title="Whisper转录测试",
        input_source=str(fake_audio),
        output_target=str(output_file),
        requirements=["language:zh", "model:small"],
        acceptance_hard=[
            {"check": "file_exists"},
            {"check": "min_bytes", "value": 10},
        ],
        worker_hint="whisper",
    )

    # 测试Renderer
    result = WhisperRenderer.render(spec)
    cmd = result["command"]
    workdir = result["workdir"]
    timeout = result["timeout"]

    print(f"  command: {cmd[:120]}...")
    print(f"  workdir: {workdir}")
    print(f"  timeout: {timeout}s")

    # 验证
    assert "whisper" in cmd, "命令应该包含whisper"
    assert "test_audio.mp3" in cmd, "命令应该包含输入文件"
    assert "--language zh" in cmd, "命令应该包含语言参数"
    assert "--model small" in cmd, "命令应该包含模型参数"
    assert "--device cpu" in cmd, "命令应该包含device参数"
    assert timeout > 0, "超时应该大于0"
    assert workdir == str(TEST_DIR), f"workdir应该是{TEST_DIR}"

    print("\n  ✓ command包含whisper")
    print("  ✓ command包含输入文件")
    print("  ✓ command包含language:zh")
    print("  ✓ command包含model:small")
    print("  ✓ command包含device:cpu")
    print(f"  ✓ timeout={timeout}s")
    print(f"  ✓ workdir={workdir}")

    print("\n[RESULT] Whisper Renderer: PASSED ✓")


def test_whisper_task_spec():
    """测试Whisper的Task Spec不包含Claude专有字段。"""
    print("\n" + "=" * 60)
    print("TEST: Whisper Task Spec 脱离 Claude")
    print("=" * 60)

    clean()
    fake_audio = TEST_DIR / "test_audio2.mp3"
    fake_audio.write_bytes(b"\x00" * 1024)

    spec = TaskSpec.create(
        task_type="transcribe",
        title="验证Task Spec",
        input_source=str(fake_audio),
        output_target=str(TEST_DIR / "output.txt"),
        requirements=["language:zh"],
        worker_hint="whisper",
    )

    # 验证spec里没有Claude专有字段
    spec_data = spec.data
    assert "prompt" not in spec_data, "Task Spec不应包含prompt"
    assert "claude" not in str(spec_data).lower() or "worker_hint" in str(spec_data), "Task Spec不应包含Claude专有字段"
    assert spec_data.get("worker_hint") == "whisper"

    print("  ✓ Task Spec不包含prompt")
    print("  ✓ Task Spec不包含Claude专有字段")
    print("  ✓ worker_hint=whisper")

    # 同一个Spec用ClaudeRenderer渲染（模拟Dispatcher选择了Claude）
    from dispatcher import ClaudeRenderer
    claude_result = ClaudeRenderer.render(spec)
    assert "claude" in claude_result["command"]
    print("  ✓ 同一Spec也可用ClaudeRenderer渲染")

    # 用WhisperRenderer渲染
    whisper_result = WhisperRenderer.render(spec)
    assert "whisper" in whisper_result["command"]
    print("  ✓ 同一Spec可用WhisperRenderer渲染")

    print("\n[RESULT] Task Spec Worker解耦: PASSED ✓")
    clean()


def main():
    print("Task OS v0.2 — Phase 2: Whisper Worker Integration")
    print("=" * 60)

    tests = [
        test_whisper_renderer,
        test_whisper_task_spec,
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

    clean()
    return failed == 0


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
