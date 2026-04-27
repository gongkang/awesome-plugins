---
name: ai-dialog-search
description: |
  用于用户要求询问多个 AI 聊天助手、跨 AI 站点比较或交叉验证回答、一起查询 DeepSeek/Kimi/豆包/Qwen/千问等指定助手，或使用"ai search""AI 搜索""对话搜索""dialog search""多问几个 AI""让几个大模型都回答""交叉验证一下""综合多个 AI 的答案""去我配置好的 AI 网站问一遍""把 DeepSeek、Kimi、豆包的回答汇总""帮我问问 DeepSeek 和 Kimi""去几个 AI 网站查一下"等触发语的场景。本技能用于 AI 对话聚合，不用于普通网页搜索、新闻检索、行情接口或公开网页事实核查。只要用户提到"多个 AI""几个 AI""都回答""交叉验证"等意图，即使没有明确说出站点名称，也应触发本技能。
---

# AI 对话聚合搜索

## 概览

使用这个技能对固定白名单中的多个 AI 对话网站按顺序执行问答。父 agent 负责读取白名单、判断采集等级、归一化问题、派发一个默认子代理承担 collector 任务、接收严格 JSON 结果并综合回答。collector 独占 `chrome-devtools MCP`，按采集等级顺序访问目标站点；网页快照、DOM、流式残片和长原文都留在子代理上下文中，不返回给父 agent。

采集等级分为标准和深入：标准是默认模式，拿到足够可用结果即可停止；高时效或高风险问题需要 2 个实时可用结果；深入模式会尝试所有目标站点。

默认聚焦统一结论；只有用户明确要求比较，或站点之间出现重大冲突时，才列出分歧点。

## 父 agent 约束

本技能触发后，父 agent 进入 AI 对话聚合模式，**只允许**做这些事：

1. 读取本技能文件和 `references/sites.md`
2. 归一化共享提问，派发一个 collector，等待严格 JSON 结果
3. 校验 collector JSON，基于 `results[]` 综合回答
4. 如果 collector 整体失败，报告原因并等待用户明确指示

**禁止**做的事（即使高时效/高风险问题也不例外）：

- 调用普通 `web search`、网页打开、图片搜索、finance/weather 等互联网工具获取答案
- 用 `curl`、`wget`、HTTP API、行情接口、新闻网站获取外部事实
- 亲自使用 `chrome-devtools MCP` 访问任何网页
- collector 失败后自动切换为普通网页搜索或接口查询
- 做外部事实复查、行情补数或新闻补充

## 工作流程

1. 读取 [references/sites.md](./references/sites.md)，构建当前启用的站点列表
2. 判断采集等级：默认 `standard`；用户明确要求深入/全面/全部站点或点名站点"都回答"时使用 `deep`
3. 归一化出一条要发给目标站点的共享提问
4. 创建一个默认子代理执行 collector 任务，必须设置 `fork_context: false`
5. 向 collector 传入：站点列表、采集等级、共享提问、[browser-operations.md](./references/browser-operations.md) 的要点摘录、严格 JSON 输出 schema
6. collector 按 [browser-operations.md](./references/browser-operations.md) 中的步骤访问、提问、提取，返回严格 JSON
7. 父 agent 校验 JSON，基于 `results[]` 融合答案

不要在运行时扩展站点范围。如果用户提到的站点不在 `references/sites.md` 中，停止执行并告知必须先把该站点加入白名单。

## 站点选择规则

- 只使用 `references/sites.md` 中列出的站点，按文件中的顺序访问
- 除非用户明确指定子集，否则优先使用所有 `enabled: yes` 的站点
- 如果站点页面结构明显失效、被限流、出现验证码，或需要当前浏览器不可直接使用的登录态，则跳过
- 记录跳过原因时使用简短且稳定的状态值：`skipped_auth_required`、`skipped_captcha`、`skipped_ui_unavailable`、`skipped_no_answer`、`skipped_timeout`、`skipped_browser_unavailable`
- 如果站点能回答但声明无法获取实时信息、没有数据时间、或只给出模拟推演，记录为 `stale_data`；如果回答明显未完成但可用，记录为 `partial`

## 采集等级

### `standard`（默认）
- collector 按目标站点顺序访问，收集到 **2 个可用结果** 后停止
- 一般问题的可用结果指 `status` 为 `success`、`partial` 或 `stale_data`
- 高时效/高风险问题的实时可用结果只包括 `success` 和带有明确数据时间的 `partial`；`stale_data` 不计入目标数
- **强制提前终止**：一旦获得足够可用结果，立即停止访问后续站点，执行完当前站点的浏览器清理后直接返回 JSON
- 如果所有目标站点都尝试完仍不足目标数，返回已有结果和跳过说明

### `deep`
- 用户明确说"深入、深度、全面、完整、全部、所有站点、跑满、每个站点、都回答"等覆盖性要求时使用
- collector 尝试所有目标站点，不因已获得足够结果而提前停止
- 如果用户点名了一组站点且要求这些站点"都回答"，使用 `deep`，但目标站点只限点名且在白名单内的站点

## Collector 派发约定

父 agent 只创建一个默认子代理承担 collector 任务，不要创建多个代理或让多个代理同时控制 Chrome。如果系统策略禁止创建子代理，说明此技能需要子代理隔离网页解析噪声，不要把页面快照拉进父 agent 上下文。

collector 的任务必须自包含，只包含：当前目标站点信息、采集等级、共享提问、[browser-operations.md](./references/browser-operations.md) 中的必要摘录、严格 JSON 输出 schema。

