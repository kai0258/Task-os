# Task OS 架构文档

## Task OS 是什么

Task OS 是一个任务调度操作系统。它把用户需求拆解为标准化的任务单元（Task Spec），通过 Renderer 翻译成不同 Worker 的执行指令，由 Worker 执行后自动验收，最终归档。

## 解决什么问题

用户说「翻译这本书」「转录这批视频」「把PDF转成Markdown」，Task OS 负责：

1. 拆解任务
2. 选择最合适的执行器
3. 派发任务
4. 验收结果
5. 失败时自动重试

执行器可以是 Claude Code、Whisper、MinerU、FFmpeg，也可以是未来任何新工具。Task OS 不绑定任何特定执行器。

## 核心架构

```
用户
 |
 v
Dispatcher（调度器）
 |
 v
Task Spec（任务规格）
 |
 v
Capability Matrix（能力矩阵）
 |
 v
Renderer（渲染器）
 |
 v
Worker（执行器）
 |
 v
Output Files（输出文件）
 |
 v
Acceptance（验收）
 |
 v
Registry（状态注册表）
```

## 组件说明

### Dispatcher（调度器）

系统的主循环。职责：

- 接收用户提交的 Task Spec
- 维护任务状态（todo → doing → review → done/failed）
- 根据 Capability Matrix 选择 Worker
- 调用 Renderer 生成执行命令
- 执行 Worker 并收集结果
- 触发 Acceptance 验收
- 失败时触发 Retry
- 启动时执行 Crash Recovery

Dispatcher 不关心具体用哪个 Worker 执行。它只管状态流转。

### Task Spec（任务规格）

描述「做什么」的标准化格式。字段：

```yaml
task_id: t_xxx
task_type: translate          # 任务类型
title: "翻译第5章"             # 标题
input:
  source: /path/to/input       # 输入文件
  reference: /path/to/source   # 参考文件（可选）
output:
  target: /path/to/output      # 输出文件
requirements:                  # 要求
  - "翻译为简体中文"
acceptance:                    # 验收标准
  hard:
    - check: file_exists
    - check: min_lines, value: 50
worker_hint: claude            # 建议Worker（可选）
depends_on: []                 # 依赖任务（预留）
```

Task Spec 不包含任何 Worker 专有信息。没有 prompt、没有 Claude 参数、没有 Whisper 命令。它是纯中立的任务描述。

### Capability Matrix（能力矩阵）

根据 task_type 选择最优 Worker：

```python
capability_matrix = {
    "pdf_to_markdown": {"preferred": "mineru", "fallbacks": ["claude"]},
    "transcribe":      {"preferred": "whisper", "fallbacks": []},
    "summarize":       {"preferred": "claude",  "fallbacks": []},
    "translate":       {"preferred": "claude",  "fallbacks": []},
}
```

Task Spec 的 worker_hint 可以覆盖默认路由。

### Renderer（渲染器）

把 Task Spec 翻译成特定 Worker 的执行指令。每个 Worker 有自己的 Renderer：

| Renderer | 输入 | 输出 |
|----------|------|------|
| ClaudeRenderer | Task Spec | `claude -p "..." --output-format json` |
| WhisperRenderer | Task Spec | `whisper input.mp3 --model small --language zh` |
| MinerURenderer | Task Spec | `python3 adapter.py input.pdf output.md` |

Renderer 是 Task Spec 和 Worker 之间的翻译层。换 Worker 只需要换 Renderer，Task Spec 不变。

### Worker（执行器）

实际执行任务的工具。可以是：

- CLI 工具（whisper、ffmpeg）
- API 调用（MinerU 云端 API）
- AI Agent（Claude Code、Codex）
- 任何能接收命令并产出文件的程序

Worker 不知道自己属于 Task OS。它只接收命令、执行、产出文件。

### Acceptance（验收）

检查 Worker 产出的文件是否符合要求。分两层：

**Hard Requirements（不过必退）：**
- 文件存在且非空
- 行数/字节数在范围内
- 必须包含指定关键词
- 编码正确

**Soft Requirements（阈值通过，v0.3实现）：**
- LLM 打分：翻译准确度、表达自然度、结构合理性

验收检查的是输出文件本身，不信任 Worker 自报的成功状态。

### Registry（状态注册表）

记录每个任务的状态。唯一状态源。

```
todo → doing → review → done
                   ↘ failed → retry → doing
                              ↘ escalated
```

Registry 使用原子写入（write tmp → fsync → rename），崩溃不会损坏。

## 设计原则

1. **Task Spec 与 Worker 解耦**：任务描述不绑定执行器
2. **Renderer 是翻译层**：换 Worker 只换 Renderer
3. **验收不信任 Worker**：只信文件系统
4. **Registry 是唯一状态源**：崩溃可恢复
5. **Memory 属于系统，不属于 Dispatcher**：换调度器不丢经验
