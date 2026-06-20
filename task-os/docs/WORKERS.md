# Worker 手册

## 已注册 Worker

| Worker | Renderer | 适用任务 | 状态 |
|--------|----------|----------|------|
| Claude | ClaudeRenderer | summarize, translate, refactor, code | 生产可用 |
| Whisper | WhisperRenderer | transcribe | 生产可用 |
| MinerU | MinerURenderer | pdf_to_markdown | 生产可用 |

## Claude Worker

**调用方式：** `claude -p "..." --output-format json`
**特点：** 强推理、强语言能力、成本较高
**适用场景：** 摘要、翻译、内容重构、代码任务
**超时：** 按输入文件大小估算（每 100KB 约 60 秒）
**Retry：** 支持 `--resume` 续接上次会话

## Whisper Worker

**调用方式：** `whisper input.mp3 --model small --language zh --device cpu`
**特点：** 本地运行、无 API 成本、速度取决于 CPU
**适用场景：** 音频/视频转录
**超时：** 按音频时长估算（每分钟约 10 秒 CPU 时间）
**Retry：** 不支持 resume，重新执行

## MinerU Worker

**调用方式：** `python3 adapter.py input.pdf output.md`
**特点：** 云端 API、擅长表格/公式/图片解析
**适用场景：** PDF 转 Markdown
**超时：** 按文件大小估算（每 MB 约 60 秒）
**Retry：** 重新上传执行

## 如何添加新 Worker

1. 在 `workers/<name>/` 下创建 `renderer.py`
2. 实现 `render(spec, registry_entry=None) -> dict` 方法，返回 `{command, workdir, timeout}`
3. 在 `capability_matrix.py` 中注册：
   - `WORKER_REGISTRY["name"] = YourRenderer`
   - 在 `capability_matrix` 字典中添加 task_type 路由
4. 编写集成测试
5. 运行全量测试确认无回归

不需要修改 Task Spec Schema。不需要修改 Registry Schema。不需要修改 Dispatcher。