collector 约束：
- 使用 `fork_context: false`，不继承父 agent 完整上下文
- 只访问白名单中的目标站点，同一站点只提交一次共享提问
- 对每个站点提取后立刻压缩成结构化对象，不保留长原文
- **`standard` 模式下拿到足够可用结果后必须立即停止**，不要继续访问剩余站点
- 完成后只返回严格 JSON，不返回 Markdown、YAML、网页快照或逐 token 思考过程

## 结构化结果协议

collector 最终必须只返回一个 JSON 对象：

```json
{
  "collector_status": "success | partial | failed",
  "collection_level": "standard | deep",
  "data_scope": "回答覆盖的站点、时间范围或 unknown",
  "completion_reason": "usable_target_reached | exhausted_targets | browser_unavailable",
  "results": [
    {
      "site": "站点名称",
      "status": "success | partial | stale_data | skipped_auth_required | skipped_captcha | skipped_ui_unavailable | skipped_no_answer | skipped_timeout | skipped_browser_unavailable",
      "attempted": true,
      "data_time": "回答或数据对应的时间点；没有则写 unknown",
      "answer_summary": ["5-10 条要点，覆盖主要结论、证据、原因、分歧和后续观察；不复制长原文"],
      "key_facts": ["关键数字、结论、判断；信息密集问题尽量保留足够数字和实体名称"],
      "source_links": ["站点回答中给出的来源链接；没有则为空数组"],
      "caveats": ["登录、验证码、超时、数据滞后、回答不完整等限制"]
    }
  ],
  "fatal_caveats": ["collector 级限制；没有则为空数组"]
}
```

如果 `chrome-devtools MCP` 在启动、列页、导航或会话层不可用，直接返回 collector 级失败 JSON（`collector_status: "failed"`, `completion_reason: "browser_unavailable"`）。不要为尚未访问的站点逐个制造失败记录。

## 时效和高风险问题

当用户问题涉及"今天、最新、实时、盘中、收盘、价格、行情、新闻、政策、法规、医疗、法律、金融投资"等高时效或高风险内容时：

- 共享提问必须要求站点返回数据时间点、来源链接，并明确说明无法实时获取时的限制
- 父 agent 不做外部事实复查，只根据各站点返回的 `data_time`、`source_links`、`caveats` 和站点间一致性判断置信度
- 对声明"无法获取实时数据"的回答标记为 `stale_data`，只保留分析框架，不采信其中的实时数字
- collector 不把 `stale_data` 计入标准模式的实时可用目标；必须继续尝试后续站点
- 最终答案必须写明数据时间范围，并保留"不构成投资/医疗/法律建议"等必要提示

## 提问归一化

- 将用户请求收敛为一条适合所有站点使用的共享提问
- 除非用户明确要求按站点定制提问，否则删除站点特定措辞
- 保留会影响答案质量的约束（格式、语言、时间范围、深度要求）
- 如果用户已经明确给出了要发送的完整提问，则直接复用

## 整合规则

- 优先采用被多个站点共同支持的结论
- 对只出现在单一站点的说法降低置信度
- 不要展示站点间的分歧对比，聚焦于综合结论；只有用户明确要求比较或出现重大冲突时才列出分歧
- 正常 AI 对话搜索应保留足够丰富的信息量：核心结论、关键事实、共同点、重要分歧、证据来源、限制和观察点
- 对复杂、研究、金融、新闻或决策类问题，最终答案通常需要 4-8 段或一个紧凑表格
- 主代理直接给出判断，不要让用户做选择题

## 输出格式

默认让用户感觉是在和一个 AI 直接对话，而不是在阅读执行报告。不要固定套用同一个模板。

- 开头直接回答用户问题，优先给判断或结论，不要先罗列站点运行情况
- 把多个站点结果融合成统一口径，用"我认为/更稳妥的判断是/可以这样看"等自然表达承接
- 短问题用 1-3 段自然语言；分析类、研究类和行情类问题要给出足够完整的综合答案
- 信息密集问题可加入小表格；数字、对比、状态或步骤较多时可超过 4 行
- 来源、置信度、跳过站点和限制信息放在结尾；不要默认暴露内部状态码
- 不要复制各站点长原文；只在重大分歧或用户要求比较时列出

## 失败处理

- collector 返回整体失败时，直接告知无法获取有效回答并说明原因
- 如果是 `browser_unavailable`、`profile locked`、`transport closed` 等基础设施故障，说明 AI 对话搜索未能执行，提示用户检查浏览器状态
- 所有站点都失败或被跳过时，直接告知无法获取有效回答
- 只有一个站点成功时，降低置信度标记
- 主代理直接判断结果可用性，不要让用户决定如何处理

## 浏览器操作

collector 的浏览器操作详见 [references/browser-operations.md](./references/browser-operations.md)，包括：

- 浏览器控制约定（单例模式、并发限制）
- 单站点执行步骤（导航、输入、等待、提取）
- 发送消息的正确方法
- 登录态处理
- 回答提取（含各站点完成标志）
- 浏览器清理（单站点清理 + 最终清理）

简要要点：
- collector 是本技能唯一的浏览器控制者，开始前先用 `list_pages` 检查 MCP 是否可用
- 使用 `type_text` + `submitKey: "Enter"` 发送消息，不要优先使用 `fill` + 点击按钮
- 每个站点提取后执行浏览器清理；所有站点完成后执行最终清理（关闭任务页）
- 不要默认用系统命令杀死 Chrome
