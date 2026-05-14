---
name: api-e2e-test
description: Use when 用户要求为接口编写、生成或维护 E2E/API 自动化测试，或要求基于接口文档补齐真实 HTTP 场景、测试数据依赖、跳过原因和执行流程记录。
origin: Custom
---

# API E2E 测试生成器

为接口生成 E2E 测试。核心原则：先打包并外部启动真实服务，再由测试程序通过 HTTP 黑盒请求验证接口；服务生命周期和场景断言必须分离。

## 何时使用

用户要求写接口 E2E 测试、生成接口自动化测试、创建端到端测试、补齐 E2E 场景、维护 E2E 脚本、记录 E2E 测试数据或处理 E2E 跳过原因时使用。

## 硬约束

- 测试程序只负责 HTTP 请求、断言和结果输出，不负责启动、停止或托管服务进程。
- 必须请求真实 HTTP 端口，例如 `http://127.0.0.1:{port}`；禁止把框架内存客户端、Mock、进程内 MVC 作为主要验证路径。
- Java 项目必须优先用 Java 实现 E2E 测试程序；不要为 Java 项目生成 Python、Shell 场景测试脚本。
- Java/Spring Boot 项目默认使用轻量 Java `main` 程序通过 HTTP 调用服务；不要默认生成 JUnit、`SpringBootTest`、`MockMvc`、随机端口或 Maven test lifecycle 绑定的 E2E。
- 服务打包、启动、等待健康检查和停止流程写在 `tests/e2e-api/README.md`；不要默认新增专门的启动脚本。
- 测试场景按接口或接口族合并；不要把同一接口族拆成过多零散文件。
- `tests/e2e-api/scripts/` 必须包含与 `tests/e2e-api/cases/` 场景文档一一对应的测试程序。
- 命名必须能看出覆盖的接口或端点；禁止使用 `smoke`，避免 `service_health` 这类仍不清楚端点的泛化名字。示例：`ApiHealthAndRootE2e`、`SearchE2e`、`StrategySearchE2e`。
- 测试程序不得导入应用模块、mock 内部对象、启动 mock 运行时或 monkeypatch 应用对象。

## 核心工作流

执行测试时必须按“人真实操作和排查”的顺序推进，而不是只按脚本最短路径推进：

- 先像人一样确认入口、登录/权限、页面或后台是否能完成造数；能通过可见后台造数时，优先使用浏览器/后台流程。
- 再像人一样启动服务、等待健康检查、观察日志、运行场景脚本、核对响应和数据来源。
- 如果页面没有入口或数据链路缺失，再按真实运维/环境操作处理，例如 Kafka、Redis、ES 或上游配置造数；操作前后都要验证查询结果。
- 不要把“直接改数据”伪装成页面操作；必须在 README 记录为什么跳过页面、用了哪个环境链路、如何验证。
- 测试脚本仍只负责黑盒 HTTP 请求和断言，不能承担启动服务、mock 内部对象、造数或环境修复。

```
1. 检查接口实现文档
2. 必要时生成接口文档
3. 探索打包命令、启动命令、端口、健康检查和依赖
4. 设计按接口合并的 Markdown 场景文档
5. 生成与场景文档一一对应的测试程序
6. 在 README 记录打包、外部启动、等待健康检查、运行测试和停止服务的流程
7. 外部启动真实服务，用测试程序发 HTTP 请求验证
8. 记录跳过原因、环境依赖、造数流程和验证结果
```

## 步骤 1：检查接口实现文档

检查 `docs/interfaces/` 是否存在接口实现文档：

```bash
ls docs/interfaces/*.md 2>/dev/null
```

如果目录不存在或为空，先使用 `api-doc-generator` 生成接口实现文档，再继续。

## 步骤 2：提取测试场景

从接口文档中提取场景：

| 文档信息 | E2E 场景 |
| --- | --- |
| 核心流程图 | 正常路径、分支路径 |
| 关键过滤与业务规则 | 参数校验、归一化、边界条件 |
| 候选源与调用链 | 各数据源命中、未命中、降级 |
| 返回策略与降级 | 成功响应、异常响应、兜底响应 |
| 已知风险与疑点 | 类型兼容、历史路由、缓存、环境依赖 |

场景名称必须使用中文描述。保留 `MANUAL`、`STATISTICS`、`MODEL`、`request_time` 等接口枚举和字段名。

## 步骤 3：探索服务启动与测试环境

