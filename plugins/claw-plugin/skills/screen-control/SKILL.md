---
name: screen-control
description: 'Use when the user asks to inspect or control the visible desktop GUI: click, type, open/switch/minimize apps or windows, navigate app screens, fill forms, take screenshots, verify dialogs or on-screen state, or handle vague requests like "点那个按钮" or "看看屏幕". Do not use for pure code, file edits, terminal commands, web search, or conceptual Q&A.'
---

# 屏幕控制技能

## ⚠️ 前置条件检查

**首次使用本技能时，必须先验证视觉能力可用性：**

```bash
# 1. 截取屏幕
python scripts/sensor.py snapshot --output /tmp/test_vision.png

# 2. 用 Read 工具查看截图
Read /tmp/test_vision.png
```

- 如果 Read 返回空或报错 → 视觉不可用 → 告知用户技能无法使用
- 如果 Read 能看到屏幕内容 → 视觉可用 → 继续操作

---

## 核心理念

```
传统方式：AI 看图估算坐标 → 点击（不精确、无验证）
本技能：多策略精确定位 → 移动鼠标 → AI 确认 → 对才点/错就改
```

**关键优化**：
1. **精确定位** - 优先使用 Accessibility API 获取像素级坐标，而非 AI 估算
2. **执行前校验** - 点击前截图让 AI 确认"鼠标指的对不对"，形成闭环

---

## 快速开始

### 智能点击（推荐）

```bash
# 自动定位并点击"发送按钮"
python3 control.py smart-click "发送按钮"

# 跳过验证直接点击（更快，但可能点错）
python3 control.py smart-click "发送按钮" --no-verify
```

### 完整操作流程

```
1. 获取画面 → sensor.py snapshot --output /tmp/frame.png
2. AI 看图分析 → Read /tmp/frame.png → 识别场景、元素
3. 智能定位 → control.py smart-click "目标"
   - 内部流程:
     a. 用 Accessibility API / OCR / 颜色 / AI 定位坐标
     b. 移动鼠标到目标位置
     c. 截图让 AI 确认位置对不对
     d. AI 说对 → 点击 / AI 说错 → 修正坐标重试
4. 等待结果 → sensor.py wait --for change --timeout 5 --output /tmp/after.png
5. 验证 → Read /tmp/after.png → 确认操作生效
```

**无需手动停止** — 按需工作，无后台进程。

---

## 命令速查

| 类别 | 命令 | 用途 | 示例 |
|------|------|------|------|
| **智能命令** | `smart-click` | 智能定位并点击 | `python3 control.py smart-click "发送按钮"` |
| | `smart-click --no-verify` | 跳过验证直接点击 | `... "发送按钮" --no-verify` |
| | `locate` | 只定位不点击 | `python3 control.py locate "企业微信图标"` |
| | `open-app` | 系统级打开应用 | `python3 control.py open-app "企业微信"` |
| **传感器** | `snapshot` | 单帧快照 | `python3 sensor.py snapshot --output frame.png` |
| | `wait --for stable` | 等待画面稳定 | `python3 sensor.py wait --for stable --timeout 15` |
| | `wait --for change` | 等待画面变化 | `python3 sensor.py wait --for change --timeout 5` |
| | `sequence` | 捕获帧序列 | `python3 sensor.py sequence --count 10 --output-dir ./frames/` |
| **控制** | `click [x] [y]` | 鼠标点击 | `python3 control.py click 100 200` |
| | `click --verify` | 点击并验证变化 | `python3 control.py click 100 200 --verify` |
| | `double-click` / `drag` / `scroll` | 双击/拖拽/滚动 | `python3 control.py drag 100 200 300 400` |
| | `type` / `hotkey` / `wait` | 输入/快捷键/等待 | `python3 control.py type "你好"` |

---

## 定位策略详解

技能按优先级尝试以下定位方式，**置信度 < 0.7 一律进入验证流程**。

### 策略优先级总览

| 优先级 | 策略 | 置信度 | 适用场景 | 切换条件 |
|-------|------|--------|---------|---------|
| 1 | Accessibility API | 0.8-1.0 | 原生应用、Electron | 失败或<0.7 切 OCR |
| 2 | OCR 文字定位 | 0.6-0.9 | 有文字的元素 | 无文字或<0.5 切颜色 |
| 3 | 颜色特征定位 | 0.5-0.8 | 应用图标 | 无特征切坐标估算 |
| 4 | 坐标估算 | 0.3-0.5 | Dock 栏、窗口控件 | 必须验证 |
| 5 | AI 视觉定位 | 0.4-0.7 | 最终兜底 | 必须验证 |

### 各策略要点

**1. Accessibility API（首选）**
- 依赖：`pip install pyobjc-core pyobjc-framework-Cocoa`
- 需要：辅助功能权限
- 跳过：目标明显是网页内容时

**2. OCR 文字定位**
- 依赖：`brew install tesseract` + `pip install pytesseract`
- 检查：`tesseract --version` 和 `tesseract --list-langs | grep chi`
- 跳过：目标不是文字时

**3. 颜色特征定位**
- 预定义：微信 (绿)、企业微信 (青绿)、钉钉 (蓝)
- 跳过：同颜色区域>5 个时

**4. 坐标估算兜底**
- Dock 栏：屏幕底部居中 10% 区域
- 关闭按钮：窗口左上角 (0-50, 0-50)
- 必须验证

**5. AI 视觉定位**
- AI 输出必须包含 reasoning
- 置信度 ≤ 0.7 必须验证，< 0.4 建议用户手动确认

> 策略切换决策树见 `references/strategy.md`

## 执行前校验闭环

