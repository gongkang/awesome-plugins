---
name: generate-codebase-wiki
description: Use when 用户要求为代码库生成、覆盖更新或审计源码驱动的项目 Wiki、架构文档、模块文档或 DeepWiki 风格文档。
---

# Generate Codebase Wiki

## Overview

Generate source-grounded project documentation in the style of DeepWiki: topic-oriented pages, architecture narrative, precise source citations, diagrams/tables where useful, and a clear distinction between verified facts and inferred design intent. Use a stable wiki spine across projects, then adapt the core implementation deep dives to the repository's own concepts and runtime shape. Do not assume a specific technology stack, architecture style, or prior project's taxonomy.

## Core Rules

- Discover the repository archetype before planning pages. A library, web app, mobile app, compiler, data pipeline, infrastructure repo, plugin system, and monorepo need different taxonomies.
- Use a two-layer taxonomy: a fixed cross-project top-level structure for orientation, plus project-specific deep dives for the actual core implementation.
- Document by user-facing concepts, domain workflows, public contracts, runtime boundaries, and subsystem responsibilities; never by dumping the file tree.
- Treat source files, tests, schemas, migrations, build scripts, configs, manifests, CI, examples, generated contracts, and existing docs as evidence. Do not infer behavior from filenames alone.
- Put the repository snapshot in the docs: commit hash, branch when available, generation date, and whether the worktree was dirty.
- Every non-trivial claim must cite source evidence with `path:line`, `path:line-line`, or an exact-commit GitHub permalink when available.
- Prefer concise uncertainty over false certainty: use `Open question` or `Inference` when the source evidence is incomplete.
- Link existing docs instead of duplicating them. Summarize only what is needed for navigation and architecture understanding.
- Keep generated docs maintainable: smaller pages, stable headings, evidence tables, and clear page ownership.
- Plan from a concept inventory and coverage matrix before writing pages; use them to expose missing subsystems, tests, docs, data flows, integration points, and operational topics.
- Treat `Core Implementation` as the main adaptive area. Identify the project's central workflows, algorithms, domain rules, state transitions, or orchestration paths and split them into detailed mechanism pages.
- Run a second-pass `Domain Coverage Audit` after the canonical first draft to find high-value domain concepts that were over-merged into broad pages.
- Each substantial page should name `Related tests` and `Existing docs`; write `None found` only after searching.
- For overwrite updates, delete only generated wiki files tracked by `.wiki-manifest.json` unless the user explicitly confirms the output directory is dedicated to generated wiki content.
- Do not transplant a taxonomy from a previous project. Create a page only when the concept is proven by source evidence and would help a maintainer navigate behavior.

## Canonical Wiki Structure

Use this as the default output shape. Keep the top-level module order and names stable across projects so generated wikis are comparable. Project-specific vocabulary belongs in page subtitles, tables, diagrams, and child pages, not in renamed top-level modules.

Required root files:

- `README.md` - Overview and Repository Map: snapshot, reading path, architecture summary, coverage summary.
- `coverage-matrix.md` - canonical module and domain concept coverage, split recommendations, evidence, and priority.
- `source-map.md` - source-to-topic navigation, including every generated domain subpage.
- `glossary.md` - project terms and public concepts.
- `.wiki-manifest.json` - generated file manifest for safe overwrite updates.

Canonical top-level modules:

1. `01-system-architecture/README.md` - major components, package/process boundaries, dependency direction, ownership of responsibilities.
2. `02-entrypoints-runtime/README.md` - how the system starts, receives input, executes work, shuts down, or is embedded.
3. `03-core-implementation/README.md` - the project-specific heart: main workflows, algorithms, domain logic, state machines, orchestration, rendering, compilation, scheduling, synchronization, or protocol handling.
4. `04-interfaces-integrations/README.md` - public APIs, CLI/UI surfaces, plugin contracts, network protocols, external services, import/export formats.
5. `05-data-state-persistence/README.md` - schemas, storage, caches, in-memory state, migrations, serialization, result/state models.
6. `06-configuration-extension-security/README.md` - config loading, feature flags, auth/permissions, trust boundaries, extension hooks.
7. `07-operations-observability/README.md` - logging, metrics, tracing, diagnostics, deployment/runtime operations, failure recovery.
8. `08-testing-build-release/README.md` - test strategy, CI, packaging, compatibility, release automation.

If a module truly does not apply, keep its row in `coverage-matrix.md` as `N/A` and explain why. For very small repositories, modules may be summarized in `README.md`, but substantial repositories should use the canonical directory names.

## Domain Coverage Audit

After drafting the canonical modules, audit whether project-specific concepts are hidden inside broad pages and deserve their own subpages. This is a second pass, not a replacement for the canonical structure.

Use these split criteria. Create a domain subpage only when the concept has source evidence plus enough supporting evidence to explain one coherent behavior:

