#!/usr/bin/env python3
"""Collect deterministic repository facts for codebase wiki generation.
收集仓库事实用于代码库 Wiki 生成。
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable


IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "vendor",
    "dist",
    "build",
    "out",
    "target",
    ".next",
    ".turbo",
    ".venv",
    "venv",
    "__pycache__",
}

MANIFEST_NAMES = {
    "package.json",
    "pnpm-workspace.yaml",
    "yarn.lock",
    "package-lock.json",
    "turbo.json",
    "nx.json",
    "pyproject.toml",
    "requirements.txt",
    "poetry.lock",
    "Cargo.toml",
    "Cargo.lock",
    "go.mod",
    "go.sum",
    "pom.xml",
    "build.gradle",
    "settings.gradle",
    "Makefile",
    "Dockerfile",
    "docker-compose.yml",
    "compose.yaml",
}

DOC_NAMES = {
    "README.md",
    "README",
    "CONTRIBUTING.md",
    "ARCHITECTURE.md",
    "SECURITY.md",
    "CHANGELOG.md",
}

CI_PATH_PREFIXES = (
    ".github/workflows/",
    ".circleci/",
    ".gitlab-ci",
    "azure-pipelines",
    "Jenkinsfile",
)

SOURCE_ROOT_NAMES = {
    "src",
    "app",
    "apps",
    "packages",
    "services",
    "server",
    "client",
    "lib",
    "internal",
    "cmd",
    "crates",
    "extensions",
    "modules",
}

NON_SOURCE_TOP_DIRS = {
    ".github",
    "docs",
    "doc",
    "test",
    "tests",
    "t",
    "examples",
    "example",
    "requirements",
}

MODULE_MANIFEST_NAMES = {
    "package.json",
    "pyproject.toml",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "requirements.txt",
}

ENTRYPOINT_STEMS = {
    "__main__",
    "main",
    "index",
    "app",
    "server",
    "cli",
    "startup",
    "bootstrap",
    "manage",
}

ENTRYPOINT_EXTENSIONS = {
    "",
    ".cjs",
    ".cs",
    ".go",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".mjs",
    ".php",
    ".py",
    ".rb",
    ".rs",
    ".sh",
    ".swift",
    ".ts",
    ".tsx",
}


def run(cmd: list[str], cwd: Path) -> str | None:
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def discover_root(path: Path) -> Path:
    resolved = path.resolve()
    git_root = run(["git", "rev-parse", "--show-toplevel"], resolved)
    return Path(git_root).resolve() if git_root else resolved


def git_files(root: Path) -> list[str]:
    output = run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], root)
    if output:
        return [line for line in output.splitlines() if line]
    return walk_files(root)


def walk_files(root: Path) -> list[str]:
    files: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in IGNORED_DIRS]
        for filename in filenames:
            path = Path(dirpath, filename)
            files.append(path.relative_to(root).as_posix())
    return sorted(files)


def top_dir(path: str) -> str:
    return path.split("/", 1)[0] if "/" in path else "."


def extension(path: str) -> str:
    suffix = Path(path).suffix.lower()
    return suffix if suffix else "[no extension]"


def is_doc(path: str) -> bool:
    name = Path(path).name
    return (
        name in DOC_NAMES
        or path.startswith("docs/")
        or path.startswith(".github/instructions/")
        or "/docs/" in path
        or "/adr/" in path.lower()
        or "architecture" in path.lower()
    )


def is_ci(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in CI_PATH_PREFIXES)


def likely_entrypoint(path: str) -> bool:
    if is_doc(path):
        return False
    p = Path(path)
    if (
        top_dir(path) in {"test", "tests", "t"}
        or "/tests/" in path
        or "/test/" in path
        or "/testing/" in path
    ):
        return False
    if p.suffix.lower() not in ENTRYPOINT_EXTENSIONS:
        return False
    stem = p.stem.lower()
    if stem == "__main__":
        return True
    if stem in {"main", "manage"}:
        return True
    if stem in ENTRYPOINT_STEMS:
        if len(p.parts) <= 2:
            return True
        if len(p.parts) <= 3 and p.parts[0] in SOURCE_ROOT_NAMES:
            return True
        if len(p.parts) >= 2 and p.parts[-2] in {"bin", "cmd", "scripts"}:
            return True
        return False
    lowered = path.lower()
    return any(token in lowered for token in ("/main.", "/server.", "/cli.", "/bootstrap."))


def limited(items: Iterable[str], limit: int) -> list[str]:
    return list(items)[:limit]


def likely_source_root(path: str) -> str | None:
    parts = path.split("/")
    if not parts:
        return None
    if parts[0] in SOURCE_ROOT_NAMES:
        return parts[0]
    if "src" not in parts:
        return None

    idx = parts.index("src")
    if idx + 2 < len(parts) and parts[idx + 1] in {"main", "test"}:
        return "/".join(parts[: idx + 3])
    return "/".join(parts[: idx + 1])


def manifest_module_root(path: str) -> str | None:
    if Path(path).name not in MODULE_MANIFEST_NAMES:
        return None
    parent = Path(path).parent.as_posix()
    return "." if parent == "." else parent


def discover_python_package_roots(files: Iterable[str]) -> list[str]:
    """Find importable Python package roots such as `celery` or `src/pkg`."""

    candidates: set[str] = set()
    for path in files:
        p = Path(path)
        if p.name != "__init__.py" or len(p.parts) < 2:
            continue
        parts = p.parts[:-1]
        if parts[0] in NON_SOURCE_TOP_DIRS:
            continue

        if len(parts) == 1:
            candidates.add(parts[0])
            continue

        if len(parts) >= 2 and parts[-2] == "src":
            candidates.add("/".join(parts))

    roots: list[str] = []
    for candidate in sorted(candidates, key=lambda item: (len(Path(item).parts), item)):
        if not any(candidate.startswith(root + "/") for root in roots):
            roots.append(candidate)
    return roots


def collect(root: Path) -> dict:
    files = git_files(root)
    by_ext = Counter(extension(path) for path in files)
    by_top_dir = Counter(top_dir(path) for path in files)

    manifests = sorted(path for path in files if Path(path).name in MANIFEST_NAMES)
    source_root_counts = Counter(
        root_path for path in files if (root_path := likely_source_root(path))
    )
    for root_path in discover_python_package_roots(files):
        source_root_counts[root_path] += sum(
            1 for path in files if path == root_path or path.startswith(root_path + "/")
        )
    module_roots = sorted(
        root_path for path in files if (root_path := manifest_module_root(path))
    )
    docs = sorted(path for path in files if is_doc(path))
    ci = sorted(path for path in files if is_ci(path))
    entrypoints = sorted(path for path in files if likely_entrypoint(path))

    tests_by_dir: dict[str, int] = defaultdict(int)
    for path in files:
        lowered = path.lower()
        if (
            "/test/" in lowered
            or "/tests/" in lowered
            or lowered.endswith((".test.ts", ".test.js", ".spec.ts", ".spec.js", "_test.go"))
            or "/__tests__/" in lowered
        ):
            tests_by_dir[top_dir(path)] += 1

    return {
        "root": str(root),
        "git": {
            "commit": run(["git", "rev-parse", "HEAD"], root),
            "branch": run(["git", "branch", "--show-current"], root),
            "remote_origin": run(["git", "remote", "get-url", "origin"], root),
            "dirty": bool(run(["git", "status", "--porcelain"], root)),
        },
        "files": {
            "count": len(files),
            "top_extensions": by_ext.most_common(20),
            "top_directories": by_top_dir.most_common(30),
        },
        "source_roots": limited(
            (root_path for root_path, _ in source_root_counts.most_common(80)),
            80,
        ),
        "module_roots": limited(module_roots, 120),
        "manifests": limited(manifests, 80),
        "ci": limited(ci, 80),
        "docs": limited(docs, 120),
        "likely_entrypoints": limited(entrypoints, 120),
        "tests_by_top_directory": sorted(tests_by_dir.items(), key=lambda item: (-item[1], item[0])),
    }


def to_markdown(snapshot: dict) -> str:
    lines = [
        "# 仓库证据快照",
        "",
        f"- 根目录: `{snapshot['root']}`",
        f"- 提交: `{snapshot['git']['commit'] or 'unknown'}`",
        f"- 分支: `{snapshot['git']['branch'] or 'unknown'}`",
        f"- 远程: `{snapshot['git']['remote_origin'] or 'unknown'}`",
        f"- 工作树脏: `{snapshot['git']['dirty']}`",
        f"- 跟踪/发现的文件: `{snapshot['files']['count']}`",
        "",
        "## 顶层目录",
        "",
    ]
    for directory, count in snapshot["files"]["top_directories"]:
        lines.append(f"- `{directory}`: {count}")

    lines.extend(["", "## 顶层扩展", ""])
    for ext, count in snapshot["files"]["top_extensions"]:
        lines.append(f"- `{ext}`: {count}")

    sections = [
        ("源码根", snapshot["source_roots"]),
        ("模块根", snapshot["module_roots"]),
        ("清单", snapshot["manifests"]),
        ("CI", snapshot["ci"]),
        ("现有文档", snapshot["docs"]),
        ("可能的入口点", snapshot["likely_entrypoints"]),
    ]
    for title, items in sections:
        lines.extend(["", f"## {title}", ""])
        if items:
            lines.extend(f"- `{item}`" for item in items)
        else:
            lines.append("- None detected")

    lines.extend(["", "## 按顶层目录统计的测试", ""])
    if snapshot["tests_by_top_directory"]:
        for directory, count in snapshot["tests_by_top_directory"]:
            lines.append(f"- `{directory}`: {count}")
    else:
        lines.append("- None detected")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", default=".", help="Repository path")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    args = parser.parse_args()

    root = discover_root(Path(args.path))
    snapshot = collect(root)
    if args.format == "markdown":
        print(to_markdown(snapshot), end="")
    else:
        print(json.dumps(snapshot, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
