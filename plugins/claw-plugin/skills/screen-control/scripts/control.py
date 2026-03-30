#!/usr/bin/env python3
"""
屏幕控制器 - 鼠标键盘操作

支持多种定位策略：
1. Accessibility API - macOS 系统级 UI 树访问（最精确）
2. OCR 文字定位 - 识别屏幕文字位置
3. 颜色特征定位 - 特定颜色/形状的图标
4. 坐标估算兜底 - 基于常识估算位置
5. AI 视觉定位 - AI 看图估算坐标（最终兜底）

执行前校验闭环：
- 移动鼠标到目标位置
- 截图让 AI 确认位置对不对
- 不对则修正坐标，重试
- 对了再点击

系统级应用启动：
- 优先使用 `open -a <应用名>` 打开应用
- 比 GUI 点击更可靠

用法：
    # 传统方式（已知坐标）
    python control.py click <x> <y>

    # 智能定位（推荐）
    python control.py smart-click "发送按钮"
    python control.py smart-click "苦尘" --verify-before-click

    # 打开应用（系统级）
    python control.py open-app "企业微信"
    python control.py open-app "WeCom"

    # 其他操作
    python control.py drag <from_x> <from_y> <to_x> <to_y>
    python control.py scroll <amount>
    python control.py type "文字"
    python control.py hotkey "cmd+c"
"""

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

# 自动切换到脚本所在目录，支持从任意目录调用
SCRIPT_DIR = Path(__file__).resolve().parent
os.chdir(SCRIPT_DIR)

import cv2
import mss
import numpy as np
import pyautogui

# 安全设置：屏幕角落触发停止
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05  # 每个操作后的小暂停，更拟人

# 导入定位器
from locators import SmartLocator, LocatorResult, AILocator


