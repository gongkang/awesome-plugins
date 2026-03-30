"""
变化检测器 - 感知哈希 + 帧差分

用于：
- 检测画面是否变化
- 提取关键帧
- 判断页面是否稳定
"""

import cv2
import numpy as np
from collections import deque
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class FrameData:
    """帧数据"""
    timestamp: float
    image: np.ndarray
    hash: int


class ChangeDetector:
    """变化检测器"""

    def __init__(self, threshold: float = 0.05):
        """
        Args:
            threshold: 变化阈值 (0-1)
        """
        self.threshold = threshold
        self.prev_hash: Optional[int] = None

    def perceptual_hash(self, image: np.ndarray, hash_size: int = 8) -> int:
        """
        计算感知哈希

        Args:
            image: RGB 图像
            hash_size: 哈希尺寸

        Returns:
            64 位整数哈希值
        """
        # 缩放到 hash_size x hash_size
        small = cv2.resize(image, (hash_size, hash_size), interpolation=cv2.INTER_AREA)

        # 转灰度
        if len(small.shape) == 3:
            gray = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY)
        else:
            gray = small

        # 计算均值
        mean = gray.mean()

        # 生成哈希：每个像素与均值比较
        bits = (gray > mean).flatten()

        # 转为整数
        hash_value = 0
        for bit in bits:
            hash_value = (hash_value << 1) | int(bit)

        return hash_value

    def detect_change(self, current_hash: int) -> bool:
        """
        检测是否发生变化

        Args:
            current_hash: 当前帧哈希

        Returns:
            是否检测到变化
        """
        if self.prev_hash is None:
            self.prev_hash = current_hash
            return True

        # 计算汉明距离
        distance = self._hamming_distance(self.prev_hash, current_hash)
        similarity = 1 - distance / 64

        self.prev_hash = current_hash

        # 相似度低于阈值 = 有变化
        return similarity < (1 - self.threshold)

    def is_stable(self, hashes: List[int], window: int = 3) -> bool:
        """
        判断画面是否稳定

        Args:
            hashes: 最近的哈希序列
            window: 检测窗口大小

        Returns:
            是否稳定
        """
        if len(hashes) < window:
            return False

        recent = hashes[-window:]
        similarities = []

        for i in range(len(recent) - 1):
            dist = self._hamming_distance(recent[i], recent[i + 1])
            similarities.append(1 - dist / 64)

        # 最近几帧都高度相似 = 稳定
        return all(s > 0.95 for s in similarities)

    def _hamming_distance(self, hash1: int, hash2: int) -> int:
        """计算汉明距离"""
        return bin(hash1 ^ hash2).count('1')


class FrameBuffer(deque):
    """
    帧缓冲区

    基于 deque 的滑动窗口缓冲区
    """

    def __init__(self, maxlen: int = 15):
        super().__init__(maxlen=maxlen)
        self.detector = ChangeDetector()

    def append(self, frame: FrameData):
        """添加帧"""
        super().append(frame)

    def get_keyframe(self) -> Optional[FrameData]:
        """
        提取关键帧

        策略：
        - 如果画面稳定，返回最新帧
        - 如果画面在变化，返回变化开始的帧
        """
        if len(self) == 0:
            return None

        if len(self) < 2:
            return self[-1]

        # 获取最近帧的哈希
        hashes = [f.hash for f in self]

        # 检查是否稳定
        if self.detector.is_stable(hashes):
            return self[-1]

        # 找变化开始的位置
        for i in range(len(self) - 2, -1, -1):
            dist = self.detector._hamming_distance(hashes[i], hashes[i + 1])
            if dist > 3:  # 有明显变化
                return self[i + 1]

        return self[-1]

    def get_sequence(self, count: int) -> List[FrameData]:
        """
        获取最近的帧序列

        Args:
            count: 帧数量

        Returns:
            帧列表（按时间顺序）
        """
        return list(self)[-count:]


def frame_diff(frame1: np.ndarray, frame2: np.ndarray) -> float:
    """
    计算两帧之间的差异程度

    Args:
        frame1, frame2: RGB 图像

    Returns:
        差异程度 (0-1)
    """
    # 确保尺寸一致
    if frame1.shape != frame2.shape:
        frame2 = cv2.resize(frame2, (frame1.shape[1], frame1.shape[0]))

    # 转灰度
    gray1 = cv2.cvtColor(frame1, cv2.COLOR_RGB2GRAY)
    gray2 = cv2.cvtColor(frame2, cv2.COLOR_RGB2GRAY)

    # 计算绝对差
    diff = cv2.absdiff(gray1, gray2)

    # 归一化
    return diff.mean() / 255.0