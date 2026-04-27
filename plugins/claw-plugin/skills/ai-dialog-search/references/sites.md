# 允许访问的 AI 对话网站

在这里维护站点白名单。只有列在本文件中的站点，`ai-dialog-search` 才允许访问。

## 格式

每个站点使用一个区块：

```md
### 站点名称
- enabled: yes
- url: https://example.com/
- notes: 可选。填写少量稳定的页面提示，例如输入框通常出现在哪里，或优先打开哪个落地页更稳妥。
```

## 当前站点

### DeepSeek
- enabled: yes
- url: https://chat.deepseek.com/
- notes: 打开主聊天页后检查输入框是否可见；如果页面跳到登录页且当前没有可用会话，则以 `skipped_auth_required` 跳过。提交问题前先切换到"专家模式"，并开启"深度思考"；通过可见文本或单选按钮状态定位，不要硬编码 uid。如果控件不可见，继续提问但在 `caveats` 中记录 `deepseek_expert_mode_unavailable` 或 `deepseek_deep_thinking_unavailable`。回答通常会给出“已阅读 X 个网页”或引用链接；高时效问题优先提取数据时间和来源链接。

### Qianwen（国内版）
- enabled: yes
- url: https://qianwen.com/
- notes: 主聊天页面；如需登录则跳过。等待“停止回答”按钮消失后再提取；高时效问题优先提取回答开头的数据时间点。

### Kimi
- enabled: yes
- url: https://www.kimi.com/
- notes: 主聊天页面；如果进入后没有自动开启对话（输入框为空），需要先点击"新建会话"链接再输入。提交后如果只出现用户问题、没有助手回答，重新聚焦输入框按 Enter，再尝试点击发送按钮；仍无回答则记为 `skipped_no_answer`。如出现"算力不足"则跳过（服务器过载，非技能问题）。

### 豆包
- enabled: yes
- url: https://www.doubao.com/
- notes: 主聊天页面，检查输入框是否可见；如果跳转到登录或订阅页面则跳过。如果出现验证码，记为 `skipped_captcha`，不要尝试破解验证码。

### Qwen（国际版）
- enabled: yes
- url: https://chat.qwen.ai/
- notes: 主聊天页面，使用前检查是否已登录；如果显示访客模式或登录墙则跳过。若回答声明无法获取实时数据或仅做模拟推演，记录为 `stale_data`，最终汇总时降低权重。
