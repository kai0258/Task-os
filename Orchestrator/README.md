# CC-Orchestrator

Claude Code parallel orchestration and task relay system.

Run multiple Claude Code instances in parallel, track progress in a shared log, and hand off context when a window runs out of space. Zero dependencies — just files and tmux.

**For AI coding agents handling large tasks that exceed a single context window.**

[中文文档](#中文文档)

---

## What it does

When a task is too big for one Claude Code window — 50+ files, 30+ steps, hours of work — CC-Orchestrator splits it into parallel lanes, each running in its own tmux session. A shared `Task_Log.md` tracks everything. When a window's context fills up, a `Handoff_Prompt.txt` carries the state to a fresh window.

```
Task arrives
  → Assess scale (Step 1)
  → Create workspace with 4 folders (Step 2)
  → Write Task_Log.md (Step 3)
  → Split into 2-4 parallel windows (Step 4-5)
  → Launch tmux sessions (Step 6)
  → Collect reports from each window (Step 7)
  → Retry only failures (Step 8)
  → Clean up (Step 10)
  → Hand off if context runs out (Step 11)
```

## Prerequisites

| Requirement | Why |
|---|---|
| [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) | The coding agent that executes tasks |
| tmux | Terminal multiplexer for parallel sessions |
| Linux / macOS / WSL | tmux doesn't run natively on Windows |

## Installation

### As a Hermes Agent skill

```bash
git clone https://github.com/kai0258/Task-os.git
cp -r Task-os/Orchestrator ~/.hermes/skills/
```

Hermes will auto-load this skill when it detects a large task.

### As a Claude Code skill

```bash
git clone https://github.com/kai0258/Task-os.git
mkdir -p ~/.claude/skills
cp -r Task-os/Orchestrator ~/.claude/skills/
```

### Manual (no agent framework)

```bash
git clone https://github.com/kai0258/Task-os.git
```

Read `SKILL.md` and follow the 11 steps directly. Works with any AI coding agent that can read instructions.

## Quick start

### 1. Create a workspace

```bash
mkdir -p ~/Task-Orchestrator-my-project/{00_Task_Log,01_Prompts,02_Prompt_Backup,03_Reports}
```

### 2. Write Task_Log.md

```bash
cat > ~/Task-Orchestrator-my-project/00_Task_Log/Task_Log.md << 'EOF'
# Task Log

## 任务描述
Refactor the auth module across 15 files.

## 当前状态
未开始

## 窗口分配
Window01: Refactor auth/login.py, auth/session.py, auth/middleware.py
Window02: Refactor auth/models.py, auth/views.py, auth/serializers.py
Window03: Update tests for Window01 changes
Window04: Update tests for Window02 changes
EOF
```

### 3. Write prompts for each window

```bash
cat > ~/Task-Orchestrator-my-project/01_Prompts/Round01_Window01.txt << 'EOF'
# 当前任务
Refactor auth module: login.py, session.py, middleware.py

# 本窗口负责范围
Only modify auth/login.py, auth/session.py, auth/middleware.py.
Do NOT touch any other files.

# 输出要求
- Extract shared constants into auth/constants.py
- Replace hardcoded secrets with environment variables
- Add type hints to all public functions

# 报告要求
完成后生成 Report_R01_W01.md 放入 03_Reports/
报告格式：完成时间、执行步骤、修改文件列表、发现问题、最终结果
EOF

# Backup
cp ~/Task-Orchestrator-my-project/01_Prompts/Round01_Window01.txt \
   ~/Task-Orchestrator-my-project/02_Prompt_Backup/
```

### 4. Launch parallel sessions

```bash
cd ~/Task-Orchestrator-my-project

tmux new-session -d -s w01 "claude -p \"$(cat 01_Prompts/Round01_Window01.txt)\" \
  --output-format json --dangerously-skip-permissions"

tmux new-session -d -s w02 "claude -p \"$(cat 01_Prompts/Round01_Window02.txt)\" \
  --output-format json --dangerously-skip-permissions"
```

### 5. Monitor progress

```bash
tmux list-sessions                          # Check if running
tmux attach -t w01                          # Watch a session
cat ~/Task-Orchestrator-my-project/00_Task_Log/Task_Log.md  # Read the log
```

### 6. Review and retry

After all windows finish, read reports in `03_Reports/`. If any failed, create a `Round02` prompt for only the failed parts and re-run that window.

## Workspace structure

```
Task-Orchestrator-[task-name]/
├─ 00_Task_Log/
│  ├─ Task_Log.md            # Central state file — read this FIRST
│  └─ Handoff_Prompt.txt     # Generated when context runs out
├─ 01_Prompts/               # Prompts sent to Claude Code
│  ├─ Round01_Window01.txt
│  └─ ...
├─ 02_Prompt_Backup/         # Mirror of 01_Prompts (auto-synced)
└─ 03_Reports/               # Reports from each window
   ├─ Report_R01_W01.md
   └─ ...
```

## Context handoff

When a Claude Code window's context is nearly full (< 20% remaining):

1. Agent stops working
2. Updates `Task_Log.md` with current progress
3. Generates `00_Task_Log/Handoff_Prompt.txt`
4. New window reads the handoff file and continues

Chains indefinitely: Window A → B → C → ...

## Comparison with alternatives

| Feature | CC-Orchestrator | oh-my-claudecode | planning-with-files | SupaConductor |
|---|---|---|---|---|
| tmux parallel windows | ✓ | ✓ | ✗ | ✗ |
| Central state log | ✓ | ✗ | ✓ (concept) | ✗ |
| Context handoff | ✓ | ✗ | ✓ (concept) | ✗ |
| Prompt distribution | ✓ | ✗ | ✗ | ✗ |
| Prompt backup | ✓ | ✗ | ✗ | ✗ |
| Per-window reports | ✓ | ✗ | ✗ | ✗ |
| Partial retry | ✓ | ✓ | ✗ | ✗ |
| Zero dependencies | ✓ | ✗ | ✓ | ✗ |
| Executable code | ✗ (methodology) | ✓ | ✗ | ✓ |

## Documentation

The full methodology with all 11 steps, templates, and pitfalls is in **[SKILL.md](SKILL.md)**.

## License

[MIT](LICENSE)

---

# 中文文档

## 这是什么

CC-Orchestrator 是一套 Claude Code 并行调度方法论。当任务太大、太长、单窗口装不下时，用它把任务拆成多个窗口并行跑，用文件系统追踪状态，上下文耗尽就自动交接给下一个窗口。

没有代码，没有依赖，就是一套操作流程。

## 适用场景

- 翻译一本书，每章一个窗口
- 重构一个大项目，每个模块一个窗口
- 批量生成研究报告，每个课题一个窗口
- 任何预计超过 30 分钟或 20 步的任务

## 安装

```bash
git clone https://github.com/kai0258/Task-os.git

# Hermes Agent
cp -r Task-os/Orchestrator ~/.hermes/skills/

# Claude Code
mkdir -p ~/.claude/skills && cp -r Task-os/Orchestrator ~/.claude/skills/
```

或者直接读 `SKILL.md` 手动执行。

## 核心设计

1. **Task_Log.md 是唯一真相源** — 所有窗口共享，任何 Agent 接手第一件事就是读它
2. **提示词必须自包含** — 每个窗口的提示词包含所有需要的信息，不依赖外部文件
3. **备份必须同步** — 提示词改了，备份立刻跟着改
4. **失败只修失败部分** — 禁止全部重做
5. **上下文耗尽主动交接** — 不要等到完全没空间了才行动

## 常见问题

**Q: 必须用 Claude Code 吗？**
A: 不必须。任何能通过命令行接收提示词的 AI 编码工具都可以（如 Codex CLI、Gemini CLI）。tmux 是通用的。

**Q: Windows 能用吗？**
A: 需要 WSL。tmux 在原生 Windows 上不运行。

**Q: 和 task-os 是什么关系？**
A: task-os 是有代码的自动化工具（引擎），Orchestrator 是纯方法论（手册）。task-os 自动跑但不支持并行；Orchestrator 支持并行但需要手动执行。详见 SKILL.md。
