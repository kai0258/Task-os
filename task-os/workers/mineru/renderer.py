"""MinerU Renderer: Task Spec -> MinerU API 调用命令。"""

import os
from pathlib import Path


class MinerURenderer:
    """将 Task Spec 渲染为 MinerU adapter 命令。"""

    @staticmethod
    def render(spec, registry_entry=None) -> dict:
        """
        Task Spec 需要的字段：
          input.source: PDF 文件路径
          output.target: 输出 Markdown 文件路径
          requirements: 可选，language:zh 等
        """
        source = spec.input.get("source", "")
        target = spec.output.get("target", "")
        workdir = str(Path(target).parent)
        Path(workdir).mkdir(parents=True, exist_ok=True)

        # 语言
        language = "ch"
        for req in spec.requirements:
            if req.startswith("language:"):
                lang = req.split(":", 1)[1]
                language = "ch" if lang in ("zh", "ch", "chinese") else "en"
                break

        # adapter 脚本路径
        adapter_path = Path(__file__).parent / "adapter.py"

        # 命令：python3 adapter.py <source> <target> [language]
        cmd = f'python3 {adapter_path} "{source}" "{target}" {language}'

        # 超时：每MB给60秒，最少120秒，最多600秒
        timeout = 300
        if Path(source).exists():
            size_mb = Path(source).stat().st_size / (1024 * 1024)
            timeout = max(120, min(600, int(size_mb * 60)))

        return {
            "command": cmd,
            "workdir": workdir,
            "timeout": timeout,
        }
