# 项目健康度检查报告

**项目**: museum-artwork-platform
**检查时间**: 2026-04-01
**项目类型**: Next.js 14 + TypeScript 前端项目（静态内容站）
**检查方式**: 静态代码分析 + 配置审查

---

## 执行摘要

| 维度 | 问题数 | 严重程度 |
|------|--------|----------|
| 代码质量 | 4 | 中 |
| 架构设计 | 3 | 中 |
| 测试覆盖 | 2 | 低 |
| 性能优化 | 2 | 中 |
| 安全性 | 1 | 低 |
| 依赖管理 | 1 | 低 |

**总计**: 13 个问题（中 8 / 低 5）

---

## 1. 代码质量

### 🟡 中优先级

#### 1.1 未使用的导入 (useState)
**位置**: `components/paged-navigation/PagedNavigator.tsx:3`

```typescript
import { motion, AnimatePresence } from 'framer-motion'
import { usePagedNavigation } from './usePagedNavigation'
import { useMediaQuery } from '@/hooks/useMediaQuery'
import { type ReactElement } from 'react'
// useState 被导入但未使用
```

**建议**: 移除未使用的 `useState` 导入，或启用 ESLint `no-unused-vars` 规则。

#### 1.2 组件职责过重
**位置**: `components/artwork/DetailLoupe.tsx:22-238`

`DetailLoupe` 组件包含超过 200 行代码，同时处理：
- 状态管理（isZoomed, loupePosition, isDragging, imageFailed）
- 事件处理（handlePointerMove, handlePointerDown, handlePointerUp, handleDoubleClick）
- 动画渲染
- 列表渲染

**建议**: 拆分为子组件：
- `LoupeOverlay` - 放大镜覆盖层
- `ZoomedView` - 全屏放大模式
- `DetailMarkers` - 细节标注点

#### 1.3 类型安全边界不清晰
**位置**: `lib/mdx.ts:10-21`

Frontmatter 使用 `unknown` 类型并通过运行时断言转换：

```typescript
interface Frontmatter {
  title?: unknown
  dynasty?: unknown
  material?: unknown
  // ...
}
```

**建议**: 使用 `zod` 或 `valibot` 在解析时进行 schema 验证。

#### 1.4 createElement 与 JSX 混用
**位置**: `components/artwork/DetailLoupe.tsx:94-236`

组件同时使用 `createElement` 和 JSX 语法，降低可读性：

```typescript
if (!image) {
  return createElement(
    'div',
    { className: 'flex h-full items-center justify-center px-8' },
    createElement('p', { className: 'font-body text-gallery-muted' }, '暂无可用于放大的图片')
  )
}
```

**建议**: 统一使用 JSX 语法提升可读性。

---

## 2. 架构设计

### 🟡 中优先级

#### 2.1 路由悬挂链接
**位置**: `components/ui/HiddenNav.tsx:51-57`

导航中包含 `/artwork` 和 `/about` 链接，但对应的页面文件不存在：
- `/artwork` -> 应有 `app/artwork/page.tsx`
- `/about` -> 应有 `app/about/page.tsx`

**建议**: 补齐缺失页面或移除对应导航链接。

#### 2.2 重复的媒体检测逻辑
**位置**: `components/artwork/ArtworkDetail.tsx:18-19`

```typescript
const screens = useMemo(
  () => [
    // ...
  ],
  [artwork]
)
```

组件内部未进行媒体检测，但 `PagedNavigator` 内部使用 `useMediaQuery`。

**建议**: 当前架构可接受，但需确保 `PagedNavigator` 的响应式处理一致。

#### 2.3 服务层与页面层边界模糊
**位置**: `app/artwork/[slug]/page.tsx:27-34`

```typescript
export default function Page({ params }: PageProps) {
  const response = getArtworkDetailPayload(params.slug)
  if (!response.ok) {
    notFound()
  }
  return <ArtworkDetail artwork={response.payload} />
}
```

**建议**: 当前实现简洁，可接受。但若后续接入 API，可考虑引入数据获取层。

---

## 3. 测试覆盖

### 🟢 低优先级

#### 3.1 测试覆盖不完整
**位置**: `tests/` 目录

