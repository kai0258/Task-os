---
name: Orchestrator
description: "Claude Code parallel orchestration and task relay system. Use when receiving large tasks, long-cycle tasks, multi-window parallel execution tasks, or when user explicitly requests orchestration. Manages task logging, prompt distribution, status tracking, failure recovery, and context-exhaustion handoff."
---

# CC-Orchestrator — Claude Code 并行调度与任务接力系统

核心原则：可恢复、可追踪、可审计、可接力、可重试。

即使当前 Agent 崩溃、窗口关闭、上下文耗尽、新 Agent 接手，也能依靠任务日志和工作文件完整恢复任务状态。

---

## Step 1: 任务规模评估

分析任务：复杂度、预计文件数、操作步骤数、是否涉及搜索/代码修改/长文处理、是否可能超出单窗口上下文。

满足以下任一条件则判定为 LARGE_TASK，自动启动本 skill：

- 预计超过 30 分钟
- 预计超过 20 个操作步骤
- 涉及多个目录
- 超出单窗口上下文容量
- 用户明确要求并行

**判定后向用户简要说明任务规模和调度计划，确认后继续。**

---

## Step 2: 建立任务工作区

在桌面创建目录结构：

```
[workspace]/Task-Orchestrator-[task-name]/
├─ 00_Task_Log\
│  └─ Task_Log.md          # 最高优先级文件，任何 Agent 接手必须先读
│  └─ Handoff_Prompt.txt    # 交接提示词（上下文耗尽时生成）
├─ 01_Prompts\              # 发给 Claude Code 的提示词
│  └─ Round01_Window01.txt
│  └─ Round01_Window02.txt
│  └─ ...
├─ 02_Prompt_Backup\        # 提示词副本（必须与 01_Prompts 同步）
└─ 03_Reports\              # Claude Code 生成的任务报告
   └─ Report_R01_W01.md
   └─ ...
```

---

## Step 3: 创建 Task_Log.md

写入 `00_Task_Log/Task_Log.md`，包含以下章节（持续更新）：

```markdown
# Task Log

## 任务描述
[原始用户需求]

## 当前状态
[未开始 / 执行中 / 等待检查 / 已完成 / 失败需重试]

## 执行轮次
Round X

## 窗口分配
Window01: [任务内容]
Window02: [任务内容]
Window03: [任务内容]
Window04: [任务内容]

## 已完成内容
[持续更新]

## 检查结果
[持续更新]

## 下一步行动
[持续更新]

## 接力说明
任何 Agent 接手时按顺序阅读：
1. Task_Log.md
2. 03_Reports/ 全部报告
3. 01_Prompts/ 当前轮次提示词
```

---

## Step 4: 决定并行规模

根据任务规模和 Claude Code 剩余上下文容量动态决定轮次和窗口数。

规则：单轮最多 4 个 Claude Code 窗口。

| 任务规模 | 轮次 | 窗口数 |
|---------|------|-------|
| 小型大型 | R01  | 2     |
| 中型     | R01  | 3     |
| 超大型   | R01  | 4，R02 依需递减 |

---

## Step 5: 生成 Claude Code 提示词

每个窗口生成独立提示词文件，存放于 `01_Prompts/`，同时复制到 `02_Prompt_Backup/`。

命名格式：`Round{XX}_Window{XX}.txt`

每个提示词必须包含：

```
# 当前任务
[任务说明]

# 本窗口负责范围
[明确边界，禁止越界修改]

# 输出要求
[生成成果]

# 报告要求
完成后生成 Report_R{XX}_W{XX}.md 放入 03_Reports/

# 报告格式
- 完成时间
- 执行步骤
- 修改文件 / 新增文件 / 删除文件
- 发现问题
- 风险项
- 建议
- 最终结果

# 自检要求
文件检查 → 逻辑检查 → 结果检查 → 确认无误后提交报告
```

**提示词必须自包含**——嵌入所有规则、质量标准和输出格式，不引用可能被并发读写的外部文件。

