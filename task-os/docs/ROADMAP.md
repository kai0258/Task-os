# Roadmap

## v0.1 — 单 Worker 闭环（已完成）

- [x] Task Spec Schema
- [x] Registry（状态管理）
- [x] ClaudeRenderer
- [x] Hard Acceptance
- [x] Dispatcher 主流程
- [x] CLI 入口（submit/run/status/retry）

## v0.1.1 — 可靠性修复（已完成）

- [x] Registry 原子写入（tmp + fsync + rename）
- [x] Crash Recovery（启动时自动恢复 stale doing / review / output missing）
- [x] Retry + Resume（保留 session_id，生成 --resume 命令）
- [x] 鲁棒 JSON 解析（容忍前后非 JSON 文本）
- [x] 防重复执行（输出文件已存在且通过验收则跳过）
- [x] 100 任务压力测试通过

## v0.2 — 多 Worker（已完成）

- [x] WhisperRenderer
- [x] MinerURenderer + MinerU Adapter
- [x] Capability Matrix（静态路由）
- [x] Worker 注册机制
- [x] 故障注入测试（5 个场景）
- [x] MinerU 集成测试
- [x] Whisper 集成测试

## 当前阶段：资产沉淀（冻结开发）

**v0.2 已满足当前所有业务需求。不主动开发 v0.3。**

当前最有价值的事不是继续开发，而是把 Task OS 从「能跑的代码」变成「能传承的资产」。

### 升级触发条件（业务指标，非技术指标）

当且仅当遇到以下任意一种情况时，才进入 v0.3：

- 同时积压 1000+ 个任务
- 需要多个 Worker 并行跑
- 想让系统自动学习经验
- 想让多个 Agent 协同工作
- 想把「丞相-六部」真正落地

**在那之前，所有精力用于：积累真实任务、沉淀 Memory、验证 Worker 能力边界。**

---

## v0.3 — Soft Acceptance + Memory（触发条件满足后启动）

- [ ] Soft Acceptance（LLM 打分：准确度、自然度、结构）
- [ ] Memory Store（文件化：user_preferences / terminology / lessons_learned）
- [ ] History → Memory 提炼机制
- [ ] Acceptance 模板化（按 task_type 自动选择验收规则）

## v0.4 — 并行执行 + 任务队列（规划中）

- [ ] 任务队列（文件系统 todo/ doing/ review/ done/）
- [ ] 多 Worker 并行执行
- [ ] Depends On 依赖关系实现（DAG 调度）
- [ ] Worker 超时自动 kill + 重试
- [ ] 并发写入安全（文件锁或 SQLite）

## v0.5 — 统计与自优化（规划中）

- [ ] Worker 性能统计（成功率、耗时、成本）
- [ ] Capability Matrix 自动学习（数据驱动路由）
- [ ] 任务模板库（常见任务的预设 Spec）
- [ ] 自动重试策略（根据失败类型选择 resume / 重建 / 切换 Worker）

## v1.0 — 生产级（远期）

- [ ] Web UI（任务提交、状态监控、结果查看）
- [ ] REST API（外部系统集成）
- [ ] 多 Dispatcher 实例（分布式调度）
- [ ] 插件化 Worker（动态注册）
- [ ] 完整的 MCP Server（让其他 Agent 调用 Task OS）
