# 运维手册

## 目录结构

```
task-os/
├── dispatcher.py          # 核心引擎
├── capability_matrix.py   # Worker 路由
├── demo.py                # Demo
├── stress_test.py         # 压力测试
├── test_fault.py          # 故障注入测试
├── test_mineru_integration.py
├── test_whisper_integration.py
├── schema_task_spec_v0.1.yaml
├── schema_registry_v0.1.yaml
├── demo_input.md
├── demo_output.md
├── workers/
│   ├── claude/
│   ├── mineru/
│   │   ├── renderer.py
│   │   ├── adapter.py
│   │   └── __init__.py
│   └── whisper/
│       └── renderer.py
├── tasks/
│   ├── specs/             # Task Spec 存储
│   └── registry/
│       └── registry.yaml  # 状态注册表
├── test_inputs/           # 压力测试输入（保留）
├── test_outputs/          # 压力测试输出（保留）
└── docs/
    ├── ARCHITECTURE.md
    ├── DECISIONS.md
    ├── ROADMAP.md
    ├── WORKERS.md
    ├── MEMORY.md
    └── OPERATIONS.md
```

## 常用命令

```bash
# 提交任务
python3 dispatcher.py submit --type summarize --title "摘要" --input /path/in --output /path/out

# 执行所有 todo 任务
python3 dispatcher.py run

# 查看状态
python3 dispatcher.py status

# 重试失败任务
python3 dispatcher.py retry <task_id>

# 运行 Demo
python3 demo.py

# 运行压力测试（100 任务）
python3 stress_test.py --count 100

# 运行故障注入测试
python3 test_fault.py

# 运行 MinerU 集成测试
python3 test_mineru_integration.py

# 运行 Whisper 集成测试
python3 test_whisper_integration.py
```

## 故障排查

### Registry 损坏

```bash
# 检查是否有 .tmp 残留
cat tasks/registry/registry.tmp

# 如果 .tmp 可读，替换 .yaml
cp tasks/registry/registry.tmp tasks/registry/registry.yaml

# 如果都损坏，从备份恢复或删除重建
rm tasks/registry/registry.yaml
```

### 任务卡在 doing 状态

```bash
# 查看状态
python3 dispatcher.py status

# 手动标记为 failed（然后 retry）
# 或者直接删除 registry.yaml 重建
```

### Claude Code 超时

- 检查网络连接
- 检查 API Key 是否有效
- 检查任务是否太大（拆分子任务）

### MinerU API 失败

- 检查 MINERU_API_KEY 环境变量
- 检查 https://mineru.net 是否可达
- 检查 API 额度是否用完

## 环境变量

| 变量 | 用途 |
|------|------|
| TASK_ROOT | 项目根目录（默认为 dispatcher.py 所在目录） |
| MINERU_API_KEY | MinerU 云端 API 密钥 |

## 备份策略

关键数据：
- `tasks/registry/registry.yaml` — 任务状态（原子写入保护）
- `tasks/specs/*.yaml` — 任务规格（创建后不变）
- `workers/` — Worker 代码

备份命令：
```bash
cp -r tasks/ /backup/task-os-tasks-$(date +%Y%m%d)/
```