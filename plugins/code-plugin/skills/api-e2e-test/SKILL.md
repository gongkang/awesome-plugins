---
name: api-e2e-test
description: 当用户要求为接口编写、生成或维护 E2E/API 自动化测试，或要求基于接口文档补齐真实 HTTP 场景、测试数据依赖、跳过原因和执行流程记录时使用此技能。也适用于：用户提到"写接口测试"、"生成 E2E 测试"、"创建端到端测试"、"补齐 E2E 场景"、"维护 E2E 脚本"、"记录 E2E 测试数据"等场景。
origin: Custom
---

# API E2E 测试生成器

为接口生成 E2E 测试。核心原则：外部启动真实服务，再由落盘测试程序通过 HTTP 黑盒请求验证接口；服务生命周期、测试数据准备和场景断言必须边界清晰。

## 何时使用

用户要求写接口 E2E 测试、生成接口自动化测试、创建端到端测试、补齐 E2E 场景、维护 E2E 脚本、记录 E2E 测试数据或处理 E2E 跳过原因时使用。

## 硬约束

- 测试程序只负责 HTTP 请求、断言和结果输出，不负责启动、停止或托管服务进程。
- 必须请求真实 HTTP 端口，例如 `http://127.0.0.1:{port}`；禁止把框架内存客户端、Mock、进程内 MVC 作为主要验证路径。
- 正式 E2E 流程必须是“真实服务 + 真实 HTTP + 落盘脚本 + 可复现测试数据”；临时 Python、临时 Shell、临时 curl 和直接改数据源只能用于排查，不能作为正式测试流程。
- 测试数据准备优先通过被测系统的真实 HTTP 接口完成，例如创建、批量导入、写入、删除或后台公开 API；禁止把直接写 ES/Kafka/Redis/DB 伪装成接口 E2E 造数。
- 如果确实需要通过运维链路准备环境数据，必须先说明原因，并在 README 记录使用了哪个环境链路、执行了什么、如何验证结果。
- 核心业务请求参数必须固定在测试程序和 case 文档中，例如样例图片、item id、tags、bbox、categories、query；环境变量只用于 `base-url`、运行开关、超时、异步等待等执行控制，除非项目已有明确约定。
- Java 项目必须优先用 Java 实现 E2E 测试程序；不要为 Java 项目生成 Python、Shell 场景测试脚本。
- Java/Spring Boot 项目默认使用轻量 Java `main` 程序通过 HTTP 调用服务；不要默认生成 JUnit、`SpringBootTest`、`MockMvc`、随机端口或 Maven test lifecycle 绑定的 E2E。
- 服务打包、启动、等待健康检查和停止流程写在 `tests/e2e-api/README.md`；不要默认新增专门的启动脚本。
- 测试场景按接口或接口族合并；不要把同一接口族拆成过多零散文件。
- 如果接口之间存在数据或状态依赖，必须先梳理依赖图和业务测试顺序，例如初始化配置/字典 -> 写入/导入 -> 查询/校验 -> 更新 -> 删除/清理；不能孤立运行后置接口并把失败归因成接口异常。
- `tests/e2e-api/scripts/` 必须包含与 `tests/e2e-api/cases/` 场景文档一一对应的测试程序。
- 单个测试程序可以包含 `prepare` 类 case，用于通过真实 HTTP 接口准备固定测试数据；后续 case 必须清楚声明依赖这些 fixture。
- 命名必须能看出覆盖的接口或端点；禁止使用 `smoke`，避免 `service_health` 这类仍不清楚端点的泛化名字。示例：`ApiHealthAndRootE2e`、`SearchE2e`、`StrategySearchE2e`。
- 测试程序不得导入应用模块、mock 内部对象、启动 mock 运行时或 monkeypatch 应用对象。
- 新增或修改会访问真实依赖的接口场景时，执行前必须先向用户说明脚本会测什么、请求参数是什么、预期结果是什么、依赖哪些前置数据，并在用户确认后再运行。

