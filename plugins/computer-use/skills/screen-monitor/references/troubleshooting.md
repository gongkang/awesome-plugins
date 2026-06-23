# 问题排查指南

## 权限问题

### macOS

#### 屏幕录制权限
**症状**：截图返回黑屏或空白

**解决**：
1. 打开"系统偏好设置" → "安全性与隐私" → "隐私"
2. 选择"屏幕录制"
3. 勾选 Terminal 或运行脚本的应用

### Windows
通常不需要特殊权限，但某些安全软件可能拦截。

### Linux
需要 X11 或 Wayland 的相应权限。

---

## 常见错误

### 1. 监控无法启动

**错误信息**：
```json
{"error": "无法初始化屏幕捕获"}
```

**解决步骤**：
```bash
# 检查 mss 是否正常
python -c "import mss; print(mss.mss().monitors)"

# 重新安装依赖
pip install --upgrade mss
```

### 2. 监控已在运行

**症状**：start 返回 "already_running"

**解决**：
```bash
# 查看状态
python scripts/monitor.py status

# 停止现有监控
python scripts/monitor.py stop

# 如果无法停止，手动清理
rm /tmp/screen_monitor.pid /tmp/screen_monitor_state.json
```

### 3. 缓冲区为空

**错误信息**：
```json
{"error": "缓冲区为空"}
```

**解决**：
```bash
# 检查状态
python scripts/monitor.py status

# 如果 running=true 但 frames_in_buffer=0
# 等待 1-2 秒后重试
```

### 4. 帧差异检测不灵敏

**症状**：页面已变化但未检测到

**解决**：
- 降低阈值：`--threshold 0.02`
- 提高帧率：`--fps 10`

### 5. 帧差异检测过于敏感

**症状**：静止页面报告有变化

**解决**：
- 提高阈值：`--threshold 0.1`
- 检查是否有动态内容（广告、动画）

---

## 性能问题

### CPU 占用过高

**解决**：
```bash
# 降低帧率
python scripts/monitor.py start --fps 2
```

### 内存占用过高

**解决**：
```bash
# 减少缓冲时长
python scripts/monitor.py start --buffer 5
```

---

## 调试技巧

### 查看监控状态

```bash
python scripts/monitor.py status
```

### 检查缓冲区内容

```bash
# 获取最近的帧
python scripts/monitor.py recent --count 5 --output-dir /tmp/debug/
```

### 手动获取关键帧

```bash
python scripts/monitor.py keyframe --output /tmp/debug.png
```

---

## 紧急情况

### 监控失控

1. **按 Ctrl+C**（如果在前台）
2. **停止监控**：
   ```bash
   python scripts/monitor.py stop
   ```
3. **手动清理**：
   ```bash
   rm /tmp/screen_monitor.pid /tmp/screen_monitor_state.json
   ```

### 完全无响应

```bash
# 查找并杀死进程
cat /tmp/screen_monitor.pid
kill <pid>

# 清理文件
rm /tmp/screen_monitor.pid /tmp/screen_monitor_state.json
```