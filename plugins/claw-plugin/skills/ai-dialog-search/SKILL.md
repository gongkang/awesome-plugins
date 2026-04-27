---
name: ai-dialog-search
description: |
  用于用户要求询问多个 AI 聊天助手、跨 AI 站点比较或交叉验证回答、一起查询 DeepSeek/Kimi/豆包/Qwen/千问等指定助手，或使用“ai search”“AI 搜索”“对话搜索”“dialog search”“多问几个 AI”“让几个大模型都回答”“交叉验证一下”“综合多个 AI 的答案”“去我配置好的 AI 网站问一遍”“把 DeepSeek、Kimi、豆包的回答汇总”等触发语的场景。本技能用于 AI 对话聚合，不用于普通网页搜索、新闻检索、行情接口或公开网页事实核查。
---

# AI 对话聚合搜索

## 概览

使用这个技能对固定白名单中的多个 AI 对话网站按顺序执行问答。父 agent 负责读取白名单、判断采集等级、归一化问题、派发一个默认子代理承担 collector 任务、接收严格 JSON 结果并综合回答。collector 独占 `chrome-devtools MCP`，按采集等级顺序访问目标站点；网页快照、DOM、流式残片和长原文都留在子代理上下文中，不返回给父 agent。

采集等级分为标准和深入：标准是默认模式，拿到足够可用结果即可停止；高时效或高风险问题需要 2 个实时可用结果；深入模式会尝试所有目标站点。

默认聚焦统一结论；只有用户明确要求比较，或站点之间出现重大冲突时，才列出分歧点。

## 父 agent 硬边界

一旦本技能被加载，父 agent 就进入 AI 对话聚合模式。除非用户在同一轮明确要求“同时做普通网页搜索/行情接口核查”，或在本技能失败后明确改口要求普通检索，否则父 agent 不得使用任何非白名单信息源补答案。

父 agent 禁止做这些事：

- 调用普通 `web search`、网页打开、图片搜索、finance/weather/sports/time 等互联网工具来获取答案事实。
- 用 `curl`、`wget`、HTTP API、行情接口、新闻网站、搜索引擎、本地脚本抓取外部事实。
- 亲自使用 `chrome-devtools MCP` 访问 AI 对话站点或普通网页；浏览器控制权只属于 collector。
- 在等待 collector 时做外部事实核查、行情补数、新闻补充或来源交叉验证。
- collector 失败后自动切换为普通网页搜索或接口查询。

父 agent 只允许做这些事：

- 读取本技能文件和 `references/sites.md`。
- 归一化共享提问，派发一个 collector，并等待 collector 的严格 JSON。
- 校验 collector JSON，基于 `results[]` 综合回答。
- 如果 collector 整体失败，直接报告 AI 对话聚合未能执行及其原因。
- 在失败说明之后，询问或等待用户明确要求是否改用普通网页检索。

高时效、高风险、金融行情问题也不例外。此类问题只改变共享提问和可用结果标准，不授权父 agent 进行普通网页或行情接口回退。

## 工作流程

1. 读取 [references/sites.md](./references/sites.md)，构建当前启用的站点列表。
2. 判断采集等级：默认 `standard`；用户明确要求深入、全面、全部站点或点名站点“都回答”时使用 `deep`。
3. 归一化出一条要发给目标站点的共享提问。
4. 创建一个默认子代理执行 collector 任务，必须设置 `fork_context: false`；不要依赖或指定名为 `browser-collector` 的特殊 agent type，也不需要给子代理起名。
5. 只向 collector 传入：站点列表、采集等级、可用结果目标数、共享提问、必要的浏览器操作规则、严格 JSON 输出 schema。
6. collector 独占 `chrome-devtools MCP`，按站点列表顺序访问、提问、等待、提取，并把每个站点的结果立即压缩成结构化对象。
7. `standard` 模式下，collector 收集到足够可用结果后停止；如果一般可用结果不足 2 个，或高时效/高风险问题的实时可用结果不足 2 个，则继续尝试后续目标站点直到列表耗尽。
8. `deep` 模式下，collector 尝试所有目标站点，不因已获得足够结果而提前停止。
9. 父 agent 派发 collector 后立即等待 collector 结果；等待期间不得启动普通网页检索、行情接口查询或其他外部事实收集。
10. collector 完成后只返回一个严格 JSON 对象；父 agent 不接收网页快照、DOM、长原文或无关 UI 文本。
11. 父 agent 校验 JSON，直接基于 `results[]` 融合答案，并自然说明成功、部分成功、跳过和限制信息。