## 核心工作流

执行测试时必须按“人真实操作和排查”的顺序推进，而不是只按脚本最短路径推进：

- 先像人一样确认入口、登录/权限、页面或后台是否能完成造数；能通过可见后台或公开 API 造数时，优先使用这些入口。
- 如果是纯 API 服务，没有可见后台，不要强行寻找页面；以 `/docs`、OpenAPI、健康检查和真实接口作为人工测试入口。
- 再像人一样启动服务、等待健康检查、观察日志、运行场景脚本、核对响应和数据来源。
- 对存在依赖关系的接口，按真实业务流执行测试：先准备上游配置和基础数据，再触发写入或状态变更，随后验证查询结果，最后执行清理；每一步都要说明上一接口给下一接口提供了什么数据或状态。
- 如果页面没有入口或数据链路缺失，再按真实运维/环境操作处理，例如 Kafka、Redis、ES 或上游配置造数；操作前后都要验证查询结果。
- 不要把“直接改数据”伪装成页面操作；必须在 README 记录为什么跳过页面、用了哪个环境链路、如何验证。
- 测试脚本只通过黑盒 HTTP 请求完成数据准备、查询、异步轮询和断言；不能承担启动服务、mock 内部对象或修复环境。

```
1. 检查接口实现文档
2. 必要时生成接口文档
3. 探索打包命令、启动命令、端口、健康检查和依赖
4. 梳理接口依赖图和推荐执行顺序，区分可独立运行的 case 和依赖前置数据的 case
5. 设计按接口合并的 Markdown 场景文档，写清楚固定测试数据、前置 fixture 和依赖来源
6. 生成与场景文档一一对应的落盘测试程序
7. 向用户说明新增场景、请求参数、预期结果、依赖链路和推荐执行顺序，等待确认
8. 在 README 记录打包、外部启动、等待健康检查、运行测试和停止服务的流程
9. 外部启动真实服务，用测试程序发 HTTP 请求验证
10. 记录通过、失败、跳过数量，以及环境依赖、造数流程和验证结果
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
- API-only 项目：优先确认 `/docs`、`/openapi.json`、OpenAPI/Swagger 入口和真实业务接口，不要生成浏览器页面测试来替代 API E2E。

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
- Python、Node、Go 等项目也应保留一个轻量共享支持文件，只放 HTTP client、断言、case 选择、结果输出、异步轮询等通用逻辑，不放应用内部导入或服务生命周期逻辑。
- 测试程序应默认支持 `--base-url`，并推荐支持 `--case` 和 `--list-cases`，方便人工逐个场景排查。
- 全量执行可先写在 README 的 shell loop 中；不要默认新增 `run_all_e2e.sh`、`start_service.sh`、`run_httpserver_e2e.*`。
- 如果用户明确要求全量入口，Java 项目优先生成 `RunAllE2e.java`，不要生成 shell 场景测试脚本。

## 步骤 6：服务启动与测试执行分离

测试程序不得托管启动服务。不要在测试 runner 中实现 `start_service`、`stop_service`、`--no-start`、`--ready-timeout` 这类服务生命周期分支。

正确流程：

1. 用独立 shell/子进程启动真实服务，确保日志可见。
2. 等健康检查通过。
3. 另一个命令运行 E2E 测试程序。
4. 测试结束后由操作者、外层 shell 或 CI 步骤决定是否停止服务；不要主动停止用户正在观察或继续手测的服务。

CI 也应把“启动服务”和“执行 E2E”拆成不同步骤。

## 步骤 7：Markdown 用例格式

````markdown
# {接口或端点组} E2E 用例

## 源码接口文档

- `docs/interfaces/{文件名}.md`

本用例集遵循源文档中的流程图、关键业务规则、返回策略和已知风险。

## 运行环境

- 前置条件：运行测试前必须先外部启动服务。
- 启动示例：`{启动命令}`
- Base URL：`http://127.0.0.1:{port}`
- 测试程序：`tests/e2e-api/scripts/{InterfaceName}E2e.java`

