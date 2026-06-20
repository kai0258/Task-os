#!/usr/bin/env python3
"""Task OS v0.2 — MinerU Worker 集成测试。"""

import os, sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
os.environ["TASK_ROOT"] = os.path.dirname(__file__)

from dispatcher import TaskSpec, SPECS_DIR, REGISTRY_PATH
from workers.mineru.renderer import MinerURenderer
from capability_matrix import resolve_worker, capability_matrix, get_renderer, WORKER_REGISTRY
from dispatcher import ClaudeRenderer

WORK_DIR = Path(os.environ["TASK_ROOT"])
TEST_DIR = WORK_DIR / "test_mineru"
TEST_DIR.mkdir(exist_ok=True)

def clean():
    for f in TEST_DIR.glob("*"): f.unlink()
    for f in SPECS_DIR.glob("*.yaml"): f.unlink()
    REGISTRY_PATH.unlink(missing_ok=True)
    REGISTRY_PATH.with_suffix(".tmp").unlink(missing_ok=True)

def test_mineru_renderer():
    """测试 MinerURenderer 生成正确的命令。"""
    print("=" * 60)
    print("TEST 1: MinerU Renderer")
    print("=" * 60)
    clean()

    fake_pdf = TEST_DIR / "test.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4 fake" + b"\x00" * 1024)
    output_md = TEST_DIR / "test.md"

    spec = TaskSpec.create(
        task_type="pdf_to_markdown",
        title="MinerU PDF转MD测试",
        input_source=str(fake_pdf),
        output_target=str(output_md),
        requirements=["language:zh"],
        acceptance_hard=[{"check": "file_exists"}],
        worker_hint="mineru",
    )

    renderer = MinerURenderer()
    result = renderer.render(spec)
    cmd = result["command"]

    print(f"  command: {cmd[:120]}")
    print(f"  timeout: {result['timeout']}s")

    assert "adapter.py" in cmd, "命令应该包含adapter.py"
    assert "test.pdf" in cmd, "命令应该包含输入文件"
    assert "ch" in cmd, "命令应该包含语言参数"
    assert result["timeout"] > 0
    print("  ✓ command包含adapter.py")
    print("  ✓ command包含输入文件")
    print("  ✓ command包含language:ch")
    print(f"  ✓ timeout={result['timeout']}s")
    print("\n[RESULT] TEST 1: PASSED ✓")
    clean()

def test_capability_matrix():
    """测试 Capability Matrix 路由。"""
    print("\n" + "=" * 60)
    print("TEST 2: Capability Matrix")
    print("=" * 60)

    # pdf_to_markdown -> mineru
    worker, fallbacks = resolve_worker("pdf_to_markdown")
    assert worker == "mineru", f"预期mineru，实际{worker}"
    print(f"  pdf_to_markdown -> {worker} ✓")

    # summarize -> claude
    worker, fallbacks = resolve_worker("summarize")
    assert worker == "claude", f"预期claude，实际{worker}"
    print(f"  summarize -> {worker} ✓")

    # transcribe -> whisper
    worker, fallbacks = resolve_worker("transcribe")
    assert worker == "whisper", f"预期whisper，实际{worker}"
    print(f"  transcribe -> {worker} ✓")

    # unknown -> claude (fallback)
    worker, fallbacks = resolve_worker("unknown_type")
    assert worker == "claude", f"预期claude，实际{worker}"
    print(f"  unknown_type -> {worker} ✓")

    # worker_hint override
    worker, _ = resolve_worker("summarize", worker_hint="whisper")
    assert worker == "whisper", f"预期whisper，实际{worker}"
    print(f"  summarize + hint=whisper -> {worker} ✓")

    print("\n[RESULT] TEST 2: PASSED ✓")

def test_task_spec_worker_decoupling():
    """验证同一个 Task Spec 可被不同 Renderer 渲染。"""
    print("\n" + "=" * 60)
    print("TEST 3: Task Spec Worker 解耦")
    print("=" * 60)
    clean()

    fake_pdf = TEST_DIR / "test.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4" + b"\x00" * 1024)

    spec = TaskSpec.create(
        task_type="pdf_to_markdown",
        title="解耦测试",
        input_source=str(fake_pdf),
        output_target=str(TEST_DIR / "out.md"),
        worker_hint="mineru",
    )

    # MinerU Renderer
    mineru_cmd = MinerURenderer().render(spec)["command"]
    assert "adapter.py" in mineru_cmd
    print(f"  MinerU: {mineru_cmd[:80]}... ✓")

    # Claude Renderer（同一个Spec，换Worker）
    claude_cmd = ClaudeRenderer.render(spec)["command"]
    assert "claude" in claude_cmd
    print(f"  Claude: {claude_cmd[:80]}... ✓")

    # Task Spec 本身不含 Claude 专有字段
    spec_str = str(spec.data)
    # title 可以包含任何内容，但 input/output/requirements 不应绑定特定 Worker
    assert spec.data["input"]["source"] == str(fake_pdf)
    assert spec.data["output"]["target"] == str(TEST_DIR / "out.md")
    assert "claude" not in " ".join(spec.data["requirements"]).lower()
    print("  ✓ Task Spec 的 input/output/requirements 不含 Worker 信息")

    print("\n[RESULT] TEST 3: PASSED ✓")
    clean()

def main():
    print("Task OS v0.2 — MinerU Worker Integration")
    print("=" * 60)
    tests = [test_mineru_renderer, test_capability_matrix, test_task_spec_worker_decoupling]
    passed = failed = 0
    for t in tests:
        try:
            t(); passed += 1
        except Exception as e:
            print(f"\n[RESULT] {t.__name__}: FAILED ✗\n  {e}")
            import traceback; traceback.print_exc()
            failed += 1
    print("\n" + "=" * 60)
    print(f"SUMMARY: {passed} passed, {failed} failed")
    print("=" * 60)
    clean()
    return failed == 0

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