不要在运行时扩展站点范围。如果用户提到的站点不在 `references/sites.md` 中，停止执行并明确告知必须先把该站点加入白名单。

## 站点选择规则

- 只使用 `references/sites.md` 中列出的站点。
- 将该文件视为完整白名单，并按文件中的站点顺序访问。
- 除非用户明确指定子集，否则优先使用所有 `enabled: yes` 的站点。
- 如果站点页面结构明显失效、被限流、出现验证码，或者需要当前浏览器不可直接使用的登录态，则跳过该站点。
- 记录跳过原因时，使用简短且稳定的状态值：`skipped_auth_required`、`skipped_captcha`、`skipped_ui_unavailable`、`skipped_no_answer`、`skipped_timeout`、`skipped_browser_unavailable`。
- 如果站点能回答但声明无法获取实时信息、没有数据时间、或只给出模拟推演，记录为 `stale_data`；如果回答明显未完成但可用，记录为 `partial`。

## 采集等级

- `standard` 是默认等级。collector 按目标站点顺序访问，直到得到 2 个可用结果后停止。一般问题的可用结果指 `status` 为 `success`、`partial` 或 `stale_data` 的站点结果。
- 高时效或高风险问题的实时可用结果只包括 `success`，以及带有明确数据时间和可用事实的 `partial`。`stale_data` 不计入目标数，只作为限制样本和分析框架保留；如果只拿到 1 个实时可用结果，继续访问后续站点直到达到 2 个或耗尽目标站点。
- `deep` 是深入等级。用户明确说“深入、深度、全面、完整、全部、所有站点、跑满、每个站点、都回答”等覆盖性要求时使用。collector 尝试所有目标站点。
- 如果用户点名了一组站点且要求这些站点“都回答/全部回答/每个都回答”，使用 `deep`，但目标站点只限点名且在白名单内的站点。
- 如果 `standard` 模式下所有目标站点都尝试完仍不足 2 个可用结果，返回已有结果和跳过说明，不再扩展白名单外站点。

## Collector 派发约定

父 agent 只创建一个默认子代理承担 collector 任务。不要创建多个站点级子代理，也不要让多个代理同时控制 Chrome。父 agent 在派发 prompt 中直接说明“你是 collector”，但不依赖宿主存在专门的 `browser-collector` 角色或 agent type，也不需要为子代理设置名称。

如果当前宿主或系统策略禁止创建子代理，先向用户简短说明此技能需要子代理隔离网页解析噪声；不能获得许可时，直接告知无法按隔离模式执行，不要把页面快照拉进父 agent 上下文。触发本技能后，父 agent 必须遵守“父 agent 硬边界”，不得用普通检索、网页浏览、行情接口或脚本抓取替代 AI 对话聚合流程。

collector 的任务必须自包含，只包含以下信息：

- 当前目标站点名称、URL、notes。
- 采集等级：`standard` 或 `deep`；`standard` 的目标数通常为 2 个可用结果，高时效或高风险问题则需要 2 个实时可用结果。
- 共享提问。
- 本技能中“浏览器控制约定”“单站点执行步骤”“发送消息的正确方法”“登录态处理”“回答提取”“浏览器清理”的必要摘录。
- 严格 JSON 输出 schema。

collector 的约束：

