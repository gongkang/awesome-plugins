# 项目健康度改善执行计划

**项目**: museum-artwork-platform
**计划制定时间**: 2026-04-01
**基于**: 健康度分析报告 v1.0

---

## 执行摘要

本计划基于健康度分析报告，将改善工作分为 4 个阶段，总计 13 项任务。

| 阶段 | 优先级 | 任务数 | 预计工作量大 |
|------|--------|--------|--------------|
| P0 - 紧急 | 立即处理 | 2 | 小 |
| P1 - 高优先级 | 短期处理 | 4 | 中 |
| P2 - 中优先级 | 中期处理 | 4 | 中 |
| P3 - 低优先级 | 长期优化 | 3 | 小 |

---

## 阶段 0：紧急处理（P0）

### 0.1 验证测试链路

**问题**：无法确认 `npm test` 是否能正常执行。

**验证步骤**：
```bash
npm test
npm run test:coverage
```

**成功标准**：
- `npm test` 执行无错误退出
- 生成覆盖率报告（若支持）

**负责人**：开发者本地验证
**预计时间**：10 分钟

---

### 0.2 修复测试执行问题

**问题**：如果测试失败，定位并修复问题。

**常见问题排查**：
1. vitest 版本兼容性
2. jsdom 环境配置
3. Mock 配置正确性

**成功标准**：测试套件全部通过
**预计时间**：30 分钟（若有问题）

---

## 阶段 1：高优先级改善（P1）

### 1.1 补充 PagedNavigator 测试

**问题**：核心导航组件无测试覆盖。

**任务清单**：
- [ ] 创建 `tests/components/PagedNavigator.test.tsx`
- [ ] 测试移动端/桌面端渲染分支
- [ ] 测试导航按钮禁用状态
- [ ] 测试页码指示器交互
- [ ] 测试空 screens 数组边界

**测试用例示例**：
```typescript
it('disables prev button on first page', () => { ... })
it('disables next button on last page', () => { ... })
it('navigates to correct page on indicator click', () => { ... })
```

**预计时间**：2 小时
**影响**：提高核心路径测试覆盖率约 8-10%

---

### 1.2 补充 usePagedNavigation Hook 测试

**问题**：核心 hook 无单元测试。

**任务清单**：
- [ ] 创建 `tests/components/usePagedNavigation.test.ts`
- [ ] 测试 currentPage 初始状态
- [ ] 测试 next/prev 边界（到边界后行为）
- [ ] 测试 navigateTo 跳转
- [ ] 测试 loop: true 循环模式
- [ ] 测试 total=0 边界情况

**预计时间**：1.5 小时

---

### 1.3 补充 DetailLoupe 正常路径测试

**问题**：仅覆盖异常分支，正常渲染路径未测试。

**任务清单**：
- [ ] 扩展 `tests/components/DetailLoupe.test.tsx`
- [ ] 添加图片正常加载测试
- [ ] 添加鼠标移动放大镜显示测试
- [ ] 添加多 details 注解渲染测试
- [ ] 测试放大镜位置计算逻辑

**预计时间**：1.5 小时

---

### 1.4 补充 useMediaQuery Hook 测试

**问题**：公共 hook 应有单元测试。

**任务清单**：
- [ ] 创建 `tests/hooks/useMediaQuery.test.ts`
- [ ] 测试媒体查询匹配/不匹配状态
- [ ] 测试媒体查询变化监听
- [ ] 测试清理函数

**预计时间**：1 小时

---

## 阶段 2：中优先级改善（P2）

### 2.1 重构 DetailLoupe 组件

**问题**：组件职责过重，认知负担高。

**重构目标**：
```
DetailLoupe/
├── DetailLoupe.tsx          # 主组件：状态管理
├── DetailLoupeImage.tsx     # 图片渲染与错误处理
├── DetailLoupeLens.tsx      # 放大镜 lens 渲染
└── DetailLoupeAnnotations.tsx  # 注解列表渲染
```

**任务清单**：
- [ ] 分析现有组件职责
- [ ] 拆分子组件
- [ ] 保持 API 向后兼容
- [ ] 更新测试

**预计时间**：3 小时

---

### 2.2 优化 usePagedNavigation 边界处理

**问题**：total=0 或无效值时可能异常。

**任务清单**：
- [ ] 添加 total 最小值校验（至少为 1）
- [ ] 添加无效 total 时的降级行为
- [ ] 添加边界值测试用例

**代码示例**：
```typescript
// 在 usePagedNavigation 中
const safeTotal = Math.max(1, total)
const validPage = Math.min(currentPage, safeTotal - 1)
```

**预计时间**：30 分钟

---

### 2.3 修复 Key 使用问题

**问题**：使用数组索引作 key 可能导致不必要的重新渲染。

**位置**：
- `components/artwork/ArtworkDetail.tsx:67`

**任务清单**：
- [ ] 检查 screens.map 中的 key 使用
- [ ] 确保使用稳定的业务标识（如 `screen.key`）

**注意**：需确认 `screen.key` 的唯一性和稳定性

**预计时间**：15 分钟

---

### 2.4 清理未使用导入

**问题**：`components/paged-navigation/PagedNavigator.tsx:3` 导入未使用的 `useState`。

**任务清单**：
- [ ] 移除未使用的 useState 导入
- [ ] 运行 lint 确认无新警告

**预计时间**：5 分钟

---

## 阶段 3：低优先级优化（P3）

### 3.1 高频事件节流优化

**问题**：DetailLoupe 和 MultiAngleViewer 的 onMouseMove 可能导致性能问题。

**任务清单**：
- [ ] 在 DetailLoupe 中添加 requestAnimationFrame 节流
- [ ] 在 MultiAngleViewer 中添加节流
- [ ] 对比优化前后性能

**预计时间**：1.5 小时

---

### 3.2 图片加载优化

**问题**：next/image 缺少 sizes 配置。

**任务清单**：
- [ ] 在 MultiAngleViewer 中添加 sizes 属性
- [ ] 审查所有 next/image 使用场景
- [ ] 确保非首屏图片不使用 priority

**预计时间**：30 分钟

---

### 3.3 建立性能基准

**任务清单**：
- [ ] 配置 Lighthouse CI
- [ ] 建立性能指标基准（LCP、CLS、INP）
- [ ] 在 PR 中自动化性能检查

**预计时间**：2 小时

---

## 执行时间线

```
Week 1:
├── P0: 测试链路验证
├── P1: 1.1-1.4 测试补充（并行）

Week 2:
├── P2: 2.1-2.4 代码质量改善

Week 3-4:
└── P3: 性能优化任务
```

---

## 成功指标

| 指标 | 当前 | 目标 |
|------|------|------|
| 测试覆盖率 | ~40% | >70% |
| 核心组件覆盖率 | ~30% | >80% |
| ESLint 警告 | 0 | 0 |
| 性能分数（Lighthouse） | 未测 | >90 |

---

## 风险管理

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 测试重构导致现有测试失败 | 中 | 分阶段提交，充分测试 |
| DetailLoupe 重构破坏现有行为 | 中 | 保持 API 兼容，添加集成测试 |
| 性能优化引入新 bug | 低 | 充分测试，灰度发布 |

---

## 后续行动

1. [ ] 确认是否按此计划执行
2. [ ] 分配负责人
3. [ ] 建立周会同步进度
4. [ ] 第一个 sprint 结束后复盘

---

*计划制定时间: 2026-04-01*
