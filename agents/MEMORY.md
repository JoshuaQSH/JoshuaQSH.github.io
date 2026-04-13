# MEMORY.md

This file holds the changing project memory for `~/home-page`.

Use it for:

- current content inventory
- what the custom pages do
- brief summaries of the existing posts and demos
- important recent updates and historical context that another agent should know before making changes

For stable working rules, read `agents/AGENTS.md`.
For the practical maintenance workflow, read `agents/SKILL.md`.

## Site snapshot

- Site owner: Shenghao Qiu
- Live site: <https://joshuaqsh.github.io/>
- Style direction: serif-heavy personal academic homepage, inspired in several places by `lei.chat`
- Main navigation: `Raccoon's Home`, `Posts`, `Categories`, `Tags`, `Hodgepodge`, `About`

## Current content inventory

### Posts

#### `hello-hugo.md`

- A simple early Hugo starter post.
- Mostly useful as baseline content and a format example.

#### `uv-tips.md`

- A practical note on using `uv` for Python project management.
- This post previously disappeared from `/posts/` because of a future date, so date sanity is worth checking if it ever “goes missing” again.

#### `llm-pricing-tracker.md`

- Pinned post.
- A data-driven tracker for LLM API pricing, subscriptions, price history, benchmark snapshots, and provider leaderboards.
- Backed by `data/llm_pricing.json` and `static/data/llm-pricing.json`.
- This page is not a normal markdown-only post and has its own custom layout and JS.

### Hodgepodge

#### `polymarket.md`

- A project/demo card pointing to the live Polymarket analytics page.
- Lives under Hodgepodge rather than the main posts feed.

#### `storybin.md`

- A Hodgepodge project page for Storybin.
- Uses a cover image and behaves like a project card/showcase page.

#### `photo-album.md`

- A personal gallery page with a vertical timeline layout.
- Uses generated compressed images and `data/photo_album.json`.
- Timeline order is newest first, so the most recent image appears at the top.

#### `claude-code-agent-harness-structure.md`

- A long-form architecture/demo page about the Claude Code runtime structure.
- Includes a generated architecture dataset and an interactive explorer over the analyzed source tree.
- Uses a dedicated custom layout and static JSON snapshot.

## Current major customizations

### Visual / shell

- Large circular avatar hero on the home page
- Vertical social icons beside the avatar
- Large serif typography with a strong editorial feel
- Borderless layout direction with divider lines
- Dark/light mode toggle in the top-right corner
- GitHub-style code blocks and Markdown alerts

### Content behavior

- Pinned posts always appear on the home page
- `/posts/` shows pinned posts first
- Post cards show title, date, summary, and simple `#t<tag>` links
- All posts and Hodgepodge pages require inline non-empty tags

### About / profile

- Profile metadata is controlled by `[params.profile]` in `config.toml`
- About page keeps the public-facing summary, contact details, and recent project information
- Email display is intentionally obfuscated in public-facing text

## Custom page memory

### LLM Pricing Tracker

Files:

- `content/posts/llm-pricing-tracker.md`
- `layouts/posts/llm-pricing-tracker.html`
- `data/llm_pricing.json`
- `static/data/llm-pricing.json`
- `scripts/sync_llm_pricing_data.py`
- `scripts/refresh_llm_tracker_snapshot.py`
- `.github/workflows/refresh-llm-tracker.yml`

Key memory:

- The editable source of truth is `data/llm_pricing.json`.
- The browser reads the published snapshot from `static/data/llm-pricing.json`.
- The refresh workflow can auto-commit to `master`, so manual pricing edits can hit rebase conflicts.
- When rebasing after tracker updates, usually preserve the newest remote-generated snapshot metadata while keeping the intended manual row edits.
- Gemma was explicitly added as a Google row and is currently represented from Google’s official pricing page as free of charge.

### Photo Album

Files:

- `content/hodgepodge/photo-album.md`
- `layouts/hodgepodge/photo-album.html`
- `data/photo_album.json`
- `static/images/photo-album/`
- `photo_album_raw/`
- `scripts/prepare_photo_album.py`

Key memory:

- Raw originals live in `photo_album_raw/`.
- Published images are compressed web copies.
- The file name becomes the default title unless overridden in `data/photo_album.json`.
- Default camera/lens values are prefilled by the prep script.

### Claude Code Agent Harness page

Files:

- `content/hodgepodge/claude-code-agent-harness-structure.md`
- `layouts/hodgepodge/claude-code-agent-harness.html`
- `scripts/analyze_claude_code_harness.py`
- `data/claude_code_harness_meta.json`
- `static/data/claude-code-harness.json`

Key memory:

- The interactive explorer depends on the deployed static JSON.
- There was a production bug where the template emitted the JSON URL with extra quotes, which broke the live explorer even though the JSON file existed.
- That issue was fixed by embedding the values safely in JS and improving wrapping for long feature-card text.

## Brief summary of the project history so far

- The repo was turned into a working Hugo + GitHub Pages deployment rather than a mixed static branch setup.
- CI and Pages deploy were added.
- A tag check and internal link checker were added.
- The homepage, navigation, post cards, and About page were heavily redesigned around the desired personal-site style.
- GitHub-style alerts and code styling were added.
- A dark/light mode toggle was added.
- The photo album timeline workflow was added.
- The LLM pricing tracker grew into a scheduled, data-backed page with charts and benchmark snapshots.
- The Claude Code harness page was added as a large architecture/demo page with an interactive explorer.

## Known issues to keep in mind

- Scheduled tracker refresh commits can race with manual pricing updates.
- Future-dated posts can silently disappear from page listings.
- The harness page is sensitive to JS template embedding mistakes.
- Large raw photos should not be pushed casually when compressed published copies are enough.

## Good pages to inspect after major changes

- `/`
- `/posts/`
- `/hodgepodge/`
- `/about/`
- `/posts/llm-pricing-tracker/`
- `/hodgepodge/photo-album/`
- `/hodgepodge/claude-code-agent-harness-structure/`