- 不要继承父 agent 的完整上下文；创建时使用 `fork_context: false`。
- 只访问白名单中的目标站点。
- 对同一个站点只提交一次共享提问；必要的重新聚焦/重新按 Enter 属于同一次提交修复。
- 对每个站点提取后立刻压缩成结构化对象，不保留长原文用于最终返回。
- 在 `standard` 模式下，获得足够可用结果后停止访问后续站点；在 `deep` 模式下尝试所有目标站点。
- 完成后只返回严格 JSON，不返回 Markdown、YAML、网页快照、长答案原文或逐 token 思考过程。

父 agent 的职责：

- 校验 collector 返回值是否为严格 JSON。
- 如果 collector 返回整体浏览器故障，直接说明无法获取有效回答。
- 基于 `results[]` 合并答案；优先采用 `success`，谨慎采用 `partial`，降低 `stale_data` 权重，跳过状态只用于覆盖说明。
- 对高时效或高风险问题，必须说明实时有效来源数量、数据时间范围、是否达到目标和置信度。
- 如果 collector 返回 `browser_unavailable`、`profile locked`、`transport closed`、无法列页或无法导航，父 agent 只报告浏览器基础设施故障，不自行杀进程、不重启 Chrome、不改用普通网页搜索；除非用户明确要求调试浏览器或改用普通检索。

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

如果 `chrome-devtools MCP` 在启动、列页、导航或会话层不可用，collector 直接返回：

```json
{
  "collector_status": "failed",
  "collection_level": "standard | deep",
  "data_scope": "unknown",
  "completion_reason": "browser_unavailable",
  "results": [],
  "fatal_caveats": ["skipped_browser_unavailable: 简短说明 MCP 或浏览器不可用原因"]
}
```

不要为尚未访问的站点逐个制造站点失败记录。

## 时效和高风险问题

当用户问题涉及“今天、最新、实时、盘中、收盘、价格、行情、新闻、政策、法规、医疗、法律、金融投资”等高时效或高风险内容时：

- 共享提问必须要求站点返回数据时间点、来源链接，并明确说明无法实时获取时的限制。
- 父 agent 不做外部事实复查，只根据各站点返回的 `data_time`、`source_links`、`caveats` 和站点间一致性判断置信度；这里的外部事实复查包括普通网页搜索、finance 行情工具、`curl`/HTTP API、新闻站点和行情接口。
- 对声明“无法获取实时数据”的回答标记为 `stale_data`，只保留其分析框架，不采信其中的实时数字。
- collector 不把 `stale_data` 计入标准模式的 2 个实时可用目标；必须继续尝试后续站点，直到获得 2 个实时可用结果或目标站点耗尽。
- 最终答案必须写明数据时间范围，并保留“不构成投资/医疗/法律建议”等必要提示。

## 浏览器控制约定

`chrome-devtools MCP` 是单例模式，整个 MCP 服务只连接一个 Chrome 实例。`isolatedContext` 只能在同一 Chrome 内创建隔离页面上下文，不能实现跨进程并发。

- collector 是本技能唯一的浏览器控制者。
- collector 在开始站点访问前，先用 `list_pages` 检查 MCP 是否可用。
- 如果出现 profile locked、transport closed、无法列页、无法导航等浏览器基础设施故障，返回 collector 级失败，不再继续访问站点。
- 不要依赖 `isolatedContext` 做跨站并发。
- 不要默认用系统命令杀死 Chrome；除非用户明确要求调试浏览器进程。

### 单站点执行步骤

collector 对当前站点按以下步骤操作：

