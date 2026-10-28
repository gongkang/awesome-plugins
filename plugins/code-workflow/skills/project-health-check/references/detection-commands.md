# 详细检测命令参考

本文档包含各维度分析的详细检测命令，供子代理参考使用。

## 1. 前后端一致性检测

### API 定义文件检测

```bash
# OpenAPI/Swagger 文件
find . -name "*.yaml" -o -name "*.json" | xargs grep -l "openapi\|swagger" 2>/dev/null

# GraphQL Schema
find . -name "*.graphql" -o -name "schema.gql" 2>/dev/null

# tRPC 路由
find . -name "router.ts" -o -name "trpc.ts" 2>/dev/null
```

### API 路由定义检测

```bash
# Express/Fastify/Koa
grep -r "app\.\(get\|post\|put\|delete\|patch\)" --include="*.js" --include="*.ts"

# FastAPI
grep -r "@\(get\|post\|put\|delete\|patch\)" --include="*.py"

# NestJS
grep -r "@Get\|@Post\|@Put\|@Delete\|@Patch" --include="*.ts"
```

### 前端 API 调用检测

```bash
# fetch/axios
grep -r "fetch\|axios" --include="*.ts" --include="*.tsx" --include="*.js"

# React Query
grep -r "useQuery\|useMutation" --include="*.ts" --include="*.tsx"

# SWR
grep -r "useSWR" --include="*.ts" --include="*.tsx"
```

### 数据模型检测

```bash
# Prisma
find . -name "schema.prisma"

# TypeORM
grep -r "@Entity" --include="*.ts"

# Django
grep -r "class.*Model" --include="*.py"

# SQLAlchemy
grep -r "class.*Base" --include="*.py"
```

---

## 2. 技术债务检测

### TODO/FIXME 统计

```bash
# 统计所有未完成项
grep -rn "TODO\|FIXME\|HACK\|XXX" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.py" --include="*.go" --include="*.java" . 2>/dev/null

# 按类型统计
grep -c "TODO" --include="*.ts" --include="*.js" -r . 2>/dev/null | awk -F: '{sum+=$2} END {print sum}'
grep -c "FIXME" --include="*.ts" --include="*.js" -r . 2>/dev/null | awk -F: '{sum+=$2} END {print sum}'
```

### 过时依赖检测

```bash
# Node.js
npm outdated --json 2>/dev/null || yarn outdated --json 2>/dev/null || pnpm outdated 2>/dev/null

# Python
pip list --outdated --format=json 2>/dev/null

# Go
go list -u -m -json all 2>/dev/null | grep -A3 "Update"

# Java (Maven)
mvn versions:display-dependency-updates 2>/dev/null
```

### 代码重复检测

```bash
# 使用 jscpd
npx jscpd --min-lines 10 --reporters json . 2>/dev/null
```

---

## 3. 安全性检测

### 敏感信息泄露检测

```bash
# 硬编码密钥
grep -rn "password\s*=\s*['\"]\|api_key\s*=\s*['\"]\|secret\s*=\s*['\"]\|token\s*=\s*['\"]" --include="*.ts" --include="*.js" --include="*.py" --include="*.go" . 2>/dev/null

# AWS Keys
grep -rn "AKIA[0-9A-Z]{16}" . 2>/dev/null

# Private Keys
grep -rn "-----BEGIN.*PRIVATE KEY-----" . 2>/dev/null

# .env 文件检查
find . -name ".env*" -not -name ".env.example" 2>/dev/null
```

### 漏洞模式检测

```bash
# SQL 注入风险
grep -rn "execute\|query.*+\|f\".*SELECT" --include="*.py" --include="*.js" --include="*.ts" . 2>/dev/null | grep -v "param\|?"

# XSS 风险
grep -rn "innerHTML\|dangerouslySetInnerHTML\|v-html" --include="*.js" --include="*.ts" --include="*.tsx" --include="*.vue" . 2>/dev/null

# 命令注入风险
grep -rn "exec\|system\|subprocess.call.*shell=True" --include="*.py" --include="*.js" --include="*.go" . 2>/dev/null

# 不安全的随机数
grep -rn "Math.random\|random.random" --include="*.js" --include="*.ts" --include="*.py" . 2>/dev/null | grep -i "token\|key\|password"
```

