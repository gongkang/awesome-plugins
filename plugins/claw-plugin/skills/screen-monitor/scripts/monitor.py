#!/usr/bin/env python3
"""
屏幕监控 - 持续录屏与变化检测

用法：
    python monitor.py start [--fps 5] [--buffer 10]
    python monitor.py stop
    python monitor.py status
    python monitor.py keyframe --output frame.png
    python monitor.py wait-change [--timeout 60]
    python monitor.py wait-stable [--timeout 30]
    python monitor.py record start --output ./rec/
    python monitor.py record stop

核心功能：
    - 后台持续录屏，维护帧缓冲区
    - 智能变化检测与关键帧提取
    - 条件等待与操作录制
"""

import argparse
import atexit
import json
import os
import signal
import sys
import tempfile
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Deque, Dict, List, Optional, Tuple

import cv2
import mss
import numpy as np

# 添加 utils 到路径
sys.path.insert(0, str(Path(__file__).parent))
from utils.detector import ChangeDetector, FrameData, FrameBuffer

# 性能监控（可选依赖）
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


# 状态文件路径
STATE_FILE = Path("/tmp/screen_monitor_state.json")
PID_FILE = Path("/tmp/screen_monitor.pid")
FRAMES_DIR = Path("/tmp/screen_monitor_frames")


@dataclass
class MonitorState:
    """监控状态"""
    running: bool = False
    fps: float = 5.0
    buffer_seconds: float = 10.0
    region: Optional[Tuple[int, int, int, int]] = None
    threshold: float = 0.05
    frames_captured: int = 0
    start_time: float = 0.0
    last_change_time: float = 0.0


@dataclass
class RecordState:
    """录制状态"""
    active: bool = False
    output_dir: Optional[str] = None
    frames: List[Dict] = field(default_factory=list)
    start_time: float = 0.0
    frame_count: int = 0