已有测试：
- `lib/artworkService.test.ts` - 服务层测试
- `lib/mdx.test.ts` - MDX 解析测试
- `tests/components/DetailLoupe.test.tsx` - 仅覆盖错误分支
- `tests/components/Model3D.test.tsx` - 边界情况覆盖
- `tests/components/MultiAngleViewer.test.tsx` - 较完整

缺失测试：
- `ArtworkDetail` 组件集成测试
- `PagedNavigator` 组件测试
- `StoryPanel` 组件测试

#### 3.2 页面层测试缺失
**位置**: `app/artwork/[slug]/page.tsx`

**建议**: 添加页面级集成测试验证：
- 有效 slug 渲染
- 无效 slug 跳转 notFound
- generateMetadata 输出

---

## 4. 性能优化

### 🟡 中优先级

#### 4.1 移动端一次性渲染
**位置**: `components/artwork/ArtworkDetail.tsx:18-51`

移动端模式下，5 个 screen 全部定义在 `screens` 数组中：

```typescript
const screens = useMemo(
  () => [
    { key: 'hero', render: () => <ArtworkHero artwork={artwork} /> },
    { key: 'viewer', render: () => <ArtworkViewer ... /> },
    // ...
  ],
  [artwork]
)
```

**建议**: 使用 React.lazy 和 Suspense 实现按需加载。

#### 4.2 高频事件未节流
**位置**: `components/artwork/MultiAngleViewer.tsx:30-42`

`handlePointerMove` 已使用 `requestAnimationFrame` 节流，设计合理。

**建议**: 当前实现可接受。

---

## 5. 安全性

### 🟢 低优先级

#### 5.1 Content Security Policy 限制严格
**位置**: `next.config.js:17-22`

```javascript
value:
  `default-src 'self'; img-src 'self' data: https://* blob:; ` +
  `style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; ` +
```

`unsafe-inline` 用于内联样式，这是 CSP 的常见权衡。

**建议**: 考虑使用nonce或hash-based CSP（生产环境）。

---

## 6. 依赖管理

### 🟢 低优先级

#### 6.1 依赖版本未锁定
**位置**: `package.json`

所有依赖使用 caret (^) 范围版本：

```json
"next": "14.2.0",
"react": "^18.3.0",
```

**建议**:
- 使用 `npm shrinkwrap` 或 `npm ci` 确保可重现构建
- 或使用 `package-lock.json` 并在 CI 中验证

---

## 积极方面

1. **项目结构清晰**: `app/`, `components/`, `lib/`, `tests/` 目录划分合理
2. **类型定义完善**: 合约类型 (`lib/contracts/`) 和领域模型 (`lib/artwork.ts`) 分离
3. **错误边界处理**: `Model3D` 组件实现了 `ModelRenderBoundary` 错误边界
4. **测试覆盖较好**: 核心组件（Model3D, MultiAngleViewer, DetailLoupe）有边界测试
5. **安全头配置**: Next.js 配置包含 CSP、X-Content-Type-Options 等安全头
6. **MDX 缓存机制**: 使用 `createCachedLoader` 避免重复解析
7. **资源加载降级**: 图片/模型加载失败有优雅降级

---

## 建议优先级

### 立即处理
1. 移除 `PagedNavigator.tsx` 中未使用的 `useState` 导入
2. 补齐 `/artwork` 和 `/about` 页面或移除悬挂链接

### 短期处理
3. 拆分 `DetailLoupe` 组件降低复杂度
4. 添加页面层集成测试

### 中期处理
5. 统一 `createElement` 和 JSX 语法
6. 引入 zod 做 frontmatter 运行时验证

### 长期处理
7. 移动端实现懒加载 screen
8. 完善测试覆盖率

---

## 技术栈概览

| 类别 | 技术 |
|------|------|
| 框架 | Next.js 14.2.0 |
| 语言 | TypeScript 5.4 |
| 样式 | Tailwind CSS 3.4 |
| 3D渲染 | @react-three/fiber + @react-three/drei |
| 动画 | framer-motion 11 |
| 测试 | Vitest 2.1 + jsdom |
| 内容 | MDX + gray-matter |

---

*报告生成时间: 2026-04-01*
