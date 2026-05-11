---
name: api-e2e-test
description: 为接口生成基于 Markdown 用例文档的 E2E 测试。当用户要求"写接口 E2E 测试"、"生成接口自动化测试"、"创建接口端到端测试"时使用此技能。用例以 Markdown 为唯一管理入口，配套可执行脚本，通过真实服务启动、发起 HTTP 请求验证响应。
origin: Custom
---

# API E2E 测试生成器

为接口生成 E2E 测试。用例以 Markdown 文档为唯一管理入口，配套可执行 Python 脚本，通过真实服务启动、发起 HTTP 请求验证响应。

## 何时使用

用户要求写接口 E2E 测试 / 生成接口自动化测试 / 创建接口端到端测试时使用。

## 核心工作流

```
1. 检查接口实现文档 → 2. 按需生成接口文档 → 3. 确定服务启动方式 → 4. 创建目录结构 → 5. 并行子代理生成用例和脚本 → 6. 生成聚合入口 → 7. 验证可运行性
```

### 步骤 1: 检查接口实现文档

检查 `docs/interfaces/` 目录是否存在且有 `.md` 文件：

```bash
ls docs/interfaces/*.md 2>/dev/null
```

**如果目录不存在或为空**：先调用 `api-doc-generator` 技能生成接口实现文档，再继续后续步骤。

### 步骤 2: 阅读接口实现文档

阅读 `docs/interfaces/` 下的接口实现文档，从中提取测试场景：

| 接口文档维度 | 对应的测试场景 |
| --- | --- |
| 核心流程图 | 正常流程、各分支路径 |
| 关键过滤与业务规则 | 参数校验、归一化、边界条件 |
| 候选源与调用链 | 各数据源的命中/未命中/降级 |
| 返回策略与降级 | 成功响应、异常响应、降级路径 |
| 已知风险与疑点 | 边界情况、类型不匹配、兼容路由 |

### 步骤 2.5: 探索项目启动方式

**不同项目启动方式差异很大，必须主动探索项目结构来确定。**

探索步骤：

1. **找启动入口**：检查项目根目录，寻找以下特征
   - `run.sh`、`start.sh`、`Makefile`、`docker-compose.yml` 等脚本
   - `main.py`、`app.py`、`server.js`、`main.go`、`Cargo.toml`、`pom.xml`、`build.gradle` 等入口文件
   - `package.json` 中的 `scripts.start` 字段

2. **确认端口**：在入口文件或配置文件中查找端口定义
   - 常见变量名：`PORT`、`port`、`listen`、`addr`、`bind`
   - 常见默认值：`8000`、`8080`、`3000`、`5000`、`9090`

3. **确认健康检查路径**：查找路由定义或文档中是否有 `/health`、`/ping`、`/` 等路径

4. **确认依赖安装方式**：`pip install`、`npm install`、`go mod download`、`mvn install` 等

**将确认的启动命令、端口、健康检查路径、依赖安装命令记录下来**。如果无法确定，先尝试 `python main.py` 或 `bash run.sh`，失败时尝试其他方式。

### 步骤 3: 创建目录结构

```
tests/e2e/
  cases/
    smoke.md                  # 冒烟用例（健康检查、根路径等）
    {interface_1}.md          # 接口 1 用例
    {interface_2}.md          # 接口 2 用例
  scripts/
    smoke.py                  # 冒烟用例执行脚本
    {interface_1}.py          # 接口 1 用例执行脚本
    {interface_2}.py          # 接口 2 用例执行脚本
    run_all_e2e.py            # 聚合入口，导入并运行所有用例
  __init__.py
```

### 步骤 4: 并行子代理生成用例和脚本

**核心步骤。** 对每个接口（含 smoke），启动一个子代理并行生成 Markdown 用例文档和对应的 Python 执行脚本。

使用 `Agent` 工具一次性启动所有子代理（`run_in_background: true`），不串行等待。

#### 子代理 prompt 模板

