# 系统经验（Memory）

> 这是从实践中提炼的规则，不是历史记录。
> History 保存发生了什么，Memory 保存应该怎么做。

## 铁律：维护顺序不可逆

**任何修改 Task OS 的行为，必须按以下顺序执行：**

1. **先更新文档**（docs/）
2. **再修改代码**（*.py）
3. **最后更新测试**（test_*.py）

**顺序不能反。** 违反此规则的修改一律拒绝。

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

## 工作模式

任何修改必须按以下步骤执行，不允许跳过：

1. 先分析
2. 输出设计方案
3. 等待确认
4. 实施修改
5. 运行测试
6. 更新文档
7. Git Commit

**除非明确要求，否则不要直接修改代码。**

## 仓库定义

`task-os/` 不是代码目录，是**数字资产仓库**。资产包含：

- 代码（dispatcher.py、renderers、adapters）
- 文档（docs/）
- 经验（MEMORY.md、DECISIONS.md）
- 测试（test_*.py、stress_test.py）
- 历史决策（DECISIONS.md）

五者缺一不可。删除任何一项等于破坏资产。

## 升级原则

v0.2 冻结开发。升级触发条件是业务指标，不是技术指标：

- 同时积压 1000+ 个任务
- 需要多个 Worker 并行跑
- 想让系统自动学习经验
- 想让多个 Agent 协同工作
- 想把「丞相-六部」真正落地

在那之前，最有价值的事是：把 Task OS 从「能跑的代码」变成「能传承的资产」。积累真实任务、沉淀 Memory、验证 Worker 能力边界。

## 任务类型 → Worker 路由

| 场景 | 首选 Worker | 原因 |
|------|-------------|------|
| PDF → Markdown | MinerU | 擅长表格、公式、图片解析，Claude 会丢失格式 |
| 音频 → 文字 | Whisper | 专用 ASR 工具，本地运行无成本 |
| 长文翻译 | Claude | 推理能力强，上下文窗口大 |
| 简单摘要 | Claude | 够用且便宜 |
| 内容重构 | Claude | 需要理解语义和结构 |
| 代码任务 | Claude | 编码能力强 |

## 验收规则

| 规则 | 原因 |
|------|------|
| 验收只看文件系统，不看 Worker 自报 | Claude 可能返回 success 但文件为空 |
| Hard 不过必退，不进入 Soft 检查 | 省 token，快速失败 |
| 翻译任务必须检查人名/数字/日期 | 这些是最容易漏译或误译的 |
| 法律文本必须保留脚注 | 丢失脚注会导致法律引用缺失 |
| 多人对话视频必须标明发言人 | 否则读者分不清谁在说话 |

## Registry 规则

| 规则 | 原因 |
|------|------|
| Registry 必须原子写入 | 崩溃不会损坏（v0.1.1 已修复） |
| retry 必须保留 session_id | 否则 Claude 无法 resume，返工等于重做 |
| doing 状态必须有超时保护 | 否则一个卡死的任务会阻塞整个队列 |
| 启动时必须执行 Crash Recovery | 恢复上次崩溃时的 doing / review 状态 |

## 执行经验

| 经验 | 来源 |
|------|------|
| Claude Code 平均执行时间 20-35 秒/简单任务 | v0.1.1 压力测试（100 任务） |
| 偶尔 Claude Code 会慢到 90-100 秒 | 可能是 API 排队 |
| Whisper CPU 模式转录 14 小时音频约需 2.5 小时 | 实际测试 |
| MinerU 云端 API 单文件处理约 30-60 秒 | 取决于 PDF 复杂度 |

## 踩坑记录

| 坑 | 解法 |
|----|------|
| `json.loads(stdout)` 不容忍前后非 JSON 文本 | 用正则提取最大的 JSON 块（v0.1.2 已修复） |
| Task Spec.create() 只保存 spec 文件，不注册到 Registry | 必须显式调用 registry.register(spec) |
| WSL 下 rm /mnt/ 路径是永久删除 | 无回收站，谨慎操作 |
| 小米 API 内容审核拦截政治敏感内容 | 用 Claude Worker 替代处理敏感任务 |