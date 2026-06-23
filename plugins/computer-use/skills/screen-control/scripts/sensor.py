#!/usr/bin/env python3
"""
屏幕传感器 - 按需抓帧（事件驱动模式）

用法：
    python sensor.py snapshot [--output frame.png]
    python sensor.py wait --for stable|change [--timeout 10] [--output frame.png]
    python sensor.py sequence --count 5 --output-dir ./frames/

设计原则：
    - 按需抓帧，无后台进程
    - 内存处理，用完即丢
    - 仅在指定 output 时写入磁盘
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# 自动切换到脚本所在目录，支持从任意目录调用
SCRIPT_DIR = Path(__file__).resolve().parent
os.chdir(SCRIPT_DIR)
from typing import Optional, Tuple

import cv2
import mss
import numpy as np


class Sensor:
    """按需屏幕传感器"""

    def __init__(self):
        self.sct: Optional[mss.mss] = None
        self.screen_size: Optional[Tuple[int, int]] = None
        self.default_resize = 640  # 默认缩放长边
        self.temp_files: list = []  # 追踪临时文件

    def _ensure_sct(self):
        """懒加载截图工具"""
        if self.sct is None:
            self.sct = mss.mss()
            self.screen_size = (
                self.sct.monitors[1]["width"],
                self.sct.monitors[1]["height"]
            )

    def _capture(self, region: Optional[Tuple[int, int, int, int]] = None) -> np.ndarray:
        """
        捕获屏幕

        Args:
            region: (x, y, width, height) 区域，None 为全屏

        Returns:
            RGB 图像数组
        """
        self._ensure_sct()

        if region:
            x, y, w, h = region
            monitor = {"left": x, "top": y, "width": w, "height": h}
        else:
            monitor = self.sct.monitors[1]

        screenshot = self.sct.grab(monitor)
        frame = np.array(screenshot)
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2RGB)

    def _resize(self, image: np.ndarray, max_edge: int = 640) -> np.ndarray:
        """语义缩放"""
        h, w = image.shape[:2]
        if max(h, w) <= max_edge:
            return image

        scale = max_edge / max(h, w)
        new_w, new_h = int(w * scale), int(h * scale)
        return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)

    def _perceptual_hash(self, image: np.ndarray) -> int:
        """计算感知哈希（用于变化检测）"""
        small = cv2.resize(image, (8, 8), interpolation=cv2.INTER_AREA)
        if len(small.shape) == 3:
            gray = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY)
        else:
            gray = small

        mean = gray.mean()
        bits = (gray > mean).flatten()

        hash_value = 0
        for bit in bits:
            hash_value = (hash_value << 1) | int(bit)
        return hash_value

    def _hash_similarity(self, h1: int, h2: int) -> float:
        """计算哈希相似度"""
        diff = bin(h1 ^ h2).count('1')
        return 1 - diff / 64

    def snapshot(self,
                 output: Optional[str] = None,
                 region: Optional[str] = None,
                 resize: int = 640) -> dict:
        """
        单帧快照

        Args:
            output: 输出文件路径
            region: 区域 "x,y,w,h"
            resize: 缩放长边

        Returns:
            结果字典
        """
        # 解析区域
        region_tuple = None
        if region:
            parts = [int(x.strip()) for x in region.split(',')]
            if len(parts) == 4:
                region_tuple = tuple(parts)

        # 捕获
        frame = self._capture(region_tuple)

        # 缩放
        resized = self._resize(frame, resize)

        # 返回信息
        h, w = frame.shape[:2]
        rh, rw = resized.shape[:2]

        result = {
            "status": "success",
            "timestamp": time.time(),
            "original_size": [w, h],
            "output_size": [rw, rh],
            "screen_size": list(self.screen_size) if self.screen_size else None
        }

        # 保存
        if output:
            cv2.imwrite(output, cv2.cvtColor(resized, cv2.COLOR_RGB2BGR))
            result["output"] = output
        else:
            # 无输出路径，保存到临时文件
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                cv2.imwrite(f.name, cv2.cvtColor(resized, cv2.COLOR_RGB2BGR))
                result["output"] = f.name
                result["temp"] = True
                self.temp_files.append(f.name)  # 追踪临时文件

        return result

    def wait(self,
             wait_for: str,
             timeout: float = 10.0,
             threshold: float = 0.95,
             interval: float = 0.3,
             output: Optional[str] = None,
             resize: int = 640) -> dict:
        """
        智能等待

        Args:
            wait_for: stable（等待稳定）或 change（等待变化）
            timeout: 超时时间
            threshold: 相似度阈值
            interval: 检测间隔
            output: 输出文件路径
            resize: 缩放长边

        Returns:
            结果字典
        """
        self._ensure_sct()

        # 获取初始帧
        frame = self._capture()
        initial_hash = self._perceptual_hash(frame)

        start_time = time.time()
        samples = 1

        if wait_for == "change":
            # 等待变化
            while time.time() - start_time < timeout:
                frame = self._capture()
                current_hash = self._perceptual_hash(frame)
                similarity = self._hash_similarity(initial_hash, current_hash)
                samples += 1

                if similarity < threshold:
                    # 检测到变化，再等待稳定
                    remaining_timeout = timeout - (time.time() - start_time)
                    if remaining_timeout > 0:
                        stable_elapsed = self._wait_stable(threshold, remaining_timeout, interval)
                    else:
                        stable_elapsed = 0
                    total_elapsed = time.time() - start_time

                    # 保存最终帧
                    resized = self._resize(frame, resize)
                    output_path = self._save_frame(resized, output)

                    return {
                        "status": "changed",
                        "elapsed": round(total_elapsed, 2),
                        "stable_after": round(stable_elapsed, 2),
                        "samples": samples,
                        "similarity": round(similarity, 4),
                        "output": output_path
                    }

                time.sleep(interval)

            # 超时
            return {
                "status": "timeout",
                "elapsed": timeout,
                "samples": samples
            }

        elif wait_for == "stable":
            # 等待稳定
            stable_result = self._wait_stable(threshold, timeout, interval)

            if stable_result["stable"]:
                # 获取稳定帧
                frame = self._capture()
                resized = self._resize(frame, resize)
                output_path = self._save_frame(resized, output)

                return {
                    "status": "stable",
                    "elapsed": round(stable_result["elapsed"], 2),
                    "samples": stable_result["samples"],
                    "similarity": round(stable_result["similarity"], 4),
                    "output": output_path
                }
            else:
                return {
                    "status": "timeout",
                    "elapsed": timeout,
                    "samples": stable_result["samples"]
                }

        return {"status": "error", "message": f"Unknown wait_for: {wait_for}"}

    def _wait_stable(self, threshold: float, timeout: float, interval: float) -> dict:
        """等待画面稳定"""
        frame = self._capture()
        prev_hash = self._perceptual_hash(frame)

        start_time = time.time()
        stable_count = 0
        samples = 1
        last_similarity = 1.0

        while time.time() - start_time < timeout:
            frame = self._capture()
            current_hash = self._perceptual_hash(frame)
            similarity = self._hash_similarity(prev_hash, current_hash)
            samples += 1

            if similarity >= threshold:
                stable_count += 1
                if stable_count >= 3:  # 连续3帧稳定
                    return {
                        "stable": True,
                        "elapsed": time.time() - start_time,
                        "samples": samples,
                        "similarity": similarity
                    }
            else:
                stable_count = 0

            prev_hash = current_hash
            last_similarity = similarity
            time.sleep(interval)

        return {
            "stable": False,
            "elapsed": timeout,
            "samples": samples,
            "similarity": last_similarity
        }

    def _save_frame(self, frame: np.ndarray, output: Optional[str] = None) -> str:
        """保存帧到文件"""
        if output:
            cv2.imwrite(output, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
            return output
        else:
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                cv2.imwrite(f.name, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
                self.temp_files.append(f.name)  # 追踪临时文件
                return f.name

    def sequence(self,
                 count: int = 5,
                 interval: float = 0.3,
                 output_dir: Optional[str] = None,
                 keep_all: bool = True) -> dict:
        """
        捕获帧序列

        Args:
            count: 帧数量
            interval: 帧间隔
            output_dir: 输出目录
            keep_all: 是否保留所有帧（False 则只保留差异帧）

        Returns:
            结果字典
        """
        self._ensure_sct()

        # 创建输出目录
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

        frames = []
        prev_hash = None

        for i in range(count):
            frame = self._capture()
            current_hash = self._perceptual_hash(frame)

            # 检查是否有变化
            has_change = True
            if prev_hash is not None:
                similarity = self._hash_similarity(prev_hash, current_hash)
                has_change = similarity < 0.98

            # 决定是否保留
            if keep_all or has_change:
                resized = self._resize(frame)

                if output_dir:
                    filepath = output_path / f"frame_{i:03d}.png"
                    cv2.imwrite(str(filepath), cv2.cvtColor(resized, cv2.COLOR_RGB2BGR))
                    frames.append({
                        "file": str(filepath),
                        "index": i,
                        "changed": has_change
                    })
                else:
                    import tempfile
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                        cv2.imwrite(f.name, cv2.cvtColor(resized, cv2.COLOR_RGB2BGR))
                        frames.append({
                            "file": f.name,
                            "index": i,
                            "changed": has_change,
                            "temp": True
                        })

            prev_hash = current_hash
            time.sleep(interval)

        return {
            "status": "success",
            "count": len(frames),
            "total_duration": round(count * interval, 2),
            "frames": frames
        }

    def close(self):
        """释放资源并清理临时文件"""
        if self.sct:
            self.sct.close()
            self.sct = None

        # 清理临时文件
        import os
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                pass  # 静默失败，临时文件不清理也不影响功能
        self.temp_files.clear()


def main():
    parser = argparse.ArgumentParser(
        description="屏幕传感器 - 按需抓帧",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 单帧快照
  python sensor.py snapshot --output frame.png

  # 等待页面加载完成
  python sensor.py wait --for stable --timeout 15

  # 等待操作生效
  python sensor.py wait --for change --timeout 5 --output after.png

  # 捕获操作序列
  python sensor.py sequence --count 10 --output-dir ./frames/
        """
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # snapshot 命令
    snap_parser = subparsers.add_parser("snapshot", help="单帧快照")
    snap_parser.add_argument("--output", "-o", help="输出文件路径")
    snap_parser.add_argument("--region", "-r", help="截取区域 x,y,w,h")
    snap_parser.add_argument("--resize", type=int, default=640, help="缩放长边")

    # wait 命令
    wait_parser = subparsers.add_parser("wait", help="智能等待")
    wait_parser.add_argument("--for", "-f", dest="wait_for", required=True,
                             choices=["stable", "change"], help="等待类型")
    wait_parser.add_argument("--timeout", "-t", type=float, default=10.0, help="超时时间")
    wait_parser.add_argument("--threshold", type=float, default=0.95, help="相似度阈值")
    wait_parser.add_argument("--interval", type=float, default=0.3, help="检测间隔")
    wait_parser.add_argument("--output", "-o", help="输出文件路径")
    wait_parser.add_argument("--resize", type=int, default=640, help="缩放长边")

    # sequence 命令
    seq_parser = subparsers.add_parser("sequence", help="捕获帧序列")
    seq_parser.add_argument("--count", "-c", type=int, default=5, help="帧数量")
    seq_parser.add_argument("--interval", "-i", type=float, default=0.3, help="帧间隔")
    seq_parser.add_argument("--output-dir", "-o", help="输出目录")
    seq_parser.add_argument("--keep-all", action="store_true", default=True,
                           help="保留所有帧（默认）")
    seq_parser.add_argument("--keep-diff", dest="keep_all", action="store_false",
                           help="只保留有变化的帧")

    args = parser.parse_args()

    sensor = Sensor()

    try:
        if args.command == "snapshot":
            result = sensor.snapshot(
                output=args.output,
                region=args.region,
                resize=args.resize
            )

        elif args.command == "wait":
            result = sensor.wait(
                wait_for=args.wait_for,
                timeout=args.timeout,
                threshold=args.threshold,
                interval=args.interval,
                output=args.output,
                resize=args.resize
            )

        elif args.command == "sequence":
            result = sensor.sequence(
                count=args.count,
                interval=args.interval,
                output_dir=args.output_dir,
                keep_all=args.keep_all
            )

        print(json.dumps(result, indent=2, ensure_ascii=False))

    finally:
        sensor.close()


if __name__ == "__main__":
    main()