# 按技术栈分析性能

性能分析先选方法，再读对应专项。只应用本次组件相关的条目，不要求每个项目跑完所有栈的检查。

## 识别实际组合

技术栈至少包含三个独立层次：**运行时与执行模型、框架/ORM、数据存储及驱动**。从包/构建配置、锁文件、入口、驱动和实际调用链确认版本，不只看文件扩展名或依赖名称。

- 同为 Java，MyBatis 动态 SQL 与 Hibernate 隐式加载要分别分析；同一 ORM 连接 PostgreSQL、MySQL 或 SQLite 时计划和索引解释也不同。
- 同为 TS/JS，浏览器、Node 服务、SSR 服务端、边缘运行时和后台任务有不同的成本与运行证据；不要将 Node 的线程池机制套到所有 JS 环境。
- 多应用、多进程或多存储项目逐组件记录实际组合。依赖已安装不证明它参与当前慢路径；模块未发现连接串也不证明没有数据库访问。
- 先确认工作负载：交互时延、API 尾延迟、批任务吞吐、CPU/内存或数据库容量。用相同条件比较对应指标，不设跨栈统一耗时阈值。

例如 Node + Prisma + PostgreSQL 的一次查询变慢，需区分事件循环等待、客户端/连接池开销、生成 SQL 和 PostgreSQL 执行成本，不能因为用了 Prisma 就套 MySQL 的 `key` 字段。

## 选择对应方法

优先复用已有运行记录；没有动态证据时追踪源码并标为风险或待验证。表中工具与指标是候选证据，不能假定已安装、已启用或允许采集。

| 识别到的组合 | 优先追踪的问题 | 优先解读的已有证据 |
| --- | --- | --- |
| Java/JVM + MyBatis/JDBC | 动态条件、foreach/嵌套映射、分页拦截器、列表与 count、事务和连接占用；展开实际 SQL 分支 | mapper 与配置、生成 SQL、请求 trace、池等待及数据库对应计划 |
| Java/JVM + JPA/Hibernate | 查询、实体关系、加载策略、序列化访问与持久化上下文，核对 secondary select、集合 fetch 和分页 | 每请求 SQL 数量、加载统计/trace、生成 SQL 和实际计划；不能只搜索显式 SQL |
| JVM 运行时 | 先区分 CPU、分配/GC、线程/锁及外部等待，再结合实际 Servlet/响应式等调用模型定位 | 与目标 JDK 匹配的已有 JFR、GC/线程或 CPU 记录；不能只凭 JVM 参数推断瓶颈 |
| Node + Express/Nest/Prisma/TypeORM 等 | 事件循环中的同步 I/O 或大计算、worker pool 等待、Promise 并发上限、ORM 关系加载/批处理与池等待 | 已有事件循环/CPU/内存记录、trace、实际生成 SQL 与数据库证据 |
| Python + Django/SQLAlchemy | QuerySet/session 的求值与缓存、懒加载、关系加载策略、对象构造及大量结果物化 | SQL 计数和 trace、实际 SQL、已有 profile/内存记录与数据库对应计划 |
| Python + FastAPI/asyncio 等 | 实际调用路径中同步库和 CPU 工作是否阻塞事件循环；区分框架线程池与直接调用工具函数 | 事件循环/线程池及请求等待记录、已有 profile；`async def` 本身不是无阻塞证据 |
| Go + database/sql/GORM 等 | goroutine 的工作与等待、取消、连接归还、实际 Preload/Joins 查询及池排队 | 已有 CPU/heap/goroutine/block/mutex profile、trace、DB.Stats 和 SQL；CPU profile 不代表全部等待 |
| .NET + EF Core 等 | LINQ 翻译与求值位置、物化/跟踪开销、关系加载、单查询或 split query 的实际工作量 | 已有 .NET 运行记录、生成 SQL/命令数、分配/池等待与实际数据库计划 |
| 浏览器 + React/Vue 等；含 SSR/水合 | 区分网络资源与 API、主线程脚本、组件更新、样式/布局、SSR 与客户端水合 | 相应页面/交互的网络与 Performance 记录、已有组件 profiler；不凭 bundle 大小或 render 次数判故障 |

## 容易误判的栈差异

