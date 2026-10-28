# Java

Java 主要参考[阿里巴巴手册摘要](java-alibaba.md)。本文件负责项目结构、框架适配和现代 JDK 补充，以下补充建议不标作阿里巴巴原条款。任务涉及 MySQL 时另读 [MySQL 条款](java-mysql.md)。

## 先确定技术基线

读取 Maven/Gradle 配置及 wrapper、编译 release/toolchain、依赖版本、父工程和 CI；确认实际 JDK、框架及模块。不要把当前官网版本、宿主机 JDK 或手册示例年代当作项目目标版本。

保留手册原等级，同时区分：项目已经采用的条款、当前适用的新代码指导、与既有约定或新 API 不一致的条款。冲突时说明具体差异和采用理由，不静默改写条款，也不因为引用手册自动迁移全项目。

## 目录与应用分层

无已有约定的常规 Java 应用采用标准构建目录，业务优先组织包；示意中的文件仅在需要时创建：

```text
src/main/java/<组织>/<应用>/
  Application.java              应用启动与框架配置入口（应用项目）
  order/                        订单业务能力
    OrderService.java           对外业务契约（符合暴露服务场景时）
    internal/                   需要隐藏的实现、实际数据访问与适配
src/main/resources/
src/test/java/<组织>/<应用>/
```

- 小应用不必有 `internal` 子包或独立构建模块；普通 Java 库也不需要应用入口。既有按层组织的项目，在相关包内改善，避免为目录一致性搬迁所有文件。
- 在模块内部明确协议入口、业务服务、数据访问和外部适配的职责。手册应用分层第 1 条属于推荐；只有存在通用编排或第三方适配需求时才考虑 Manager 等角色。
- 手册命名风格第 17 条对 SOA 场景中暴露的 Service/DAO 服务接口有强制要求。符合场景时保留接口及实现命名；不要将其扩展为每个私有辅助类都必须配接口。
- DO、DTO、VO 等职责参考手册命名与模型条款。根据数据归属、信任边界及字段差异决定具体模型，不为没有差异的数据机械增加四套转换。
- Java 子包不继承父包的包可见性；拆入子包后检查实际可访问性。包级隐藏、构建模块边界或现有架构检查可以约束内部实现；不能仅凭目录叫 `internal` 就宣称编译器已禁止跨模块访问。
- 模块间通过明确契约调用，避免直接查询另一个业务模块拥有的表或访问其实现。依赖组装放在配置或启动位置，避免业务代码自行定位全局容器。

## Spring 补充：只在使用 Spring 时应用

- 构造器表达必需协作者，避免隐藏依赖和业务代码中取 Bean。不要为使用注入容器把所有值对象和纯规则都注册成组件。
- 启动类、组件扫描、实体与配置扫描位置遵循目标 Spring Boot 版本，不扩大扫描到无关依赖。
- 事务边界对应一个需要原子性的业务操作，核对传播、回滚、方法可见性及代理生效方式。默认代理模式下自调用不会经过代理，不能仅通过添加注解证明事务有效。
- 捕获异常时保留需要传播的失败语义；需要回滚时确认异常路径确实触发回滚。不要无条件给每个方法添加相同的 `rollbackFor`、大事务或独立事务。
- 入参校验、鉴权和资源归属检查各有职责。异常统一映射到项目已有响应契约，内部原因用于排查，不向用户泄露堆栈和敏感参数。

## JDK 补充：按目标版本适配

- 优先使用目标版本支持的日期时间 API，明确时区与格式语义；耗时测量和业务时间不是同一个概念。
- 不可变对象、record、sealed 类型及新 switch 语法仅在版本和序列化/ORM 兼容时使用，不自动升级语言级别。
- 手册并发第 3、4 条中的线程池指导按传统平台线程场景理解。对于目标 JDK 已支持的虚拟线程，核对其任务模型及官方限制，不按旧示例给每个虚拟线程池化，也不直接用传统 P3C 告警否定新 API。
- 对 `BigDecimal` 区分数值相等与表示/scale 相等，业务数值比较按手册使用 `compareTo`；特意比较表示时说明契约差异。金额存储遵循项目约定，偏离手册最小单位整数规则时显式记录，不能静默替换既有存储类型。
- 自动资源管理能覆盖资源时优先使用目标版本支持的 `try-with-resources`；不能自动管理的资源仍需完整的成功、失败和取消清理路径。

## 验证

从构建和 CI 确认项目实际使用的编译、单测、集成、格式及静态检查插件、profile 和模块范围。只运行已配置且兼容目标 JDK 的工具，不强行引入 P3C 或固定插件版本。

设计自查仍需覆盖规则归属、契约及事务；数据库集成检查确认真正的回滚和映射；并发行为检查资源清理与状态正确性。扫描结果是部分证据，不能替代行为验证。

## 补充来源

- [Spring Boot：Structuring Your Code](https://docs.spring.io/spring-boot/reference/using/structuring-your-code.html)
- [Spring Framework：Constructor-based Dependency Injection](https://docs.spring.io/spring-framework/reference/core/beans/dependencies/factory-collaborators.html)
- [Spring Framework：Using @Transactional](https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/annotations.html)
- [Oracle：Virtual Threads，JDK 21](https://docs.oracle.com/en/java/javase/21/core/virtual-threads.html)

核对日期：2026-10-28。Spring 链接为可变的当前文档，使用具体机制前选择与项目依赖一致的版本；JDK 21 链接仅服务于相应虚拟线程补充。
