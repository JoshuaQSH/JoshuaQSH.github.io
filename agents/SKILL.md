# SKILL.md

# Skill: Maintain Joshua's Hugo Home Page

Use this skill when working on `~/home-page`, a Hugo Extended site deployed to GitHub Pages.

This skill is intentionally practical. It tells another agent how to make changes safely, where the custom logic lives, and what must be validated before pushing.

## What this skill is for

Use it for tasks like:

- add a new post
- add a new Hodgepodge demo page
- tweak the home page or About page
- update profile metadata or icons
- maintain the LLM pricing tracker
- maintain the photo album
- fix layout regressions in custom templates
- debug GitHub Pages / Hugo rendering issues

## Fast orientation

### Core facts

- Repo root: `~/home-page`
- Generator: Hugo Extended
- Deploy target: GitHub Pages
- Primary branch: `master`
- Deployment workflow: `.github/workflows/gh-pages.yml`
- Scheduled data-refresh workflow: `.github/workflows/refresh-llm-tracker.yml`

### Most important files

- `config.toml`
- `GUIDE.md`
- `agents/AGENTS.md`
- `agents/MEMORY.md`
- `layouts/_default/baseof.html`
- `layouts/index.html`
- `layouts/posts/list.html`
- `layouts/posts/llm-pricing-tracker.html`
- `layouts/hodgepodge/photo-album.html`
- `layouts/hodgepodge/claude-code-agent-harness.html`
- `data/llm_pricing.json`
- `data/photo_album.json`

## Default working style

1. Work directly in the repo rather than proposing vague plans.
2. Prefer small, targeted edits.
3. Rebuild after every meaningful change batch.
4. Do not forget the repo-specific validation scripts.
5. If editing pricing data, sync the published JSON before build.
6. If pushing fails because remote moved, fetch and rebase instead of force-pushing.

Use `agents/AGENTS.md` for stable repo rules and `agents/MEMORY.md` for the current content/state snapshot.

## Required validation steps

Run these from `~/home-page`.

### Standard validation

```sh
./scripts/check_posts_have_tags.sh
python3 ./scripts/sync_llm_pricing_data.py
hugo --minify --cleanDestinationDir
./scripts/check_internal_links.sh public
```

### Local preview

```sh
hugo server --bind 127.0.0.1 --port 1313 --disableFastRender
```

Open and inspect the pages you changed.

## Project-specific rules

### 1. Tags are required for posts and Hodgepodge pages

Use inline array syntax only:

```yaml
tags: ["tag-a", "tag-b"]
```

The checker will fail on empty or missing inline tags.

### 2. Future dates hide content from listing pages

If a post does not show up in `/posts/`, check whether its front-matter date is in the future.

### 3. Pinned posts always stay visible on the home page

Use:

```yaml
pinned: true
```

Pinned posts are always shown in home-page `Latest Posts` and appear first on `/posts/`.

### 4. The LLM tracker is data-driven

Do not treat it like a plain markdown page.

If you edit the tracker:

- source markdown: `content/posts/llm-pricing-tracker.md`
- custom template: `layouts/posts/llm-pricing-tracker.html`
- editable data: `data/llm_pricing.json`
- published data: `static/data/llm-pricing.json`

After editing data, always run:

```sh
python3 ./scripts/sync_llm_pricing_data.py
```

### 5. The photo album is generated from raw uploads

Workflow:

```sh
python3 ./scripts/prepare_photo_album.py
```

This updates:

- `static/images/photo-album/`
- `data/photo_album.json`

The timeline is newest-first.

### 6. The harness page depends on a static JSON dataset

If changing the Claude Code explorer:

- regenerate data when needed with `python3 scripts/analyze_claude_code_harness.py`
- keep `static/data/claude-code-harness.json` deployable
- check template JS embedding carefully
- use wrapping rules for long code-like strings

### 7. GitHub-style alerts are custom-rendered

Markdown alert syntax is supported:

```md
> [!NOTE]
> Message.
```

The icon mapping and styling live in `layouts/_default/baseof.html`.

