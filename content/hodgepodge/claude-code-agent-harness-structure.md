---
title: "Claude Code Agent Harness Structure"
date: 2026-04-01
categories: ["Hodgepodge"]
tags: ["agents", "architecture", "typescript", "terminal", "runtime", "claude-code"]
image: "/images/hodgepodge/Claude_Code_Agent_Harness_Cover.png"
imageAlt: "Claude Code Agent Harness Structure cover"
summary: "A structured walkthrough of the Claude Code CLI runtime: boot flow, query loop, tools, permissions, remote planning, and an interactive source explorer over the whole src tree."
layout: "claude-code-agent-harness"
---

> [!NOTE]
> This walkthrough is based on a local source snapshot under `~/claude-code-fork-main/src`, analyzed on April 1, 2026. It is not an official architecture document.

Claude Code’s terminal runtime stands out because it is not built like a thin CLI wrapper around a model API. It behaves much more like an **agent harness platform**: a long-lived session runtime with explicit tool protocols, permission races, background tasks, remote execution, transcript persistence, and multiple extension layers that all meet in the same query loop.

What feels especially strong in this codebase is the amount of runtime engineering that has been pulled into first-class subsystems instead of being left as hidden glue:

1. **Boot is optimized like an application startup path**, not a script entrypoint. `main.tsx` starts MDM and keychain prefetch immediately, then continues loading the runtime in parallel.
2. **The query/tool loop is shared infrastructure** across interactive REPL, headless printing, remote control, and remote sessions, instead of separate product-specific paths.
3. **Permissions are treated as a multi-source control problem**. User approval, hooks, bridge replies, channels, and classifiers are all explicit resolution paths.
4. **State persistence is central, not optional**. Transcript JSONL, task sidecars, file history, compaction boundaries, and recovery code make long sessions resumable.
5. **Feature layers are deeply integrated but still shippable** through build-time feature gates and runtime experiments. BUDDY, KAIROS, ULTRAPLAN, coordinator mode, cron triggers, bridge mode, and MCP all slot into the same harness.

## Simple Roadmap

1. **CLI bootstrap**
   `main.tsx`, `setup.ts`, `entrypoints/`, `bootstrap/state.ts`
2. **Interactive surfaces**
   `screens/REPL.tsx`, `cli/print.ts`, `interactiveHelpers.tsx`, `replLauncher.tsx`
3. **Conversation engine**
   `QueryEngine.ts`, `query.ts`, `services/compact/*`, `context.ts`
4. **Tool and permission runtime**
   `tools.ts`, `Tool.ts`, `services/tools/*`, `hooks/toolPermission/*`, `utils/permissions/*`
5. **Agent/task orchestration**
   `tasks/*`, `tools/AgentTool/*`, `coordinator/coordinatorMode.ts`
6. **Extension layers**
   `services/mcp/*`, `skills/*`, `utils/plugins/*`, `commands/*`
7. **Remote and bridge execution**
   `bridge/*`, `commands/ultraplan.tsx`, `utils/ultraplan/*`, `remote/*`
8. **Persistence and recovery**
   `utils/sessionStorage.ts`, `utils/conversationRecovery.ts`, `history.ts`, `memdir/*`

The interactive explorer below is meant to make that structure inspectable. Start from the overview graph, click into a subsystem or file, and then pivot through imports, reverse imports, and neighboring directories.
