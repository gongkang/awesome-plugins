# 仓库约定

新增插件必须同时兼容 Claude Code、Codex 和 Antigravity，分别维护 `.claude-plugin/plugin.json`、`.codex-plugin/plugin.json` 和 `.antigravity-plugin/plugin.json`，并复用插件内的 `skills/<skill-name>/SKILL.md`。

仓库架构、市场清单维护方式和验证命令见 [CLAUDE.md](CLAUDE.md)。新增插件时遵循其中的「新增插件兼容性检查项」。