```
为以下接口生成 E2E 测试用例和脚本：

**接口文档**: docs/interfaces/{文件名}.md
**用例文档输出路径**: tests/e2e/cases/{文件名}.md
**脚本输出路径**: tests/e2e/scripts/{文件名}.py

**环境信息**:
- 服务启动命令: {启动命令}
- Base URL: http://127.0.0.1:{端口}
- 健康检查路径: {健康检查路径}

**要求**:
1. 阅读接口文档，根据流程图、业务规则、返回策略、已知风险设计测试用例
2. 先编写 Markdown 用例文档，格式参照下方"Markdown 用例格式"
3. 再编写 Python 执行脚本，格式参照下方"Python 脚本格式"
4. 用例需覆盖：正常路径、参数校验、边界条件、降级路径、文档中标注的风险点
5. Python 脚本的 CASES 列表必须与 Markdown 用例一一对应
6. 脚本应自包含，包含启动服务、发送请求、断言、停止服务的完整逻辑

**Markdown 用例格式**:
# {接口名称} E2E Cases

## Source Interface Document
- `docs/interfaces/{文件名}.md`
本用例集遵循源文档中的流程图、关键业务规则、返回策略和已知风险。

## Runtime
- 启动: {启动命令}
- Base URL: http://127.0.0.1:{端口}

## Case: {场景名称}
**Purpose:** 该用例验证的端到端行为。
**Preconditions:** 所需的测试数据或配置。
**Request:**
```http
POST /{路由路径}
Content-Type: application/json
```
```json
{ "key": "value" }
```
**Expected Response:**
```json
{ "code": 0, "message": "success" }
```
**Assertions:**
- HTTP 状态码为 `200`。
- `code` 为 `0`。
**Manual Postman Notes:**
- 粘贴请求 JSON 作为 raw JSON。
- 记录响应体和耗时。

**Python 脚本格式**:
每个脚本应自包含，包含以下能力：
- 启动服务（通过项目的启动命令）
- 等待服务就绪（轮询健康检查）
- 发送 HTTP 请求并验证响应
- 打印用例执行结果（[PASS]/[FAIL]）
- 停止服务
- 支持 --case、--list-cases、--no-start 等 CLI 参数
```

对于 smoke 用例，子代理 prompt 简化为：

```
生成冒烟测试用例和脚本：

**用例文档输出路径**: tests/e2e/cases/smoke.md
**脚本输出路径**: tests/e2e/scripts/smoke.py

**环境信息**:
- 服务启动命令: {启动命令}
- Base URL: http://127.0.0.1:{端口}
- 健康检查路径: {健康检查路径}

**smoke 测试应覆盖**:
- 服务健康检查接口
- 服务是否能正常启动并响应
- 基本的路径是否存在（404 响应也是有效响应）

[插入上面的 Markdown 用例格式和 Python 脚本格式模板]
```

#### 错误处理

- 如果某个子代理失败（如接口文档不存在），在日志中标记该接口测试生成失败，继续处理其他接口
- 所有子代理完成后，汇总成功/失败数量并报告给用户

### 步骤 5: 生成聚合入口

等待所有子代理完成后，主进程生成 `tests/e2e/scripts/run_all_e2e.py`，导入所有已生成的 per-document CASES 并执行。

#### 聚合入口格式

```python
"""聚合入口：运行所有 E2E 用例。"""
import subprocess
import sys
import importlib

# 动态导入所有用例脚本
MODULES = ["smoke", "interface_1", "interface_2"]  # 按实际生成的文件名修改

def main():
    failed = 0
    for mod_name in MODULES:
        mod = importlib.import_module(mod_name)
        if hasattr(mod, "main"):
            result = subprocess.run(
                [sys.executable, f"{mod_name}.py"] + sys.argv[1:],
                capture_output=False,
            )
            if result.returncode != 0:
                failed += 1
    if failed > 0:
        print(f"\n{failed} 个用例脚本执行失败")
        sys.exit(1)
    print("\n所有 E2E 用例通过")

if __name__ == "__main__":
    main()
```

### 步骤 6: 验证可运行性

生成完成后，执行基本验证：

1. 检查所有生成的 Python 脚本语法是否正确：
   ```bash
   python -m py_compile tests/e2e/scripts/smoke.py
   # 对其他脚本重复
   ```

2. 检查 `run_all_e2e.py` 中的 MODULES 列表是否与已生成的文件匹配

3. 检查 Markdown 用例和 Python CASES 列表数量是否一致

## 架构约束

E2E 测试必须：

- 通过项目的服务启动入口启动真实服务（如 `python main.py`、`go run cmd/main.go`、`java -jar app.jar` 等）
- 等待服务就绪（如健康检查返回成功）
- 向 `127.0.0.1:{PORT}` 发送真实 HTTP 请求
- 打印每个用例的请求、响应、状态码、耗时
- 失败时退出非零状态码
- 测试完成后停止服务

E2E 测试不得：

- 导入应用模块并 mock 内部对象
- 使用框架内置的测试客户端作为主要机制
- 启动 mock 运行时
- 在进程内 monkeypatch Python 对象

## Markdown 用例格式

````markdown
# {接口名称} E2E Cases

## Source Interface Document

- `docs/interfaces/{文件名}.md`

本用例集遵循源文档中的流程图、关键业务规则、返回策略和已知风险。

## Runtime

- 启动: `bash app/run.sh`
- Base URL: `http://127.0.0.1:{端口}`
- 配置来源: 根据环境变量决定

## Case: {场景名称}

**Purpose:** 该用例验证的端到端行为。

**Preconditions:**
- 所需的上游测试数据或配置。
- 所需的模型/缓存/向量行为。

