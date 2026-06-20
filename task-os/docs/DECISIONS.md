# 架构决策记录

## 为什么不用 LangGraph

LangGraph 是一个图执行框架，适合复杂的工作流编排。但 Task OS 的核心需求是：

- 用户说一句话 → 拆成任务 → 执行 → 验收
- 不需要复杂的条件分支、循环、子图
- 需要的是状态机，不是 DAG

LangGraph 引入了不必要的抽象层。我们的 Dispatcher 用 200 行 Python 就实现了完整的状态机，没有额外依赖。

## 为什么不用 AutoGen

AutoGen 是多 Agent 对话框架。Task OS 不需要多个 AI Agent 对话。我们的架构是：

- Dispatcher 是调度器（不是 Agent）
- Worker 是执行器（可以是 Agent，也可以是 CLI 工具）
- 两者是单向调用关系，不是对话关系

AutoGen 解决的是「让 AI Agent 互相聊天」，Task OS 解决的是「让任务可靠地被执行」。

## 为什么采用 Task Spec

核心洞察：**Prompt 是 Worker 专属格式，Task Spec 是系统级格式。**

如果 Dispatcher 直接生成 Prompt：
- 换 Worker 要改 Dispatcher 代码
- 无法做 Capability Matrix 路由
- 无法对同类任务做统计分析

Task Spec 把「做什么」和「怎么做」分离。Dispatcher 只管「做什么」，Renderer 负责「怎么做」。

## 为什么采用 Registry

核心洞察：**系统需要一个唯一状态源。**

没有 Registry：
- Dispatcher 崩溃后不知道哪些任务在跑
- 无法做 Crash Recovery
- 无法追踪进度

Registry 使用原子写入（tmp + fsync + rename），保证崩溃安全。v0.1.1 压力测试验证了 300+ 次写入零损坏。

## 为什么采用 Renderer

核心洞察：**同一个任务，不同 Worker 需要完全不同的指令格式。**

Claude 需要自然语言 Prompt，Whisper 需要 CLI 命令，MinerU 需要 API 调用脚本。Renderer 把统一的 Task Spec 翻译成各 Worker 能理解的指令。

好处：
- 加新 Worker 只需写一个 Renderer
- Task Spec 永远不变
- 可以对同一个 Task Spec 用不同 Renderer 做 A/B 测试

## 为什么采用 Capability Matrix

核心洞察：**不同任务类型有不同的最优执行器。**

- PDF 解析 MinerU 比 Claude 好（表格、公式、图片）
- 语音转录 Whisper 是专用工具
- 翻译 Claude 推理能力强

Capability Matrix 让 Dispatcher 自动选择最优 Worker，不需要用户每次手动指定。

## 为什么验收不信任 Worker 自报

Claude Code 可能返回 `{"status": "success"}` 但输出文件为空。Whisper 可能返回 exit_code=0 但输出文件只有乱码。

验收只检查输出文件本身：存在？非空？行数够？关键词在？

Worker 说什么不重要，文件系统说什么才重要。

## 为什么 Memory 和 History 分离

History 是事实（「任务#001 翻译了第5章，耗时320秒」）。
Memory 是规则（「法律文本必须保留脚注」）。

History 可以很大，Memory 必须精炼。

把所有 History 塞进 Memory 会撑爆上下文。把 Memory 只存在 History 里会丢失经验。

正确做法：History → 定期复盘 → 提炼规则 → 写入 Memory。