这是本技能的核心改进。

### 闭环流程

```
1. 获取坐标 → 2. 移动鼠标 → 3. 截图标记 → 4. AI 验证 → 5. 点击
                ↓                    ↓
           不匹配则修正坐标 ←──  match? no_match
                (最多重试 3 次)
```

### AI 验证输出规范

**输入**：
```json
{
  "action": "ai_verify",
  "image": "/tmp/verify_marked.png",
  "target": "发送按钮",
  "prompt": "红圈/鼠标指针中心位置是不是'发送按钮'？请回答 match 或 no_match"
}
```

**AI 必须返回的格式**：

1. **匹配（位置正确）**：
   ```json
   {"match": true}
   ```

2. **不匹配（需要修正）**：
   ```json
   {
     "match": false,
     "reason": "红圈中心是取消按钮，不是发送按钮",
     "correction": {
       "x": 1234,
       "y": 567,
       "confidence": 0.8
     }
   }
   ```

3. **无法判断（需要人工确认）**：
   ```json
   {
     "match": null,
     "reason": "截图太模糊，无法辨认目标元素",
     "suggestion": "建议使用 OCR 或 Accessibility API 重新定位"
   }
   ```

### 验证重试策略

| 重试次数 | 置信度要求 | 行为 |
|---------|-----------|------|
| 第 1 次失败 | 任何 no_match | 采用 AI 修正坐标，立即重试 |
| 第 2 次失败 | 任何 no_match | 采用 AI 修正坐标，再次重试 |
| 第 3 次失败 | 任何 no_match | 停止自动重试，向用户报告并询问下一步 |

**提前终止条件**（满足任一即停止）：
- AI 返回 `{"match": null}` 且建议换方法 → 终止并报告用户
- 连续 2 次修正坐标相同 → 可能进入死循环，终止并报告
- 定位置信度 < 0.3 → 直接使用 AI 视觉兜底，跳过验证

### 什么时候可以跳过验证

**可以跳过验证的情况**（`--no-verify`）：

| 场景 | 理由 |
|------|------|
| Accessibility API 置信度 ≥ 0.9 | 系统级 API 非常可靠 |
| 用户明确说坐标正确 | 用户已确认位置 |
| 简单重复点击（已验证过多次） | 同一元素连续点击 |
| 紧急操作/快速演示 | 速度优先于精确度 |

**绝对不能跳过验证的情况**：

| 场景 | 理由 |
|------|------|
| 首次操作某元素 | 位置未经验证 |
| 关键操作（删除、提交、支付） | 错误后果严重 |
| AI 定位（置信度 < 0.7） | AI 估算可能不准 |
| 坐标估算兜底 | 置信度最低 |
| 之前点击失败过 | 说明位置可能不对 |

---

## 典型场景示例

**场景 1：打开应用并发消息**
```
1. smart-click "企业微信" → 2. wait --for stable → 3. smart-click "搜索"
4. type "苦尘" → 5. smart-click "苦尘" → 6. type "hello" → 7. hotkey "enter"
```

**场景 2：处理弹窗**
```
1. snapshot --output /tmp/frame.png → 2. smart-click "确定" → 3. wait --for change
```

> 更多场景参见 `references/scenarios.md`

---

## 错误处理与重试

### 错误分类与恢复策略

| 错误类型 | 现象 | 恢复策略 |
|---------|------|---------|
| **定位错误** | 未找到目标/多个匹配 | 降级策略：AX → OCR → 颜色 → AI 视觉 |
| **验证错误** | AI 总说不匹配/死循环 | 采用修正坐标，最多 3 次，失败则终止 |
| **执行错误** | 点击无反应/输入错误 | 截图确认，重试或换快捷键/剪贴板方式 |
| **权限错误** | 截图黑屏/操作无响应 | 引导用户授权（屏幕录制/辅助功能） |

**终止条件**（满足任一立即停止）：
- 连续 3 次验证失败  |  连续 2 次修正坐标相同  |  AI 建议换方法  |  耗时>30 秒

**何时放弃**：权限错误未解决、所有策略置信度<0.3、关键操作多次失败

> 详细排查指南见 `references/troubleshooting.md`

---

## 拟人化操作建议

### 等待策略

| 操作类型 | 建议做法 |
|---------|---------|
| 简单点击 | 操作后 `wait --for change` |
| 打开应用 | `wait --for stable --timeout 5` |
| 加载页面 | `wait --for stable --timeout 15` |
| 动画过渡 | `wait --for stable` |

### 输入策略

分段输入更自然：
```bash
python3 control.py type "这是一段"
python3 control.py wait 0.3
python3 control.py type "很长的"
python3 control.py wait 0.3
python3 control.py type "文字内容..."
```

---

## 安全与权限

### macOS 权限

首次使用需授权：
- **屏幕录制**：系统偏好设置 → 安全性与隐私 → 隐私 → 屏幕录制
- **辅助功能**：系统偏好设置 → 安全性与隐私 → 隐私 → 辅助功能

### 紧急停止

操作失控时：
1. 移动鼠标到屏幕左上角（触发 FAILSAFE）
2. 在终端按 `Ctrl+C`

---

## 测试用例

**基础测试**（T01-T08）：点击系统应用、Dock 图标、文字按钮、图标按钮、填写表单、关闭窗口、处理弹窗、打开应用

**进阶测试**（T10-T14）：多步操作、跨应用操作、动态内容、错误恢复、多显示器

> 完整测试用例与评估标准见 `tests/evals.md`

## 参考文档

- `references/element-guide.md` - UI 元素识别指南
- `references/troubleshooting.md` - 问题排查指南
