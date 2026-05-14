#!/usr/bin/env python3
"""Prepare and track generated wiki output files."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


MANIFEST_NAME = ".wiki-manifest.json"


def resolve_output(path: str) -> Path:
    return Path(path).resolve()


def is_relative_child(path: Path) -> bool:
    return not path.is_absolute() and ".." not in path.parts


def safe_child(output: Path, relative: str) -> Path:
    rel = Path(relative)
    if not is_relative_child(rel):
        raise ValueError(f"unsafe manifest path: {relative}")

    candidate = (output / rel).resolve()
    try:
        candidate.relative_to(output)
    except ValueError as exc:
        raise ValueError(f"path escapes output directory: {relative}") from exc
    return candidate


def load_manifest(output: Path) -> list[str] | None:
    path = output / MANIFEST_NAME
    if not path.exists():
        return None

    data = json.loads(path.read_text())
    files = data.get("files")
    if not isinstance(files, list) or not all(isinstance(item, str) for item in files):
        raise ValueError(f"{MANIFEST_NAME} must contain a string list named files")
    return files


def delete_empty_dirs(output: Path, dry_run: bool) -> None:
    dirs = sorted((path for path in output.rglob("*") if path.is_dir()), key=lambda path: len(path.parts), reverse=True)
    for directory in dirs:
        if directory == output:
            continue
        try:
            next(directory.iterdir())
        except StopIteration:
            print(f"remove empty dir: {directory.relative_to(output).as_posix()}")
            if not dry_run:
                directory.rmdir()


def remove_files(output: Path, files: Iterable[str], dry_run: bool) -> None:
    for relative in sorted(set(files)):
        target = safe_child(output, relative)
        if not target.exists():
            continue
        if target.is_dir():
            raise ValueError(f"manifest path is a directory, not a file: {relative}")
        print(f"remove file: {relative}")
        if not dry_run:
            target.unlink()
    delete_empty_dirs(output, dry_run)


def discover_files(output: Path) -> list[str]:
    files: list[str] = []
    if not output.exists():
        return files
    for path in output.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(output).as_posix()
        if relative == MANIFEST_NAME:
            continue
        files.append(relative)
    return sorted(files)


def prepare(output: Path, mode: str, all_files: bool, dry_run: bool) -> None:
    if not dry_run:
        output.mkdir(parents=True, exist_ok=True)
    elif not output.exists():
        print(f"would create directory: {output}")

    if mode == "merge":
        print(f"merge mode: preserving existing files in {output}")
        return

    manifest_files = load_manifest(output)
    if manifest_files is None:
        if not all_files:
            raise SystemExit(
                f"{MANIFEST_NAME} not found. Re-run with --all only when {output} is a dedicated generated wiki directory."
            )
        manifest_files = discover_files(output)

    remove_files(output, manifest_files, dry_run)
    manifest_path = output / MANIFEST_NAME
    if manifest_path.exists():
        print(f"remove file: {MANIFEST_NAME}")
        if not dry_run:
            manifest_path.unlink()


def write_manifest(output: Path, files: list[str]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    selected = files or discover_files(output)
    normalized = [safe_child(output, item).relative_to(output).as_posix() for item in selected]
    data = {
        "generated_by": "generate-codebase-wiki",
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "files": sorted(set(normalized)),
    }
    (output / MANIFEST_NAME).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    print(f"wrote {MANIFEST_NAME} with {len(data['files'])} files")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser("prepare", help="prepare an output directory")
    prepare_parser.add_argument("output", help="Wiki output directory")
    prepare_parser.add_argument("--mode", choices=["merge", "overwrite"], default="merge")
    prepare_parser.add_argument("--all", action="store_true", help="Overwrite all files when no manifest exists")
    prepare_parser.add_argument("--dry-run", action="store_true", help="Print actions without modifying files")

    manifest_parser = subparsers.add_parser("manifest", help="write a generation manifest")
    manifest_parser.add_argument("output", help="Wiki output directory")
    manifest_parser.add_argument("files", nargs="*", help="Generated files relative to the output directory")

    args = parser.parse_args()
    output = resolve_output(args.output)
    if args.command == "prepare":
        prepare(output, args.mode, args.all, args.dry_run)
    elif args.command == "manifest":
        write_manifest(output, args.files)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