class ScreenMonitor:
    """屏幕监控器"""

    def __init__(self):
        self.state = MonitorState()
        self.record_state = RecordState()
        self.buffer: Optional[FrameBuffer] = None
        self.detector: Optional[ChangeDetector] = None
        self.stop_event = threading.Event()
        self.capture_thread: Optional[threading.Thread] = None
        self.sct: Optional[mss.mss] = None
        self.lock = threading.Lock()

        self._load_state()

    def _load_state(self):
        """从文件加载状态"""
        if STATE_FILE.exists():
            try:
                data = json.loads(STATE_FILE.read_text())
                self.state.running = data.get("running", False)
                self.state.fps = data.get("fps", 5.0)
                self.state.buffer_seconds = data.get("buffer_seconds", 10.0)
                self.state.frames_captured = data.get("frames_captured", 0)
                self.state.start_time = data.get("start_time", 0.0)
                if data.get("region"):
                    self.state.region = tuple(data["region"])
            except Exception:
                pass

    def _save_state(self):
        """保存状态到文件"""
        data = {
            "running": self.state.running,
            "fps": self.state.fps,
            "buffer_seconds": self.state.buffer_seconds,
            "frames_captured": self.state.frames_captured,
            "start_time": self.state.start_time,
            "last_change_time": self.state.last_change_time,
            "region": list(self.state.region) if self.state.region else None,
            "pid": os.getpid()
        }
        STATE_FILE.write_text(json.dumps(data))

    def start(self, fps: float = 5.0, buffer_seconds: float = 10.0,
              region: Optional[str] = None, threshold: float = 0.05):
        """启动监控"""
        # 检查是否已在运行
        if self._is_running():
            print(json.dumps({
                "status": "already_running",
                "message": "监控已在运行",
                "pid": self._get_running_pid()
            }))
            return

        # 解析区域
        region_tuple = None
        if region:
            parts = [int(x.strip()) for x in region.split(',')]
            if len(parts) == 4:
                region_tuple = tuple(parts)

        # 初始化
        self.state.fps = fps
        self.state.buffer_seconds = buffer_seconds
        self.state.region = region_tuple
        self.state.threshold = threshold
        self.state.running = True
        self.state.start_time = time.time()
        self.state.frames_captured = 0

        self.buffer = FrameBuffer(maxlen=int(fps * buffer_seconds))
        self.detector = ChangeDetector(threshold=threshold)
        self.sct = mss.mss()
        self.stop_event.clear()

        # 创建帧目录
        FRAMES_DIR.mkdir(parents=True, exist_ok=True)

        # 写入 PID
        PID_FILE.write_text(str(os.getpid()))

        # 启动捕获线程
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()

        self._save_state()

        print(json.dumps({
            "status": "started",
            "fps": fps,
            "buffer_seconds": buffer_seconds,
            "region": region,
            "pid": os.getpid()
        }))

    def stop(self):
        """停止监控"""
        if not self._is_running():
            print(json.dumps({"status": "not_running"}))
            return

        # 如果是另一个进程在运行，尝试杀死它
        if not self.state.running and PID_FILE.exists():
            try:
                pid = int(PID_FILE.read_text())
                os.kill(pid, signal.SIGTERM)
                time.sleep(0.5)
                self._cleanup()
                print(json.dumps({"status": "stopped", "killed_pid": pid}))
                return
            except (OSError, ValueError) as e:
                self._cleanup()

        self.stop_event.set()
        self.state.running = False

        if self.capture_thread:
            self.capture_thread.join(timeout=2)

        if self.sct:
            self.sct.close()

        # 停止录制
        if self.record_state.active:
            self._stop_recording()

        runtime = time.time() - self.state.start_time
        self._cleanup()

        print(json.dumps({
            "status": "stopped",
            "total_frames": self.state.frames_captured,
            "runtime_seconds": round(runtime, 1)
        }))

    def _cleanup(self):
        """清理资源"""
        PID_FILE.unlink(missing_ok=True)
        STATE_FILE.unlink(missing_ok=True)

    def _get_performance_stats(self) -> dict:
        """获取性能统计"""
        stats = {}
        if HAS_PSUTIL:
            try:
                process = psutil.Process(os.getpid())
                stats["cpu_percent"] = round(process.cpu_percent(interval=0.1), 1)
                stats["memory_mb"] = round(process.memory_info().rss / 1024 / 1024, 1)
            except Exception:
                pass
        return stats

    def status(self):
        """获取状态"""
        # 检查其他进程
        if not self.state.running and PID_FILE.exists():
            try:
                pid = int(PID_FILE.read_text())
                os.kill(pid, 0)  # 检查进程是否存在
                if STATE_FILE.exists():
                    data = json.loads(STATE_FILE.read_text())
                    print(json.dumps({
                        "running": True,
                        "pid": pid,
                        "fps": data.get("fps", 5.0),
                        "buffer_seconds": data.get("buffer_seconds", 10.0),
                        "frames_captured": data.get("frames_captured", "unknown"),
                        "runtime_seconds": round(time.time() - data.get("start_time", time.time()), 1),
                        "last_change": round(time.time() - data.get("last_change_time", time.time()), 1) if data.get("last_change_time") else None
                    }, indent=2))
                    return
            except (OSError, ValueError):
                self._cleanup()

        # 本地状态
        result = {
            "running": self.state.running,
            "fps": self.state.fps,
            "buffer_seconds": self.state.buffer_seconds,
            "frames_in_buffer": len(self.buffer) if self.buffer else 0,
            "total_frames": self.state.frames_captured,
            "runtime_seconds": round(time.time() - self.state.start_time, 1) if self.state.start_time else 0,
            "last_change": round(time.time() - self.state.last_change_time, 1) if self.state.last_change_time else None
        }
        result.update(self._get_performance_stats())
        print(json.dumps(result, indent=2))

    def keyframe(self, output: str, mode: str = "latest"):
        """
        获取关键帧

        Args:
            output: 输出路径
            mode: latest（最新帧）| stable（稳定帧）| changed（变化帧）
        """
        if not self._is_running():
            print(json.dumps({"error": "监控未运行"}))
            return

        if not self.buffer or len(self.buffer) == 0:
            print(json.dumps({"error": "缓冲区为空"}))
            return

        with self.lock:
            if mode == "latest":
                frame_data = self.buffer[-1]
            elif mode == "stable":
                frame_data = self._find_stable_frame()
            elif mode == "changed":
                frame_data = self._find_changed_frame()
            else:
                frame_data = self.buffer[-1]

            if frame_data:
                self._save_frame(frame_data.image, output)
                print(json.dumps({
                    "status": "success",
                    "output": output,
                    "frame_age_seconds": round(time.time() - frame_data.timestamp, 2),
                    "mode": mode
                }))
            else:
                print(json.dumps({"error": "无法提取关键帧"}))

    def recent(self, count: int, output_dir: str):
        """获取最近的帧"""
        if not self._is_running():
            print(json.dumps({"error": "监控未运行"}))
            return

        if not self.buffer or len(self.buffer) == 0:
            print(json.dumps({"error": "缓冲区为空"}))
            return

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        with self.lock:
            frames = list(self.buffer)[-count:]
            saved = []

            for i, frame_data in enumerate(frames):
                filepath = output_path / f"frame_{i:04d}.png"
                self._save_frame(frame_data.image, str(filepath))
                saved.append({
                    "file": str(filepath),
                    "timestamp": round(frame_data.timestamp, 2),
                    "age_seconds": round(time.time() - frame_data.timestamp, 2)
                })

            print(json.dumps({
                "status": "success",
                "count": len(saved),
                "frames": saved
            }, indent=2))

    def wait_change(self, timeout: float = 60.0, threshold: float = 0.05,
                    output: Optional[str] = None):
        """等待画面变化"""
        self._ensure_sct()

        # 获取初始帧
        frame = self._capture_frame()
        initial_hash = self.detector.perceptual_hash(frame)

        start_time = time.time()

        print(json.dumps({
            "status": "waiting",
            "timeout": timeout,
            "threshold": threshold
        }))

        while time.time() - start_time < timeout:
            frame = self._capture_frame()
            current_hash = self.detector.perceptual_hash(frame)
            similarity = 1 - self.detector.hamming_distance(initial_hash, current_hash) / 64

            if similarity < (1 - threshold):
                elapsed = time.time() - start_time

                if output:
                    self._save_frame(frame, output)

                print(json.dumps({
                    "status": "changed",
                    "elapsed": round(elapsed, 2),
                    "similarity": round(similarity, 4),
                    "output": output
                }))
                return

            time.sleep(0.3)

        print(json.dumps({
            "status": "timeout",
            "elapsed": timeout
        }))

    def wait_stable(self, timeout: float = 30.0, threshold: float = 0.95,
                    output: Optional[str] = None):
        """等待画面稳定"""
        self._ensure_sct()

        prev_hash = None
        stable_count = 0
        start_time = time.time()

        print(json.dumps({
            "status": "waiting",
            "timeout": timeout,
            "threshold": threshold
        }))

        while time.time() - start_time < timeout:
            frame = self._capture_frame()
            current_hash = self.detector.perceptual_hash(frame)

            if prev_hash is not None:
                similarity = 1 - self.detector.hamming_distance(prev_hash, current_hash) / 64

                if similarity >= threshold:
                    stable_count += 1
                    if stable_count >= 3:
                        elapsed = time.time() - start_time

                        if output:
                            self._save_frame(frame, output)

                        print(json.dumps({
                            "status": "stable",
                            "elapsed": round(elapsed, 2),
                            "similarity": round(similarity, 4),
                            "stable_frames": stable_count,
                            "output": output
                        }))
                        return
                else:
                    stable_count = 0

            prev_hash = current_hash
            time.sleep(0.3)

        print(json.dumps({
            "status": "timeout",
            "elapsed": timeout,
            "stable_frames": stable_count
        }))

    def wait_text(self, text: str, timeout: float = 120.0,
                  region: Optional[str] = None, output: Optional[str] = None):
        """等待文字出现（使用 Tesseract OCR）"""
        self._ensure_sct()

        # 解析区域
        target_region = None
        if region:
            parts = [int(x.strip()) for x in region.split(',')]
            if len(parts) == 4:
                target_region = tuple(parts)

        # 检查 OCR 依赖
        try:
            import pytesseract
        except ImportError:
            print(json.dumps({
                "status": "error",
                "message": "wait-text 需要 pytesseract 支持。请运行: pip install pytesseract && brew install tesseract"
            }))
            return

        prev_hash = None
        start_time = time.time()

        while time.time() - start_time < timeout:
            frame = self._capture_frame()

            # 如果指定了区域，裁剪到目标区域
            if target_region:
                x, y, w, h = target_region
                frame = frame[y:y+h, x:x+w]

            # OCR 识别
            try:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                ocr_result = pytesseract.image_to_data(
                    rgb_frame, lang='chi_sim+eng', output_type=pytesseract.Output.DICT
                )

                # 搜索目标文字
                for i, txt in enumerate(ocr_result['text']):
                    if text.lower() in txt.strip().lower():
                        elapsed = time.time() - start_time
                        conf = ocr_result['conf'][i]
                        bounds = [
                            ocr_result['left'][i],
                            ocr_result['top'][i],
                            ocr_result['width'][i],
                            ocr_result['height'][i]
                        ]

                        if output:
                            self._save_frame(frame, output)

                        print(json.dumps({
                            "status": "found",
                            "elapsed": round(elapsed, 2),
                            "text": text,
                            "matched_text": txt.strip(),
                            "bounds": bounds,
                            "confidence": conf,
                            "output": output
                        }))
                        return
            except Exception as e:
                sys.stderr.write(f"OCR 错误: {e}\n")

            time.sleep(1.0)  # OCR 较慢，降低检测频率

        print(json.dumps({
            "status": "timeout",
            "elapsed": round(time.time() - start_time, 2),
            "text": text
        }))

    # ==================== 录制功能 ====================

    def record_start(self, output: str, fps: float = 10.0, only_changes: bool = False):
        """开始录制"""
        if self.record_state.active:
            print(json.dumps({"status": "already_recording"}))
            return

        output_path = Path(output)
        output_path.mkdir(parents=True, exist_ok=True)

        self.record_state.active = True
        self.record_state.output_dir = str(output_path)
        self.record_state.frames = []
        self.record_state.start_time = time.time()
        self.record_state.frame_count = 0
        self._record_only_changes = only_changes
        self._record_fps = fps
        self._record_prev_hash = None

        print(json.dumps({
            "status": "recording",
            "output": output,
            "fps": fps
        }))

    def record_stop(self):
        """停止录制"""
        if not self.record_state.active:
            print(json.dumps({"status": "not_recording"}))
            return

        self.record_state.active = False

        # 生成元数据
        metadata = {
            "start_time": self.record_state.start_time,
            "end_time": time.time(),
            "total_frames": self.record_state.frame_count,
            "duration_seconds": round(time.time() - self.record_state.start_time, 1),
            "fps": self._record_fps,
            "frames": self.record_state.frames
        }

        metadata_path = Path(self.record_state.output_dir) / "metadata.json"
        metadata_path.write_text(json.dumps(metadata, indent=2))

        print(json.dumps({
            "status": "stopped",
            "output_dir": self.record_state.output_dir,
            "total_frames": self.record_state.frame_count,
            "duration_seconds": metadata["duration_seconds"],
            "metadata": str(metadata_path)
        }))

    def record_status(self):
        """录制状态"""
        if not self.record_state.active:
            print(json.dumps({
                "recording": False
            }))
        else:
            print(json.dumps({
                "recording": True,
                "output_dir": self.record_state.output_dir,
                "frames_captured": self.record_state.frame_count,
                "duration_seconds": round(time.time() - self.record_state.start_time, 1)
            }))

    # ==================== 内部方法 ====================

    def _is_running(self) -> bool:
        """检查是否在运行"""
        if self.state.running:
            return True
        if PID_FILE.exists():
            try:
                pid = int(PID_FILE.read_text())
                os.kill(pid, 0)
                return True
            except (OSError, ValueError):
                pass
        return False

    def _get_running_pid(self) -> Optional[int]:
        """获取运行中的 PID"""
        if PID_FILE.exists():
            try:
                return int(PID_FILE.read_text())
            except ValueError:
                pass
        return None

    def _ensure_sct(self):
        """确保截图工具初始化"""
        if self.sct is None:
            self.sct = mss.mss()
        if self.detector is None:
            self.detector = ChangeDetector()

    def _capture_frame(self) -> np.ndarray:
        """捕获一帧"""
        self._ensure_sct()

        if self.state.region:
            x, y, w, h = self.state.region
            monitor = {"left": x, "top": y, "width": w, "height": h}
        else:
            monitor = self.sct.monitors[1]

        screenshot = self.sct.grab(monitor)
        frame = np.array(screenshot)
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2RGB)

    def _capture_loop(self):
        """捕获循环（后台线程）"""
        monitor = self.sct.monitors[1]
        if self.state.region:
            x, y, w, h = self.state.region
            monitor = {"left": x, "top": y, "width": w, "height": h}

        frame_interval = 1.0 / self.state.fps

        while not self.stop_event.is_set():
            try:
                start = time.time()

                # 截图
                screenshot = self.sct.grab(monitor)
                frame = np.array(screenshot)
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGRA2RGB)

                # 计算哈希
                frame_hash = self.detector.perceptual_hash(frame_rgb)

                # 检测变化
                is_change = self.detector.detect_change(frame_hash)
                if is_change:
                    self.state.last_change_time = time.time()

                # 添加到缓冲区
                with self.lock:
                    frame_data = FrameData(
                        timestamp=time.time(),
                        image=frame_rgb,
                        hash=frame_hash,
                        changed=is_change
                    )
                    self.buffer.append(frame_data)
                    self.state.frames_captured += 1

                # 录制
                if self.record_state.active:
                    self._record_frame(frame_rgb, frame_hash, is_change)

                # 更新状态
                self._save_state()

                # 控制帧率
                elapsed = time.time() - start
                sleep_time = max(0, frame_interval - elapsed)
                time.sleep(sleep_time)

            except Exception as e:
                sys.stderr.write(f"捕获错误: {e}\n")
                time.sleep(0.5)

    def _record_frame(self, frame: np.ndarray, frame_hash: int, is_change: bool):
        """录制帧"""
        if self._record_only_changes and self._record_prev_hash is not None:
            similarity = 1 - self.detector.hamming_distance(self._record_prev_hash, frame_hash) / 64
            if similarity >= 0.98:  # 无变化，跳过
                return

        # 保存帧
        filename = f"frame_{self.record_state.frame_count:05d}.png"
        filepath = Path(self.record_state.output_dir) / filename
        self._save_frame(frame, str(filepath))

        # 记录
        self.record_state.frames.append({
            "file": filename,
            "timestamp": round(time.time() - self.record_state.start_time, 2),
            "changed": is_change
        })
        self.record_state.frame_count += 1
        self._record_prev_hash = frame_hash

    def _save_frame(self, frame: np.ndarray, output: str):
        """保存帧到文件"""
        # 缩放
        h, w = frame.shape[:2]
        max_edge = 640
        if max(h, w) > max_edge:
            scale = max_edge / max(h, w)
            new_w, new_h = int(w * scale), int(h * scale)
            frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

        cv2.imwrite(output, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))

    def _find_stable_frame(self) -> Optional[FrameData]:
        """查找稳定帧"""
        if len(self.buffer) < 3:
            return self.buffer[-1] if self.buffer else None

        # 从后往前找连续稳定的帧
        for i in range(len(self.buffer) - 2, 0, -1):
            f1, f2, f3 = self.buffer[i], self.buffer[i+1], self.buffer[i+2]
            s12 = 1 - self.detector.hamming_distance(f1.hash, f2.hash) / 64
            s23 = 1 - self.detector.hamming_distance(f2.hash, f3.hash) / 64

            if s12 >= 0.95 and s23 >= 0.95:
                return f3

        return self.buffer[-1]

    def _find_changed_frame(self) -> Optional[FrameData]:
        """查找变化帧"""
        for frame_data in reversed(list(self.buffer)):
            if frame_data.changed:
                return frame_data
        return self.buffer[-1] if self.buffer else None


