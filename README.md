# Awesome Plugins

Claude Code 与 Codex 插件市场

[https://github.com/gongkang/awesome-plugins](https://github.com/gongkang/awesome-plugins)

## 目录结构

```text
awesome-plugins/
├── .agents/
│   └── plugins/
│       └── marketplace.json       # Codex 市场清单
├── .claude-plugin/
│   └── marketplace.json           # Claude Code 市场清单
├── plugins/
│   ├── code-workflow/             # 代码项目开发流程技能
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
│   ├── computer-use/              # 屏幕控制与屏幕监控技能
│   │   ├── .codex-plugin/
│   │   │   └── plugin.json
│   │   ├── .claude-plugin/
│   │   │   └── plugin.json
│   │   └── skills/
│   │       ├── screen-control/
│   │       └── screen-monitor/
│   ├── search/                    # 搜索与资料聚合技能
│   │   ├── .codex-plugin/
│   │   │   └── plugin.json
│   │   ├── .claude-plugin/
│   │   │   └── plugin.json
│   │   └── skills/
│   │       └── ai-dialog-search/
│   └── notes/                     # 笔记整理与美化命令
│       ├── .codex-plugin/
│       │   └── plugin.json
│       ├── .claude-plugin/
│       │   └── plugin.json
│       └── commands/
│           └── beautify-notes.md
└── README.md
```

## 插件列表

| 插件 | 描述 | 当前能力 |
|------|------|----------|
| `code-workflow` | 代码项目开发流程技能集合 | api-doc-generator, api-e2e-test, browser-tester, generate-codebase-wiki, project-health-check |
| `computer-use` | 屏幕控制与屏幕监控技能集合 | screen-control, screen-monitor |
| `search` | 搜索与资料聚合技能集合 | ai-dialog-search |
| `notes` | 笔记整理与美化命令集合 | beautify-notes |

## 安装

### Claude Code

官方插件市场文档：[Create and distribute a plugin marketplace](https://code.claude.com/docs/en/plugin-marketplaces)

官方插件开发文档：[Create plugins](https://code.claude.com/docs/en/plugins)

```bash
# 添加市场
/plugin marketplace add gongkang/awesome-plugins

# 安装插件
/plugin install code-workflow@awesome-plugins
/plugin install computer-use@awesome-plugins
/plugin install search@awesome-plugins
/plugin install notes@awesome-plugins
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
- 当前 Codex marketplace 发布 `code-workflow`、`computer-use`、`search`；`notes` 目前只有 Claude Code slash command，暂不加入 Codex marketplace。
