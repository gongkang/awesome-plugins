# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目定位

这是 `gongkang/awesome-plugins` 插件市场仓库，同时面向 Claude Code 和 Codex 发布插件集合。

- Claude Code 市场清单：`.claude-plugin/marketplace.json`
- Codex 市场清单：`.agents/plugins/marketplace.json`
- 插件源码：`plugins/<plugin-name>/`
- Claude Code 插件清单：`plugins/<plugin-name>/.claude-plugin/plugin.json`
- Codex 插件清单：`plugins/<plugin-name>/.codex-plugin/plugin.json`

当前插件：

- `code-workflow`：代码项目开发流程技能集合（API 文档、API E2E、浏览器测试、代码库 Wiki、项目健康检查）。
- `computer-use`：电脑/屏幕使用相关技能集合（屏幕控制、屏幕监控、GUI 操作、截图感知）。
- `search`：搜索与资料聚合技能集合，当前包含 AI 对话网站聚合搜索。
- `notes`：笔记整理与美化命令集合，当前包含 Markdown 笔记美化 slash command。

## 常用命令

本仓库没有根目录级 package/build/lint 配置；大部分内容是 Markdown 技能、JSON 清单和少量 Python 辅助脚本。运行命令前先在相关技能目录确认是否存在自己的配置。

### screen-control 本地脚本

从技能目录运行更直观，脚本内部也会切到自身所在目录。

```bash
cd plugins/computer-use/skills/screen-control/scripts
python3 sensor.py snapshot --output /tmp/frame.png
python3 sensor.py wait --for stable --timeout 15
python3 control.py locate "搜索按钮"
python3 control.py smart-click "发送按钮"
python3 control.py type "你好"
```

依赖来自 `plugins/computer-use/skills/screen-control/pyproject.toml`。可选能力：

- `vision` extra 使用 OpenAI 兼容多模态定位，读取 `OPENAI_API_KEY`、`OPENAI_MODEL`、`OPENAI_BASE_URL` 或用户 `~/.env`。
- `ocr` extra 需要 `pytesseract`，macOS 还需要系统 `tesseract`。
- `macos` extra 提供 Accessibility API 所需的 PyObjC 依赖。

### screen-monitor 本地脚本

```bash
cd plugins/computer-use/skills/screen-monitor/scripts
python3 monitor.py start --fps 5 --buffer 10
python3 monitor.py status
python3 monitor.py keyframe --output /tmp/check.png
python3 monitor.py wait-change --timeout 60 --output /tmp/changed.png
python3 monitor.py wait-stable --timeout 30
python3 monitor.py stop
```

该脚本使用 `/tmp/screen_monitor_state.json`、`/tmp/screen_monitor.pid`、`/tmp/screen_monitor_frames` 保存运行状态和帧。

### generate-codebase-wiki 辅助脚本

```bash
# 生成当前仓库的事实快照（Markdown）
python3 plugins/code-workflow/skills/generate-codebase-wiki/scripts/repo_snapshot.py . --format markdown

# 准备 Wiki 输出目录：合并模式
python3 plugins/code-workflow/skills/generate-codebase-wiki/scripts/prepare_wiki_output.py prepare docs/wiki --mode merge

# 覆盖更新已有生成文件（依赖 .wiki-manifest.json）
python3 plugins/code-workflow/skills/generate-codebase-wiki/scripts/prepare_wiki_output.py prepare docs/wiki --mode overwrite

# 写入/刷新生成清单
python3 plugins/code-workflow/skills/generate-codebase-wiki/scripts/prepare_wiki_output.py manifest docs/wiki
```

### 插件安装/市场命令（来自 README）

Claude Code：

```bash
/plugin marketplace add gongkang/awesome-plugins
/plugin install code-workflow@awesome-plugins
/plugin install computer-use@awesome-plugins
/plugin install search@awesome-plugins
/plugin install notes@awesome-plugins
```

Codex：

```bash
codex plugin marketplace add gongkang/awesome-plugins
codex plugin marketplace upgrade awesome-plugins
```

当前 Codex marketplace 发布 `code-workflow`、`computer-use`、`search`；`notes` 目前只有 Claude Code slash command，暂不加入 Codex marketplace。

### 插件结构验证命令

修改插件目录、manifest 或 marketplace 后，运行以下命令做结构验证：

