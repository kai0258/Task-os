"""Capability Matrix: task_type -> preferred worker 映射。

v0.1 静态版本。未来可接入统计学习。
"""

# Worker 名称与 Renderer 类的映射
WORKER_REGISTRY = {}

def register_worker(name: str):
    """装饰器：注册 Worker。"""
    def decorator(cls):
        WORKER_REGISTRY[name] = cls
        return cls
    return decorator


def get_renderer(worker_name: str):
    """根据 worker 名称获取 Renderer 实例。"""
    if worker_name not in WORKER_REGISTRY:
        raise ValueError(f"Unknown worker: {worker_name}. Available: {list(WORKER_REGISTRY.keys())}")
    return WORKER_REGISTRY[worker_name]() if callable(WORKER_REGISTRY[worker_name]) else WORKER_REGISTRY[worker_name]


# ═══════════════════════════════════════════
# Static Capability Matrix
# ═══════════════════════════════════════════

capability_matrix = {
    "summarize": {
        "preferred": "claude",
        "fallbacks": [],
        "reason": "简单摘要，Claude够用且便宜",
    },
    "translate": {
        "preferred": "claude",
        "fallbacks": [],
        "reason": "翻译需要强语言能力",
    },
    "pdf_to_markdown": {
        "preferred": "mineru",
        "fallbacks": ["claude"],
        "reason": "MinerU擅长PDF结构化解析（表格、公式、图片）",
    },
    "transcribe": {
        "preferred": "whisper",
        "fallbacks": [],
        "reason": "Whisper是本地语音转录工具",
    },
    "refactor": {
        "preferred": "claude",
        "fallbacks": [],
        "reason": "内容重构需要强推理",
    },
    "code": {
        "preferred": "claude",
        "fallbacks": [],
        "reason": "代码任务需要强编码能力",
    },
    "video_to_article": {
        "preferred": "claude",
        "fallbacks": [],
        "reason": "字幕重构为文章需要强语言理解和长文本生成",
    },
}


def resolve_worker(task_type: str, worker_hint: str = None) -> tuple[str, list[str]]:
    """解析应该使用的 Worker。
    
    返回: (preferred_worker, fallback_workers)
    """
    # 1. Task Spec 的 worker_hint 优先
    if worker_hint:
        cap = capability_matrix.get(task_type, {})
        fallbacks = cap.get("fallbacks", [])
        if worker_hint in WORKER_REGISTRY:
            return (worker_hint, fallbacks)
        # hint 不可用，降级到默认
    
    # 2. 从 Capability Matrix 查找
    cap = capability_matrix.get(task_type)
    if cap:
        return (cap["preferred"], cap.get("fallbacks", []))
    
    # 3. 未知 task_type，回退到 claude
    return ("claude", [])


# ═══════════════════════════════════════════
# Register Workers
# ═══════════════════════════════════════════

def _register_all():
    """延迟注册所有已知 Worker，避免循环导入。"""
    from workers.whisper.renderer import WhisperRenderer
    from workers.mineru.renderer import MinerURenderer
    from dispatcher import ClaudeRenderer

    WORKER_REGISTRY["claude"] = ClaudeRenderer
    WORKER_REGISTRY["whisper"] = WhisperRenderer
    WORKER_REGISTRY["mineru"] = MinerURenderer

_register_all()
