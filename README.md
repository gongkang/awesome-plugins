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
│   │       ├── code-review/
│   │       ├── development-guide/
│   │       ├── generate-codebase-wiki/
│   │       └── project-health-check/
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
| `code-workflow` | 代码项目开发流程技能集合 | api-doc-generator, api-e2e-test, browser-tester, code-review, development-guide, generate-codebase-wiki, project-health-check |
| `search` | 搜索与资料聚合技能集合 | ai-dialog-search |
| `notes` | 笔记整理与美化命令集合 | beautify-notes |

`code-review`（代码评审）用于日常改完代码后的轻量检查，默认审查全部未提交改动和未忽略的新文件；静态优先，必要时少量验证，直接在对话返回发现，不自动修复或生成报告。

`development-guide`（开发指南）支持 TS/JS、Python、Java、Go 的项目结构、可读性、模块设计和质量验证，Java 主要参考阿里巴巴《Java 开发手册（黄山版）》1.7.1。既可指导本次开发，也可按要求制定项目指南；旧项目在本次改动范围内渐进改善，复用现有检查工具。

使用示例：

```text
使用 $code-review 审查当前改动。
使用 $development-guide 实现这个功能，保持现有模块边界并运行相关检查。
使用 $development-guide 为当前项目制定开发指南，Java 部分参考阿里巴巴手册。
```

## 安装

### Claude Code

官方插件市场文档：[Create and distribute a plugin marketplace](https://code.claude.com/docs/en/plugin-marketplaces)

官方插件开发文档：[Create plugins](https://code.claude.com/docs/en/plugins)

```bash
# 添加市场
/plugin marketplace add gongkang/awesome-plugins

# 安装插件
/plugin install code-workflow@awesome-plugins
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
- 当前 Codex marketplace 发布 `code-workflow`、`search`；`notes` 目前只有 Claude Code slash command，暂不加入 Codex marketplace。