- Distinct lifecycle, state machine, algorithm, orchestration path, protocol, domain rule set, error/retry path, storage path, UI flow, command flow, deployment flow, or extension contract.
- Evidence from at least two relevant categories: source code, tests, configuration/schema/migration, lifecycle or state transitions, error handling, operational behavior, examples, official docs, or external reference docs.
- A maintainer would search for the concept by name, and the current page would otherwise mix multiple workflows.
- The new subpage can be represented in both `coverage-matrix.md` and `source-map.md` with source evidence, test evidence when available, external reference evidence when used, and priority.

Do not split a topic just because an external wiki, official guide, or previous project has a page for it. External documents are useful for discovering possible coverage gaps; source evidence decides whether the local wiki gets a page.

## Anti-Customization Guardrails

- Keep the canonical top-level modules stable across projects. Put project-specific concepts in child pages, not in new top-level modules.
- Do not copy a DeepWiki, official docs, or another repository's table of contents into this skill or into a generated wiki.
- Do not make every project generate pages from one project's domain model. Domain examples are illustrative only; they are not required pages.
- Every new domain subpage must have a `coverage-matrix.md` row and a `source-map.md` row.
- If a domain concept is interesting but lacks source/test/config/lifecycle/error/docs evidence, record it as a coverage gap or open question instead of writing a speculative page.

## Workflow

1. **Establish scope**
   - If the user did not choose an output location, default to `docs/wiki/`.
   - If the repo is local, generate docs from the current worktree. If the repo is remote, browse or clone only when needed and allowed.
   - Scale depth to discovered concepts, not only file count: small repos can use one index plus 3-8 pages; medium repos usually need 8-25 pages; large mature repos can use 10-20 parent pages plus 30-70 child pages when evidence supports that depth.

2. **Prepare the wiki output directory**
   - Resolve helper scripts relative to this skill directory. In command examples below, `scripts/...` refers to the `scripts/` folder next to this `SKILL.md`.
   - Default to merge mode when the user asks to generate or update docs without saying overwrite:
     ```bash
     python3 scripts/prepare_wiki_output.py prepare docs/wiki --mode merge
     ```
   - Use Overwrite update mode when the user asks for `覆盖更新`, `overwrite`, `regenerate`, or replacement of an existing generated wiki:
     ```bash
     python3 scripts/prepare_wiki_output.py prepare docs/wiki --mode overwrite
     ```
   - If there is no `.wiki-manifest.json`, inspect the directory first. Use `--all` only when the user clearly wants to replace that dedicated generated wiki directory:
     ```bash
     python3 scripts/prepare_wiki_output.py prepare docs/wiki --mode overwrite --all
     ```

3. **Create a repository evidence snapshot and concept inventory**
   - Run the helper when available:
     ```bash
     python3 scripts/repo_snapshot.py . --format markdown
     ```
   - Use the snapshot to identify language mix, source roots, package boundaries, manifests, CI, existing docs, generated artifacts, and likely entry points.
   - Supplement with targeted `rg`, `git grep`, `git log`, and file reads. Search for concrete project signals: registrations, routes, commands, UI screens, services, controllers, jobs, pipelines, providers, adapters, plugins, schemas, migrations, events, protocols, examples, tests, and deployment descriptors.
   - If using DeepWiki, official docs, or external docs, use them only to discover possible gaps and vocabulary. Do not copy their structure; verify every planned page against local source evidence.
   - Build a concept inventory before the wiki tree. Useful rows include: public surface, entry points, runtime units, core implementation candidates, domain workflows, algorithms, state transitions, data/state model, external IO, extension contracts, configuration/security, observability, operations, testing/build/release, and glossary terms. Omit rows that do not exist.

4. **Plan the wiki tree**
   - Start from the Canonical Wiki Structure so different project wikis remain comparable. Then adapt summaries, examples, diagrams, and child pages to this repository's language and evidence.
   - Preserve canonical top-level filenames unless the user explicitly requests a different output convention.
   - Build a topic taxonomy around how a maintainer would explain the system: what the project exposes, how it starts, what runs at runtime, how data/control moves, where state lives, what it integrates with, how it is configured, how it is extended, how it is tested, and how it is operated or released.
   - Create a coverage matrix before writing. It must track: canonical module, domain concept, current coverage, split recommendation, source evidence, test evidence, external reference evidence, and priority.
   - Adapt those dimensions to the repo. For example, a CLI tool may need command parsing and filesystem effects; a frontend may need state management and routing; a library may need public APIs and compatibility contracts; an infrastructure repo may need environments, providers, and rollout flow.
   - Split a topic when it has multiple lifecycles, multiple owners, or more than one coherent page of evidence.
   - Merge topics when they are only directory names without independent behavior.
   - Always include an overview page and a glossary for large projects.
   - Use parent pages for orientation and child pages for source-dense mechanisms. Avoid one broad page that combines multiple public concepts simply because they share a directory or framework label.
   - For `03-core-implementation`, choose child pages from the repository's real behavior. Small/medium repositories usually need 1-3 core child pages; complex repositories usually need 3-8 or more. Each deep dive should trace one meaningful behavior end to end.