**避免在提示词中列出敏感文档名称**——内容过滤可能拦截包含敏感词的提示词。改为指示 Claude Code 自行扫描目标目录识别文件。

---

## Step 6: 发送任务到 Claude Code

使用 claude skill 的方式执行：

- **print mode (`-p`)** 用于单轮单窗口任务
- **tmux 并行** 用于多窗口任务

每个窗口在独立 tmux session 中运行，互不干扰。

提示词修改时必须同步更新 `02_Prompt_Backup/`。

---

## Step 7: 检查流程

所有窗口完成后统一检查：

1. 阅读 Task_Log.md
2. 阅读 03_Reports/ 全部报告
3. 检查成果文件

检查项：
- 是否满足任务要求
- 是否存在遗漏
- 是否存在冲突
- 是否存在重复劳动

**检查结果写入 Task_Log.md 的「检查结果」章节。**

---

## Step 8: 失败重试机制

检查失败时：

1. 更新 Task_Log.md，记录失败原因、问题位置、需修复内容
2. 仅修复失败部分，禁止全部重做
3. 生成下一轮提示词（Round{N+1}），只包含修复任务
4. 回到 Step 6 执行

---

## Step 9: 任务结束

全部检查通过后：

1. Task_Log.md 状态更新为「已完成」
2. 生成 `00_Task_Log/Final_Summary.md`：任务概览、执行轮次、窗口数量、完成成果、检查结果、最终结论
3. 向用户汇报结果

---

## Step 10: 清理

用户确认成果无误后，删除：

- `00_Task_Log/`
- `01_Prompts/`
- `02_Prompt_Backup/`
- `03_Reports/`

保留最终成果文件。清理完成任务结束。

---

## Step 11: 上下文耗尽交接机制

### 触发条件

满足任一条件立即停止任务，优先执行交接：

- Claude Code 上下文预计剩余低于 20%
- Hermes 上下文预计剩余低于 20%
- Agent 判断任务无法在当前上下文内完成
- 用户明确要求切换窗口

### 交接流程

1. 更新 Task_Log.md（当前进度、已/未完成部分、当前问题、下一步计划、报告列表）
2. 生成 `00_Task_Log/Handoff_Prompt.txt`，同时复制到 `02_Prompt_Backup/`

### Handoff_Prompt.txt 模板

```
# 任务交接

你正在接手一个尚未完成的大型任务。
开始工作前必须依次阅读：
1. Task_Log.md
2. 03_Reports/ 全部报告
3. 当前轮次对应提示词

阅读完成后先总结当前任务状态，确认：
- 已完成内容
- 未完成内容
- 当前阻塞问题
- 下一步计划

确认无误后继续执行。

# 当前任务目标
[自动填入]

# 当前任务状态
[自动填入]

# 已完成内容
[自动填入]

# 未完成内容
[自动填入]

# 当前轮次
Round X / Window X

# 下一步优先事项
[自动填入]

# 注意事项
- 禁止重复执行已完成任务
- 禁止覆盖已验证成果
- 优先延续现有工作流
- 所有新增工作必须记录到 Task_Log.md
- 所有执行结果必须生成报告

# 接手确认
阅读完 Task_Log 与 Reports 后再开始工作。
不要重新规划、拆分或分析需求。
直接从当前进度继续执行。
```

### 强制规则

- 一旦触发交接，当前 Agent 任务结束，禁止继续工作
- 允许无限次接力：Agent A → Agent B → Agent C → ...
- 每次接力必须生成新的 Handoff_Prompt.txt

---

## Pitfalls

1. **提示词必须自包含**——不要引用可能被并发修改的共享文件
2. **提示词备份必须同步**——修改 01_Prompts 后立即更新 02_Prompt_Backup
3. **上下文耗尽前主动触发交接**——不要等到完全耗尽才行动
4. **失败重试只修失败部分**——禁止全部重做
5. **清理前确认路径**——删除操作不可逆，确认路径正确再执行
6. **避免在提示词中列出敏感文档名**——指示 CC 自行扫描目录
