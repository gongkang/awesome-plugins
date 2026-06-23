---
name: screen-monitor
description: 'Use when the user asks to watch, monitor, observe, or track what happens on screen over time: "帮我盯着这个页面", "监控变化", "等下载完成", "等待文字出现", "检测弹窗", "录制操作过程", "持续观察屏幕", "等页面稳定", "录屏", "看屏幕有什么变化". For one-off actions like clicking, typing, or opening apps, use screen-control instead. If the user mentions screenshots + waiting + detecting changes, ALWAYS use this skill.'
---

# 屏幕监控技能

## 核心理念

```
screen-control：按需抓帧 → 分析 → 操作
screen-monitor：持续录屏 → 检测变化 → 触发响应
```

**核心能力**：
- 持续感知：后台录屏，维护时序帧缓冲
- 智能检测：感知哈希 + 汉明距离做变化检测、关键帧提取
- 条件响应：检测到变化/稳定/文字时触发动作

---

## 快速开始

### 监控变化

```bash
# 启动后台监控
python scripts/monitor.py start --fps 5 --buffer 10

# 查看状态 → 定期检查关键帧 → [看图判断]
python scripts/monitor.py keyframe --output /tmp/check.png

# 停止监控
python scripts/monitor.py stop
```

### 等待条件

```bash
# 等待画面变化（阻塞式）
python scripts/monitor.py wait-change --timeout 60 --output /tmp/changed.png

# 等待画面稳定（连续 3 帧相似即判定稳定）
python scripts/monitor.py wait-stable --timeout 30

# 等待特定文字出现（需要 pytesseract，见下方依赖说明）
python scripts/monitor.py wait-text "成功" --timeout 60
```

### 录制操作

```bash
python scripts/monitor.py record start --output ./recording/ --only-changes
# ... 执行操作 ...
python scripts/monitor.py record stop
# 生成 frame_NNNNN.png + metadata.json
```

---

## 命令速查

| 命令 | 用途 |
|------|------|
| `start [--fps N] [--buffer SEC] [--region x,y,w,h] [--threshold T]` | 启动后台监控，阻塞运行 |
| `stop` | 停止监控 |
| `status` | 查看运行状态（不阻塞） |
| `keyframe --output PATH [--mode latest|stable|changed]` | 提取关键帧 |
| `recent --count N --output-dir DIR` | 导出最近 N 帧 |
| `wait-change [--timeout SEC] [--threshold T] [--output PATH]` | 阻塞等待画面变化 |
| `wait-stable [--timeout SEC] [--threshold T] [--output PATH]` | 阻塞等待画面稳定 |
| `wait-text "文字" [--timeout SEC] [--output PATH]` | 阻塞等待文字出现 |
| `record start --output DIR [--fps N] [--only-changes]` | 开始录制 |
| `record stop` | 停止录制 |
| `record status` | 录制状态 |

---

## 典型场景

### 监控异常弹窗

```
用户：帮我盯着这个页面，有错误弹窗就告诉我

1. python scripts/monitor.py start --fps 2 --buffer 30 &
2. 循环：keyframe --output /tmp/check.png → [看图] 检查弹窗
3. 发现 → 通知用户
4. stop
```

### 等待下载/加载完成

```
用户：帮我等下载完成

python scripts/monitor.py wait-stable --timeout 300 --output /tmp/done.png
# 进度条消失、画面稳定后返回
# [看图] 确认完成
```

### 等待特定文字

```
用户：帮我等页面显示"处理完成"

python scripts/monitor.py wait-text "处理完成" --timeout 600 --output /tmp/done.png
```

### 录制操作教程

```
用户：帮我录制这个操作过程

1. python scripts/monitor.py record start --output ./tutorial/ --fps 5 --only-changes
2. 用户执行操作...
3. python scripts/monitor.py record stop
```

---

## 与 screen-control 配合

```
用户：帮我监控这个页面，有弹窗就点掉它

screen-monitor：
  1. start --fps 2 --buffer 30 &
  2. 循环 keyframe → 截帧
  3. [检测弹窗] → 保存截图路径

screen-control：
  4. 读取截图，OCR 识别关闭按钮位置
  5. 点击关闭按钮
  6. 返回步骤 2 继续监控
```

```
用户：帮我等下载完成，然后打开文件

screen-monitor：
  1. wait-stable --timeout 300 → 等进度条消失
  2. 返回完成截图

screen-control：
  3. 分析截图，定位文件
  4. 双击打开
```

---

## 依赖与权限

### Python 依赖

```bash
pip install mss opencv-python numpy
# wait-text 额外需要：
pip install pytesseract
brew install tesseract  # macOS
```

### macOS 权限

首次使用需授权屏幕录制权限：
系统偏好设置 → 安全性与隐私 → 隐私 → 屏幕录制 → 勾选 Terminal

### 配置文件

技能支持 `config.json`（放在技能根目录），可预设默认参数：

```json
{
  "default_fps": 5.0,
  "default_buffer_seconds": 10.0,
  "change_threshold": 0.05,
  "stable_threshold": 0.95,
  "region": null
}
```

CLI 参数优先级高于配置文件。

### 性能参考

| 场景 | 帧率 | 缓冲 | 内存估算 |
|------|------|------|---------|
| 静态页面 | 1-2 fps | 10s | ~1MB |
| 常规监控 | 5 fps | 10s | ~5MB |
| 录制操作 | 10 fps | N/A | 每帧 ~100KB |

内存估算：`帧数 × 单帧大小（640px 长边缩放过 ≈ 50-100KB）`

---

## 问题排查

详细排查见 `references/troubleshooting.md`，常见问题：

| 问题 | 解决 |
|------|------|
| 截图黑屏 | 授权屏幕录制权限 |
| already_running | `stop` 后重试，或清理 `/tmp/screen_monitor.pid` |
| 检测不灵敏 | 降低 `--threshold` 至 0.02 |
| 过于敏感 | 提高 `--threshold` 至 0.1 |
| CPU 过高 | 降低 `--fps` |
| wait-text 报错 | 安装 pytesseract + tesseract |
| 状态无 cpu/memory | 安装 psutil: `pip install psutil` |