**Request:**

```http
POST /{路由路径}
Content-Type: application/json
```

```json
{
  "key": "value"
}
```

**Expected Response:**

```json
{
  "code": 0,
  "message": "success"
}
```

**Assertions:**
- HTTP 状态码为 `200`。
- `code` 为 `0`。
- ...

**Manual Postman Notes:**
- 粘贴请求 JSON 作为 raw JSON。
- 记录响应体和耗时。
````

## Python 脚本格式

每个 Python 脚本应自包含，包含以下核心能力。脚本通过 `subprocess` 调用项目对应的启动命令，使用 `requests` 库发送 HTTP 请求。

```python
"""{接口名称} E2E 测试脚本。"""
import subprocess
import sys
import time
import argparse
import requests
from typing import Optional

# === 配置（由生成时填充） ===
SERVICE_CMD = "bash app/run.sh"
BASE_URL = "http://127.0.0.1:8000"
HEALTH_PATH = "/health"
READY_TIMEOUT = 30

CASES: list[dict] = [
    {
        "name": "场景名称",
        "docs": "tests/e2e/cases/xxx.md#case-场景名称",
        "method": "GET",
        "path": "/路由",
        "json": {"key": "value"},
        "expect": {
            "status": 200,
            "json_contains": {"code": 0},
            "json_has_keys": ["code", "message"],
        },
    },
]

# === 运行时函数 ===

def start_service() -> subprocess.Popen:
    proc = subprocess.Popen(SERVICE_CMD.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc

def stop_service(proc: subprocess.Popen) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()

def wait_ready(proc: subprocess.Popen, timeout: int = READY_TIMEOUT) -> bool:
    url = f"{BASE_URL}{HEALTH_PATH}"
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            return False
        try:
            r = requests.get(url, timeout=2)
            if r.status_code == 200:
                return True
        except requests.ConnectionError:
            pass
        time.sleep(0.5)
    return False

def send_request(method: str, path: str, payload: Optional[dict] = None) -> tuple:
    url = f"{BASE_URL}{path}"
    t0 = time.time()
    r = requests.request(method, url, json=payload, timeout=30)
    return r.status_code, r.text, (time.time() - t0) * 1000

def run_case(case: dict) -> bool:
    name, method, path = case["name"], case.get("method", "GET"), case["path"]
    expect = case.get("expect", {})
    status, body, elapsed = send_request(method, path, case.get("json"))
    passed = True
    if expect.get("status") and status != expect["status"]:
        passed = False
    if expect.get("json_contains"):
        import json
        try:
            resp = json.loads(body)
            for k, v in expect["json_contains"].items():
                if resp.get(k) != v:
                    passed = False
        except json.JSONDecodeError:
            passed = False
    if expect.get("json_has_keys"):
        import json
        try:
            resp = json.loads(body)
            for k in expect["json_has_keys"]:
                if k not in resp:
                    passed = False
        except json.JSONDecodeError:
            passed = False
    tag = "[PASS]" if passed else "[FAIL]"
    print(f"{tag} {name} | {method} {path} | {status} | {elapsed:.0f}ms")
    if not passed:
        print(f"    Response: {body[:300]}")
    return passed

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", help="只运行指定用例")
    parser.add_argument("--list-cases", action="store_true")
    parser.add_argument("--no-start", action="store_true", help="不自动启动服务")
    args = parser.parse_args()

    cases = [c for c in CASES if not args.case or c["name"] == args.case]
    if args.list_cases:
        for c in CASES:
            print(c["name"])
        return

    service_proc = None
    if not args.no_start:
        service_proc = start_service()
        if not wait_ready(service_proc):
            print("[E2E] 服务启动失败"); sys.exit(1)

    results = [run_case(c) for c in cases]
    if service_proc:
        stop_service(service_proc)

    passed, failed = sum(results), len(results) - sum(results)
    print(f"\nSummary: {passed} passed, {failed} failed")
    if failed:
        sys.exit(1)

if __name__ == "__main__":
    main()
```

## 用例覆盖矩阵

| 维度 | 典型用例 |
| --- | --- |
| 请求校验 | 空 body、空字段、非法类型 |
| 参数归一化 | query 转小写、source 别名映射 |
| 正常路径 | 已知数据精确命中 |
| 降级路径 | 精确未命中 → 向量 → 模型 |
| 显式参数 | source 指定、version 路由 |
| 多源合并 | 多 source 同时请求 |
| 边界情况 | top_k 截断、isReverse 保留 |
| 已知风险 | 文档中标注的潜在问题 |

## 输出

```
tests/e2e/
  cases/
    smoke.md
    search_category.md
    search_first_category.md
  scripts/
    smoke.py
    search_category.py
    search_first_category.py
    run_all_e2e.py
  __init__.py
```