def main():
    parser = argparse.ArgumentParser(
        description="屏幕监控 - 持续录屏与变化检测",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # start
    start_parser = subparsers.add_parser("start", help="启动监控")
    start_parser.add_argument("--fps", type=float, default=5.0, help="采样帧率")
    start_parser.add_argument("--buffer", type=float, default=10.0, help="缓冲时长(秒)")
    start_parser.add_argument("--region", help="监控区域 x,y,w,h")
    start_parser.add_argument("--threshold", type=float, default=0.05, help="变化阈值")

    # stop
    subparsers.add_parser("stop", help="停止监控")

    # status
    subparsers.add_parser("status", help="查看状态")

    # keyframe
    kf_parser = subparsers.add_parser("keyframe", help="获取关键帧")
    kf_parser.add_argument("--output", "-o", required=True, help="输出路径")
    kf_parser.add_argument("--mode", choices=["latest", "stable", "changed"],
                          default="latest", help="提取模式")

    # recent
    recent_parser = subparsers.add_parser("recent", help="获取最近帧")
    recent_parser.add_argument("--count", "-c", type=int, default=5, help="帧数量")
    recent_parser.add_argument("--output-dir", "-o", required=True, help="输出目录")

    # wait-change
    wc_parser = subparsers.add_parser("wait-change", help="等待变化")
    wc_parser.add_argument("--timeout", "-t", type=float, default=60.0, help="超时时间")
    wc_parser.add_argument("--threshold", type=float, default=0.05, help="变化阈值")
    wc_parser.add_argument("--output", "-o", help="输出路径")

    # wait-stable
    ws_parser = subparsers.add_parser("wait-stable", help="等待稳定")
    ws_parser.add_argument("--timeout", "-t", type=float, default=30.0, help="超时时间")
    ws_parser.add_argument("--threshold", type=float, default=0.95, help="稳定阈值")
    ws_parser.add_argument("--output", "-o", help="输出路径")

    # wait-text
    wt_parser = subparsers.add_parser("wait-text", help="等待文字出现")
    wt_parser.add_argument("text", help="要检测的文字")
    wt_parser.add_argument("--timeout", "-t", type=float, default=120.0, help="超时时间")
    wt_parser.add_argument("--region", help="检测区域")
    wt_parser.add_argument("--output", "-o", help="输出路径")

    # record
    record_parser = subparsers.add_parser("record", help="录制")
    record_sub = record_parser.add_subparsers(dest="record_cmd", required=True)

    rec_start = record_sub.add_parser("start", help="开始录制")
    rec_start.add_argument("--output", "-o", required=True, help="输出目录")
    rec_start.add_argument("--fps", type=float, default=10.0, help="录制帧率")
    rec_start.add_argument("--only-changes", action="store_true", help="只录制变化帧")

    rec_stop = record_sub.add_parser("stop", help="停止录制")
    rec_status = record_sub.add_parser("status", help="录制状态")

    args = parser.parse_args()

    monitor = ScreenMonitor()

    # 注册退出处理
    atexit.register(lambda: monitor._cleanup())

    if args.command == "start":
        monitor.start(
            fps=args.fps,
            buffer_seconds=args.buffer,
            region=args.region,
            threshold=args.threshold
        )
        # 保持运行
        try:
            while monitor.state.running:
                time.sleep(1)
        except KeyboardInterrupt:
            monitor.stop()

    elif args.command == "stop":
        monitor.stop()

    elif args.command == "status":
        monitor.status()

    elif args.command == "keyframe":
        monitor.keyframe(output=args.output, mode=args.mode)

    elif args.command == "recent":
        monitor.recent(count=args.count, output_dir=args.output_dir)

    elif args.command == "wait-change":
        monitor.wait_change(timeout=args.timeout, threshold=args.threshold, output=args.output)

    elif args.command == "wait-stable":
        monitor.wait_stable(timeout=args.timeout, threshold=args.threshold, output=args.output)

    elif args.command == "wait-text":
        monitor.wait_text(text=args.text, timeout=args.timeout, region=args.region, output=args.output)

    elif args.command == "record":
        if args.record_cmd == "start":
            monitor.start(fps=args.fps)  # 确保监控运行
            time.sleep(0.5)
            monitor.record_start(output=args.output, fps=args.fps, only_changes=args.only_changes)
            try:
                while monitor.record_state.active:
                    time.sleep(1)
            except KeyboardInterrupt:
                monitor.record_stop()
        elif args.record_cmd == "stop":
            monitor.record_stop()
        elif args.record_cmd == "status":
            monitor.record_status()


if __name__ == "__main__":
    main()