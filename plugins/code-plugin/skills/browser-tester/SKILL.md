---
name: browser-tester
description: 使用 chrome-devtools MCP 进行浏览器自动化测试。像测试工程师一样发现功能和 UI 问题，自动生成精简 Bug 报告并执行修复。支持前端、后端、全栈项目的可配置深度测试。
origin: Custom
---

# Browser Tester - 浏览器自动化测试技能

使用 chrome-devtools MCP 工具进行浏览器自动化测试，发现功能 bug 和 UI 问题，自动修复并验证。

## 何时使用

**使用此技能当：**
- 完成新功能开发，需要验证功能正常
- 准备发布前进行全面测试
- 收到 bug 报告，需要复现和验证
- 重构代码后确保没有回归问题
- 用户说"测试一下这个项目"、"找找 bug"、"检查功能是否正常"

**不适用：**
- 需要正式的 Playwright/E2E 测试套件（使用 e2e-testing 技能）
- 只需要单元测试或集成测试

## 核心工作流

```
1. 项目分析 → 2. 制定测试计划 → 3. 执行测试 → 4. 生成 Bug 报告 → 5. 自动修复 → 6. 验证修复
```

### 步骤 1: 项目分析

首先分析项目类型，决定测试策略：

```bash
# 检查项目结构
ls -la
cat package.json | grep -E '"(react|vue|angular|next|svelte)"'
cat requirements.txt | grep -E '(flask|django|fastapi)'
```

**项目类型判断：**

| 特征 | 类型 | 测试策略 |
|-----|------|---------|
| 有 frontend/ 或 src/ 含组件文件 | 前端项目 | 测试所有交互 + UI |
| 有 app.py/main.py 含路由定义 | 后端项目 | 测试 API 端点 |
| 同时有前后端目录 | 全栈项目 | 只通过前端测试 |

### 步骤 2: 制定测试计划

根据项目类型和测试深度生成测试计划：

**测试深度配置：**

| 深度 | 耗时 | 覆盖范围 |
|-----|------|---------|
| `quick` | 10-15 分钟 | 核心功能流程 |
| `standard` | 20-30 分钟 | 主要功能 + 常见边界 |
| `comprehensive` | 45-60 分钟 | 所有交互 + 边界情况 + 压力测试 |

**测试计划模板：**

```markdown
## 测试计划

**项目类型：** 前端项目
**测试深度：** standard
**预计耗时：** 25 分钟

### 测试覆盖

1. 页面加载测试
   - 首页 /
   - 主要功能页面

2. 交互测试
   - 表单提交
   - 按钮点击
   - 导航跳转

3. UI 测试
   - 响应式布局
   - 元素对齐
   - 文字渲染

4. 错误处理
   - 无效输入
   - 网络错误
   - 404 页面
```

### 步骤 3: 执行测试

使用 chrome-devtools MCP 工具执行测试：

#### 打开浏览器并导航

```bash
# 打开新页面
mcp__chrome-devtools__new_page url="http://localhost:3000"
```

#### 页面快照和检查

```bash
# 获取页面快照
mcp__chrome-devtools__take_snapshot

# 检查特定元素
mcp__chrome-devtools__hover uid="button-id"
mcp__chrome-devtools__click uid="button-id"
```

#### 表单交互

```bash
# 填写表单
mcp__chrome-devtools__fill uid="email-input" value="test@example.com"
mcp__chrome-devtools__fill uid="password-input" value="testpass123"

# 提交表单
mcp__chrome-devtools__click uid="submit-button"
```

#### 检查控制台错误

```bash
# 获取控制台消息
mcp__chrome-devtools__list_console_messages

# 获取特定错误详情
mcp__chrome-devtools__get_console_message msgid=123
```

#### 检查网络请求

```bash
# 列出网络请求
mcp__chrome-devtools__list_network_requests

# 获取特定请求详情
mcp__chrome-devtools__get_network_request reqid=456
```

#### 截图记录

```bash
# 页面截图
mcp__chrome-devtools__take_screenshot filePath="bugs/bug-001.png"

# 特定元素截图
mcp__chrome-devtools__take_screenshot uid="broken-element" filePath="bugs/bug-002.png"
```

### 步骤 4: 生成 Bug 报告

**精简 Bug 报告格式：**

```markdown
# Bug 报告

**项目：** alphaquant
**测试深度：** standard
**测试时间：** 2026-03-02 14:30
**状态：** ❌ 发现 3 个问题

---

## 严重 Bug (P0)

### 1. 登录按钮无响应
- **位置：** /login 页面
- **复现：** 点击登录按钮无反应
- **错误：** 控制台报错 `Uncaught TypeError: Cannot read property 'value' of null`
- **截图：** bugs/bug-001.png

---

## UI 问题 (P1)

### 2. 导航栏在移动端错位
- **位置：** 首页顶部导航
- **问题：** 宽度 <768px 时菜单项重叠
- **截图：** bugs/bug-002.png

---

## 建议优化 (P2)

### 3. 加载状态缺失
- **位置：** 数据表格
- **问题：** 数据加载时无 loading 提示
- **建议：** 添加骨架屏或 loading 动画

---

## 修复计划

1. [P0] 修复登录按钮 null 引用错误 (预计 10 分钟)
2. [P1] 修复移动端导航 CSS (预计 15 分钟)
3. [P2] 添加加载状态组件 (预计 20 分钟)
```

### 步骤 5: 自动修复

生成报告后，立即执行修复：

