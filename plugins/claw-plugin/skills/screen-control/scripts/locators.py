#!/usr/bin/env python3
"""
目标定位器 - 多种策略获取精确坐标

定位策略（按优先级）：
1. Accessibility API - macOS 系统级 UI 树访问
2. OCR 文字定位 - 识别屏幕文字位置
3. AI 视觉定位 - AI 看图估算坐标（兜底）
4. 颜色特征定位 - 特定颜色/形状的图标
"""

import json
import os
import subprocess
import sys
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import pyautogui

# 自动切换到脚本所在目录
SCRIPT_DIR = Path(__file__).resolve().parent
os.chdir(SCRIPT_DIR)


class LocatorResult:
    """定位结果"""

    def __init__(self, success: bool, x: int = 0, y: int = 0,
                 width: int = 0, height: int = 0,
                 confidence: float = 0.0, source: str = "",
                 error: str = ""):
        self.success = success
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.confidence = confidence
        self.source = source
        self.error = error

    def center(self) -> Tuple[int, int]:
        """返回中心坐标"""
        return (self.x + self.width // 2, self.y + self.height // 2)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "confidence": round(self.confidence, 4),
            "source": self.source,
            "error": self.error,
            "center": self.center()
        }


class BaseLocator(ABC):
    """定位器基类"""

    @abstractmethod
    def can_handle(self, description: str) -> bool:
        """判断是否能处理这个描述"""
        pass

    @abstractmethod
    def find(self, description: str, screenshot: np.ndarray = None) -> LocatorResult:
        """查找目标位置"""
        pass


class AccessibilityLocator(BaseLocator):
    """
    macOS Accessibility API 定位器

    使用系统级 AX API 获取 UI 元素位置，最精确
    """

    def __init__(self):
        self.ax_app = None
        self._init_ax()

    def _init_ax(self):
        """初始化 Accessibility API"""
        try:
            # 延迟导入，避免没有 pyobjc 时报错
            from AppKit import AXUIElementCreateApplication, NSWorkspace
            self.NSWorkspace = NSWorkspace
            self.AXUIElementCreateApplication = AXUIElementCreateApplication
        except ImportError:
            pass

    def can_handle(self, description: str) -> bool:
        # Accessibility API 可以尝试处理所有描述
        return True

    def _get_focused_window(self):
        """获取当前焦点窗口"""
        try:
            app = self.NSWorkspace.sharedWorkspace().frontmostApplication()
            if app is None:
                return None

            pid = app.processIdentifier()
            ax_app = self.AXUIElementCreateApplication(pid)
            self.ax_app = ax_app

            # 获取焦点窗口
            error, ref = AXUIElementCopyAttributeValue(
                ax_app, "AXFocusedWindow", None
            )
            if error == 0:
                return ref
            return None
        except Exception as e:
            return None

    def _get_all_elements(self, container, depth: int = 0, max_depth: int = 5) -> List[dict]:
        """递归获取所有 UI 元素"""
        elements = []
        if depth > max_depth:
            return elements

        try:
            from AppKit import AXUIElementCopyAttributeValue

            # 获取子元素
            error, children = AXUIElementCopyAttributeValue(
                container, "AXChildren", None
            )
            if error != 0 or children is None:
                return elements

            for i in range(len(children)):
                child = children[i]
                elem_info = self._extract_element_info(child)
                if elem_info:
                    elements.append(elem_info)
                    # 递归获取子元素的子元素
                    elements.extend(self._get_all_elements(child, depth + 1, max_depth))

        except Exception as e:
            pass

        return elements

    def _extract_element_info(self, element) -> Optional[dict]:
        """提取元素信息"""
        try:
            from AppKit import AXUIElementCopyAttributeValue, CFGetTypeID, CFGetTypeID

            info = {}

            # 获取角色类型
            error, role = AXUIElementCopyAttributeValue(element, "AXRole", None)
            if error == 0 and role:
                info["role"] = str(role)

            # 获取描述/标题
            error, desc = AXUIElementCopyAttributeValue(element, "AXDescription", None)
            if error == 0 and desc:
                info["description"] = str(desc)

            error, title = AXUIElementCopyAttributeValue(element, "AXTitle", None)
            if error == 0 and title:
                info["title"] = str(title)

            # 获取值（按钮文字等）
            error, value = AXUIElementCopyAttributeValue(element, "AXValue", None)
            if error == 0 and value:
                info["value"] = str(value)

            # 获取位置
            error, pos = AXUIElementCopyAttributeValue(element, "AXPosition", None)
            if error == 0 and pos:
                info["x"] = int(pos.x)
                info["y"] = int(pos.y)

            # 获取尺寸
            error, size = AXUIElementCopyAttributeValue(element, "AXSize", None)
            if error == 0 and size:
                info["width"] = int(size.width)
                info["height"] = int(size.height)

            # 只有有位置信息的才返回
            if "x" in info and "y" in info:
                return info

        except Exception as e:
            pass

        return None

    def find(self, description: str, screenshot: np.ndarray = None) -> LocatorResult:
        """
        使用 Accessibility API 查找目标

        description 示例：
        - "发送按钮"
        - "搜索框"
        - "企业微信窗口的关闭按钮"
        - "苦尘"（聊天对象名）
        """
        try:
            from AppKit import AXUIElementCopyAttributeValue

            # 获取焦点窗口
            window = self._get_focused_window()
            if window is None:
                return LocatorResult(
                    success=False, error="无法获取焦点窗口", source="accessibility"
                )

            # 获取所有 UI 元素
            elements = self._get_all_elements(window)

            # 解析描述，提取关键词
            keywords = self._extract_keywords(description)

            # 匹配元素
            for elem in elements:
                if self._match_element(elem, keywords, description):
                    return LocatorResult(
                        success=True,
                        x=elem.get("x", 0),
                        y=elem.get("y", 0),
                        width=elem.get("width", 0),
                        height=elem.get("height", 0),
                        confidence=0.9,
                        source="accessibility"
                    )

            return LocatorResult(
                success=False,
                error=f"未找到匹配的元素：{description}",
                source="accessibility"
            )

        except ImportError:
            return LocatorResult(
                success=False,
                error="需要安装 pyobjc: pip install pyobjc-core pyobjc-framework-Cocoa",
                source="accessibility"
            )
        except Exception as e:
            return LocatorResult(
                success=False, error=str(e), source="accessibility"
            )

    def _extract_keywords(self, description: str) -> List[str]:
        """从描述中提取关键词"""
        # 角色类型关键词
        roles = {
            "按钮": "button",
            "按钮": "button",
            "输入框": "text",
            "搜索": "search",
            "关闭": "close",
            "发送": "send",
            "确定": "ok",
            "取消": "cancel",
        }

        keywords = []
        desc_lower = description.lower()

        for cn, en in roles.items():
            if cn in description:
                keywords.append(en)
                keywords.append(cn)

        return keywords

    def _match_element(self, elem: dict, keywords: List[str],
                       description: str) -> bool:
        """判断元素是否匹配描述"""
        # 检查角色
        role = elem.get("role", "").lower()
        title = elem.get("title", "").lower()
        desc = elem.get("description", "").lower()
        value = elem.get("value", "").lower()

        all_text = f"{role} {title} {desc} {value}"

        # 检查关键词
        for kw in keywords:
            if kw.lower() in all_text:
                return True

        # 直接检查描述是否包含
        if description.lower() in all_text:
            return True

        return False


