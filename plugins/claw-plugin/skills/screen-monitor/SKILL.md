---
name: screen-monitor
description: |
  屏幕监控 - 持续感知屏幕变化，自动检测异常或指定事件。

  【何时触发此技能】
  当用户的请求涉及以下任一情况时，触发此技能：

  - **持续监控**："帮我盯着这个页面"、"监控屏幕变化"
  - **异常检测**："有弹窗就告诉我"、"出错时通知我"
  - **条件触发**："股价涨到 100 告诉我"、"看到 XX 就..."
  - **操作录制**："帮我录制这个操作过程"、"记录我做了什么"
  - **定时截图**："每分钟截个图"、"定期保存屏幕状态"

  与 screen-control 的区别：监控是"看着"，控制是"操作"。
---

# 屏幕监控技能

## 核心理念

```
screen-control：按需抓帧 → 分析 → 操作
screen-monitor：持续录屏 → 检测变化 → 触发响应
```

**核心能力**：
- 持续感知：后台录屏，维护时序帧缓冲
- 智能检测：变化检测、相似度分析、关键帧提取
- 条件响应：检测到指定条件时执行动作

---

## 快速开始

### 场景 1：监控变化

```bash
# 启动监控（后台运行）
python scripts/monitor.py start --fps 5 --buffer 10

# 查看状态
python scripts/monitor.py status

# 获取最新关键帧
python scripts/monitor.py keyframe --output /tmp/latest.png

# 停止监控
python scripts/monitor.py stop
```

### 场景 2：等待条件

```bash
# 等待画面变化（阻塞式）
python scripts/monitor.py wait-change --timeout 60 --output /tmp/changed.png

# 等待画面稳定
python scripts/monitor.py wait-stable --timeout 30

# 等待特定文字出现
python scripts/monitor.py wait-text "成功" --timeout 60
```

### 场景 3：录制操作

```bash
# 开始录制
python scripts/monitor.py record start --output ./recording/

# 执行你的操作...

# 停止录制
python scripts/monitor.py record stop

# 生成的文件：
# ./recording/
# ├── frame_000.png
# ├── frame_001.png
# ├── ...
# └── metadata.json
```

---

## 命令速查

### 监控控制

| 命令 | 用途 | 示例 |
|------|------|------|
| `start` | 启动后台监控 | `python scripts/monitor.py start --fps 5` |
| `stop` | 停止监控 | `python scripts/monitor.py stop` |
| `status` | 查看运行状态 | `python scripts/monitor.py status` |
| `keyframe` | 获取关键帧 | `python scripts/monitor.py keyframe --output kf.png` |
| `recent` | 获取最近 N 帧 | `python scripts/monitor.py recent --count 5 --output-dir ./frames/` |

### 条件等待

| 命令 | 用途 | 示例 |
|------|------|------|
| `wait-change` | 等待画面变化 | `python scripts/monitor.py wait-change --timeout 60` |
| `wait-stable` | 等待画面稳定 | `python scripts/monitor.py wait-stable --timeout 30` |
| `wait-text` | 等待文字出现 | `python scripts/monitor.py wait-text "完成" --timeout 120` |
| `wait-region` | 等待区域变化 | `python scripts/monitor.py wait-region 100,100,200,50 --timeout 30` |

### 录制

| 命令 | 用途 | 示例 |
|------|------|------|
| `record start` | 开始录制 | `python scripts/monitor.py record start --output ./demo/` |
| `record stop` | 停止录制 | `python scripts/monitor.py record stop` |
| `record status` | 录制状态 | `python scripts/monitor.py record status` |

---

## 命令详解

### start - 启动后台监控

启动持续录屏，维护帧缓冲区。

```bash
python scripts/monitor.py start --fps 5 --buffer 10 --region 0,0,1920,1080
```

**参数**：
- `--fps`：采样帧率，默认 5
- `--buffer`：缓冲时长（秒），默认 10
- `--region`：监控区域 `x,y,w,h`，默认全屏
- `--threshold`：变化检测阈值，默认 0.05

**输出**：
```json
{
  "status": "started",
  "fps": 5.0,
  "buffer_seconds": 10.0,
  "pid": 12345
}
```

### stop - 停止监控

```bash
python scripts/monitor.py stop
```

**输出**：
```json
{
  "status": "stopped",
  "total_frames": 1523,
  "runtime_seconds": 305
}
```

### status - 查看状态

```bash
python scripts/monitor.py status
```

**输出**：
```json
{
  "running": true,
  "fps": 5.0,
  "buffer_seconds": 10.0,
  "frames_in_buffer": 50,
  "total_frames": 1523,
  "runtime_seconds": 305,
  "last_change": 2.5,
  "cpu_percent": 2.3,
  "memory_mb": 45
}
```

### keyframe - 获取关键帧

从缓冲区提取最具代表性的帧。

```bash
python scripts/monitor.py keyframe --output /tmp/kf.png
```

**参数**：
- `--output`：输出文件路径
- `--mode`：提取模式 `latest|stable|changed`，默认 `latest`