### 依赖漏洞检测

```bash
# Node.js
npm audit --json 2>/dev/null || yarn audit --json 2>/dev/null || pnpm audit --json 2>/dev/null

# Python
pip-audit 2>/dev/null || safety check --json 2>/dev/null

# Go
govulncheck ./... 2>/dev/null

# Java
./mvnw dependency-check:check 2>/dev/null
```

---

## 4. 性能瓶颈检测

先按 [技术栈](performance-by-stack.md) 选择方法；涉及关系型数据库时再读 [数据库性能分析](database-performance.md)。命令在对应组件根目录运行，缩小到实际语言、框架和存储；不要在所有项目上执行整套候选搜索。

### 技术栈定位

```bash
# 从清单、锁文件和框架配置识别候选，随后读取入口及调用路径确认实际使用
rg --files -g 'package.json' -g '*lock*' -g 'pom.xml' -g 'build.gradle*' -g 'pyproject.toml' -g 'requirements*.txt' -g 'go.mod' -g '*.csproj' -g 'schema.prisma' -g 'settings.py' -g 'next.config.*'
```

结合实际驱动和 ORM provider 确认数据库，不能由 Java 推断 MyBatis、由 Prisma 推断 MySQL，或把前端和 Node 服务当作同一个运行环境。运行时、协程/事件循环或渲染问题按对应参考分析；下列 SQL 搜索仅在有对应访问时使用，不会自动确认慢查、索引未命中或线上高频。

### 查询、索引及运行证据定位

```bash
# 查询和模型候选文件；尊重 ignore，随后按实际源码根目录缩小范围
rg --files -g '*.sql' -g '*Mapper.xml' -g '*.prisma' -g '*.java' -g '*.py' -g '*.go' -g '*.ts' -g '*.tsx' -g '*.js' -g '*.cs'

# SQL、Java 注解/MyBatis 和 ORM 调用；回到文件读取完整语句和动态分支
rg -n -i -g '*.sql' -g '*.xml' -g '*.java' -g '*.py' -g '*.go' -g '*.ts' -g '*.tsx' -g '*.js' -g '*.cs' 'select\b|join\b|@Select|selectList|selectOne|createQueryBuilder|findMany|select_related|prefetch_related|joinedload|selectinload|Preload|ToListAsync|AsEnumerable|Include\(' .

# 索引声明（只证明仓库声明，不能证明已经部署或被实际使用）
rg -n -i -g '*.sql' -g '*.xml' -g '*.prisma' -g '*.java' -g '*.py' -g '*.go' -g '*.ts' -g '*.cs' 'create\s+(unique\s+)?index|add\s+(unique\s+)?(index|key)|primary\s+key|\bkey\s+|@@index|@@unique|@Index|Index\(|indexes\s*=|index:|HasIndex\(' .

# 已提供的本地计划、慢日志或统计导出；没有文件不等于没有慢查
rg --files -g '*explain*' -g '*slow*' -g '*query*stats*' -g '*trace*.json' -g '*digest*'
```

### 循环、分页和关联候选

```bash
# N+1 需要读取循环体、被调函数及 ORM 加载策略，不能由邻近关键字直接定性
rg -n -g '*.java' -g '*.py' -g '*.go' -g '*.ts' -g '*.js' 'for\s*\(|for\s+|\.forEach\(|\.map\(' .

# 分页、计数、聚合和关联：检查是否下推到数据库及结果语义
rg -n -i -g '*.sql' -g '*.xml' -g '*.java' -g '*.py' -g '*.go' -g '*.ts' -g '*.js' 'offset\b|limit\b|count\s*\(|distinct\b|group\s+by|order\s+by|join\b' .
```