class OcrLocator(BaseLocator):
    """
    OCR 文字定位器

    使用 pytesseract 识别屏幕文字位置
    """

    def __init__(self):
        self.tesseract_available = self._check_tesseract()

    def _check_tesseract(self) -> bool:
        """检查 tesseract 是否可用"""
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    def can_handle(self, description: str) -> bool:
        # 如果描述包含具体文字（非纯动作），可以尝试 OCR
        # 如 "苦尘"、"发送"、"确定"
        return len(description.strip()) > 0

    def find(self, description: str, screenshot: np.ndarray = None) -> LocatorResult:
        """使用 OCR 查找文字位置"""
        if not self.tesseract_available:
            return LocatorResult(
                success=False,
                error="tesseract 不可用，请安装：brew install tesseract",
                source="ocr"
            )

        if screenshot is None:
            # 自己截图
            try:
                import mss
                sct = mss.mss()
                monitor = sct.monitors[1]
                screenshot_obj = sct.grab(monitor)
                screenshot = np.array(screenshot_obj)
                screenshot = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2RGB)
            except Exception as e:
                return LocatorResult(
                    success=False, error=f"截图失败：{e}", source="ocr"
                )

        try:
            import pytesseract

            # OCR 识别
            data = pytesseract.image_to_data(
                screenshot, output_type=pytesseract.Output.DICT, lang='chi_sim+eng'
            )

            # 查找匹配的文字
            best_match = None
            best_score = 0

            for i, text in enumerate(data['text']):
                if not text.strip():
                    continue

                # 计算相似度
                score = self._text_similarity(description.lower(), text.lower())
                if score > best_score and score > 0.3:
                    best_score = score
                    best_match = {
                        'x': data['left'][i],
                        'y': data['top'][i],
                        'w': data['width'][i],
                        'h': data['height'][i],
                        'text': text
                    }

            if best_match:
                return LocatorResult(
                    success=True,
                    x=best_match['x'],
                    y=best_match['y'],
                    width=best_match['w'],
                    height=best_match['h'],
                    confidence=best_score,
                    source="ocr"
                )

            return LocatorResult(
                success=False,
                error=f"未找到文字：{description}",
                source="ocr"
            )

        except Exception as e:
            return LocatorResult(
                success=False, error=str(e), source="ocr"
            )

    def _text_similarity(self, target: str, text: str) -> float:
        """计算文字相似度"""
        # 完全包含
        if target in text or text in target:
            return 1.0

        # 部分匹配
        common = len(set(target) & set(text))
        return common / max(len(target), len(text), 1)