5. **Write pages from evidence**
   - Begin each page with `Relevant Source Files` or `Relevant Artifacts`, listing code, tests, schemas, configs, docs, or generated contracts that actually prove the page.
   - Include `Related tests` and `Existing docs` sections or rows when evidence exists.
   - State `Purpose and Scope` before details.
   - Use tables for symbol/path/responsibility mappings.
   - Use Mermaid diagrams for lifecycles, process boundaries, data flow, dependency direction, or request flow.
   - Name pages in the repository's own language. Do not force every project into pages such as worker, backend, queue, controller, or service unless those concepts are present.
   - In `Core Implementation` pages, go deeper than orientation: show trigger/input, coordinator, collaborators, data/state changes, branching rules, error/fallback behavior, extension points, and tests.
   - Include tests, configuration, schemas, examples, and deployment files where they explain behavior.
   - Use GitHub permalinks pinned to the snapshot commit for externally shared docs; keep local `path:line-line` citations acceptable for local-only docs.
   - End with `Sources` or inline citations dense enough that a reader can jump to code.
   - Read `references/page-templates.md` when writing multi-page docs or when the user asks for a reusable template.

6. **Run Domain Coverage Audit**
   - Re-read the coverage matrix, source map, existing docs, and any external comparison notes.
   - Mark each candidate domain concept with `current coverage`, `split recommendation`, and `priority`.
   - Split only when the split criteria above are met. If the recommendation is `Split`, add or update the subpage and add rows to both `coverage-matrix.md` and `source-map.md`.
   - If an external document suggests a topic but local evidence is weak, mark it as `Gap` or `Monitor`; do not create a page from the external table of contents.

7. **Update the generation manifest**
   - After writing pages, record the generated file set so the next overwrite update can remove stale pages without touching user notes:
     ```bash
     python3 scripts/prepare_wiki_output.py manifest docs/wiki
     ```
   - If the wiki directory intentionally contains user-maintained notes, pass only the generated file paths to the manifest command.

8. **Review the generated docs**
   - Check that every page can answer: what this subsystem does, where it starts, what it depends on, how data/control flows, how it is configured, how it is tested, and what remains uncertain.
   - Compare final pages against the coverage matrix. Add pages for missing high-value concepts or explicitly mark why a topic is out of scope.
   - When comparing with DeepWiki or another external wiki, account for commit/version differences and use it as a coverage benchmark, not as proof that the local code has the same concepts.
   - Remove generic filler such as "handles business logic" unless it is made specific and cited.
   - Verify path names and line numbers after edits. If files changed during generation, update citations or note the snapshot.

## Output Shape

For a substantial repository, create:

- `docs/wiki/README.md` - table of contents, repository snapshot, architecture overview, and reading path.
- `docs/wiki/coverage-matrix.md` - required; records canonical module, domain concept, current coverage, split recommendation, source evidence, test evidence, external reference evidence, and priority.
- `docs/wiki/01-system-architecture/README.md`
- `docs/wiki/02-entrypoints-runtime/README.md`
- `docs/wiki/03-core-implementation/README.md` plus project-specific child pages.
- `docs/wiki/04-interfaces-integrations/README.md`
- `docs/wiki/05-data-state-persistence/README.md`
- `docs/wiki/06-configuration-extension-security/README.md`
- `docs/wiki/07-operations-observability/README.md`
- `docs/wiki/08-testing-build-release/README.md`
- `docs/wiki/glossary.md` - project terms, acronyms, key services, and public concepts.
- `docs/wiki/source-map.md` - required source-to-topic map; every generated domain subpage should appear here.
- `docs/wiki/.wiki-manifest.json` - generated file list used for safe overwrite updates.

For a small repository, a single `docs/wiki/README.md` can be enough if it still includes the canonical module headings, citations, architecture, testing, and source map sections.

## DeepWiki-Inspired Quality Bar

Good pages have these traits:

- **Topic first**: "Configuration Resolution" beats "src/config folder".
- **Stable structure, adaptive detail**: every wiki uses the canonical top-level modules, while `Core Implementation` follows the specific repository's real workflows.
- **Evidence visible**: each paragraph has nearby source links or `path:line` evidence.
- **Architecture before details**: orient the reader before naming every class.
- **Cross-links**: overview pages point to deep dives; deep dives link back to related topics.
- **Complete enough taxonomy**: mature repos cover their public surface, runtime behavior, state/data model, integrations, configuration, observability, operations, testing, and release path when those concepts exist.
- **Tables and diagrams**: use them to compress relationships, not decorate.
- **Snapshot discipline**: docs say which code version they describe.

Avoid these failure modes:

- File-tree documentation that explains paths but not behavior.
- AI summary without citations.
- Over-broad pages that mix unrelated subsystems.
- Diagrams that are not backed by source evidence.
- Rewriting existing official docs instead of linking and contextualizing them.
- Assuming a fixed architecture pattern, such as every project having an API server, database, worker, queue, CLI, or frontend.
- Copying a previous repository's page tree instead of deriving this repository's concepts from evidence.
