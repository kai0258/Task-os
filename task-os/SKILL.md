---
name: task-os
description: >
  Task OS — Hermes 作为总调度官的任务编排系统。管理 Task Spec → Renderer → Worker → Acceptance → Registry 的完整生命周期。
  支持多 Worker（Claude Code、MinerU、Whisper）通过 Capability Matrix 自动路由。
  包含 Crash Recovery、Retry+Resume、原子写入等生产级防护。
triggers:
  - 任务编排
  - 任务调度
  - 批量处理
  - PDF转Markdown
  - 视频转文章
  - Worker调度
  - task orchestration
  - task dispatch
  - batch processing
  - 多Agent调度
  - Worker派发
  - Hermes + Claude Code workflow
  - 任务队列
  - task queue
  - 验收机制
  - acceptance criteria
  - 批量任务处理
  - batch task processing
  - Task Spec
  - Registry
  - Renderer
  - stress test
version: 0.3.0
author: Agent
metadata:
  hermes:
    tags: [orchestration, task-spec, multi-agent, dispatch, acceptance, batch-processing]
    related_skills: [kanban-orchestrator, kanban-worker, claude-code, codex, subagent-driven-development]
---

# Task OS — 任务编排系统

Hermes 不再承担重型执行任务，而是承担：理解用户需求 → 拆解任务 → 派发给 Worker → 验收结果 → 归档。

## 核心架构

```
用户需求 → Hermes 拆解为 Task Spec(s)
    → Capability Matrix 选择 Worker
    → Renderer 生成 Worker 指令
    → Worker 执行
    → Hard Acceptance 验收
    → Registry 更新状态
```

## 代码位置

`[your-project-root]/task-os/`

## Task Spec Schema（不可变）

```yaml
task_id: t_xxx           # 自动生成
task_type: translate      # translate | summarize | pdf_to_markdown | transcribe | refactor | code
title: "任务标题"
input:
  source: /path/to/input
  reference: /path/to/reference  # 可选
output:
  target: /path/to/output
requirements:
  - "具体要求1"
  - "具体要求2"
acceptance:
  hard:
    - check: file_exists
    - check: min_lines, value: 50
    - check: contains_all, values: ["关键词1"]
    - check: min_bytes, value: 1000
    - check: max_bytes, value: 500000
    - check: encoding, value: utf-8
    - check: compression_ratio, source: /path/to/source, min: 30, max: 70
    - check: has_frontmatter
    - check: has_h2, value: 3
worker_hint: claude       # 可选，省略由 Capability Matrix 决定
depends_on: []            # 预留，v0.2 未实现
```

**关键约束：Task Spec 不含任何 Worker 专有字段（无 prompt、无 --max-turns、无 claude 参数）。** 换 Worker 不改 Spec。

## Registry Schema（可变状态）

```yaml
version: "0.2"
tasks:
  t_xxx:
    status: todo | doing | review | done | failed | escalated
    worker: claude-code
    session_id: "abc123"       # Claude Code session，用于 resume
    spec_path: tasks/specs/t_xxx.yaml
    output_path: /path/to/output
    created_at / started_at / completed_at
    retry_count: 0
    max_retries: 3
    acceptance: {hard_pass, hard_failures, verdict}
    error: null
```

## Capability Matrix

| task_type | preferred | fallback |
|-----------|-----------|----------|
| summarize | claude | — |
| translate | claude | — |
| pdf_to_markdown | mineru | claude |
| transcribe | whisper | — |
| refactor | claude | — |
| code | claude | — |
| video_to_article | claude | — |

Worker 注册在 `capability_matrix.py` 的 `WORKER_REGISTRY` 中。

路由优先级：Task Spec 的 worker_hint > Capability Matrix 默认 > 回退到 claude

## Claude Renderer Pattern

Converts Task Spec into a `claude -p` invocation:

```python
def render(spec):
    prompt = build_prompt(spec)  # Task Spec → natural language
    return {
        "command": f"claude -p {shell_quote(prompt)} --output-format json --max-turns 20 --dangerously-skip-permissions",
        "workdir": str(Path(spec.output["target"]).parent),
        "timeout": estimate_timeout(spec),
    }
```