别用排除包含 page/limit 的单行来认定缺少分页：调用方可能限制了结果，ORM 也可能在关联后做内存分页。高频多表关联需核对关联基数、排序、count 与实际统计；元数据、普通计划和指纹统计的条件及示例见 [数据库性能分析](database-performance.md)。

### API 与前端性能

```bash
# 追踪等待、并发和池配置；出现串行调用不一定可以并行
rg -n -g '*.ts' -g '*.js' -g '*.py' -g '*.go' -g '*.java' 'await |Promise\.all|gather\(|connectionTimeout|maximumPoolSize|SetMaxOpenConns' .
```

检查每请求 I/O 次数、依赖关系、超时、池等待、响应大小及对象映射开销；提出并行、批量或缓存前确认资源上限和一致性。

```bash
# 已有构建产物大小仅为线索，不为检查自动触发构建或覆盖文件
du -sh dist/ build/ .next/ 2>/dev/null

# 读取相关页面和实际资源加载行为，不以 lazy 数量判断性能
rg -n -g '*.tsx' -g '*.jsx' -g '*.vue' 'lazy|Suspense|dynamic\(|import\(' .
```

优先解读已有 bundle、网络瀑布、长任务或渲染记录。没有运行数据时只报告资源/实现风险，不虚构首屏、长任务或吞吐指标。

---

## 5. 测试覆盖度检测

```bash
# 查找测试文件
find . -name "*.test.*" -o -name "*.spec.*" -o -name "test_*.py" -o -name "*_test.go" 2>/dev/null

# 测试框架配置
find . -name "jest.config.*" -o -name "vitest.config.*" -o -name "pytest.ini" -o -name "setup.cfg" 2>/dev/null

# 运行覆盖率 (Node.js)
npm run test:coverage -- --reporter=json-summary 2>/dev/null

# 运行覆盖率 (Python)
pytest --cov --cov-report=json 2>/dev/null

# 运行覆盖率 (Go)
go test -coverprofile=coverage.out 2>/dev/null
```

---

## 6. 代码质量检测

### Linter 配置检测

```bash
# Linter 配置文件
find . -name ".eslintrc*" -o -name "eslint.config.*" -o -name ".pylintrc" -o -name ".flake8" -o -name "golangci.yml" 2>/dev/null

# Formatter 配置
find . -name ".prettierrc*" -o -name "pyproject.toml" -o -name ".editorconfig" 2>/dev/null
```

### 代码复杂度检测

```bash
# TypeScript/JavaScript
npx escomplex --format json . 2>/dev/null

# Python
radon cc -s -j . 2>/dev/null

# Go
gocyclo -avg . 2>/dev/null
```

---

## 7. 架构健康度检测

### 循环依赖检测

```bash
# TypeScript/JavaScript
npx madge --circular . 2>/dev/null

# Python
pylint --disable=all --enable=cyclic-import . 2>/dev/null

# Go
go list -json ./... 2>/dev/null | grep -A5 "Deps\|Imports"
```

### 分层违规检测

```bash
# 前端组件直接调用数据层
grep -rn "from.*models\|import.*models" --include="*.tsx" --include="*.jsx" --include="*.vue" . 2>/dev/null

# 工具类依赖业务层
grep -rn "from.*services\|from.*controllers" --include="*.ts" --include="*.js" . 2>/dev/null | grep "utils/\|lib/\|helpers/"
```

---

## 8. 文档完整性检测

```bash
# README 文件
find . -maxdepth 2 -name "README*" -o -name "readme*" 2>/dev/null

# API 文档
find . -name "openapi.*" -o -name "swagger.*" -o -name "api-docs" -type d 2>/dev/null

# CONTRIBUTING
find . -maxdepth 2 -name "CONTRIBUTING*" -o -name "contributing*" 2>/dev/null

# CHANGELOG
find . -maxdepth 2 -name "CHANGELOG*" -o -name "changelog*" -o -name "HISTORY*" 2>/dev/null

# 开发环境配置
find . -name "Makefile" -o -name "docker-compose*.yml" -o -name ".devcontainer" 2>/dev/null
```
