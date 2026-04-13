# AGENTS.md

This file is the stable handoff note for agents working on `~/home-page`, the Hugo source repo for <https://joshuaqsh.github.io/>.

Use this file for the basics:

- what the project is
- how to work in it safely
- how to test locally
- where the deeper repo memory lives

For the changing project state, current content inventory, and a brief summary of existing pages and recent updates, read `agents/MEMORY.md`.

For the task-oriented maintenance playbook, read `agents/SKILL.md`.

## Project basics

- Repo root: `~/home-page`
- Site generator: Hugo Extended
- Deploy target: GitHub Pages
- Primary branch: `master`
- Main deploy workflow: `.github/workflows/gh-pages.yml`
- Scheduled data-refresh workflow: `.github/workflows/refresh-llm-tracker.yml`

This site started from the `minimalist` theme, but most important behavior now comes from local templates, CSS, scripts, and data files in this repo.

## Start here

If you are a new agent taking over this repo, read these first:

1. `config.toml`
2. `GUIDE.md`
3. `agents/MEMORY.md`
4. `agents/SKILL.md`
5. `layouts/_default/baseof.html`

## Core repo map

- `config.toml`: site config, profile metadata, menus, syntax highlighting
- `content/`: markdown content
- `layouts/`: custom templates and most site behavior
- `data/`: structured data backing custom pages
- `static/`: deployed assets and published JSON snapshots
- `scripts/`: local maintenance and validation scripts
- `.github/workflows/`: CI, Pages deploy, and scheduled tracker refresh

## Local workflow

### Build and validate

Run these from `~/home-page`:

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

Then inspect the pages you changed.

## Important repo rules

### Tags are mandatory

Every markdown page under:

- `content/posts/*.md`
- `content/hodgepodge/*.md`

must define inline non-empty tags, for example:

```yaml
tags: ["tag-a", "tag-b"]
```

### Future-dated posts can disappear from listings

If a post is missing from `/posts/`, check its front matter `date`.

### Pricing tracker data must be synced

If you edit `data/llm_pricing.json`, also run:

```sh
python3 ./scripts/sync_llm_pricing_data.py
```

### Photo album uses generated assets

If you add or replace album photos, use:

```sh
python3 ./scripts/prepare_photo_album.py
```

### GitHub Pages must use GitHub Actions

The repo Pages source should be `GitHub Actions`, not branch deployment.

### Remote may move underneath you

The scheduled LLM tracker refresh workflow can commit directly to `master`.
If `git push` is rejected:

```sh
git fetch origin master
git rebase origin/master
```

## Publish

```sh
git add <files>
git commit -m "<message>"
git push origin master
```

## File roles

- `agents/AGENTS.md`: stable repo-level handoff basics
- `agents/MEMORY.md`: current project state, content inventory, and recent context
- `agents/SKILL.md`: step-by-step maintenance workflow for another agent
- `GUIDE.md`: author-facing usage guide for posting and asset updates