1. 使用 `navigate_page` 导航到配置的 URL（在同一标签页内，不要创建新标签）。
2. 检查页面中是否存在可见输入框；输入框 `uid` 每次页面加载后都会变化，不要硬编码 uid，要通过 `placeholder`、`aria-label` 或可见文本动态定位。
3. 检查阻塞项：登录提示、验证码、订阅墙、空壳页面。
4. 站点特殊交互注意事项：
   - **DeepSeek**：提交问题前优先切换到页面上的“专家模式”，并开启“深度思考”；如果控件不可见，继续提问但在 `caveats` 中记录 `deepseek_expert_mode_unavailable` 或 `deepseek_deep_thinking_unavailable`。
   - **Kimi**：如果进入页面后没有自动开启对话（输入框为空或提示“新建会话”），需要先点击“新建会话”链接，再使用 `type_text` 输入。
   - **豆包**：输入框 `placeholder` 通常是“发消息...”，用 `type_text` 发送后，等待回答中出现“请仔细甄别”字样表示回答完成。
5. 使用 `type_text` 向输入框发送消息，并在 `submitKey` 参数传 `"Enter"`。
6. 提交后验证是否真的开始生成回答：
   - 10-15 秒内没有出现新的助手回答容器、流式文本、停止按钮或 loading 状态时，重新聚焦输入框再按一次 `Enter`。
   - 如果仍未提交，尝试点击发送按钮一次。
   - 如果页面只留下用户问题而没有助手回答，记录为 `skipped_no_answer`，不要笼统记为超时。
7. 等待回答完成：
   - 优先观察回答区域文本是否停止明显增长。
   - 出现特定完成标志时提取：豆包是“请仔细甄别”，DeepSeek 是参考来源列表，Qwen 是“停止回答”按钮消失。
   - 如果等待超时（>60秒），提取当前已生成的内容并标记 `partial`。
   - 不要死等某个特定 UI 元素；文本已停止增长且内容充足时可以提取。
8. 用 `take_snapshot` 获取页面快照，从 `StaticText` 节点中提取回答内容。
9. 将当前站点结果压缩成结构化对象，然后执行浏览器清理，再继续下一个目标站点。

### 发送消息的正确方法

在 DeepSeek、Kimi 等大多数 AI 对话站点：

```text
type_text(uid="<输入框uid>", text="你的问题", submitKey="Enter")
```

不要优先使用 `fill` + 点击发送按钮的组合；在某些站点这个组合不会触发表单提交。如果 `type_text` 不可用，再尝试点击发送按钮。

### 登录态处理

chrome-devtools-mcp 连接的 Chrome 位于 `~/.cache/chrome-devtools-mcp/chrome-profile`，是一个可见的实浏览器窗口。

- 首次使用：在 MCP 的 Chrome 窗口中访问各站点，手动登录一次。
- 登录态持久性：在同一 MCP 会话内，登录态会跨页面导航保持。
- 如果某个站点出现登录墙，先检查是否已在 MCP Chrome 中登录过，再决定是否跳过。

### 回答提取

- 优先用 `take_snapshot` 获取当前页面快照，从快照的 `StaticText` 节点中提取回答内容。
- 对带引用、来源卡片或搜索结果面板的站点，补充使用 `evaluate_script` 在回答区域附近提取 `<a href>` 完整链接；如果只能拿到域名或来源标题，在 `caveats` 记录 `source_links_low_resolution`。
- 页面回答可能在流式生成中；等待文本停止明显增长后再提取。
- 各站点的完成标志参考：
  - **DeepSeek**：出现“参考 X 篇资料”列表表示回答完成。
  - **豆包**：出现“内容由豆包 AI 生成，请仔细甄别”表示回答完成。
  - **Qwen/Qianwen**：按钮文字可能不变，观察文本区段标题是否出现（如“风险提示”“总结建议”等收尾段落）；如等待超 60 秒，提取当前内容。
  - **Kimi**：出现“仅供参考”等结语时表示完成。

## 提问归一化

在分发给各站点之前：

- 将用户请求收敛为一条适合所有站点使用的共享提问。
- 除非用户明确要求按站点定制提问，否则删除站点特定措辞。
- 保留会影响答案质量的约束，例如格式、语言、时间范围和深度要求。

如果用户已经明确给出了要发送的完整提问，则直接复用。

## 整合规则

整合时信息要充分，但不要堆原文：