- **MyBatis**：mapper 上的可选条件和拦截器会改变最终谓词、分页及 count；挑重要参数分支还原后再核对索引，不能只解释 XML 的一个静态片段。
- **JPA/Hibernate**：EAGER 仍可能产生额外查询，LAZY 是否触发取决于访问；结合持久化上下文和 SQL 计数。不要全局改 EAGER 或给全部集合加 JOIN FETCH，避免行数放大和分页语义变化。
- **Django/SQLAlchemy**：ORM 方法调用不等于数据库执行次数。关注延迟求值、QuerySet 缓存或 session/关系加载；按关系基数比较 select_related/prefetch_related、joinedload/selectinload 等实际行为与内存成本，不能统一替换成 JOIN。
- **Node 与 Python 异步**：异步函数中仍可运行同步计算/I/O；框架代为调度同步入口和普通函数被直接调用不是一回事。并发增加也可能放大池等待，不能一律改为 Promise.all/gather。
- **Go**：goroutine 多不直接证明泄漏；结合栈、等待和负载变化。DB.Stats 的 WaitCount/WaitDuration 等累计值需相同窗口的差值，不能单凭计数认定当前饱和。
- **EF Core**：核对数据库 provider、版本及 LINQ 实际翻译，查明过滤发生在数据库还是物化后。split query 可能减少行数放大，但会增加查询/往返及一致性取舍；不自动视为更快。
- **前端/SSR**：服务端快不证明页面交互快；开发模式、生产构建、网络和 profiler 自身开销要区分。相同页面/交互及可比设备条件下再比较；没有动态记录不虚构 LCP/INP 或渲染收益。

## 数据存储再分流

| 实际后端 | 方法与边界 |
| --- | --- |
| MySQL / PostgreSQL | 使用 [数据库性能分析](database-performance.md) 的相应章节；普通计划、实测计划、统计字段和计时单位分别处理 |
| SQLite | 读取目标版本 `EXPLAIN QUERY PLAN` 的 SCAN/SEARCH、索引及临时排序信息；该输出不是 MySQL 的 key/type，也不是执行时延，格式可能随版本变化 |
| MongoDB | 按实际查询/聚合及版本读取 plan stage、索引边界、返回文档、扫描 keys/docs 和关联/排序工作；区分 queryPlanner 与执行统计，后者可能实际执行，不能自动运行 |
| Redis | 区分命令执行、大数据结构操作、客户端连接/网络及应用缓存命中；SLOWLOG 的执行时间不含客户端 I/O，不能拿它证明端到端延迟；不套关系型索引命中概念 |
| 其他数据库、搜索引擎、语言或框架 | 从实际版本和调用路径查官方诊断方法，不套上述命令、字段或默认阈值，也不因未列出就跳过目标组件 |

## 报告与验证

记录每个组件的实际组合、工作负载、选用方法和版本，明确已经审查的范围与缺失证据。运行证据用 `observed`，估算计划用 `estimated`，源码/配置风险用 `static_risk`，无法判断用 `unverified`；子结论的确信程度对应自身证据。

建议要落到相应成本：SQL、池排队、CPU/分配、锁、事件循环、网络或渲染，说明依据和同条件验证方式。不要用数据库计划解释应用 GC，也不要用服务端 SQL 时延代替浏览器交互指标；同一请求的跨层耗时可能包含或重叠，不能简单相加。

沿用健康检查的只读边界：优先已有 profile/trace/统计，不自动安装工具、注入监控、开启调试端口或改采样配置。数据库采集和实际执行仍遵守授权范围；缺少运行环境时完成静态分析和待验证项。

## 官方参考

核对日期：2026-10-28。固定版本链接只服务于对应版本；可变文档执行前按项目实际版本选择，不将当前官网默认行为当作所有版本行为。

- [MyBatis 动态 SQL](https://mybatis.org/mybatis-3/dynamic-sql.html)、[Hibernate 6.6 Fetching](https://docs.hibernate.org/orm/6.6/userguide/html_single/#fetching)
- [JDK 21 JFR 性能分析](https://docs.oracle.com/en/java/javase/21/troubleshoot/troubleshoot-performance-issues-using-jfr.html)
- [Node Event Loop / Worker Pool](https://nodejs.org/en/learn/asynchronous-work/dont-block-the-event-loop)、[Prisma 查询优化](https://www.prisma.io/docs/orm/prisma-client/queries/query-optimization-performance)（核对时重定向至 v7，旧项目选择相应版本）
- [Django 5.2 数据库优化](https://docs.djangoproject.com/en/5.2/topics/db/optimization/)、[SQLAlchemy 2.0 关系加载](https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html)、[FastAPI async](https://fastapi.tiangolo.com/async/)
- [Go 连接管理](https://go.dev/doc/database/manage-connections)及[运行诊断](https://go.dev/doc/diagnostics)、[EF Core 查询性能](https://learn.microsoft.com/en-us/ef/core/performance/efficient-querying)
- [React Profiler](https://react.dev/reference/react/Profiler)、[SQLite QUERY PLAN](https://www.sqlite.org/eqp.html)、[MongoDB Explain](https://www.mongodb.com/docs/manual/reference/explain-results/)、[Redis SLOWLOG](https://redis.io/docs/latest/commands/slowlog/)
