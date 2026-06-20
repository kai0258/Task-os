# Task OS

A lightweight, file-based task orchestration system for AI coding agents.

Routes tasks to the right worker, validates results with deterministic checks, and recovers from crashes automatically.

**Task Spec → Renderer → Worker → Acceptance → Registry.**

## Install

```bash
git clone https://github.com/kai0258/Task-os.git
cd Task-os/task-os
```

## Quick start

```bash
# Submit a task
python3 dispatcher.py submit --type translate --title "Translate README" \
  --input ./README.md --output ./README_zh.md

# Run
python3 dispatcher.py run

# Check status
python3 dispatcher.py status

# Retry
python3 dispatcher.py retry <task_id>
```

## How it works

```
Submit → Capability Matrix → Renderer → Worker → Hard Acceptance → Registry
```

- **Capability Matrix** routes by task_type (translate → Claude, pdf → MinerU, audio → Whisper)
- **Hard Acceptance** validates with deterministic checks (file exists, min lines, encoding, keywords)
- **Crash Recovery** auto-recovers stale tasks and interrupted writes
- **Retry via Resume** resumes failed sessions with `--resume <session_id>`

## Workers

| Worker | Task types | How |
|--------|-----------|-----|
| Claude Code | translate, summarize, code | `claude -p "..." --output-format json` |
| MinerU | pdf_to_markdown | Cloud API (`MINERU_API_KEY`) |
| Whisper | transcribe | Local CLI |

## Documentation

Full docs in [task-os/](task-os/):

- [SKILL.md](task-os/SKILL.md) — Complete reference
- [docs/ARCHITECTURE.md](task-os/docs/ARCHITECTURE.md) — Architecture
- [docs/DECISIONS.md](task-os/docs/DECISIONS.md) — Design decisions
- [docs/WORKERS.md](task-os/docs/WORKERS.md) — Worker development guide

## License

[MIT](task-os/LICENSE)
