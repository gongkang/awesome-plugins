"""配置管理"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import json
import platform


@dataclass
class Config:
    """传感器配置"""

    # 帧率设置
    default_fps: float = 5.0
    min_fps: float = 1.0
    max_fps: float = 30.0

    # 缓冲设置
    default_buffer_seconds: float = 3.0
    max_buffer_seconds: float = 10.0

    # 图像处理
    semantic_resize_target: int = 640  # 语义缩放目标长边

    # 变化检测
    change_threshold: float = 0.05  # 变化阈值
    stable_threshold: float = 0.95  # 稳定阈值

    # 平台检测
    platform: str = platform.system()

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "Config":
        """从文件加载配置"""
        if path is None:
            # 默认配置路径
            path = Path(__file__).parent.parent.parent / "config.json"

        if path.exists():
            with open(path) as f:
                data = json.load(f)
            return cls(**data)

        return cls()

    def save(self, path: Optional[Path] = None):
        """保存配置到文件"""
        if path is None:
            path = Path(__file__).parent.parent.parent / "config.json"

        with open(path, "w") as f:
            json.dump(self.__dict__, f, indent=2)