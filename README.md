# Task OS

A lightweight task operating system for AI agents.

Task OS provides deterministic task routing, execution tracking, validation, and recovery for long-running agent workflows. It also includes an orchestration methodology for coordinating multiple agents in parallel.

Instead of relying on chat history, Task OS stores task state explicitly and allows agents to resume work reliably across sessions.

---

## Why Task OS

AI agents are increasingly capable of performing complex work, but many workflows still depend on fragile chat sessions.

Task OS introduces a file-based execution model:

```
Task → Routing → Execution → Validation → Registry
```

This approach provides:

* Explicit task lifecycle management
* Crash recovery
* Resume support
* Deterministic acceptance checks
* Persistent execution history

---

## Install

```bash
git clone https://github.com/kai0258/Task-os.git
cd Task-os/task-os
```

## Quick Start

```bash
# Submit a task
python3 dispatcher.py submit --type translate --title "Translate README" \
  --input ./README.md --output ./README_zh.md

# Run all pending tasks
python3 dispatcher.py run

# Check status
python3 dispatcher.py status

# Retry a failed task
python3 dispatcher.py retry <task_id>
```

---

## Core Architecture

```
Submit
  ↓
Capability Matrix
  ↓
Renderer
  ↓
Worker
  ↓
Acceptance
  ↓
Registry
```

### Capability Matrix

Routes tasks to the most appropriate worker.

* Translation → Claude Code
* PDF extraction → MinerU
* Audio transcription → Whisper
* Code generation → Claude Code

### Renderer

Converts a Task Spec into a worker-specific command. Changing workers doesn't require changing specs.

### Hard Acceptance

Outputs must pass deterministic checks before completion:

* File existence
* Minimum content requirements (lines, bytes)
* Encoding validation (UTF-8)
* Keyword validation
* Compression ratio (output-to-input sanity)

### Crash Recovery

Automatically recovers interrupted executions and stale task states on startup:

* Recovers `.tmp` registry files from interrupted atomic writes
* Marks stale `doing` tasks (> 1 hour) as `failed`
* Re-validates `review` tasks whose output may now exist
* Marks `done` tasks with missing output as `failed`

### Resume Support

Failed sessions can continue from the last known execution state via `--resume <session_id>`.

---

## Supported Workers

| Worker      | Purpose                    |
|-------------|----------------------------|
| Claude Code | Coding and knowledge tasks |
| MinerU      | PDF extraction (cloud API) |
| Whisper     | Speech transcription (local CLI) |

Additional workers can be added through the worker interface in `capability_matrix.py`.

---

## Known Pitfalls

These are real issues encountered during development. Read before using in production.

1. **`TaskSpec.create()` ≠ `Registry.register()`** — create only saves the spec file. You must call `submit()` to appear in the registry.

2. **Atomic writes must use `os.replace()`** — writing directly with `open("w")` corrupts on crash. Always: write to `.tmp` → `fsync` → `os.replace()`.

3. **`subprocess.run` is blocking** — one task blocks the entire dispatcher. 100 tasks serial ≈ 55 minutes.

4. **MinerU is a cloud API** — requires `MINERU_API_KEY` environment variable.

5. **Timeout but file already written** — Claude may finish writing after subprocess timeout. Check output file before marking as failed.

6. **BOM prefix breaks frontmatter detection** — Windows editors may save with UTF-8 BOM. Use `utf-8-sig` encoding and `lstrip('\ufeff')` before checking for `---`.

---

---

## Orchestrator Framework

Task OS includes a lightweight orchestration methodology for coordinating multiple AI agents in parallel.

The framework defines:

* Task decomposition
* Worker assignment
* Shared task logs (Task_Log.md)
* Context handoff (Handoff_Prompt.txt)
* Failure recovery (partial retry)

Unlike fully autonomous orchestration systems, the Task OS orchestrator follows a human-supervised execution model designed for Claude Code, Hermes, Codex, and terminal-based agent workflows.

See: [`Orchestrator/`](Orchestrator/)

## Design Goals

Task OS is designed around four principles:

1. **Explicit state over chat memory** — task state lives in files, not in context windows
2. **Deterministic validation over subjective evaluation** — hard checks, not LLM self-assessment
3. **Recovery over restart** — crash recovery and resume, not "run it again"
4. **Reproducible workflows over one-off execution** — same spec, same result

---

## Documentation

* [SKILL.md](task-os/SKILL.md) — Full system reference
* [docs/ARCHITECTURE.md](task-os/docs/ARCHITECTURE.md) — Design overview
* [docs/DECISIONS.md](task-os/docs/DECISIONS.md) — Engineering rationale
* [docs/WORKERS.md](task-os/docs/WORKERS.md) — Worker development guide
* [docs/OPERATIONS.md](task-os/docs/OPERATIONS.md) — Operations guide
* [docs/ROADMAP.md](task-os/docs/ROADMAP.md) — Future plans
* [Orchestrator/README.md](Orchestrator/README.md) — Orchestration framework
* [Orchestrator/SKILL.md](Orchestrator/SKILL.md) — Full orchestration methodology

---

## Intended Use Cases

* AI-assisted software development
* Research workflows
* Document processing
* Translation pipelines
* Multi-step automation
* Long-running agent tasks

---

## License

[MIT](task-os/LICENSE)