**输出**：
```json
{
  "status": "success",
  "output": "/tmp/kf.png",
  "frame_age_seconds": 0.2,
  "stable": true
}
```

### wait-change - 等待变化

阻塞等待画面发生变化。

```bash
python scripts/monitor.py wait-change --timeout 60 --output /tmp/changed.png
```

**参数**：
- `--timeout`：超时时间，默认 60 秒
- `--threshold`：变化阈值，默认 0.05
- `--output`：变化后保存帧

**输出**：
```json
{
  "status": "changed",
  "elapsed": 12.5,
  "similarity": 0.82,
  "output": "/tmp/changed.png"
}
```

### wait-text - 等待文字出现

阻塞等待指定文字在屏幕上出现。

```bash
python scripts/monitor.py wait-text "登录成功" --timeout 120 --output /tmp/found.png
```

**参数**：
- 文字：要检测的文字
- `--timeout`：超时时间
- `--region`：检测区域
- `--output`：找到后保存帧

**输出**：
```json
{
  "status": "found",
  "elapsed": 8.3,
  "text": "登录成功",
  "bounds": [100, 200, 200, 230],
  "confidence": 0.95,
  "output": "/tmp/found.png"
}
```

### record - 录制操作

录制操作过程，保存帧序列。

```bash
# 开始录制
python scripts/monitor.py record start --output ./demo/ --fps 10

# 执行操作...

# 停止录制
python scripts/monitor.py record stop
```

**参数**：
- `--output`：输出目录
- `--fps`：录制帧率
- `--only-changes`：只保存有变化的帧

**生成的 metadata.json**：
```json
{
  "start_time": "2024-03-20T10:30:00",
  "end_time": "2024-03-20T10:32:30",
  "total_frames": 150,
  "duration_seconds": 150,
  "fps": 10,
  "frames": [
    {"file": "frame_000.png", "timestamp": 0.0, "changed": true},
    {"file": "frame_001.png", "timestamp": 0.1, "changed": false},
    ...
  ]
}
```

---

## 典型场景示例

### 场景 1：监控异常弹窗

```
用户：帮我盯着这个页面，有错误弹窗就告诉我

执行步骤：

1. python scripts/monitor.py start --fps 2 --buffer 30
2. 定期检查关键帧：
   - python scripts/monitor.py keyframe --output /tmp/check.png
   - [看图] 检查是否有错误弹窗
3. 发现弹窗时通知用户
4. python scripts/monitor.py stop
```

### 场景 2：等待下载完成

```
用户：帮我等下载完成

执行步骤：

1. python scripts/monitor.py wait-stable --timeout 300 --output /tmp/done.png
   # 等待画面稳定（下载进度条消失）
2. [看图] 确认下载完成
```

### 场景 3：录制操作教程

```
用户：帮我录制这个操作过程

执行步骤：

1. python scripts/monitor.py record start --output ./tutorial/ --fps 5
2. 用户执行操作...
3. python scripts/monitor.py record stop
4. 生成的帧序列可用于制作教程
```

### 场景 4：等待特定文字

```
用户：帮我等页面显示"处理完成"

执行步骤：

1. python scripts/monitor.py wait-text "处理完成" --timeout 600 --output /tmp/done.png
2. 自动等待并检测
3. 检测到后返回结果
```

---

## 与 screen-control 的协作

两个技能可以配合使用：

```
用户：帮我监控这个页面，有弹窗就点掉它

screen-monitor 负责：
1. 持续监控页面变化
2. 检测到弹窗时通知

screen-control 负责：
3. 分析弹窗内容
4. 点击关闭按钮
```

---

## 性能优化

### 帧率选择

| 场景 | 推荐帧率 | 理由 |
|------|---------|------|
| 静态页面监控 | 1-2 fps | 页面很少变化，低帧率够用 |
| 常规监控 | 5 fps | 平衡性能和响应速度 |
| 快速变化场景 | 10-15 fps | 捕捉快速变化 |
| 录制操作 | 10 fps | 流畅回放 |

### 缓冲时长

| 场景 | 推荐时长 | 理由 |
|------|---------|------|
| 即时响应 | 5 秒 | 减少内存占用 |
| 常规监控 | 10-30 秒 | 保留足够历史帧 |
| 长时间监控 | 60 秒 | 更长的回溯能力 |

### 内存估算

```
单帧大小 ≈ 屏幕分辨率 × 压缩率
1920x1080 缩放到 640 长边 ≈ 50-100KB

缓冲内存 ≈ 帧数 × 单帧大小
5fps × 10秒 × 100KB ≈ 5MB
```

---

## 安全与权限

### macOS 权限

首次使用需授权：
- **屏幕录制**：系统偏好设置 → 安全性与隐私 → 隐私 → 屏幕录制

### 资源管理

长时间运行注意：
- 监控 CPU/内存占用
- 定期检查缓冲区大小
- 必要时降低帧率

---

## 参考文档

- `references/troubleshooting.md` - 问题排查指南
- `references/detection-algorithms.md` - 检测算法说明