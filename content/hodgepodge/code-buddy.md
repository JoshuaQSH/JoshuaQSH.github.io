---
title: "Claude Code BUDDY Hatchery"
date: 2026-04-13
categories: ["Hodgepodge"]
tags: ["claude-code", "agents", "buddy", "browser-game", "terminal-ui"]
image: "/images/hodgepodge/code_buddy_cover.png"
imageAlt: "Code BUDDY companion cover art"
summary: "A browser hatchery for Claude Code's deterministic BUDDY companion roll, with rarity search and a tiny endless runner."
layout: "code-buddy"
---

> [!NOTE]
> This playground mirrors the BUDDY bones from the local Claude Code fork under `src/buddy`: rarity, species, eyes, hats, shiny rolls, and stats are all derived from a deterministic user ID roll.

BUDDY is the small terminal companion layer in the harness. Its charm comes from a very plain trick: the visible companion is not stored as editable config. The repeatable bones are regenerated from the user ID, while the soft personality layer can live separately.

The little hatchery below keeps that spirit. Type an ID, inspect the generated companion, brute-force a matching rarity when curiosity wins, then put the result on the runner track.
