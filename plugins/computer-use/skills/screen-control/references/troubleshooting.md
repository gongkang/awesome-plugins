# 问题排查指南

## 权限问题

### macOS

#### 屏幕录制权限
**症状**：截图返回黑屏或空白

**解决**：
1. 打开"系统偏好设置" → "安全性与隐私" → "隐私"
2. 选择"屏幕录制"
3. 勾选 Terminal 或运行脚本的应用

#### 辅助功能权限
**症状**：鼠标/键盘操作无响应

**解决**：
1. 打开"系统偏好设置" → "安全性与隐私" → "隐私"
2. 选择"辅助功能"
3. 添加 Terminal 或 Python 到允许列表
4. 可能需要重启应用

### Windows
通常不需要特殊权限，但某些安全软件可能拦截自动化操作。

### Linux
需要 X11 或 Wayland 的相应权限。

---

## 常见错误

### 1. 传感器无法启动

**错误信息**：
```
{"error": "无法初始化屏幕捕获"}
```

**可能原因**：
- 没有显示器连接
- 权限未授权
- mss 库安装问题

**解决步骤**：
```bash
# 检查 mss 是否正常
python -c "import mss; print(mss.mss().monitors)"

# 重新安装依赖
pip install --upgrade mss
```

### 2. 点击坐标不正确

**症状**：点击位置与预期不符

**可能原因**：
- 多显示器配置
- 显示缩放（Retina / HiDPI）
- 坐标估算错误

**解决步骤**：
```bash
# 检查屏幕尺寸
python -c "import pyautogui; print(pyautogui.size())"

# 检查 mss 检测的显示器
python -c "import mss; print(mss.mss().monitors)"
```

**调整**：
- 如果有缩放，需要乘以缩放比例
- 多显示器时，坐标是全局的

### 3. 中文输入失败

**症状**：中文显示为乱码或不显示

**可能原因**：
- 输入法未切换
- 剪贴板问题

**解决步骤**：
```bash
# 确保安装了 pyperclip
pip install pyperclip

# 测试剪贴板
python -c "import pyperclip; pyperclip.copy('测试'); print(pyperclip.paste())"
```

**替代方案**：
- 先切换到中文输入法
- 使用 `type` 命令会自动用剪贴板处理中文

### 4. 帧缓冲区为空

**错误信息**：
```
{"error": "缓冲区为空"}
```

**可能原因**：
- 传感器未启动
- 刚启动还没来得及捕获帧

**解决步骤**：
```bash
# 检查状态
python scripts/sensor.py status

# 如果 running=true 但 frames_in_buffer=0
# 等待 1 秒后重试
```

### 5. 画面变化检测不灵敏

**症状**：页面已变化但报告稳定

**解决**：
- 降低 `change_threshold`（在 config.py 中）
- 提高帧率以获得更密集的采样

### 6. 画面变化检测过于敏感

**症状**：静止页面报告有变化

**解决**：
- 提高 `change_threshold`
- 检查是否有动态内容（广告、动画背景）

---

## 性能问题

### CPU 占用过高

**原因**：帧率设置过高

**解决**：
```bash
# 降低帧率
python scripts/sensor.py start --fps 2
```

### 内存占用过高

**原因**：缓冲时长设置过长

**解决**：
```bash
# 减少缓冲时长
python scripts/sensor.py start --buffer 2
```

### 操作延迟

**原因**：
- 网络延迟（如果涉及远程）
- 系统负载过高
- pyautogui 的 PAUSE 设置

**解决**：
```python
# 在 control.py 中调整
pyautogui.PAUSE = 0.01  # 默认 0.05
```

---

## 调试技巧

### 查看当前鼠标位置

```bash
python -c "import pyautogui; print(pyautogui.position())"
```

### 查看指定坐标的颜色

```bash
python -c "import pyautogui; print(pyautogui.pixel(100, 200))"
```

### 截图保存当前屏幕

```python
import mss
with mss.mss() as sct:
    sct.shot(output="debug.png")
```

### 检查帧缓冲内容

```python
import pickle
# 在 sensor.py 中添加调试代码保存缓冲区
# 然后加载并检查
```

---

## 紧急情况

### 操作失控

1. **移动鼠标到屏幕左上角**（触发 pyautogui 的 FAILSAFE）
2. **按 Ctrl+C**（如果脚本在前台）
3. **杀死进程**：
   ```bash
   # 查找 PID
   cat /tmp/screen_sensor.pid

   # 杀死
   kill <pid>
   ```

### 完全无响应

```bash
# 强制杀死所有 Python 进程（谨慎使用）
pkill -9 python
```