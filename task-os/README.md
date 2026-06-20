# Task OS

A lightweight, file-based task orchestration system for AI coding agents. Routes tasks to the right worker, validates results with deterministic checks, and recovers from crashes automatically.

**Task Spec → Renderer → Worker → Acceptance → Registry.**

[中文文档](#中文文档)

---

## What it does

Task OS turns a task request into a validated result through a pipeline that enforces quality at every step:

```
Submit Task → Capability Matrix routes to Worker → Renderer generates command
→ Worker executes → Hard Acceptance validates → Registry updates state
```

The key differentiator is **Hard Acceptance** — results are validated with deterministic checks (file exists, minimum lines, correct encoding, content matching), not LLM self-assessment. If validation fails, the task is automatically retried.

## Quick start

### 1. Install

```bash
git clone https://github.com/kai0258/task-os.git
cd task-os
```

### 2. Submit a task

```bash
python3 dispatcher.py submit \
  --type translate \
  --title "Translate README to Chinese" \
  --input ./README.md \
  --output ./README_zh.md
```

### 3. Run all pending tasks

```bash
python3 dispatcher.py run
```

### 4. Check status

```bash
python3 dispatcher.py status
```

### 5. Retry a failed task

```bash
python3 dispatcher.py retry <task_id>
```

## How it works

### Task Spec (immutable)

Every task is defined as a YAML spec that describes *what* to do, not *how*:

```yaml
task_id: t_abc123
task_type: translate
title: "Translate README to Chinese"
input:
  source: ./README.md
output:
  target: ./README_zh.md
requirements:
  - "Faithful translation, no additions"
acceptance:
  hard:
    - check: file_exists
    - check: min_lines, value: 50
    - check: encoding, value: utf-8
    - check: compression_ratio, source: ./README.md, min: 30, max: 70
worker_hint: claude  # optional, Capability Matrix decides if omitted
```

**Key constraint:** Task Spec contains no worker-specific fields. Changing workers doesn't require changing specs.

### Capability Matrix (routing)

Routes tasks to the best worker based on `task_type`:

| task_type | preferred | fallback |
|-----------|-----------|----------|
| translate | claude | — |
| summarize | claude | — |
| pdf_to_markdown | mineru | claude |
| transcribe | whisper | — |
| code | claude | — |
| video_to_article | claude | — |

Workers are registered in `capability_matrix.py`.

### Renderer (adaptation)

Converts a Task Spec into a worker-specific command:

```python
# Claude Renderer
def render(spec):
    prompt = build_prompt(spec)  # Task Spec → natural language
    return {
        "command": f"claude -p {shell_quote(prompt)} --output-format json --max-turns 20",
        "workdir": str(Path(spec.output["target"]).parent),
        "timeout": estimate_timeout(spec),
    }
```

### Hard Acceptance (validation)

Deterministic checks that run after every task:

| Check | What it does |
|-------|-------------|
| `file_exists` | Output file was created |
| `min_lines` | File has enough lines |
| `min_bytes` / `max_bytes` | File size is reasonable |
| `encoding` | File is valid UTF-8 |
| `contains_all` | Required keywords are present |
| `compression_ratio` | Output-to-input ratio is sane |
| `has_frontmatter` | YAML frontmatter exists |
| `has_h2` | Minimum number of H2 headers |

### Registry (state)

Persistent YAML file tracking every task:

```yaml
version: "0.2"
tasks:
  t_abc123:
    status: done
    worker: claude-code
    session_id: "abc123"
    retry_count: 0
    acceptance:
      hard_pass: true
      hard_failures: []
      verdict: PASS
```

Atomic writes: write to `.tmp` → `fsync` → `os.replace()` — no corruption on crash.

### Crash Recovery (automatic)

On startup, the dispatcher automatically:

1. Recovers `.tmp` registry files (atomic write interruption)
2. Marks stale `doing` tasks (> 1 hour) as `failed`
3. Re-validates `review` tasks (output may exist)
4. Marks `done` tasks with missing output as `failed`

### Retry via Resume

Failed tasks can be retried by resuming the original Claude Code session:

```bash
# Small fix: resume the same session
claude -p "fix the encoding issue" --resume <session_id>

# Wrong direction: new session with old output as reference
# The dispatcher handles this automatically
```

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│  Task Spec  │ ──→ │ Capability Matrix │ ──→ │  Renderer   │
│  (YAML)     │     │  (routes by type) │     │  (adapts)   │
└─────────────┘     └──────────────────┘     └──────┬──────┘
                                                     │
                                              ┌──────▼──────┐
                                              │   Worker    │
                                              │ (executes)  │
                                              └──────┬──────┘
                                                     │
                                              ┌──────▼──────┐
                                              │   Accept    │
                                              │ (validates) │
                                              └──────┬──────┘
                                                     │
                                              ┌──────▼──────┐
                                              │  Registry   │
                                              │ (persists)  │
                                              └─────────────┘
```

## Workers

| Worker | What it does | How it runs |
|--------|-------------|-------------|
| Claude Code | Translation, summarization, code, writing | `claude -p "..." --output-format json` |
| MinerU | PDF → Markdown | Cloud API via `mineru.net/api/v4` |
| Whisper | Audio → Text | Local CLI `whisper input.mp3 --model small` |

Adding a new worker: create a renderer in `workers/<name>/renderer.py` and register it in `capability_matrix.py`.

## CLI reference

```bash
# Submit a task
python3 dispatcher.py submit --type <type> --title "<title>" --input <path> --output <path>

# Run all pending tasks
python3 dispatcher.py run

# Show task status
python3 dispatcher.py status

# Retry a failed task
python3 dispatcher.py retry <task_id>

# Run stress test
python3 stress_test.py --count 100

# Run fault injection tests
python3 test_fault.py
```

## File structure

```
task-os/
├── dispatcher.py              # Core: submit, run, status, retry
├── capability_matrix.py       # Worker routing logic
├── demo.py                    # Interactive demo
├── schema_task_spec_v0.1.yaml # Task Spec schema
├── schema_registry_v0.1.yaml  # Registry schema
├── workers/
│   ├── mineru/
│   │   ├── adapter.py         # MinerU cloud API adapter
│   │   └── renderer.py        # MinerU command renderer
│   └── whisper/
│       └── renderer.py        # Whisper command renderer
├── docs/
│   ├── ARCHITECTURE.md        # System architecture
│   ├── DECISIONS.md           # Design decisions
│   ├── MEMORY.md              # Project memory
│   ├── OPERATIONS.md          # Operations guide
│   ├── ROADMAP.md             # Future plans
│   └── WORKERS.md             # Worker development guide
├── stress_test.py             # 100-task stress test
├── test_fault.py              # Fault injection tests
├── test_mineru_integration.py # MinerU integration tests
└── test_whisper_integration.py # Whisper integration tests
```

## Pitfalls

These are real issues encountered during development. Read before using in production.

1. **`TaskSpec.create()` ≠ `Registry.register()`** — create only saves the spec file. You must call `dispatcher.submit()` or `registry.register()` to appear in the registry.

2. **Atomic writes must use `os.replace()`** — writing directly with `open("w")` corrupts on crash. Always: write to `.tmp` → `fsync` → `os.replace()`.

3. **JSON parsing must be robust** — Claude Code stdout may have non-JSON text (warnings, errors). Use `_parse_claude_output()` to extract the largest JSON block.

4. **`subprocess.run` is blocking** — one task blocks the entire dispatcher. 100 tasks serial ≈ 55 minutes. Parallelism requires architectural changes.

5. **MinerU is a cloud API** — requires `MINERU_API_KEY` environment variable. Adapter at `workers/mineru/adapter.py`.

6. **Timeout but file already written** — Claude may finish writing after subprocess timeout. Check output file before marking as failed.

7. **BOM prefix breaks frontmatter detection** — Windows editors may save with UTF-8 BOM. Use `encoding='utf-8-sig'` and `lstrip('\ufeff')` before checking for `---`.

8. **Long tasks need dynamic timeout** — `video_to_article` tasks need 30+ max-turns and `max(900, min(1800, size_kb * 1.5))` timeout.

## License

MIT

---

# 中文文档

## 这是什么

一个轻量级、基于文件系统的 AI Agent 任务编排系统。把任务路由到最合适的工具，用确定性检查验收结果，崩溃了自动恢复。

## 核心理念

任务描述（Task Spec）和执行工具（Worker）完全解耦。换工具不用改任务描述。验收靠硬指标，不靠 AI 自评。

## 六个组件

| 组件 | 职责 | 变化频率 |
|------|------|---------|
| Task Spec | 描述"做什么" | 不变 |
| Registry | 记录任务状态 | 每个任务都在变 |
| Memory | 经验教训 | 偶尔更新 |
| Capability Matrix | 路由到哪个 Worker | 加新 Worker 时改 |
| Renderer | 把 Spec 翻译成 Worker 命令 | 加新 Worker 时改 |
| Acceptance | 验收标准 | 按任务类型定义 |

## 什么时候用 task-os vs cc-orchestrator

- **task-os**：有代码、有 CLI、自动跑、自动验收。适合重复性批量任务。
- **cc-orchestrator**：纯方法论、手动执行、支持并行。适合一次性大任务。

详见 SKILL.md。
