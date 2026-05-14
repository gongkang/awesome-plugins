# Awesome Plugins

Claude Code 与 Codex 插件市场

[https://github.com/gongkang/awesome-plugins](https://github.com/gongkang/awesome-plugins)

## 目录结构

```
awesome-plugins/
├── .agents/
│   └── plugins/
│       └── marketplace.json       # Codex 市场清单
├── .claude-plugin/
│   └── marketplace.json           # Claude Code 市场清单
├── plugins/
│   ├── code-plugin/               # 代码插件
│   │   ├── .codex-plugin/
│   │   │   └── plugin.json
│   │   ├── .claude-plugin/
│   │   │   └── plugin.json
│   │   └── skills/
│   │       ├── api-doc-generator/
│   │       ├── api-e2e-test/
│   │       ├── browser-tester/
│   │       ├── generate-codebase-wiki/
│   │       └── project-health-check/
│   └── claw-plugin/               # NanoClaw 插件
│       ├── .codex-plugin/
│       │   └── plugin.json
│       ├── .claude-plugin/
│       │   └── plugin.json
│       ├── commands/
│       └── skills/
│           ├── ai-dialog-search/
│           ├── screen-monitor/
│           └── screen-control/
└── README.md
```

## 插件列表

| 插件 | 描述 | 技能 |
|------|------|------|
| `code-plugin` | 代码相关插件集合 | api-doc-generator, api-e2e-test, browser-tester, generate-codebase-wiki, project-health-check |
| `claw-plugin` | NanoClaw 插件 | ai-dialog-search, screen-monitor, screen-control |

## 安装

### Claude Code

官方插件市场文档：[Create and distribute a plugin marketplace](https://code.claude.com/docs/en/plugin-marketplaces)

官方插件开发文档：[Create plugins](https://code.claude.com/docs/en/plugins)

```bash
# 添加市场
/plugin marketplace add gongkang/awesome-plugins

# 安装插件
/plugin install code-plugin@awesome-plugins
/plugin install claw-plugin@awesome-plugins
```

### Codex

官方插件开发文档：[Build plugins - Codex](https://developers.openai.com/codex/plugins/build)

```bash
# 添加市场
codex plugin marketplace add gongkang/awesome-plugins

# 刷新市场
codex plugin marketplace upgrade awesome-plugins
```

Codex 兼容入口：

- Repo 级市场清单：`.agents/plugins/marketplace.json`
- 插件清单：`plugins/<plugin-name>/.codex-plugin/plugin.json`
- 插件内容路径：`skills` 使用相对插件根目录的 `./skills/`