```bash
# 验证 marketplace JSON
python3 -m json.tool .claude-plugin/marketplace.json >/dev/null
python3 -m json.tool .agents/plugins/marketplace.json >/dev/null

# 验证所有插件 manifest JSON
for file in plugins/*/.claude-plugin/plugin.json plugins/*/.codex-plugin/plugin.json; do
  python3 -m json.tool "$file" >/dev/null
done

# 检查 manifest name 是否与插件目录名一致
python3 - <<'PY'
import json
from pathlib import Path
for pattern in ("*/.claude-plugin/plugin.json", "*/.codex-plugin/plugin.json"):
    for path in sorted(Path("plugins").glob(pattern)):
        plugin_dir = path.parents[1].name
        data = json.loads(path.read_text())
        assert data["name"] == plugin_dir, (path, data["name"], plugin_dir)
print("plugin manifests ok")
PY
```

## 架构与目录约定

### 双市场结构

仓库根目录维护两套市场入口：

- `.claude-plugin/marketplace.json` 使用 Claude Code marketplace schema，插件条目通过 `source: "./plugins/<name>"` 指向本仓库插件目录。
- `.agents/plugins/marketplace.json` 是 Codex 兼容市场清单，插件条目通过 `source.path: "./plugins/<name>"` 指向同一插件目录。

新增、重命名或删除插件时，需要同步更新这两个市场清单，并同步维护插件内部的 `.claude-plugin/plugin.json` 与 `.codex-plugin/plugin.json`。

### 插件目录结构

每个插件位于 `plugins/<plugin-name>/`，遵循 Claude Code 插件约定：

- `.claude-plugin/plugin.json`：Claude Code 插件 manifest。
- `.codex-plugin/plugin.json`：Codex 兼容 manifest。
- `commands/`：slash command Markdown 文件（目前 `notes` 使用）。
- `skills/<skill-name>/SKILL.md`：技能定义。技能的脚本、参考资料、eval 放在该技能目录下的 `scripts/`、`references/`、`evals/` 等子目录。
- 当前仓库没有插件级 hooks 或 MCP server 配置。

Claude Code manifest 中，`commands` / `skills` 字段使用数组形式（例如 `['./skills/']`）；Codex manifest 中，`skills` 使用相对插件根目录的字符串路径（例如 `"./skills/"`）。

### code-workflow

`plugins/code-workflow` 是项目开发流程技能插件，没有命令。技能分为两类：

- 纯指令技能：`api-doc-generator`、`api-e2e-test`、`browser-tester`、`project-health-check` 主要由 `SKILL.md` 描述工作流、约束和输出格式。
- 带辅助脚本的技能：`generate-codebase-wiki` 除 `SKILL.md` 外还有 `scripts/prepare_wiki_output.py`、`scripts/repo_snapshot.py` 和 `references/page-templates.md`。脚本是跨项目生成 Wiki 时的安全准备、快照和清单工具。

### computer-use

`plugins/computer-use` 是电脑/屏幕使用技能插件，当前包含：

- `skills/screen-control`：按需截图、定位和 GUI 操作技能。核心脚本在 `scripts/control.py`、`scripts/sensor.py`、`scripts/locators.py`，共享工具在 `scripts/utils/`。
- `skills/screen-monitor`：持续录屏、变化检测和等待条件技能。核心脚本在 `scripts/monitor.py`，与 `screen-control` 共享相似的检测工具模式。

`screen-control` 与 `screen-monitor` 的分工：前者执行一次性 GUI 检查/点击/输入/打开应用等操作；后者持续观察屏幕、等待变化/稳定/文字出现或录制过程。

### search

`plugins/search` 是搜索与资料聚合技能插件，当前包含：

- `skills/ai-dialog-search`：AI 对话网站聚合搜索技能，站点白名单和浏览器操作规则在 `references/`，另有 `agents/openai.yaml` 和 eval 数据。

### notes

`plugins/notes` 是笔记整理与美化命令插件，当前包含：

- `commands/beautify-notes.md`：Markdown 笔记美化 slash command。

## 编辑注意事项

- 修改技能触发条件时，优先编辑对应 `SKILL.md` 的 frontmatter `description`；这是技能是否被自动选择的关键字段。
- 修改插件能力、路径或元数据时，同时检查 Claude Code 与 Codex 两份 manifest，避免市场信息不一致。
- 技能内引用辅助脚本或参考文件时，使用相对技能目录的路径并保持目录自包含；不要依赖仓库根目录作为运行时工作目录。
- 不要提交本地缓存和运行产物：`.claude/`、`*.local.json`、`.pytest_cache/`、`__pycache__/`、`.DS_Store`、`node_modules/`、`.venv/` 已在 `.gitignore` 中列出。