- 优先采用被多个站点共同支持的结论。
- 对只出现在单一站点的说法降低置信度。
- 不要展示站点间的分歧对比，聚焦于综合结论。
- 正常 AI 对话搜索应保留足够丰富的信息量：核心结论、关键事实、各站共同点、重要分歧、证据来源、限制和下一步观察点都应进入最终答案。
- 对复杂、研究、金融、新闻或决策类问题，最终答案通常需要 4-8 段或一个紧凑表格，而不是只给 1-2 段摘要。
- 主代理直接给出判断，不要让用户做选择题。

## 输出格式

默认让用户感觉是在和一个 AI 直接对话，而不是在阅读多个站点的执行报告。不要固定套用同一个模板；根据问题类型选择最自然的呈现。

输出原则：

- 开头直接回答用户问题，优先给判断或结论，不要先罗列站点运行情况。
- 把多个站点的结果融合成统一口径，用“我认为/更稳妥的判断是/可以这样看”等自然表达承接，不要逐站机械复述。
- 短问题用 1-3 段自然语言即可；分析类、研究类和行情类问题要给出足够完整的综合答案，避免过度压缩。
- 信息密集问题可加入一个小表格；表格是可选增强，不是默认格式。数字、对比、状态或步骤较多时可超过 4 行，但要保持可读。
- 来源、置信度、跳过站点和限制信息放在结尾，用一小段或简短表格说明；不要让它们抢在正文前面。
- 不要默认暴露内部状态码；只有调试或用户要求时才展示。
- 不要复制各站点长原文；只在重大分歧或用户要求比较时列出分歧。

可选呈现方式：

```markdown
{直接结论句。}

{自然语言综合回答，按需要分成 3-8 段；信息密集时加入紧凑表格。}

来源与限制：成功参考了 {站点名}；{部分参考/跳过说明，如无则省略}。置信度：{高/中/低}。{必要风险提示}
```

## 失败处理

- 如果 collector 返回整体失败，直接告知用户无法获取有效回答，并简短说明 collector 级限制。
- 如果 collector 失败原因是 `browser_unavailable`、`profile locked`、`transport closed`、无法列页或无法导航，说明 AI 对话聚合没有真正进入站点采集；可以提示用户关闭占用 MCP profile 的 Chrome、恢复 MCP 后重试，但不要执行这些操作，除非用户明确要求。
- 如果所有站点都失败或被跳过，直接告知用户无法获取有效回答。
- 如果只有一个站点成功，降低置信度标记。
- 主代理直接判断结果可用性，不要让用户决定如何处理。
- 不要在失败处理里自动补做普通互联网检索。只有用户明确说“改用普通搜索/联网查/用网页搜索再查一次”等，才开始新的普通检索流程。

## 反例和正确收口

场景：用户说“AI 搜索 今天大盘走势”。

- 正确：触发本技能，归一化为面向白名单 AI 站点的共享提问，派发一个 collector，等待 JSON。若 collector 返回 2 个实时可用结果，则基于这些结果汇总。若 collector 返回 `browser_unavailable`，直接说明 AI 对话搜索未能执行及浏览器原因。
- 错误：collector 运行中或失败后，父 agent 自行调用普通网页搜索、财经搜索、finance 工具、东方财富/新浪接口、`curl` 或脚本获取指数与成交额，再把这些内容当作本技能结果回答。

## 浏览器清理

collector 在每个站点提取并压缩结果后，必须释放当前页面资源：

- 如果存在多个标签页，关闭当前任务页（使用 `close_page`）。
- 如果只剩一个标签页，导航到 `about:blank`，不要强行关闭最后一个页面。
- 不要要求用户手动关闭 Chrome 窗口，除非用户明确要求。

父 agent 不需要再次访问各站点；只基于 collector 返回的 JSON 汇总。

## 参考文件

- 在分发 collector 任务前先读取 [references/sites.md](./references/sites.md)。
- 白名单变化时更新该文件。
- 站点备注保持简短，只保留 URL、启用状态和足够稳定的交互提示。
