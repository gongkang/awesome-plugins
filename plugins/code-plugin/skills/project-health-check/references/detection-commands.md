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

### 数据库查询问题

```bash
# N+1 查询模式
grep -rn "\.forEach\|for.*in" --include="*.ts" --include="*.js" --include="*.py" . -A 3 | grep -i "find\|get\|query\|select"

# SELECT * 模式
grep -rn "SELECT \*\|select(\*)" --include="*.py" --include="*.ts" --include="*.sql" . 2>/dev/null
```

### API 性能问题

```bash
# 缺少分页
grep -rn "find\|list\|get.*all" --include="*.ts" --include="*.py" . | grep -v "page\|limit\|offset\|cursor"

# 同步等待多个请求
grep -rn "await.*await" --include="*.ts" --include="*.js" . 2>/dev/null
```

### 前端性能问题

```bash
# 包大小
du -sh dist/ build/ .next/ 2>/dev/null

# 代码分割
grep -rn "lazy\|Suspense\|dynamic" --include="*.tsx" --include="*.jsx" . 2>/dev/null | wc -l

# 大型图片
find . -name "*.png" -o -name "*.jpg" -size +500k 2>/dev/null
```

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