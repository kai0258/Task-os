#!/usr/bin/env python3
"""
Task OS v0.1 — Demo

演示完整闭环：
  Task Spec → Claude Renderer → Claude Code → Hard Acceptance → Registry

用法：
  python demo.py
"""

import sys
import os

# 确保能找到dispatcher模块
sys.path.insert(0, os.path.dirname(__file__))
os.environ["TASK_ROOT"] = os.path.dirname(__file__)

from dispatcher import Dispatcher, TaskSpec

def main():
    print("=" * 60)
    print("Task OS v0.1 — Demo")
    print("=" * 60)

    # 初始化Dispatcher
    dispatcher = Dispatcher()

    # ─────────────────────────────────────
    # Step 1: 定义Task Spec
    # ─────────────────────────────────────
    demo_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(demo_dir, "demo_input.md")
    output_file = os.path.join(demo_dir, "demo_output.md")

    spec = TaskSpec.create(
        task_type="summarize",
        title="Demo：将AI发展简史摘要为300字以内的短文",
        input_source=input_file,
        output_target=output_file,
        requirements=[
            "用简体中文写摘要",
            "保留关键人物和年份",
            "不超过300字",
            "包含一句总结性评价",
        ],
        acceptance_hard=[
            {"check": "file_exists"},
            {"check": "min_lines", "value": 5},
            {"check": "max_lines", "value": 30},
            {"check": "min_bytes", "value": 200},
            {"check": "contains_all", "values": ["图灵", "深度学习"]},
            {"check": "encoding", "value": "utf-8"},
        ],
        worker_hint="claude",
    )

    print(f"\n[Spec] task_id = {spec.task_id}")
    print(f"[Spec] title  = {spec.title}")
    print(f"[Spec] input  = {spec.input['source']}")
    print(f"[Spec] output = {spec.output['target']}")

    # ─────────────────────────────────────
    # Step 2: 提交任务
    # ─────────────────────────────────────
    task_id = dispatcher.submit(spec)

    # ─────────────────────────────────────
    # Step 3: 查看任务单（生成的prompt）
    # ─────────────────────────────────────
    from dispatcher import ClaudeRenderer
    renderer = ClaudeRenderer()
    render_result = renderer.render(spec)
    print(f"\n[Renderer] 生成的Claude命令：")
    print(f"  workdir: {render_result['workdir']}")
    print(f"  timeout: {render_result['timeout']}s")
    print(f"  command: {render_result['command'][:200]}...")

    # ─────────────────────────────────────
    # Step 4: 执行（派发给Claude Code）
    # ─────────────────────────────────────
    print(f"\n[Dispatcher] 开始执行...")
    dispatcher.run_all()

    # ─────────────────────────────────────
    # Step 5: 查看结果
    # ─────────────────────────────────────
    dispatcher.status()

    # 如果成功，显示输出文件内容
    if os.path.exists(output_file):
        print(f"\n{'='*60}")
        print(f"[输出] {output_file} 的内容：")
        print(f"{'='*60}")
        with open(output_file, "r", encoding="utf-8") as f:
            print(f.read())
    else:
        print(f"\n[输出] 输出文件不存在：{output_file}")

    print(f"\n{'='*60}")
    print("Demo完成。")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
