# Awesome Plugins

Claude Code 插件市场

[https://github.com/gongkang/awesome-plugins](https://github.com/gongkang/awesome-plugins)

## 目录结构

```
awesome-plugins/
├── .claude-plugin/
│   └── marketplace.json           # 市场清单
├── plugins/
│   ├── code-plugin/               # 代码插件
│   │   ├── .claude-plugin/
│   │   │   └── plugin.json
│   │   └── skills/
│   │       ├── browser-tester/
│   │       └── project-health-check/
│   └── claw-plugin/               # NanoClaw 插件
│       ├── .claude-plugin/
│       │   └── plugin.json
│       └── skills/
│           ├── screen-monitor/
│           └── screen-control/
└── README.md
```

## 插件列表

| 插件 | 描述 | 技能 |
|------|------|------|
| `code-plugin` | 代码相关插件集合 | browser-tester, project-health-check |
| `claw-plugin` | NanoClaw 插件 | screen-monitor, screen-control |

## 安装

```bash
# 添加市场
/plugin marketplace add gongkang/awesome-plugins

# 安装插件
/plugin install code-plugin@awesome-plugins
/plugin install claw-plugin@awesome-plugins
```