必须先探索项目，不要套模板：

- 打包入口：`pom.xml`、`build.gradle`、`package.json`、`Makefile`、Dockerfile 等。
- 启动入口：可执行 jar/war、`run.sh`、`start.sh`、`docker-compose.yml`、`main.py`、`server.js`、`main.go` 等。
- 端口：查 `server.port`、`PORT`、`listen`、`addr`、`bind` 或配置文件。
- 健康检查：查 `/health`、`/ping`、`/slb/health`、`/` 等真实路由。
- 依赖：JDK/Maven/Gradle、npm、Go module、模型文件、缓存、Apollo/Redis/上游数据等。

把确认结果写入 `tests/e2e-api/README.md`：打包命令、启动命令、Base URL、健康检查路径、环境依赖、测试数据准备方式。

## 步骤 4：选择执行方式

硬约束是“真实服务 + HTTP 黑盒请求”。优先使用项目语言和工具链：

| 技术栈 | 推荐方式 |
| --- | --- |
| Java / Spring Boot | Java `main` E2E 程序 + `HttpURLConnection` 或可用的 Java HTTP client，请求外部启动的真实服务 |
| Node.js | 项目已有 test runner 或 Node 脚本 + `fetch`/`axios` 请求真实服务 |
| Go | `go test` 或 Go `main` 程序 + `net/http` 请求真实服务 |
| Python | pytest/httpx/requests，或项目已有脚本方式 |
| 无测试栈或脚本型项目 | 生成与项目工具链一致的轻量 HTTP runner |

只有用户明确要求，或项目已有稳定约定时，才把 E2E 放入 JUnit、pytest、go test 等测试框架生命周期。否则保持“外部启动服务 + 独立 HTTP 测试程序”的流程。

## Java / Maven 推荐流程

对 Java Maven 服务，README 中优先记录以下流程。具体系统参数、artifact 路径和端口必须按项目实际结果填写。

1. 打包服务：

```bash
mvn clean package -DskipTests
```

2. 在单独 shell 或外层流程中启动打包产物：

```bash
java {system-properties} -jar {module}/target/{artifact}.jar
```

或：

```bash
java {system-properties} -jar {module}/target/{artifact}.war
```

3. 等待健康检查：

```bash
curl -i http://127.0.0.1:{port}/{health-path}
```

4. 编译并运行 Java E2E 程序：

```bash
mkdir -p /tmp/{project}-e2e-api-classes
javac -encoding UTF-8 -d /tmp/{project}-e2e-api-classes tests/e2e-api/scripts/*.java
java -cp /tmp/{project}-e2e-api-classes {InterfaceName}E2e --base-url http://127.0.0.1:{port}
```

可以在 README 里提供后台启动和清理的 shell 片段，但不要把它抽成默认启动脚本。

## 步骤 5：目录、命名与脚本结构

默认结构：

```text
tests/e2e-api/
  README.md
  cases/
    api_health_and_root.md
    {interface_or_api_group}.md
  scripts/
    ApiHealthAndRootE2e.java
    {InterfaceOrApiGroup}E2e.java
    E2eSupport.java
```

约束：

- 一个场景文档对应一个测试程序。
- 按接口或接口族合并场景，例如 `search.md` 对应 `SearchE2e.java`，`strategy_search.md` 对应 `StrategySearchE2e.java`。
- 文档和程序名必须表达接口或端点；`ApiHealthAndRootE2e` 比 `SmokeE2e` 或 `ServiceHealthE2e` 更清楚。
- Java 项目可以保留一个共享 `E2eSupport.java`，仅放 HTTP、断言、Base URL、结果输出等通用逻辑，不放服务启动/停止逻辑。
- 全量执行可先写在 README 的 shell loop 中；不要默认新增 `run_all_e2e.sh`、`start_service.sh`、`run_httpserver_e2e.*`。
- 如果用户明确要求全量入口，Java 项目优先生成 `RunAllE2e.java`，不要生成 shell 场景测试脚本。

## 步骤 6：服务启动与测试执行分离

测试程序不得托管启动服务。不要在测试 runner 中实现 `start_service`、`stop_service`、`--no-start`、`--ready-timeout` 这类服务生命周期分支。

正确流程：

1. 用独立 shell/子进程启动真实服务，确保日志可见。
2. 等健康检查通过。
3. 另一个命令运行 E2E 测试程序。
4. 测试结束后由操作者、外层 shell 或 CI 步骤停止服务。