Key flags:
- `--output-format json`: structured return with session_id for resume
- `--dangerously-skip-permissions`: unattended execution
- `--max-turns`: prevent runaway
- `--resume <session_id>`: for retry/rework

## Retry / Resume

| Situation | Strategy |
|-----------|----------|
| Small fix (format, missing keyword) | `claude -p "fix X" --resume <session_id>` |
| Direction wrong (style, approach) | New session + attach old output as reference |
| API failure (timeout, 500) | New session, same prompt |
| Multiple failures | New session + simplify prompt / reduce scope |

## Worker 清单

| Worker | Renderer | 执行方式 |
|--------|----------|----------|
| Claude Code | `dispatcher.py` 内置 ClaudeRenderer | `claude -p "..." --output-format json` |
| MinerU | `workers/mineru/renderer.py` | `python3 adapter.py input.pdf output.md`（云端 API） |
| Whisper | `workers/whisper/renderer.py` | `whisper input.mp3 --model small --language zh`（本地 CLI） |

## Crash Recovery（启动时自动执行）

Dispatcher 启动时 `_crash_recovery()` 自动处理：

1. **.tmp 文件恢复**：如果 `registry.tmp` 存在且可解析，用它替换 `registry.yaml`（原子写入中断恢复）
2. **stale doing → failed**：doing 状态超过 1 小时的任务标记为 failed
3. **review → 重新验收**：输出文件可能已生成，重新执行 Hard Acceptance
4. **done + 输出丢失 → failed**：输出文件不存在则标记 failed

## Retry + Resume

- `retry()` 保留 `session_id`，不清除
- `ClaudeRenderer.render()` 检测到旧 `session_id` 时生成 `claude -p "返工指令" --resume <session_id>`
- 返工指令由 Dispatcher 从 Acceptance 的 `hard_failures` 自动生成

## CLI 用法

```bash
cd [your-project-root]/task-os

# 提交任务
python3 dispatcher.py submit --type translate --title "翻译XX" --input /path/in --output /path/out

# 执行所有 todo 任务
python3 dispatcher.py run

# 查看状态
python3 dispatcher.py status

# 重试失败任务
python3 dispatcher.py retry <task_id>
```

## 测试

```bash
python3 stress_test.py --count 100           # 压力测试
python3 test_fault.py                         # 5 个故障注入测试
python3 test_mineru_integration.py            # 3 个 MinerU 集成测试
python3 test_whisper_integration.py           # 2 个 Whisper 集成测试
```

## 仓库

- **GitHub**: https://github.com/[your-username]/Task-os
- **本地**: [your-project-root]/task-os/
- **Windows**: [your-project-root]\task-os

仓库 = 数字资产（代码 + 文档 + 经验 + 测试 + 历史决策），五者缺一不可。

## 维护者原则（10条）

1. 优先保持架构一致性
2. 任何功能修改必须同步更新文档
3. 任何功能修改必须补充测试
4. 不允许绕过 Task Spec
5. 不允许绕过 Acceptance
6. 不允许把 Worker 逻辑写进 Dispatcher
7. Capability Matrix 负责路由
8. Renderer 负责适配
9. Registry 是唯一状态源
10. Memory 是长期资产

## 工作模式（7步，不允许跳过）

1. 先分析
2. 输出设计方案
3. 等待确认
4. 实施修改
5. 运行测试
6. 更新文档
7. Git Commit

**除非明确要求，否则不要直接修改代码。** 顺序必须是：先文档 → 再代码 → 最后测试。

## 升级触发条件（业务指标，非技术指标）

v0.2 冻结开发。当且仅当遇到以下任意一种情况时才进入 v0.3：

- 同时积压 1000+ 个任务
- 需要多个 Worker 并行跑
- 想让系统自动学习经验
- 想让多个 Agent 协同工作
- 想把「丞相-六部」真正落地

在那之前，最有价值的事是把 Task OS 从「能跑的代码」变成「能传承的资产」。

