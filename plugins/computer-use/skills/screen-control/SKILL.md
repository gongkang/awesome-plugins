---
name: screen-control
description: 'Use when the user asks to inspect or control the visible desktop GUI: click, type, open/switch/minimize apps or windows, navigate app screens, fill forms, take screenshots, verify dialogs or on-screen state, or handle vague requests like "点那个按钮" or "看看屏幕". Do not use for pure code, file edits, terminal commands, web search, or conceptual Q&A.'
---

# 屏幕控制技能

## 工作原理

```
截图感知 → AI 识别场景 → 智能定位坐标 → 执行前校验(移动→AI确认→点击) → 等待结果验证
```

定位策略按优先级自动降级：
1. **Accessibility API** — macOS 系统 UI 树访问，最精确
2. **OCR 文字定位** — 识别屏幕文字位置
3. **颜色特征定位** — 匹配已知应用图标颜色
4. **云端视觉定位** — 多模态模型返回 bbox（需配置 API key）
5. **坐标估算兜底** — 基于常识估算位置
6. **AI 视觉定位** — 最终兜底，必须验证

## 快速开始

### 智能点击（推荐）

```bash
# 自动定位目标并点击，默认点击前 AI 验证
python3 control.py smart-click "发送按钮"

# 跳过验证直接点击（更快但可能点错）
python3 control.py smart-click "发送按钮" --no-verify
```

### 完整操作流程

```
1. 截取当前屏幕 → sensor.py snapshot --output /tmp/frame.png
2. AI 看图分析 → Read /tmp/frame.png，识别场景和 UI 元素
3. 智能点击 → control.py smart-click "目标"
   内部流程：多种策略定位坐标 → 移动鼠标 → 截图让 AI 确认 → 对就点/错就改
4. 等待变化 → sensor.py wait --for change --timeout 5 --output /tmp/after.png
5. 验证结果 → Read /tmp/after.png，确认操作生效
```

## 命令速查

| 命令 | 用途 | 示例 |
|------|------|------|
| `smart-click "目标"` | 智能定位并点击 | `python3 control.py smart-click "发送按钮"` |
| `smart-click "目标" --no-verify` | 跳过验证直接点击 | `python3 control.py smart-click "发送按钮" --no-verify` |
| `locate "目标"` | 只定位返回坐标 | `python3 control.py locate "企业微信图标"` |
| `locate "目标" --prefer 方式` | 指定定位方式 | `python3 control.py locate "搜索" --prefer ocr` |
| `open-app "应用名"` | 系统级打开应用 | `python3 control.py open-app "企业微信"` |
| `snapshot --output file` | 截取屏幕 | `python3 sensor.py snapshot --output /tmp/frame.png` |
| `wait --for stable` | 等待画面稳定 | `python3 sensor.py wait --for stable --timeout 15` |
| `wait --for change` | 等待画面变化 | `python3 sensor.py wait --for change --timeout 5` |
| `click X Y` | 点击坐标 | `python3 control.py click 100 200` |
| `double-click X Y` | 双击坐标 | `python3 control.py double-click 100 200` |
| `drag X1 Y1 X2 Y2` | 拖拽 | `python3 control.py drag 100 200 300 400` |
| `type "文字"` | 输入文字 | `python3 control.py type "你好"` |
| `clear-and-type "文字"` | 清空后输入 | `python3 control.py clear-and-type "你好"` |
| `hotkey "cmd+key"` | 快捷键 | `python3 control.py hotkey "cmd+a"` |
| `wait N` | 等待 N 秒 | `python3 control.py wait 0.5` |
| `verify --mode stable` | 等待画面稳定 | `python3 control.py verify --mode stable` |
| `verify --mode change` | 等待画面变化 | `python3 control.py verify --mode change --timeout 5` |

## 执行前校验闭环

核心机制：点击前移动鼠标到目标位置，截图让 AI 确认位置是否正确。

```
获取坐标 → 移动鼠标 → 截图标记 → AI 验证 → 匹配则点击，不匹配则修正坐标重试
                                                        ↓ (最多 3 次)
                                                 仍失败 → 终止并向用户报告
```

### 什么时候可以跳过验证

| 可跳过 | 必须验证 |
|--------|---------|
| Accessibility API 置信度 ≥ 0.9 | 首次操作某个元素 |
| 用户明确确认过坐标 | 删除/提交/支付等关键操作 |
| 连续点击同一已验证元素 | AI 定位或坐标估算兜底 |
| 快速演示场景 | 之前点击失败过 |

### 终止条件

连续 3 次验证失败 | 连续 2 次修正坐标相同 | AI 建议换方法 | 总耗时 > 30 秒

## 典型场景示例

**打开应用并发送消息**：
```
smart-click "企业微信" → wait --for stable → smart-click "搜索"
→ type "苦尘" → smart-click "苦尘" → type "hello" → hotkey "enter"
```

**处理弹窗**：
```
snapshot --output /tmp/frame.png → smart-click "确定" → wait --for change
```

**填写表单**：
```
smart-click "用户名输入框" → type "user123"
→ smart-click "密码输入框" → type "pass456"
→ smart-click "登录按钮" → wait --for change
```

## 权限要求

首次使用需授权（macOS）：
- **屏幕录制**：系统偏好设置 → 安全性与隐私 → 隐私 → 屏幕录制
- **辅助功能**：系统偏好设置 → 安全性与隐私 → 隐私 → 辅助功能

授权后需重启终端生效。测试方法：
```bash
python3 sensor.py snapshot --output /tmp/test.png
Read /tmp/test.png
```
如果 Read 能看到屏幕内容，说明权限正常。

## 紧急停止

操作失控时：
1. 移动鼠标到屏幕左上角（触发 pyautogui FAILSAFE）
2. 在终端按 `Ctrl+C`

## 等待策略

| 场景 | 做法 |
|------|------|
| 点击后等待响应 | `wait --for change --timeout 5` |
| 打开应用等待加载 | `wait --for stable --timeout 5` |
| 页面加载完成 | `wait --for stable --timeout 15` |

## 输入建议

中文输入自动使用剪贴板粘贴，无需额外操作。长文本建议分段输入，更自然：
```bash
python3 control.py type "这是一段"
python3 control.py wait 0.3
python3 control.py type "很长的文字..."
```

## 参考文档

- `references/element-guide.md` — UI 元素识别指南（按钮、输入框、弹窗等识别）
- `references/troubleshooting.md` — 问题排查指南（权限、坐标、输入等常见错误）