CI 也应把“启动服务”和“执行 E2E”拆成不同步骤。

## 步骤 7：Markdown 用例格式

````markdown
# {接口或端点组} E2E 用例

## Source Interface Document

- `docs/interfaces/{文件名}.md`

本用例集遵循源文档中的流程图、关键业务规则、返回策略和已知风险。

## Runtime

- Prerequisite: start the service externally before running these cases.
- Startup example: `{启动命令}`
- Base URL: `http://127.0.0.1:{port}`
- Test program: `tests/e2e-api/scripts/{InterfaceName}E2e.java`

## Covered Endpoints

- `GET /example`
- `POST /api/example`

<a id="case-stable-anchor"></a>

## 场景：{中文场景描述}

**Purpose:** 该用例验证的端到端行为。

**Preconditions:**
- 所需的上游测试数据、模型、缓存或配置。

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

**Assertions:**
- 请求必须经过真实 HTTP 端口。
- HTTP 状态码符合预期。
- 关键响应字段符合预期。
- 测试日志输出状态码、响应体或关键字段和耗时。
````

如果脚本中的 `docs` 使用英文 anchor，Markdown 标题前补显式 `<a id="..."></a>`，避免中文标题导致链接不可控。

## 步骤 8：README 记录规范

`tests/e2e-api/README.md` 是 E2E 问题与操作记录入口，必须记录：

- 执行入口：如何打包服务、如何外部启动服务、如何等待健康检查、如何运行单个场景、如何运行全部场景、如何停止服务。
- 场景映射：每个 Markdown 场景文档、对应测试程序、覆盖端点。
- 环境依赖：JDK/Maven/Gradle、模型、缓存、上游服务、权限、登录、测试环境地址。
- 测试数据：固定 query、后台入口、造数步骤、删除/清理方式。
- 操作路径：按人的操作顺序记录“页面/后台尝试 -> 环境链路处理 -> 接口验证”的过程；直接 ES/Kafka/Redis 造数必须写明页面无法完成的原因。
- 跳过原因：对应场景、`skip_reason`、解除跳过的条件。
- 问题记录：登录/权限/测试环境问题和处理方式。

遇到测试环境问题时，先把问题和处理方式写入 README，再继续。

## 步骤 9：Java E2E 程序要求

Java 轻量 E2E 程序应满足：

- 每个程序有独立 `public static void main(String[] args)`。
- 支持 `--base-url URL`，并可从 `BASE_URL` 读取默认值。
- 支持 `--help` 输出用法。
- 使用 `HttpURLConnection` 或当前 JDK 可用的标准 HTTP client。
- 打印每个用例的 `[PASS]`、`[FAIL]`、`[SKIP]`、case id、请求方法、路径、HTTP 状态码、耗时、响应体或关键字段。
- 失败时退出非零状态码。
- 对数据缺失但已确认暂不可造的场景使用 skip，并在 README 记录原因和解除条件。

`--list-cases`、`--case` 过滤是可选能力；只有生成集合入口或用户明确要求筛选能力时才必须实现。

## 步骤 10：验证

生成或修改后必须验证：

1. 语法/编译：
   - Java 轻量程序：`javac -encoding UTF-8 -d /tmp/{project}-e2e-api-classes tests/e2e-api/scripts/*.java`
   - Java 框架内集成测试：仅在用户明确要求时使用 `mvn -pl {module} -DskipTests test-compile`
   - Python：`python -m py_compile tests/e2e-api/scripts/*.py`
   - Node：项目 lint/typecheck 或 test runner 的 list/collect 命令
   - Go：`go test ./... -run TestName -count=0`
2. 陈旧引用检查：

```bash
rg -n "smoke|Smoke|SpringBootTest|MockMvc|randomPort|JUnit|start_service|run_httpserver" tests/e2e-api src/test 2>/dev/null
```

3. 外部启动真实服务后，运行每个场景测试程序并确认退出码。
4. 记录真实通过、失败、跳过数量。
5. 测试完成后确认服务由外层流程停止，必要时检查端口没有残留。

如果验证需要人工扫码、权限、造数或测试环境修复，停止并说明需要用户处理什么。

## 子代理使用

只有当用户明确要求“子代理、并行代理、并行处理”时，才把接口拆给子代理。拆分时每个代理只负责一个场景文档和对应测试程序，写入范围必须互不重叠。否则主流程自己完成。