## 覆盖端点

- `GET /example`
- `POST /api/example`

<a id="case-stable-anchor"></a>

## 场景：{中文场景描述}

**目的：** 该用例验证的端到端行为。

**前置条件：**
- 所需的上游测试数据、模型、缓存或配置。

**请求：**

```http
POST /{路由路径}
Content-Type: application/json
```

```json
{
  "key": "value"
}
```

**断言：**
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
- 固定测试约束：真实服务、真实 HTTP、落盘脚本、可复现测试数据、禁止临时脚本作为正式流程。
- 测试数据：固定 query、固定请求参数、后台或 HTTP 造数入口、造数步骤、删除/清理方式。
- 接口依赖流程：按业务顺序列出需要先后执行的接口、每一步产出的关键数据或状态、后续接口如何使用它们；独立 case 和依赖 case 要分开说明。
- 异步链路：如果写入、删除或索引更新是异步的，记录哪个脚本只断言受理成功，哪个脚本轮询验证最终可见或最终删除。
- 单场景排查：记录如何使用 `--case` 或等价能力只运行某个 case；准备 fixture 的 case 要单独列出。
- 操作路径：按人的操作顺序记录“页面/后台尝试 -> 环境链路处理 -> 接口验证”的过程；直接 ES/Kafka/Redis 造数必须写明页面无法完成的原因。
- 跳过原因：对应场景、`skip_reason`、解除跳过的条件。
- 问题记录：登录/权限/测试环境问题和处理方式。

遇到测试环境问题时，先把问题和处理方式写入 README，再继续。

## 步骤 9：Java E2E 程序要求

所有语言的 E2E 程序都应满足：

- 有独立命令入口，可以被人工单独执行。
- 支持 `--base-url URL` 或项目等价参数。
- 推荐支持 `--case` 和 `--list-cases`；当用户要求逐个接口或逐个过滤条件测试时必须支持。
- 打印每个用例的 `[PASS]`、`[FAIL]`、`[SKIP]`、case id、请求方法、路径、HTTP 状态码、耗时、响应体或关键字段。
- 失败时退出非零状态码。
- 对真实依赖未开启、权限缺失或环境数据暂不可造的场景使用 skip，并在 README 记录原因和解除条件。
- 涉及异步写入、删除、索引更新或缓存刷新时，使用轮询等待最终状态，不用固定 sleep 代替断言。
- 不在程序运行中创建临时测试脚本、临时 curl 文件或直接写内部数据源。

Java 轻量 E2E 程序应满足：

- 每个程序有独立 `public static void main(String[] args)`。
- 支持 `--base-url URL`，并可从 `BASE_URL` 读取默认值。
- 支持 `--help` 输出用法。
- 使用 `HttpURLConnection` 或当前 JDK 可用的标准 HTTP client。

`--list-cases`、`--case` 过滤是推荐能力；只有极小的单场景脚本才可以省略。

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

3. 黑盒纯度检查：

```bash
rg -n "TestClient|from .*app|from .*\\.app|mock|monkeypatch|tempfile|NamedTemporaryFile" tests/e2e-api/scripts 2>/dev/null
```

4. 外部启动真实服务后，运行每个场景测试程序并确认退出码。
5. 记录真实通过、失败、跳过数量。
6. 测试完成后不要主动停止用户仍在使用的服务；只有 README、CI 或用户明确要求停止时，才执行外层停止流程。

如果验证需要人工扫码、权限、造数或测试环境修复，停止并说明需要用户处理什么。

## 子代理使用

只有当用户明确要求“子代理、并行代理、并行处理”时，才把接口拆给子代理。拆分时每个代理只负责一个场景文档和对应测试程序，写入范围必须互不重叠。否则主流程自己完成。