```markdown
## 开始修复

正在修复 P0 问题：登录按钮无响应

1. 定位问题代码
   - 检查登录组件
   - 找到 null 引用位置

2. 应用修复
   - 添加空值检查
   - 修复元素选择器

3. 验证修复
   - 重新测试登录流程
   - 确认问题解决
```

### 步骤 6: 验证修复

修复后重新测试确保问题解决：

```bash
# 刷新页面
mcp__chrome-devtools__navigate_page type="reload"

# 重新执行测试步骤
mcp__chrome-devtools__click uid="login-button"

# 验证结果
mcp__chrome-devtools__wait_for text="欢迎回来"
```

---

## Bug 分类和优先级

| 优先级 | 类型 | 响应 |
|-------|------|-----|
| **P0** | 功能阻断、数据丢失、安全漏洞 | 立即修复 |
| **P1** | UI 错位、非核心功能异常 | 本次修复 |
| **P2** | 体验优化、性能建议 | 建议修复，用户决定 |

---

## 常见测试场景

### 用户认证流程

```bash
# 1. 导航到登录页
mcp__chrome-devtools__navigate_page url="http://localhost:3000/login"

# 2. 填写表单
mcp__chrome-devtools__fill uid="email" value="test@example.com"
mcp__chrome-devtools__fill uid="password" value="password123"

# 3. 提交
mcp__chrome-devtools__click uid="submit"

# 4. 等待跳转
mcp__chrome-devtools__wait_for text="仪表盘"

# 5. 验证登录成功
mcp__chrome-devtools__take_snapshot
```

### 表单验证测试

```bash
# 测试空值提交
mcp__chrome-devtools__fill uid="name" value=""
mcp__chrome-devtools__click uid="submit"
mcp__chrome-devtools__wait_for text="必填"

# 测试无效格式
mcp__chrome-devtools__fill uid="email" value="invalid-email"
mcp__chrome-devtools__click uid="submit"
mcp__chrome-devtools__wait_for text="格式不正确"
```

### 响应式布局测试

```bash
# 移动端视图
mcp__chrome-devtools__resize_page width=375 height=667
mcp__chrome-devtools__take_snapshot
mcp__chrome-devtools__take_screenshot filePath="bugs/mobile-layout.png"

# 平板视图
mcp__chrome-devtools__resize_page width=768 height=1024
mcp__chrome-devtools__take_snapshot

# 桌面视图
mcp__chrome-devtools__resize_page width=1920 height=1080
```

### API 错误处理

```bash
# 触发错误请求
mcp__chrome-devtools__click uid="load-data"

# 检查网络响应
mcp__chrome-devtools__list_network_requests resourceTypes=["xhr","fetch"]
mcp__chrome-devtools__get_network_request reqid=789

# 验证错误 UI
mcp__chrome-devtools__wait_for text="加载失败"
```

---

## 修复模式

### 前端问题修复

**问题：** 按钮点击无响应

**诊断步骤：**
1. 检查控制台错误
2. 检查元素是否存在
3. 检查事件绑定

**修复模式：**
```javascript
// 错误代码
document.getElementById('btn').addEventListener('click', handler)

// 修复后
const btn = document.getElementById('btn')
if (btn) {
  btn.addEventListener('click', handler)
}
```

### UI 错位修复

**问题：** 元素重叠/溢出

**诊断步骤：**
1. 截图记录问题
2. 检查 CSS 样式
3. 检查父容器尺寸

**修复模式：**
```css
/* 添加 overflow 处理 */
.container {
  overflow: hidden;
  display: flex;
  flex-wrap: wrap;
}
```

### 网络错误修复

**问题：** API 请求失败

**诊断步骤：**
1. 检查请求 URL
2. 检查请求参数
3. 检查后端服务状态

**修复模式：**
```javascript
// 添加错误重试
async function fetchData() {
  try {
    const res = await fetch('/api/data')
    return await res.json()
  } catch (e) {
    // 重试逻辑
    setTimeout(fetchData, 1000)
  }
}
```

---

## 输出结构

```
browser-tester-workspace/
├── bug-reports/
│   ├── bug-report-20260302-1430.md
│   └── bug-report-20260302-1600.md
├── screenshots/
│   ├── bug-001.png
│   └── bug-002.png
├── network-logs/
│   └── requests-20260302-1430.json
└── fix-logs/
    └── fix-20260302-1430.md
```

---

## 配置选项

测试前询问用户：

```
1. 测试深度？(quick/standard/comprehensive)
2. 关注特定功能？(登录/支付/数据展示...)
3. 跳过某些页面？
```

默认使用 `standard` 深度，测试所有主要功能。

---

## 示例对话

**用户：** "测试一下这个项目的功能"

**技能：**
```
好的，我来执行一次标准测试。

**项目分析中...**
- 检测到 React 前端项目
- 包含登录、数据展示、设置页面

**测试计划：**
1. 首页加载和导航
2. 登录功能测试
3. 数据展示测试
4. 响应式布局检查

预计耗时：25 分钟

开始测试...
```

**测试完成后：**
```
测试完成！发现 2 个问题：

**P0 - 登录按钮偶尔无响应**
控制台报错：`Cannot read property 'value' of null`

**P1 - 数据表格在移动端显示不全**
宽度 <768px 时右侧内容被截断

正在自动修复...

[P0 修复完成] 已添加空值检查
[P1 修复完成] 已添加水平滚动

验证测试通过！✅
```
