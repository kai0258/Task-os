"""Whisper Renderer: Task Spec -> whisper CLI 命令。"""

import os
from pathlib import Path


class WhisperRenderer:
    """将 Task Spec 渲染为 whisper CLI 命令。"""

    @staticmethod
    def render(spec, registry_entry=None) -> dict:
        """
        返回：{"command": str, "workdir": str, "timeout": int}
        Task Spec 需要的字段：
          input.source: 音频文件路径
          output.target: 输出文本文件路径
          requirements: 可选，第一个 requirement 如果是语言代码则用作 language 参数
        """
        source = spec.input.get("source", "")
        target = spec.output.get("target", "")
        workdir = str(Path(target).parent)
        Path(workdir).mkdir(parents=True, exist_ok=True)

        # 语言检测：requirements 里如果有 "language:zh" 这样的格式
        language = "zh"
        for req in spec.requirements:
            if req.startswith("language:"):
                language = req.split(":", 1)[1]
                break

        # 模型大小：默认 small（速度和精度平衡）
        model = "small"
        for req in spec.requirements:
            if req.startswith("model:"):
                model = req.split(":", 1)[1]
                break

        # 输出格式：txt
        out_dir = str(Path(target).parent)
        out_stem = Path(target).stem

        cmd = (
            f"whisper \"{source}\" "
            f"--model {model} "
            f"--language {language} "
            f"--output_format txt "
            f"--output_dir \"{out_dir}\" "
            f"--device cpu "
            f"--fp16 False"
        )

        # whisper 输出文件名是 {stem}.txt
        # 我们需要在执行后把它移动到 target 路径
        whisper_output = os.path.join(out_dir, f"{Path(source).stem}.txt")

        # 超时：根据文件大小估算（每MB音频约60秒）
        timeout = 600  # 默认10分钟
        if Path(source).exists():
            size_mb = Path(source).stat().st_size / (1024 * 1024)
            timeout = max(120, int(size_mb * 60))

        # 如果whisper输出路径和target不同，执行后需要移动
        post_cmd = ""
        if whisper_output != target:
            post_cmd = f" && mv \"{whisper_output}\" \"{target}\""

        return {
            "command": cmd + post_cmd,
            "workdir": workdir,
            "timeout": timeout,
            "whisper_output": whisper_output,
            "target": target,
        }
