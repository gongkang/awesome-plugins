"""配置管理"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple
import json
import platform


@dataclass
class Config:
    """监控配置"""

    # 帧率设置
    default_fps: float = 5.0
    min_fps: float = 1.0
    max_fps: float = 30.0

    # 缓冲设置
    default_buffer_seconds: float = 10.0
    max_buffer_seconds: float = 60.0

    # 图像处理
    semantic_resize_target: int = 640

    # 变化检测
    change_threshold: float = 0.05
    stable_threshold: float = 0.95

    # 监控区域（None = 全屏）
    region: Optional[Tuple[int, int, int, int]] = None

    # 平台检测
    platform: str = platform.system()

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "Config":
        """从文件加载配置"""
        if path is None:
            path = Path(__file__).parent.parent.parent / "config.json"

        if path.exists():
            with open(path) as f:
                data = json.load(f)

            # 处理 region
            if data.get("region"):
                data["region"] = tuple(data["region"])

            return cls(**data)

        return cls()

    def save(self, path: Optional[Path] = None):
        """保存配置到文件"""
        if path is None:
            path = Path(__file__).parent.parent.parent / "config.json"

        data = self.__dict__.copy()
        if data["region"]:
            data["region"] = list(data["region"])

        with open(path, "w") as f:
            json.dump(data, f, indent=2)