class ColorLocator(BaseLocator):
    """
    颜色特征定位器

    针对有鲜明颜色特征的应用图标
    """

    # 预定义的颜色范围（HSV）
    KNOWN_COLORS = {
        "wechat": {  # 微信 - 绿色
            "lower": np.array([40, 50, 50]),
            "upper": np.array([70, 255, 255])
        },
        "wecom": {  # 企业微信 - 青绿色
            "lower": np.array([80, 50, 50]),
            "upper": np.array([100, 255, 255])
        },
        "dingtalk": {  # 钉钉 - 蓝色
            "lower": np.array([100, 50, 50]),
            "upper": np.array([130, 255, 255])
        },
    }

    def can_handle(self, description: str) -> bool:
        desc_lower = description.lower()
        for app_name in self.KNOWN_COLORS.keys():
            if app_name in desc_lower:
                return True
        return False

    def find(self, description: str, screenshot: np.ndarray = None) -> LocatorResult:
        """使用颜色特征查找"""
        if screenshot is None:
            try:
                import mss
                sct = mss.mss()
                monitor = sct.monitors[1]
                screenshot_obj = sct.grab(monitor)
                screenshot = np.array(screenshot_obj)
                screenshot = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2RGB)
            except Exception as e:
                return LocatorResult(
                    success=False, error=f"截图失败：{e}", source="color"
                )

        # 转 HSV
        hsv = cv2.cvtColor(screenshot, cv2.COLOR_RGB2HSV)

        # 确定用哪个颜色范围
        color_key = self._find_matching_color(description)
        if color_key is None:
            return LocatorResult(
                success=False,
                error="未找到匹配的颜色范围",
                source="color"
            )

        color_range = self.KNOWN_COLORS[color_key]

        # 颜色分割
        mask = cv2.inRange(hsv, color_range['lower'], color_range['upper'])

        # 形态学操作去噪
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        # 找轮廓
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return LocatorResult(
                success=False,
                error=f"未找到 {color_key} 颜色的图标",
                source="color"
            )

        # 找最大轮廓
        largest = max(contours, key=cv2.contourArea)
        ((x, y), radius) = cv2.minEnclosingCircle(largest)

        return LocatorResult(
            success=True,
            x=int(x - radius),
            y=int(y - radius),
            width=int(radius * 2),
            height=int(radius * 2),
            confidence=0.7,
            source="color"
        )

    def _find_matching_color(self, description: str) -> Optional[str]:
        """找到匹配的颜色范围"""
        desc_lower = description.lower()

        for app_name in self.KNOWN_COLORS.keys():
            if app_name in desc_lower:
                return app_name

        return None


class AILocator(BaseLocator):
    """
    AI 视觉定位器（兜底方案）

    截图让 AI 分析目标位置
    """

    def can_handle(self, description: str) -> bool:
        # AI 可以处理所有描述，作为最后兜底
        return True

    def find(self, description: str, screenshot: np.ndarray = None) -> LocatorResult:
        """AI 定位 - 需要外部调用"""
        # 这个定位器需要 AI 参与，返回一个占位结果
        # 实际由上层调用 AI 来填充坐标
        return LocatorResult(
            success=False,
            error="AI 定位器需要外部 AI 调用，请通过 AI 分析截图获取坐标",
            source="ai"
        )

    def parse_ai_response(self, ai_output: str, screen_width: int,
                          screen_height: int) -> LocatorResult:
        """
        解析 AI 返回的坐标

        AI 输出格式示例：
        {
            "target": "发送按钮",
            "location": "窗口右下角",
            "x": 1200,
            "y": 800,
            "width": 80,
            "height": 40,
            "confidence": 0.8
        }
        """
        try:
            data = json.loads(ai_output)
            return LocatorResult(
                success=True,
                x=data.get('x', 0),
                y=data.get('y', 0),
                width=data.get('width', 0),
                height=data.get('height', 0),
                confidence=data.get('confidence', 0.5),
                source="ai"
            )
        except Exception as e:
            return LocatorResult(
                success=False, error=str(e), source="ai"
            )