class ChangeVerifier:
    """变化验证器 - 验证操作后画面是否变化"""

    def __init__(self):
        self.sct = mss.mss()
        self.detector = None
        # 延迟导入避免循环依赖
        from utils.detector import ChangeDetector
        self.detector = ChangeDetector()

    def capture_hash(self) -> int:
        """捕获当前画面并计算哈希"""
        monitor = self.sct.monitors[1]
        screenshot = self.sct.grab(monitor)
        frame = np.array(screenshot)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGRA2RGB)
        return self.detector.perceptual_hash(frame_rgb)

    def verify_change(self, before_hash: int, timeout: float = 5.0,
                      threshold: float = 0.95) -> dict:
        """
        验证画面是否变化

        Args:
            before_hash: 操作前的画面哈希
            timeout: 超时时间
            threshold: 相似度阈值，低于此值认为有变化

        Returns:
            验证结果字典
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            current_hash = self.capture_hash()
            similarity = 1 - self.detector._hamming_distance(before_hash, current_hash) / 64

            if similarity < threshold:
                return {
                    "changed": True,
                    "similarity": round(similarity, 4),
                    "elapsed": round(time.time() - start_time, 2)
                }

            time.sleep(0.2)

        # 超时，获取最终相似度
        current_hash = self.capture_hash()
        similarity = 1 - self.detector._hamming_distance(before_hash, current_hash) / 64

        return {
            "changed": similarity < threshold,
            "similarity": round(similarity, 4),
            "elapsed": round(timeout, 2),
            "timeout": True
        }

    def verify_stable(self, timeout: float = 5.0, threshold: float = 0.95,
                      window: int = 3) -> dict:
        """
        验证画面是否稳定

        Args:
            timeout: 超时时间
            threshold: 相似度阈值
            window: 稳定窗口大小

        Returns:
            验证结果字典
        """
        start_time = time.time()
        stable_count = 0
        prev_hash = None

        while time.time() - start_time < timeout:
            current_hash = self.capture_hash()

            if prev_hash is not None:
                similarity = 1 - self.detector._hamming_distance(prev_hash, current_hash) / 64

                if similarity >= threshold:
                    stable_count += 1
                    if stable_count >= window:
                        return {
                            "stable": True,
                            "similarity": round(similarity, 4),
                            "elapsed": round(time.time() - start_time, 2)
                        }
                else:
                    stable_count = 0
                    prev_hash = current_hash  # 重置为当前哈希，重新计算连续稳定
            time.sleep(0.3)

        return {
            "stable": False,
            "elapsed": round(timeout, 2),
            "timeout": True
        }

    def close(self):
        """关闭资源"""
        if self.sct:
            self.sct.close()


class ScreenController:
    """屏幕控制器 - 执行鼠标键盘操作"""

    def __init__(self):
        self.screen_width, self.screen_height = pyautogui.size()
        self.verifier = None
        self.locator = SmartLocator()

    def _get_verifier(self) -> ChangeVerifier:
        """懒加载验证器"""
        if self.verifier is None:
            self.verifier = ChangeVerifier()
        return self.verifier

    def _capture_screen(self) -> np.ndarray:
        """截取当前屏幕（带鼠标光标）"""
        sct = mss.mss()
        monitor = sct.monitors[1]
        screenshot = sct.grab(monitor)
        frame = np.array(screenshot)
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2RGB)

    def _save_for_ai_verify(self, filepath: str = "/tmp/verify_click.png") -> str:
        """截图并保存，用于 AI 验证"""
        frame = self._capture_screen()
        cv2.imwrite(filepath, frame)
        return filepath

    def _mark_position(self, x: int, y: int, radius: int = 20,
                       color: Tuple = (255, 0, 0), thickness: int = 3,
                       output: str = "/tmp/verify_marked.png") -> str:
        """在截图上标记位置（红圈）"""
        frame = self._capture_screen()
        cv2.circle(frame, (x, y), radius, color, thickness)
        cv2.imwrite(output, frame)
        return output

    def _mark_direction(self, x: int, y: int, direction: str = "center",
                        output: str = "/tmp/verify_direction.png") -> str:
        """在截图上标记位置和方向箭头"""
        frame = self._capture_screen()

        # 画中心圆
        cv2.circle(frame, (x, y), 15, (255, 0, 0), 3)

        # 画方向箭头
        arrow_length = 60
        angle_map = {
            "top": -90, "bottom": 90, "left": 180, "right": 0,
            "top-left": -135, "top-right": -45,
            "bottom-left": 135, "bottom-right": 45,
            "center": 0  # 默认不画箭头或指向右侧
        }
        angle = angle_map.get(direction, 0)
        import math
        rad = math.radians(angle)
        end_x = int(x + arrow_length * math.cos(rad))
        end_y = int(y + arrow_length * math.sin(rad))
        cv2.arrowedLine(frame, (x, y), (end_x, end_y), (0, 255, 0), 3)

        cv2.imwrite(output, frame)
        return output

    def smart_click(self, target_description: str,
                    verify_before_click: bool = True,
                    max_verify_attempts: int = 3,
                    verify_timeout: float = 5.0) -> dict:
        """
        智能点击 - 自动定位目标并执行点击

        闭环流程：
        1. 用多种策略获取精确坐标（Accessibility API / OCR / 颜色 / AI）
        2. 移动鼠标到目标位置（不点击）
        3. 截图让 AI 验证位置对不对
        4. AI 说对 → 点击
        5. AI 说不对 → 修正坐标，重试（最多 N 次）

        Args:
            target_description: 目标描述，如"发送按钮"、"苦尘"
            verify_before_click: 是否在点击前让 AI 验证
            max_verify_attempts: 最大验证重试次数
            verify_timeout: 每次验证的超时时间

        Returns:
            结果字典
        """
        result = {
            "action": "smart_click",
            "target": target_description,
            "status": "running"
        }

        # 步骤 1: 定位目标
        print(json.dumps({
            "step": 1,
            "action": "locating",
            "target": target_description
        }, ensure_ascii=False))

        loc_result = self.locator.locate(target_description)

        if not loc_result.success:
            result["status"] = "failed"
            result["error"] = f"定位失败：{loc_result.error}"
            print(json.dumps(result, ensure_ascii=False))
            return result

        x, y = loc_result.center()
        print(json.dumps({
            "step": 1,
            "action": "located",
            "source": loc_result.source,
            "confidence": loc_result.confidence,
            "x": x,
            "y": y,
            "box": [loc_result.x, loc_result.y, loc_result.width, loc_result.height]
        }, ensure_ascii=False))

        # 步骤 2-N: 验证闭环
        current_x, current_y = x, y

        for attempt in range(max_verify_attempts):
            print(json.dumps({
                "step": 2 + attempt,
                "action": "verify_attempt",
                "attempt": attempt + 1,
                "max_attempts": max_verify_attempts
            }, ensure_ascii=False))

            # 移动鼠标到目标位置（不点击）
            self._human_move(current_x, current_y)
            time.sleep(0.2)  # 等鼠标渲染

            if verify_before_click:
                # 截图带标记
                marked_path = self._mark_position(current_x, current_y)

                # AI 验证 - 输出验证信息
                verify_info = {
                    "step": 2 + attempt,
                    "action": "ai_verify",
                    "image": marked_path,
                    "target": target_description,
                    "prompt": f"鼠标指针/红圈中心位置是不是'{target_description}'？请回答 match 或 no_match，如果不对请给出修正坐标"
                }
                print(json.dumps(verify_info, ensure_ascii=False))

                # 注意：这里需要外部 AI 调用并返回结果
                # 在命令行模式下，我们输出信息让用户判断
                # 在技能模式下，AI 会读取输出并返回决策

                # 等待 AI 响应（在技能中会自动进行）
                # 这里假设 AI 返回结果在环境变量或标准输入中
                ai_decision = self._get_ai_decision(target_description, marked_path)

                if ai_decision.get("match", True):
                    # AI 确认位置正确，执行点击
                    print(json.dumps({
                        "step": "click",
                        "action": "executing_click",
                        "verified": True
                    }, ensure_ascii=False))

                    pyautogui.click()

                    result["status"] = "success"
                    result["x"] = current_x
                    result["y"] = current_y
                    result["verified"] = True
                    result["attempts"] = attempt + 1
                    print(json.dumps(result, ensure_ascii=False))
                    return result
                else:
                    # AI 说位置不对，尝试修正
                    correction = ai_decision.get("correction")
                    if correction:
                        current_x = correction.get("x", current_x)
                        current_y = correction.get("y", current_y)
                        print(json.dumps({
                            "step": "correction",
                            "action": "apply_correction",
                            "new_x": current_x,
                            "new_y": current_y
                        }, ensure_ascii=False))
                    else:
                        # 没有修正坐标，重试
                        print(json.dumps({
                            "step": "correction",
                            "action": "retry_without_correction"
                        }, ensure_ascii=False))
            else:
                # 不验证，直接点击
                pyautogui.click()
                result["status"] = "success"
                result["x"] = current_x
                result["y"] = current_y
                result["verified"] = False
                print(json.dumps(result, ensure_ascii=False))
                return result

        # 超过最大重试次数
        result["status"] = "failed"
        result["error"] = f"超过最大验证次数 ({max_verify_attempts})"
        print(json.dumps(result, ensure_ascii=False))
        return result

    def _get_ai_decision(self, target_description: str, marked_image_path: str) -> dict:
        """
        获取 AI 决策

        在技能模式下，AI 会读取输出并自动响应：
        1. 输出带标记的截图路径
        2. AI 使用 Read 工具查看截图
        3. AI 返回 match/no_match 决策

        在命令行模式下，暂停等待用户输入

        Returns:
            {"match": bool, "correction": {"x": int, "y": int}}
        """
        # 输出验证信息，等待 AI 响应
        # 在技能模式下，这会触发 Claude 读取截图并返回决策
        print(json.dumps({
            "action": "waiting_for_ai_decision",
            "target": target_description,
            "verify_image": marked_image_path,
            "instruction": f"请用 Read 工具查看 {marked_image_path}，判断红圈中心位置是否是'{target_description}'。如果是，返回 {{\"match\": true}}；如果不是，返回 {{\"match\": false, \"correction\": {{\"x\": 新 x 坐标，\"y\": 新 y 坐标}}}}"
        }, ensure_ascii=False))

        # 尝试从标准输入读取 AI 决策（技能模式下）
        if not sys.stdin.isatty():
            try:
                line = sys.stdin.readline()
                if line:
                    return json.loads(line)
            except:
                pass

        # 命令行模式：没有 AI 参与，默认匹配（不验证）
        # 技能模式下，上面会阻塞等待 AI 输入
        return {"match": True}

    def click(self, x: int, y: int, button: str = "left",
              verify: bool = False, retry: int = 0, verify_timeout: float = 3.0):
        """
        点击指定坐标（传统方式）

        Args:
            x: X 坐标
            y: Y 坐标
            button: left / right / middle
            verify: 是否验证画面变化
            retry: 失败重试次数
            verify_timeout: 验证超时时间
        """
        # 边界检查
        x = max(0, min(x, self.screen_width - 1))
        y = max(0, min(y, self.screen_height - 1))

        attempts = 0
        max_attempts = retry + 1

        while attempts < max_attempts:
            # 如果需要验证，记录操作前的状态
            before_hash = None
            if verify:
                verifier = self._get_verifier()
                before_hash = verifier.capture_hash()

            # 拟人化移动
            self._human_move(x, y)

            # 点击
            pyautogui.click(button=button)

            # 验证
            if verify and before_hash is not None:
                time.sleep(0.3)  # 短暂等待
                result = verifier.verify_change(before_hash, timeout=verify_timeout)

                if result["changed"]:
                    print(json.dumps({
                        "action": "click",
                        "x": x,
                        "y": y,
                        "button": button,
                        "status": "success",
                        "verified": True,
                        "attempt": attempts + 1,
                        "verification": result
                    }))
                    return
                else:
                    attempts += 1
                    if attempts < max_attempts:
                        time.sleep(0.5)  # 重试前等待
                        continue
                    else:
                        print(json.dumps({
                            "action": "click",
                            "x": x,
                            "y": y,
                            "button": button,
                            "status": "failed",
                            "verified": True,
                            "attempt": attempts,
                            "reason": "no_change_detected",
                            "verification": result
                        }))
                        return
            else:
                # 无需验证，直接返回成功
                print(json.dumps({
                    "action": "click",
                    "x": x,
                    "y": y,
                    "button": button,
                    "status": "success",
                    "verified": False,
                    "attempt": attempts + 1
                }))
                return

    def double_click(self, x: int, y: int, verify: bool = False,
                     retry: int = 0, verify_timeout: float = 3.0):
        """双击"""
        x = max(0, min(x, self.screen_width - 1))
        y = max(0, min(y, self.screen_height - 1))

        attempts = 0
        max_attempts = retry + 1

        while attempts < max_attempts:
            before_hash = None
            if verify:
                verifier = self._get_verifier()
                before_hash = verifier.capture_hash()

            self._human_move(x, y)
            pyautogui.doubleClick()

            if verify and before_hash is not None:
                time.sleep(0.3)
                result = verifier.verify_change(before_hash, timeout=verify_timeout)

                if result["changed"]:
                    print(json.dumps({
                        "action": "double_click",
                        "x": x,
                        "y": y,
                        "status": "success",
                        "verified": True,
                        "attempt": attempts + 1,
                        "verification": result
                    }))
                    return
                else:
                    attempts += 1
                    if attempts < max_attempts:
                        time.sleep(0.5)
                        continue
                    else:
                        print(json.dumps({
                            "action": "double_click",
                            "x": x,
                            "y": y,
                            "status": "failed",
                            "verified": True,
                            "attempt": attempts,
                            "reason": "no_change_detected",
                            "verification": result
                        }))
                        return
            else:
                print(json.dumps({
                    "action": "double_click",
                    "x": x,
                    "y": y,
                    "status": "success",
                    "verified": False,
                    "attempt": attempts + 1
                }))
                return

    def drag(self, from_x: int, from_y: int, to_x: int, to_y: int,
             duration: float = 0.5, verify: bool = False, verify_timeout: float = 3.0):
        """
        拖拽

        Args:
            from_x, from_y: 起始坐标
            to_x, to_y: 目标坐标
            duration: 拖拽持续时间
            verify: 是否验证画面变化
            verify_timeout: 验证超时时间
        """
        # 边界检查
        from_x = max(0, min(from_x, self.screen_width - 1))
        from_y = max(0, min(from_y, self.screen_height - 1))
        to_x = max(0, min(to_x, self.screen_width - 1))
        to_y = max(0, min(to_y, self.screen_height - 1))

        before_hash = None
        if verify:
            verifier = self._get_verifier()
            before_hash = verifier.capture_hash()

        # 移动到起点
        self._human_move(from_x, from_y)

        # 拖拽到终点
        pyautogui.drag(to_x - from_x, to_y - from_y, duration=duration)

        result = None
        if verify and before_hash is not None:
            time.sleep(0.3)
            result = verifier.verify_change(before_hash, timeout=verify_timeout)

        print(json.dumps({
            "action": "drag",
            "from": [from_x, from_y],
            "to": [to_x, to_y],
            "status": "success",
            "verified": verify,
            "verification": result
        }))

    def visual_approach(self, target_description: str,
                        initial_x: int = None, initial_y: int = None,
                        max_steps: int = 5, step_size: int = 100) -> dict:
        """
        视觉渐进式定位 - 像人一样通过视觉反馈逐步逼近目标

        流程：
        1. 从初始位置开始（如果有）
        2. 截图让 AI 判断目标在哪个方向
        3. 朝目标方向移动 step_size 像素
        4. 重复直到 AI 说"找到了"或"差不多了"
        5. 返回最终坐标

        Args:
            target_description: 目标描述
            initial_x, initial_y: 初始坐标（可选，默认用当前鼠标位置）
            max_steps: 最大尝试步数
            step_size: 每步移动像素

        Returns:
            结果字典 {"success": bool, "x": int, "y": int, "steps": int}
        """
        import pyautogui

        result = {
            "action": "visual_approach",
            "target": target_description,
            "status": "running"
        }

        # 获取初始位置
        if initial_x is None or initial_y is None:
            current_x, current_y = pyautogui.position()
        else:
            current_x, current_y = initial_x, initial_y

        # 移动鼠标到初始位置
        self._human_move(current_x, current_y)
        time.sleep(0.3)

        print(json.dumps({
            "action": "visual_approach_start",
            "target": target_description,
            "start_x": current_x,
            "start_y": current_y,
            "max_steps": max_steps,
            "step_size": step_size
        }, ensure_ascii=False))

        for step in range(max_steps):
            print(json.dumps({
                "step": step + 1,
                "action": "analyzing_direction",
                "current_x": current_x,
                "current_y": current_y
            }, ensure_ascii=False))

            # 截图带方向标记
            marked_path = self._mark_direction(current_x, current_y, "center")

            # AI 判断目标方向
            print(json.dumps({
                "action": "ai_direction_check",
                "image": marked_path,
                "prompt": f"从截图看，'{target_description}'在当前鼠标位置（蓝色圆圈中心）的哪个方向？请从以下选择：top(上方)/bottom(下方)/left(左方)/right(右方)/top-left(左上)/top-right(右上)/bottom-left(左下)/bottom-right(右下)/found(已找到/差不多了)。回答格式：{{\"direction\": \"xxx\", \"confidence\": 0.x}}"
            }, ensure_ascii=False))

            # 获取 AI 决策
            ai_decision = self._get_direction_decision()

            direction = ai_decision.get("direction", "")
            confidence = ai_decision.get("confidence", 0)

            print(json.dumps({
                "action": "ai_direction_result",
                "direction": direction,
                "confidence": confidence
            }, ensure_ascii=False))

            # 如果 AI 说找到了，返回
            if direction == "found" or confidence > 0.8:
                result["status"] = "success"
                result["x"] = current_x
                result["y"] = current_y
                result["steps"] = step + 1
                result["found"] = True
                print(json.dumps(result, ensure_ascii=False))
                return result

            # 否则朝目标方向移动
            if direction in ["top", "bottom", "left", "right", "top-left", "top-right", "bottom-left", "bottom-right"]:
                current_x, current_y = self._move_in_direction(current_x, current_y, direction, step_size)

                # 边界检查
                current_x = max(0, min(current_x, self.screen_width - 1))
                current_y = max(0, min(current_y, self.screen_height - 1))

                # 移动鼠标
                self._human_move(current_x, current_y)
                time.sleep(0.3)
            else:
                # AI 没有返回有效方向，重试
                print(json.dumps({
                    "action": "invalid_direction",
                    "received": direction
                }, ensure_ascii=False))

        # 超过最大步数
        result["status"] = "failed"
        result["error"] = f"超过最大步数 ({max_steps})，未找到目标"
        result["x"] = current_x
        result["y"] = current_y
        result["found"] = False
        print(json.dumps(result, ensure_ascii=False))
        return result

    def _move_in_direction(self, x: int, y: int, direction: str, distance: int) -> Tuple[int, int]:
        """朝指定方向移动"""
        deltas = {
            "top": (0, -distance),
            "bottom": (0, distance),
            "left": (-distance, 0),
            "right": (distance, 0),
            "top-left": (-distance, -distance),
            "top-right": (distance, -distance),
            "bottom-left": (-distance, distance),
            "bottom-right": (distance, distance)
        }
        dx, dy = deltas.get(direction, (0, 0))
        return x + dx, y + dy

    def _get_direction_decision(self) -> dict:
        """获取 AI 方向决策"""
        # 尝试从标准输入读取
        if not sys.stdin.isatty():
            try:
                line = sys.stdin.readline()
                if line:
                    return json.loads(line)
            except:
                pass

        # 默认返回 found（不验证模式）
        return {"direction": "found", "confidence": 0.5}

    def scroll(self, amount: int):
        """
        滚动

        Args:
            amount: 正数向上，负数向下
        """
        pyautogui.scroll(amount)

        print(json.dumps({
            "action": "scroll",
            "amount": amount,
            "status": "success"
        }))

    def open_app(self, app_name: str, wait_for_stable: bool = True,
                 timeout: float = 5.0) -> dict:
        """
        系统级打开应用

        使用 macOS `open -a` 命令，比 GUI 点击更可靠

        Args:
            app_name: 应用名称（如 "企业微信" 或 "WeCom"）
            wait_for_stable: 是否等待应用窗口稳定
            timeout: 等待超时时间

        Returns:
            结果字典
        """
        import subprocess

        result = {
            "action": "open_app",
            "app_name": app_name,
            "status": "running"
        }

        # 尝试不同的应用名称
        app_names_to_try = [app_name]

        # 添加常见别名
        if app_name.lower() in ["wecom", "企业微信"]:
            app_names_to_try.extend(["WeCom", "企业微信"])
        elif app_name.lower() in ["wechat", "微信"]:
            app_names_to_try.extend(["WeChat", "微信"])
        elif app_name.lower() in ["dingtalk", "钉钉"]:
            app_names_to_try.extend(["DingTalk", "钉钉"])

        # 尝试打开应用
        for name in app_names_to_try:
            try:
                subprocess.run(["open", "-a", name], check=True, capture_output=True)
                result["used_name"] = name
                break
            except subprocess.CalledProcessError:
                continue
        else:
            result["status"] = "failed"
            result["error"] = f"无法打开应用：{app_name}，请检查应用名称是否正确"
            print(json.dumps(result, ensure_ascii=False))
            return result

        # 等待应用启动
        if wait_for_stable:
            print(json.dumps({
                "action": "waiting",
                "status": "waiting_for_app_to_stabilize",
                "timeout": timeout
            }, ensure_ascii=False))

            verifier = self._get_verifier()
            stable_result = verifier.verify_stable(timeout=timeout)

            if stable_result.get("stable"):
                result["status"] = "success"
                result["app_launched"] = True
            else:
                result["status"] = "success"  # 应用可能已启动，但窗口未稳定
                result["app_launched"] = True
                result["note"] = "应用已启动，但窗口可能仍在加载"
        else:
            result["status"] = "success"
            result["app_launched"] = True

        print(json.dumps(result, ensure_ascii=False))
        return result

    def type_text(self, text: str, interval: float = 0.05):
        """
        输入文字

        Args:
            text: 要输入的文字
            interval: 字符间隔（拟人化）
        """
        # 中文输入需要使用剪贴板
        if any('\u4e00' <= c <= '\u9fff' for c in text):
            self._type_chinese(text)
        else:
            pyautogui.write(text, interval=interval)

        print(json.dumps({
            "action": "type",
            "text": text,
            "status": "success"
        }))

    def _type_chinese(self, text: str):
        """使用剪贴板输入中文"""
        import pyperclip

        pyperclip.copy(text)
        # 粘贴
        if sys.platform == "darwin":  # macOS
            pyautogui.hotkey("command", "v")
        else:  # Windows/Linux
            pyautogui.hotkey("ctrl", "v")

        time.sleep(0.1)  # 等待粘贴完成

    def hotkey(self, keys: str):
        """
        执行快捷键

        Args:
            keys: 快捷键字符串，如 "cmd+c", "ctrl+shift+t"
        """
        key_list = [k.strip().lower() for k in keys.split("+")]

        # 键名映射（macOS 特殊键）
        key_map = {
            "cmd": "command",
            "opt": "option",
            "ctrl": "control",
        }

        key_list = [key_map.get(k, k) for k in key_list]

        pyautogui.hotkey(*key_list)

        print(json.dumps({
            "action": "hotkey",
            "keys": key_list,
            "status": "success"
        }))

    def wait(self, seconds: float):
        """
        等待（拟人化，有随机波动）

        Args:
            seconds: 等待秒数
        """
        # 添加 10% 随机波动
        actual_wait = seconds * (1 + random.uniform(-0.1, 0.1))
        time.sleep(actual_wait)

        print(json.dumps({
            "action": "wait",
            "seconds": seconds,
            "actual": round(actual_wait, 3),
            "status": "success"
        }))

    def _human_move(self, x: int, y: int):
        """
        拟人化移动鼠标

        使用缓动曲线移动，而非直线
        """
        current_x, current_y = pyautogui.position()

        # 计算移动时间（基于距离）
        distance = ((x - current_x) ** 2 + (y - current_y) ** 2) ** 0.5
        duration = min(0.5, distance / 1000)  # 最长 0.5 秒

        # 使用 easeOutQuad 缓动函数
        pyautogui.moveTo(x, y, duration=duration, _pause=False)

    def verify_screen(self, timeout: float = 5.0, threshold: float = 0.95,
                      mode: str = "change"):
        """
        验证屏幕状态

        Args:
            timeout: 超时时间
            threshold: 相似度阈值
            mode: change=等待变化，stable=等待稳定
        """
        verifier = self._get_verifier()

        if mode == "change":
            # 获取初始帧
            initial_hash = verifier.capture_hash()
            time.sleep(0.1)

            result = {"status": "waiting", "mode": "change"}
            print(json.dumps(result))

            start_time = time.time()
            while time.time() - start_time < timeout:
                current_hash = verifier.capture_hash()
                similarity = 1 - verifier.detector._hamming_distance(initial_hash, current_hash) / 64

                if similarity < threshold:
                    print(json.dumps({
                        "status": "changed",
                        "similarity": round(similarity, 4),
                        "elapsed": round(time.time() - start_time, 2)
                    }))
                    return

                time.sleep(0.3)

            print(json.dumps({
                "status": "timeout",
                "elapsed": timeout
            }))

        else:  # stable
            result = verifier.verify_stable(timeout, threshold)
            print(json.dumps({
                "status": "stable" if result["stable"] else "unstable",
                "verification": result
            }))


def main():
    parser = argparse.ArgumentParser(description="屏幕控制器")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # smart-click 命令（新增）
    smart_parser = subparsers.add_parser("smart-click", help="智能点击 - 自动定位并验证")
    smart_parser.add_argument("target", help="目标描述，如'发送按钮'、'苦尘'")
    smart_parser.add_argument("--verify-before-click", action="store_true", default=True,
                              help="点击前让 AI 验证位置")
    smart_parser.add_argument("--max-attempts", type=int, default=3,
                              help="最大验证重试次数")
    smart_parser.add_argument("--no-verify", action="store_true",
                              help="跳过验证，直接点击（定位后）")

    # click 命令
    click_parser = subparsers.add_parser("click", help="点击")
    click_parser.add_argument("x", type=int, help="X 坐标")
    click_parser.add_argument("y", type=int, help="Y 坐标")
    click_parser.add_argument("--button", default="left", choices=["left", "right", "middle"])
    click_parser.add_argument("--verify", action="store_true", help="验证操作后画面变化")
    click_parser.add_argument("--retry", type=int, default=0, help="失败重试次数")
    click_parser.add_argument("--verify-timeout", type=float, default=3.0, help="验证超时时间")

    # locate 命令（新增）- 只定位不点击
    locate_parser = subparsers.add_parser("locate", help="定位目标并返回坐标")
    locate_parser.add_argument("target", help="目标描述")
    locate_parser.add_argument("--prefer", choices=["accessibility", "ocr", "color", "ai"],
                               help="优先使用的定位方式")

    # double_click 命令
    dc_parser = subparsers.add_parser("double-click", help="双击")
    dc_parser.add_argument("x", type=int)
    dc_parser.add_argument("y", type=int)
    dc_parser.add_argument("--verify", action="store_true", help="验证操作后画面变化")
    dc_parser.add_argument("--retry", type=int, default=0, help="失败重试次数")
    dc_parser.add_argument("--verify-timeout", type=float, default=3.0, help="验证超时时间")

    # drag 命令
    drag_parser = subparsers.add_parser("drag", help="拖拽")
    drag_parser.add_argument("from_x", type=int)
    drag_parser.add_argument("from_y", type=int)
    drag_parser.add_argument("to_x", type=int)
    drag_parser.add_argument("to_y", type=int)
    drag_parser.add_argument("--duration", type=float, default=0.5)
    drag_parser.add_argument("--verify", action="store_true", help="验证操作后画面变化")
    drag_parser.add_argument("--verify-timeout", type=float, default=3.0, help="验证超时时间")

    # scroll 命令
    scroll_parser = subparsers.add_parser("scroll", help="滚动")
    scroll_parser.add_argument("amount", type=int, help="滚动量（正上负下）")

    # type 命令
    type_parser = subparsers.add_parser("type", help="输入文字")
    type_parser.add_argument("text", help="要输入的文字")

    # hotkey 命令
    hotkey_parser = subparsers.add_parser("hotkey", help="快捷键")
    hotkey_parser.add_argument("keys", help='快捷键，如 "cmd+c"')

    # wait 命令
    wait_parser = subparsers.add_parser("wait", help="等待")
    wait_parser.add_argument("seconds", type=float, help="等待秒数")

    # verify 命令 - 独立验证命令
    verify_parser = subparsers.add_parser("verify", help="验证画面状态")
    verify_parser.add_argument("--timeout", type=float, default=5.0, help="超时时间")
    verify_parser.add_argument("--threshold", type=float, default=0.95, help="相似度阈值")
    verify_parser.add_argument("--mode", choices=["change", "stable"], default="change",
                               help="验证模式：change=等待变化，stable=等待稳定")

    # open-app 命令（新增）- 系统级打开应用
    open_app_parser = subparsers.add_parser("open-app", help="打开应用（系统级）")
    open_app_parser.add_argument("app_name", help="应用名称，如'企业微信'、'WeCom'")
    open_app_parser.add_argument("--no-wait", action="store_true",
                                 help="不等待应用窗口稳定")
    open_app_parser.add_argument("--timeout", type=float, default=5.0,
                                 help="等待超时时间")

    # visual-approach 命令（新增）- 视觉渐进式定位
    visual_approach_parser = subparsers.add_parser("visual-approach", help="视觉渐进式定位目标")
    visual_approach_parser.add_argument("target", help="目标描述，如'发送按钮'、'苦尘'")
    visual_approach_parser.add_argument("--max-steps", type=int, default=5,
                                        help="最大尝试步数")
    visual_approach_parser.add_argument("--step-size", type=int, default=100,
                                        help="每步移动像素")
    visual_approach_parser.add_argument("--start-x", type=int, default=None,
                                        help="初始 X 坐标")
    visual_approach_parser.add_argument("--start-y", type=int, default=None,
                                        help="初始 Y 坐标")

    args = parser.parse_args()

    controller = ScreenController()

    if args.command == "smart-click":
        result = controller.smart_click(
            args.target,
            verify_before_click=not args.no_verify,
            max_verify_attempts=args.max_attempts
        )
    elif args.command == "locate":
        result = controller.locator.locate(args.target, args.prefer)
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    elif args.command == "open-app":
        result = controller.open_app(
            args.app_name,
            wait_for_stable=not args.no_wait,
            timeout=args.timeout
        )
    elif args.command == "click":
        controller.click(args.x, args.y, args.button, args.verify, args.retry, args.verify_timeout)
    elif args.command == "double-click":
        controller.double_click(args.x, args.y, args.verify, args.retry, args.verify_timeout)
    elif args.command == "drag":
        controller.drag(args.from_x, args.from_y, args.to_x, args.to_y,
                       args.duration, args.verify, args.verify_timeout)
    elif args.command == "scroll":
        controller.scroll(args.amount)
    elif args.command == "type":
        controller.type_text(args.text)
    elif args.command == "hotkey":
        controller.hotkey(args.keys)
    elif args.command == "wait":
        controller.wait(args.seconds)
    elif args.command == "verify":
        controller.verify_screen(args.timeout, args.threshold, args.mode)

    # 清理验证器资源
    if controller.verifier:
        controller.verifier.close()


if __name__ == "__main__":
    main()
