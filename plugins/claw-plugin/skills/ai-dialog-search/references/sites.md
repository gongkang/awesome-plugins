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

## 如何添加新站点

在"当前站点"部分新增一个区块，格式如下：

```md
### 站点名称
- enabled: yes
- url: https://example.com/
- notes: 简短描述页面交互要点，如输入框位置、特殊按钮、完成标志等
```

添加后，本技能自动在下次执行时包含该站点。只使用 `enabled: yes` 的站点。

## 当前站点

### DeepSeek
- enabled: yes
- url: https://chat.deepseek.com/
- notes: 交互细节见 [browser-operations.md](./browser-operations.md) 的 DeepSeek 专区。

### Qianwen（国内版）
- enabled: yes
- url: https://qianwen.com/
- notes: 交互细节见 [browser-operations.md](./browser-operations.md) 的 Qwen/Qianwen 专区。如需登录则跳过。

### Kimi
- enabled: yes
- url: https://www.kimi.com/
- notes: 交互细节见 [browser-operations.md](./browser-operations.md) 的 Kimi 专区。如出现"算力不足"则跳过。

### 豆包
- enabled: yes
- url: https://www.doubao.com/
- notes: 交互细节见 [browser-operations.md](./browser-operations.md) 的豆包专区。如果出现验证码，记为 `skipped_captcha`。