class FallbackLocator(BaseLocator):
    """
    兜底坐标估算器

    当所有定位方式都失败时，基于常识估算坐标：
    - Dock 栏应用图标位置
    - 窗口控制按钮（关闭/最小化/最大化）
    - 常见 UI 元素位置
    """

    # Dock 栏位置（macOS 默认在底部居中）
    DOCK_ICON_Y_RATIO = 0.95  # Dock 在屏幕底部 5% 区域
    DOCK_ICON_WIDTH = 60
    DOCK_ICON_HEIGHT = 60

    # 窗口控制按钮（左上角）
    CLOSE_BUTTON_X = 50
    CLOSE_BUTTON_Y = 30

    def can_handle(self, description: str) -> bool:
        # 兜底策略总是可以处理
        desc_lower = description.lower()
        # 只处理常见的 UI 元素描述
        keywords = ["dock", "应用", "图标", "关闭", "最小化", "最大化", "搜索", "菜单"]
        return any(kw in desc_lower for kw in keywords)

    def find(self, description: str, screenshot: np.ndarray = None) -> LocatorResult:
        """基于常识估算坐标"""
        desc_lower = description.lower()
        screen_w, screen_h = pyautogui.size()

        # Dock 栏应用图标
        if "dock" in desc_lower or "图标" in desc_lower:
            # 估算 Dock 栏位置（底部居中区域）
            dock_y = int(screen_h * self.DOCK_ICON_Y_RATIO)
            # 假设第一个图标在左侧 1/4 处
            dock_x = int(screen_w * 0.15)

            return LocatorResult(
                success=True,
                x=dock_x - self.DOCK_ICON_WIDTH // 2,
                y=dock_y - self.DOCK_ICON_HEIGHT // 2,
                width=self.DOCK_ICON_WIDTH,
                height=self.DOCK_ICON_HEIGHT,
                confidence=0.4,  # 低置信度
                source="fallback"
            )

        # 窗口关闭按钮（左上角）
        if "关闭" in desc_lower:
            return LocatorResult(
                success=True,
                x=self.CLOSE_BUTTON_X,
                y=self.CLOSE_BUTTON_Y,
                width=20,
                height=20,
                confidence=0.5,
                source="fallback"
            )

        # 搜索框（通常在顶部或左侧）
        if "搜索" in desc_lower:
            # 估算搜索框位置（窗口顶部）
            return LocatorResult(
                success=True,
                x=int(screen_w * 0.1),
                y=int(screen_h * 0.05),
                width=200,
                height=30,
                confidence=0.3,
                source="fallback"
            )

        return LocatorResult(
            success=False,
            error="无法估算坐标",
            source="fallback"
        )


class SmartLocator:
    """
    智能定位管理器

    按优先级尝试多种定位策略
    """

    def __init__(self):
        self.locators = [
            AccessibilityLocator(),  # 1. 首选
            OcrLocator(),            # 2. 文字定位
            ColorLocator(),          # 3. 颜色定位
            FallbackLocator(),       # 4. 坐标估算兜底
            AILocator(),             # 5. AI 兜底
        ]
        self.screen_size = self._get_screen_size()

    def _get_screen_size(self) -> Tuple[int, int]:
        """获取屏幕尺寸"""
        try:
            import pyautogui
            return pyautogui.size()
        except Exception:
            return (1440, 900)

    def locate(self, description: str,
               prefer_source: str = None) -> LocatorResult:
        """
        智能定位目标

        Args:
            description: 目标描述，如"发送按钮"、"苦尘"
            prefer_source: 优先使用的定位方式

        Returns:
            LocatorResult 定位结果
        """
        results = []

        # 按优先级尝试
        for locator in self.locators:
            if prefer_source and locator.__class__.__name__.lower() != prefer_source.lower():
                continue

            # 检查是否能处理
            if not locator.can_handle(description):
                continue

            # 执行定位
            result = locator.find(description)
            results.append(result)

            if result.success:
                return result

        # 全部失败，返回错误信息
        return LocatorResult(
            success=False,
            error=f"所有定位方式都失败：{description}",
            source="all"
        )

    def locate_with_ai_verify(self, description: str,
                               max_attempts: int = 3) -> LocatorResult:
        """
        定位并使用 AI 验证

        闭环流程：
        1. 用各种方式获取坐标
        2. 移动鼠标到目标位置
        3. 截图让 AI 确认位置对不对
        4. 不对则修正坐标，重试
        """
        # 先获取初始坐标
        result = self.locate(description)

        if not result.success:
            # 定位失败，需要 AI 从头开始
            return result

        # TODO: 实现 AI 验证闭环
        # 这个需要 AI 参与，在 control.py 中实现

        return result


def main():
    """测试定位器"""
    import argparse

    parser = argparse.ArgumentParser(description="目标定位器")
    parser.add_argument("description", help="目标描述，如'发送按钮'、'苦尘'")
    parser.add_argument("--prefer", choices=["accessibility", "ocr", "color", "ai"],
                        help="优先使用的定位方式")

    args = parser.parse_args()

    locator = SmartLocator()
    result = locator.locate(args.description, args.prefer)

    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