## Pitfalls

1. **`TaskSpec.create()` 不等于 `Registry.register()`**：create 只保存 spec 文件，不注册到 Registry。必须调用 `dispatcher.submit(spec)` 或 `registry.register(spec)` 才能在 Registry 中找到任务。测试代码忘记 register 会导致 entry 为 None。
2. **Registry 原子写入必须用 `os.replace()`**：直接 `open("w")` 写入在崩溃时会损坏文件。必须 write to .tmp → fsync → os.replace。
3. **JSON 解析必须鲁棒**：Claude Code 的 stdout 前后可能有非 JSON 文本（Warning 等）。用 `_parse_claude_output()` 提取最大的 JSON 块。
4. **subprocess.run 是同步阻塞**：一个任务执行期间 Dispatcher 完全阻塞。100 个任务串行 ≈ 55 分钟。并行需要改架构。
5. **MinerU 是云端 API 不是本地工具**：需要 `MINERU_API_KEY` 环境变量，通过 `mineru.net/api/v4` 调用。适配器在 `workers/mineru/adapter.py`。
6. **语音识别模型兼容性**：某些 ASR 模型可能因 GPU 计算能力不兼容而无法使用。备选方案：用 `faster-whisper`（CPU 模式）替代。
7. **批量门控（All-or-Nothing Gate）导致静默死锁**：Cron 任务要求"N 个输入全部就位才执行"，缺 1 个就永远不触发。用"能做多少做多少"策略，缺失项主动告警。
8. **临时目录在系统重启时清空**：长时间任务产出必须写到持久化存储路径，不写临时目录。用 checkpoint 模式每完成一个单元就落盘。
9. **OOM 级联故障**：内存爆满 → 进程被杀 → 临时文件丢失 → 后台进程丢失 → 定时任务依赖永远不满足 → 批量任务永远不触发。长任务用持久化 checkpoint + 完成通知。
10. **video_to_article 任务需要特殊参数**：此类任务 CC 需要多轮读分段文件+写长文，默认 max_turns=20 不够。应设为 30。timeout 也不够——按文件大小 `max(900, min(1800, size_kb * 1.5))` 计算（最低15分钟）。在 `render()` 中按 `spec.task_type` 动态设置。
11. **超时但文件已写入**：CC 可能在 subprocess 超时后仍在后台执行并完成写入。超时处理应先检查输出文件是否已存在且通过验收，通过则标记 done 而非 failed。
12. **BOM 前缀导致 frontmatter 检测失败**：Windows 编辑器保存的 .md 文件可能带 UTF-8 BOM（`\ufeff`）。`has_frontmatter` 检查必须用 `encoding='utf-8-sig'` 打开并 `lstrip('\ufeff')` 再检测 `---`。
13. **底层模型可能受内容审核限制**：某些模型会对敏感内容触发 content_filter。对策：在 prompt 中明确指令，或改用不受限的模型/会话处理。
14. **批量外部工具调用**：Python 中逐个调用 terminal() 会因 stderr 干扰导致 JSON 解析失败，且受 tool call 数量限制。应用 bash 循环一次性处理批量操作。

## Design Decisions

Key architectural decisions and their rationale are documented in `references/design-decisions.md`. Covers:
- Task Spec vs Worker prompt separation
- Hermes as Dispatcher + Worker dual role
- Three core file separation (Spec / Registry / Memory)
- Memory ownership (system, not Dispatcher)
- Hard/Soft acceptance layering
- Retry via Resume strategy
- Capability Matrix evolution path

## Support Files

- `references/architecture-decisions.md` — 8 key design decisions with rationale
- `references/fault-patterns.md` — fault scenarios, recovery strategies, test results
- `references/cron-batch-faults.md` — cron job / batch automation failure modes (all-or-nothing gate, /tmp volatility, OOM cascade)
- `references/design-decisions.md` — consolidated design conversation notes
- `references/task-os-implementation.md` — code patterns: crash recovery, JSON parsing, anti-duplication, atomic writes
- `references/mineru-worker.md` — MinerU cloud API Worker details