## Common workflows

## Add a normal post

1. Create a file in `content/posts/`.
2. Add title, date, categories, and inline tags.
3. Add `summary` so the home page and post cards look good.
4. Add `pinned: true` only if it should always stay visible.
5. Build and validate.

Suggested starter front matter:

```yaml
---
title: "Post title"
date: 2026-04-13
summary: "Short summary for cards and lists."
categories: ["Notes"]
tags: ["example", "todo"]
---
```

## Add a Hodgepodge project or demo

1. Create a file in `content/hodgepodge/`.
2. Add `summary`, `categories`, inline `tags`, and optional `image` / `imageAlt`.
3. Put cover images under `static/images/hodgepodge/`.
4. If the page needs custom behavior, create a matching template in `layouts/hodgepodge/`.
5. Build and validate.

## Update profile / About / navigation

Typical files:

- `config.toml`
- `content/about.md`
- `layouts/_default/single.html`
- `layouts/partials/profile-hero.html`
- `layouts/_default/baseof.html`

## Update the pricing tracker manually

1. Edit `data/llm_pricing.json`.
2. If needed, update the intro or notes in `content/posts/llm-pricing-tracker.md`.
3. Run:

```sh
python3 ./scripts/sync_llm_pricing_data.py
hugo --minify --cleanDestinationDir
./scripts/check_internal_links.sh public
./scripts/check_posts_have_tags.sh
```

4. If `git push` is rejected, do:

```sh
git fetch origin master
git rebase origin/master
```

5. Resolve conflicts in `data/llm_pricing.json` and `static/data/llm-pricing.json` carefully. Usually keep the latest remote-generated timestamp and preserve your manual content row changes.

## Refresh the photo album

1. Add raw files to `photo_album_raw/`.
2. Run:

```sh
python3 ./scripts/prepare_photo_album.py
```

3. Optionally refine metadata in `data/photo_album.json`.
4. Rebuild and validate.

## Edit visual design or global styling

Start here:

- `layouts/_default/baseof.html`

This file contains:

- theme variables
- home / post / hero styling
- dark-mode logic
- GitHub-style alert rendering
- photo-album CSS
- shared site shell styling

## Publishing workflow

### Normal publish

```sh
git add <files>
git commit -m "<message>"
git push origin master
```

### If remote moved first

This repo can move underneath you because the scheduled LLM refresh workflow can auto-commit to `master`.
When that happens:

```sh
git fetch origin master
git rebase origin/master
```

Then rebuild and push again.

## What to inspect after changes

Always inspect the exact page you touched, plus any related indexes.

Examples:

- changed a post: inspect `/posts/` and `/`
- changed Hodgepodge: inspect `/hodgepodge/`
- changed tags or categories: inspect `/tags/` and `/categories/`
- changed About/profile: inspect `/` and `/about/`
- changed tracker: inspect `/posts/llm-pricing-tracker/`
- changed photo album: inspect `/hodgepodge/photo-album/`
- changed harness page: inspect `/hodgepodge/claude-code-agent-harness-structure/`

## Known non-obvious pitfalls

- GitHub Pages must be configured to use `GitHub Actions` as the source.
- The pricing tracker has both editable data and published data; forgetting to sync them causes stale live content.
- The harness explorer can silently fail if JS values are serialized with extra quotes.
- Long strings in custom grids can overflow without explicit wrapping CSS.
- The tag-check script accepts `rg` or `grep`; CI does not require `rg`.
- Raw photo files can be large; publish compressed copies instead of blindly committing originals.

## Quick success checklist

Before you finish, confirm all of these:

- content has inline non-empty tags
- no unintended future date hides content
- pricing data was synced if edited
- Hugo build passed
- internal link check passed
- changed pages render locally
- git worktree is clean before or after push

## Related docs

- `agents/AGENTS.md`: broad repo handoff and stable repo rules
- `agents/MEMORY.md`: current content inventory and recent project context
- `GUIDE.md`: posting, Markdown, cover-image, and photo-album usage guide
