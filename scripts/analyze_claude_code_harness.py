#!/usr/bin/env python3
"""Generate architecture data for the Claude Code harness walkthrough page.

This script analyzes the local TypeScript source tree under
`~/claude-code-fork-main/src` and emits:

1. A compact Hugo data file for server-rendered summary stats
2. A richer static JSON file for the interactive diagram explorer
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable


THIS_DIR = Path(__file__).resolve().parent
SITE_ROOT = THIS_DIR.parent
DEFAULT_SOURCE_ROOT = Path("/home/joshua/claude-code-fork-main/src")
DEFAULT_META_OUTPUT = SITE_ROOT / "data" / "claude_code_harness_meta.json"
DEFAULT_FULL_OUTPUT = SITE_ROOT / "static" / "data" / "claude-code-harness.json"
SOURCE_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx")
SUMMARY_OVERRIDES = {
    "src/main.tsx": "Primary CLI bootstrap. Starts early prefetch work, wires feature-gated modules, initializes plugins and skills, parses the command line, and launches the interactive runtime.",
    "src/setup.ts": "Session and workspace preparation. Validates runtime prerequisites, initializes the working directory, handles worktree and tmux setup, and restores per-session state before the agent loop begins.",
    "src/replLauncher.tsx": "Thin launcher that mounts the shared App shell and the REPL screen after startup setup completes.",
    "src/screens/REPL.tsx": "Interactive terminal runtime. Owns the message list, prompt UX, hooks, permissions UI, background tasks, bridge state, MCP state, and the main user-facing agent loop.",
    "src/query.ts": "Main query loop. Sends messages to the model, detects tool calls, runs compaction and retry logic, and decides whether another model round is needed.",
    "src/QueryEngine.ts": "Session-scoped orchestration object. Holds conversation state, file caches, tool context, usage tracking, and the glue around the lower-level query loop.",
    "src/tools.ts": "Tool registry. Builds the available tool pool with feature-gated and environment-specific tools, preserving a stable runtime contract for the agent loop.",
    "src/commands.ts": "Slash-command registry. Loads user-facing commands and uses build-time feature gates to trim command surface by product mode.",
    "src/Tool.ts": "Core tool protocol definitions: schemas, permission hooks, progress reporting, rendering, and the shared context object passed into every tool.",
    "src/services/tools/toolOrchestration.ts": "Tool scheduler. Partitions tool calls into concurrency-safe batches and serial batches so read-only work can run in parallel without corrupting mutable state.",
    "src/services/tools/toolExecution.ts": "Per-tool execution pipeline. Performs validation, permission checks, hook execution, telemetry, result shaping, and error normalization for every tool call.",
    "src/services/tools/StreamingToolExecutor.ts": "Streaming-time tool runner. Starts tools before the full assistant message is finished, preserves order for yielded results, and aborts siblings when a parallel branch fails.",
    "src/services/compact/autoCompact.ts": "Automatic context budgeting. Tracks thresholds, blocking limits, and compaction triggers so long sessions stay inside the effective context window.",
    "src/services/compact/compact.ts": "Conversation compaction engine. Summarizes prior rounds, inserts compact boundaries, preserves critical attachments and plan state, and rebuilds the next prompt after compression.",
    "src/utils/sessionStorage.ts": "Transcript persistence backbone. Writes JSONL session history, file snapshots, metadata, and sidecar task state so sessions can resume and background work can be recovered.",
    "src/utils/conversationRecovery.ts": "Resume and repair logic for stored transcripts. Rehydrates messages, fixes interrupted turns, and normalizes restored state before a session continues.",
    "src/hooks/toolPermission/PermissionContext.ts": "Permission decision hub. Coordinates queue state, hook decisions, classifier shortcuts, and resolve-once semantics so multiple approval paths can safely race.",
    "src/hooks/toolPermission/handlers/interactiveHandler.ts": "Interactive permission race handler. Lets user input, hooks, bridge responses, channel replies, and classifier decisions compete without double-resolving a tool request.",
    "src/utils/permissions/permissions.ts": "Core permission policy engine. Applies modes like auto, plan, default, and bypass, runs the auto-mode classifier, and explains why a tool is allowed, denied, or escalated.",
    "src/tools/BashTool/bashPermissions.ts": "Bash-specific safety layer. Checks command rules, speculative classifiers, read-only fast paths, and rich permission metadata before a shell command is allowed to run.",
    "src/bridge/bridgeMain.ts": "Standalone bridge daemon. Connects IDE clients and remote-control flows to the same runtime primitives used by the terminal REPL.",
    "src/bridge/replBridge.ts": "REPL bridge adapter. Mirrors local conversation state into a bridge session so IDEs and remote surfaces can watch or interact with the same workflow.",
    "src/bridge/initReplBridge.ts": "REPL-specific bridge bootstrap. Owns the wiring that attaches bridge state, session pointers, and resume behavior to the live terminal session.",
    "src/commands/ultraplan.tsx": "Remote planning entrypoint. Launches a Claude Code on the web session, streams status back into the terminal, and handles teleport or remote-execution outcomes.",
    "src/utils/ultraplan/ccrSession.ts": "Ultraplan remote poller. Scans CCR event streams for plan approval, teleport markers, rejection loops, and timeout or termination conditions.",
    "src/coordinator/coordinatorMode.ts": "Coordinator-mode prompt and policy layer. Reframes Claude Code as an orchestrator that spawns workers, synthesizes findings, and manages concurrency explicitly.",
    "src/tasks/LocalAgentTask/LocalAgentTask.tsx": "Local agent task lifecycle. Tracks sub-agent progress, streamed transcript state, disk-backed output, and completion notifications for spawned workers.",
    "src/tasks/RemoteAgentTask/RemoteAgentTask.tsx": "Remote task lifecycle. Tracks remote Claude sessions, review or ultraplan state, poll status, and durable metadata for restored sessions.",
    "src/utils/plugins/pluginLoader.ts": "Plugin discovery and loading pipeline. Resolves plugins from marketplaces or local sources, validates manifests, and merges commands, agents, and hooks into the runtime.",
    "src/services/mcp/client.ts": "MCP client runtime. Connects to MCP servers, exposes tools/resources/commands, and handles authentication, transport normalization, and error shaping.",
    "src/services/mcp/MCPConnectionManager.tsx": "React-side MCP connection coordinator. Provides reconnect and toggle controls for the live REPL while delegating connection state to the MCP management hook.",
    "src/skills/bundled/index.ts": "Bundled-skill bootstrap. Registers shipped markdown skills and conditionally enables feature-gated skills such as dream, loop, and Claude API helpers.",
    "src/buddy/CompanionSprite.tsx": "BUDDY UI surface. Renders the animated companion sprite, floating speech bubble, and interaction timing inside the REPL.",
    "src/buddy/companion.ts": "BUDDY identity generator. Deterministically rolls companion traits, rarity, and stats from user identity and stored config.",
    "src/buddy/prompt.ts": "BUDDY prompt attachment builder. Injects a lightweight companion contract so the assistant and companion bubble can coexist cleanly.",
    "src/assistant/sessionHistory.ts": "Assistant-session history fetcher used by KAIROS-style surfaces to page through remote session events with shared auth context.",
    "src/tools/ScheduleCronTool/prompt.ts": "KAIROS-trigger scheduling rules. Describes how recurring and one-shot cron prompts are exposed to the agent runtime and gated at runtime.",
}

IMPORT_PATTERN = re.compile(
    r"""
    (?:import|export)\s+(?:type\s+)?(?:[^'"\n]+?\s+from\s+)?["'](?P<spec>(?:\.{1,2}/|src/)[^"']+)["']
    |
    import\(\s*["'](?P<dynamic>(?:\.{1,2}/|src/)[^"']+)["']\s*\)
    |
    require\(\s*["'](?P<require>(?:\.{1,2}/|src/)[^"']+)["']\s*\)
    """,
    re.VERBOSE,
)

FEATURE_PATTERN = re.compile(r"feature\('([A-Z0-9_]+)'\)")
EXPORT_PATTERN = re.compile(
    r"""
    export\s+
    (?:
      async\s+function\s+(?P<async_fn>[A-Za-z0-9_]+)
      |
      function\s+(?P<fn>[A-Za-z0-9_]+)
      |
      class\s+(?P<class_name>[A-Za-z0-9_]+)
      |
      const\s+(?P<const_name>[A-Za-z0-9_]+)
      |
      let\s+(?P<let_name>[A-Za-z0-9_]+)
      |
      var\s+(?P<var_name>[A-Za-z0-9_]+)
      |
      interface\s+(?P<interface_name>[A-Za-z0-9_]+)
      |
      type\s+(?P<type_name>[A-Za-z0-9_]+)
      |
      enum\s+(?P<enum_name>[A-Za-z0-9_]+)
    )
    """,
    re.VERBOSE,
)
EXPORT_LIST_PATTERN = re.compile(r"export\s*\{\s*([^}]+)\}")
BLOCK_COMMENT_PATTERN = re.compile(r"/\*\*(.*?)\*/", re.DOTALL)
LINE_COMMENT_PATTERN = re.compile(r"^\s*//\s?(.*)$")


@dataclass
class FileAnalysis:
    path: str
    name: str
    dir_path: str
    top_module: str
    line_count: int
    summary: str
    imports: list[str]
    imported_by: list[str]
    feature_flags: list[str]
    exports: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-root",
        type=Path,
        default=DEFAULT_SOURCE_ROOT,
        help="Path to the src directory to analyze.",
    )
    parser.add_argument(
        "--meta-output",
        type=Path,
        default=DEFAULT_META_OUTPUT,
        help="Path to the compact Hugo data JSON output.",
    )
    parser.add_argument(
        "--full-output",
        type=Path,
        default=DEFAULT_FULL_OUTPUT,
        help="Path to the full static JSON output for the interactive explorer.",
    )
    return parser.parse_args()


def strip_js_suffix(spec: str) -> str:
    for suffix in (".js", ".jsx", ".mjs", ".cjs"):
        if spec.endswith(suffix):
            return spec[: -len(suffix)]
    return spec


def resolve_import_spec(
    file_path: Path,
    spec: str,
    repo_root: Path,
    src_root: Path,
) -> Path | None:
    normalized = strip_js_suffix(spec)
    if normalized.startswith("src/"):
        base = repo_root / normalized
    else:
        base = (file_path.parent / normalized).resolve()

    candidates: list[Path] = []
    if base.suffix:
        candidates.append(base)
    else:
        for suffix in SOURCE_EXTENSIONS:
            candidates.append(Path(f"{base}{suffix}"))
        for suffix in SOURCE_EXTENSIONS:
            candidates.append(base / f"index{suffix}")

    for candidate in candidates:
        if candidate.exists() and src_root in candidate.parents:
            return candidate

    return None


def normalize_doc_line(line: str) -> str:
    text = line.strip()
    if text.startswith("*"):
        text = text[1:].strip()
    return text


def is_noise_comment(line: str) -> bool:
    lowered = line.lower()
    return (
        not line
        or lowered.startswith("eslint")
        or lowered.startswith("biome")
        or lowered.startswith("@ts-")
        or lowered.startswith("todo(")
        or lowered.startswith("todo:")
        or lowered.startswith("note:")
        or lowered.startswith("#")
        or "sourceMappingURL" in line
    )


def summarize_from_comment(text: str) -> str | None:
    match = BLOCK_COMMENT_PATTERN.search(text)
    if match:
        lines = [
            normalize_doc_line(line)
            for line in match.group(1).splitlines()
        ]
        cleaned = [line for line in lines if not is_noise_comment(line)]
        if cleaned:
            return " ".join(cleaned[:3]).strip()

    line_comments: list[str] = []
    for raw_line in text.splitlines()[:80]:
        line_match = LINE_COMMENT_PATTERN.match(raw_line)
        if not line_match:
            if line_comments:
                break
            continue
        comment = line_match.group(1).strip()
        if is_noise_comment(comment):
            if line_comments:
                break
            continue
        line_comments.append(comment)
        if len(line_comments) >= 3:
            break
    if line_comments:
        return " ".join(line_comments).strip()

    return None


def fallback_summary(path: str, top_module: str, exports: list[str]) -> str:
    base_name = Path(path).stem.replace("-", " ").replace("_", " ")
    if exports:
        return (
            f"{base_name.title()} in the {top_module} subsystem. "
            f"Exports include {', '.join(exports[:3])}."
        )
    if top_module == "(root)":
        return f"{base_name.title()} is one of the root runtime entry files."
    return f"{base_name.title()} belongs to the {top_module} subsystem."


def extract_exports(text: str) -> list[str]:
    names: list[str] = []
    for match in EXPORT_PATTERN.finditer(text):
        name = next(group for group in match.groups() if group)
        names.append(name)
    for match in EXPORT_LIST_PATTERN.finditer(text):
        raw_names = match.group(1).split(",")
        for raw_name in raw_names:
            candidate = raw_name.strip().split(" as ")[0].strip()
            if candidate:
                names.append(candidate)
    deduped: list[str] = []
    seen: set[str] = set()
    for name in names:
        if name not in seen:
            seen.add(name)
            deduped.append(name)
    return deduped[:12]


def iter_source_files(src_root: Path) -> Iterable[Path]:
    for path in sorted(src_root.rglob("*")):
        if path.is_file() and path.suffix in (".ts", ".tsx"):
            yield path


def build_directory_record(
    dir_path: str,
    files_by_dir: dict[str, list[str]],
    all_dirs: set[str],
    file_records: dict[str, FileAnalysis],
) -> dict[str, object]:
    child_dirs = sorted(
        candidate
        for candidate in all_dirs
        if Path(candidate).parent.as_posix() == dir_path and candidate != dir_path
    )
    child_files = sorted(files_by_dir.get(dir_path, []))
    descendant_files = [
        record
        for path, record in file_records.items()
        if path == dir_path or path.startswith(f"{dir_path}/") or record.dir_path.startswith(f"{dir_path}/")
    ]
    top_files = sorted(
        child_files,
        key=lambda path: (
            -len(file_records[path].imported_by),
            -file_records[path].line_count,
            path,
        ),
    )[:10]
    feature_counter = Counter()
    total_lines = 0
    for record in descendant_files:
        total_lines += record.line_count
        feature_counter.update(record.feature_flags)

    return {
        "path": dir_path,
        "depth": 0 if dir_path == "src" else dir_path.count("/") - 1,
        "child_dirs": child_dirs,
        "child_files": child_files,
        "file_count": len(descendant_files),
        "direct_file_count": len(child_files),
        "total_lines": total_lines,
        "top_files": top_files,
        "top_feature_flags": [
            {"name": name, "count": count}
            for name, count in feature_counter.most_common(8)
        ],
    }


def main() -> None:
    args = parse_args()
    src_root = args.source_root.resolve()
    repo_root = src_root.parent

    if not src_root.exists():
        raise SystemExit(f"Source root not found: {src_root}")

    file_records: dict[str, FileAnalysis] = {}
    reverse_imports: defaultdict[str, list[str]] = defaultdict(list)
    module_counter: Counter[str] = Counter()
    module_line_counter: Counter[str] = Counter()
    module_edge_counter: Counter[tuple[str, str]] = Counter()
    feature_counter: Counter[str] = Counter()
    files_by_dir: defaultdict[str, list[str]] = defaultdict(list)
    all_dirs: set[str] = {"src"}

    source_files = list(iter_source_files(src_root))

    for file_path in source_files:
        rel_path = file_path.relative_to(repo_root).as_posix()
        top_module = (
            rel_path.split("/")[1]
            if rel_path.count("/") >= 2
            else "(root)"
        )
        dir_path = file_path.parent.relative_to(repo_root).as_posix()
        all_dirs.add(dir_path)
        for parent in file_path.parent.relative_to(repo_root).parents:
            parent_path = parent.as_posix()
            if parent_path != ".":
                all_dirs.add(parent_path)

        text = file_path.read_text(errors="ignore")
        feature_flags = sorted(set(FEATURE_PATTERN.findall(text)))
        exports = extract_exports(text)

        imports: list[str] = []
        seen_imports: set[str] = set()
        for match in IMPORT_PATTERN.finditer(text):
            spec = match.group("spec") or match.group("dynamic") or match.group("require")
            resolved = resolve_import_spec(file_path, spec, repo_root, src_root)
            if not resolved:
                continue
            resolved_rel = resolved.relative_to(repo_root).as_posix()
            if resolved_rel in seen_imports:
                continue
            seen_imports.add(resolved_rel)
            imports.append(resolved_rel)
            reverse_imports[resolved_rel].append(rel_path)

            target_top = (
                resolved_rel.split("/")[1]
                if resolved_rel.count("/") >= 2
                else "(root)"
            )
            if target_top != top_module:
                module_edge_counter[(top_module, target_top)] += 1

        line_count = text.count("\n") + 1
        summary = SUMMARY_OVERRIDES.get(rel_path) or summarize_from_comment(
            text
        ) or fallback_summary(rel_path, top_module, exports)

        record = FileAnalysis(
            path=rel_path,
            name=file_path.name,
            dir_path=dir_path,
            top_module=top_module,
            line_count=line_count,
            summary=summary,
            imports=imports,
            imported_by=[],
            feature_flags=feature_flags,
            exports=exports,
        )
        file_records[rel_path] = record
        files_by_dir[dir_path].append(rel_path)
        module_counter[top_module] += 1
        module_line_counter[top_module] += line_count
        feature_counter.update(feature_flags)

    for rel_path, importers in reverse_imports.items():
        if rel_path in file_records:
            file_records[rel_path].imported_by = sorted(set(importers))

    directories = {
        dir_path: build_directory_record(
            dir_path,
            files_by_dir,
            all_dirs,
            file_records,
        )
        for dir_path in sorted(all_dirs)
    }

    largest_files = sorted(
        file_records.values(),
        key=lambda record: (-record.line_count, record.path),
    )[:20]
    most_imported = sorted(
        file_records.values(),
        key=lambda record: (-len(record.imported_by), record.path),
    )[:20]

    meta = {
        "generated_at": str(date.today()),
        "source_root": str(src_root),
        "total_files": len(file_records),
        "total_directories": len(directories),
        "total_lines": sum(record.line_count for record in file_records.values()),
        "top_modules": [
            {
                "name": name,
                "file_count": count,
                "line_count": module_line_counter[name],
            }
            for name, count in module_counter.most_common(12)
        ],
        "top_feature_flags": [
            {"name": name, "count": count}
            for name, count in feature_counter.most_common(12)
        ],
        "largest_files": [
            {
                "path": record.path,
                "line_count": record.line_count,
                "summary": record.summary,
            }
            for record in largest_files
        ],
        "most_imported_files": [
            {
                "path": record.path,
                "imported_by_count": len(record.imported_by),
                "summary": record.summary,
            }
            for record in most_imported
        ],
        "module_edges": [
            {"from": source, "to": target, "count": count}
            for (source, target), count in module_edge_counter.most_common(30)
        ],
    }

    full_payload = {
        "generated_at": str(date.today()),
        "source_root": str(src_root),
        "stats": meta,
        "directories": directories,
        "files": {
            path: {
                "path": record.path,
                "name": record.name,
                "dir_path": record.dir_path,
                "top_module": record.top_module,
                "line_count": record.line_count,
                "summary": record.summary,
                "imports": record.imports,
                "imported_by": record.imported_by,
                "feature_flags": record.feature_flags,
                "exports": record.exports,
            }
            for path, record in sorted(file_records.items())
        },
    }

    args.meta_output.parent.mkdir(parents=True, exist_ok=True)
    args.full_output.parent.mkdir(parents=True, exist_ok=True)
    args.meta_output.write_text(json.dumps(meta, indent=2) + "\n")
    args.full_output.write_text(json.dumps(full_payload, indent=2) + "\n")

    print(
        json.dumps(
            {
                "generated_at": meta["generated_at"],
                "total_files": meta["total_files"],
                "total_directories": meta["total_directories"],
                "total_lines": meta["total_lines"],
                "meta_output": str(args.meta_output),
                "full_output": str(args.full_output),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
