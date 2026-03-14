# Hugo Usage Guide

## Install Hugo (Extended required)

Hugo is available as a prebuilt binary for most platforms. Follow the official install instructions for your OS:

- macOS (Homebrew):
  ```sh
  brew install hugo
  ```
- Windows (Chocolatey):
  ```powershell
  choco install hugo -confirm
  ```
- Linux:
  ```sh
  sudo apt-get install hugo
  ```

This site requires **Hugo Extended** (for the theme asset pipeline). For other platforms or the extended version, see https://gohugo.io/installation/.

## Run the local server

From the repo root, run:

```sh
hugo server
```

The site will be available at http://localhost:1313/ and will live-reload as you edit files.

### Test environment commands + gotchas

When running inside this repo's test container, Hugo Extended is not preinstalled. I used the GitHub release tarball and installed the binary into `/usr/local/bin`:

```sh
HUGO_VERSION=0.154.5
curl -L -o /tmp/hugo.tar.gz "https://github.com/gohugoio/hugo/releases/download/v${HUGO_VERSION}/hugo_extended_${HUGO_VERSION}_linux-amd64.tar.gz"
sudo tar -C /usr/local/bin -xzf /tmp/hugo.tar.gz hugo
hugo version
```

To make the local server reachable from the browser container, I bound it to all interfaces and set the port explicitly:

```sh
hugo server --bind 0.0.0.0 --port 1313
```

## Add posts (front matter example)

Create a new Markdown file under `content/` (or a section like `content/posts/`). For example:

```sh
hugo new posts/my-first-post.md
```

Then edit the file with front matter like:

```toml
---
title = "My First Post"
date = 2024-01-01T12:00:00Z
draft = true
categories = ["updates"]
tags = ["hugo", "notes"]
---
```

Add your content below the front matter and set `draft = false` when ready to publish.

### Why a post may not show up

- Check the `date` in front matter. If the date is in the future, Hugo will not list it in normal page lists.
- Ensure the file is under the correct section (for example `content/posts/` for `/posts/`).
- Ensure `draft` is not `true`.

## Add categories/tags

Use the `categories` and `tags` arrays in your front matter:

```toml
categories = ["hugo", "site"]
tags = ["theme", "design", "notes"]
```

## Markdown Cheatsheet (GitHub-style)

Use this as a quick reminder when writing new posts.

### Headings

```md
# H1
## H2
### H3
```

### Emphasis

```md
**bold**
*italic*
~~strikethrough~~
`inline code`
```

### Lists

```md
- item
- item

1. first
2. second
```

### Links and images

```md
[OpenAI](https://openai.com)
![Alt text](/images/hodgepodge/my-photo.jpg)
```

### Code blocks (syntax highlighting enabled)

Use fenced code blocks with an info string:

```md
```python
def hello():
    print("hello")
```
```

```md
```bash
uv sync
```
```

### Blockquotes and GitHub-style alerts

Normal blockquote:

```md
> This is a quote.
```

Alert blockquotes (rendered with alert style on this site):

```md
> [!NOTE]
> Helpful context.

> [!TIP]
> Shortcut or best practice.

> [!IMPORTANT]
> Critical detail to remember.

> [!WARNING]
> Risky behavior.

> [!CAUTION]
> Could cause damage/data loss.
```

### Tables

```md
| Name | Value |
| --- | --- |
| alpha | 1 |
| beta | 2 |
```

### Task lists

```md
- [x] done
- [ ] todo
```

## Add photos to Hodgepodge

Place photos in `static/` so they are served at the site root. For example, if you add:

```
static/images/hodgepodge/my-photo.jpg
```

You can reference it in content like:

```md
![Caption](/images/hodgepodge/my-photo.jpg)
```

If the Hodgepodge section has a specific content folder (for example `content/hodgepodge/`), add a Markdown file there and embed images using the same `static/` path.

## Hodgepodge Cover Upload Guide

Hodgepodge cover images are currently rendered in two places:

- In the Hodgepodge card grid, where the image fills the card width with `width: 100%` and `height: auto`
- In the single-post hero image, where the image expands to the article width

Because the layout does **not** crop covers automatically, landscape images with a consistent aspect ratio look best.

### Recommended size

- Best practical aspect ratio: about `3:2`
- Good sizes:
  - `900 x 600`
  - `1200 x 800`
  - `1500 x 1000`
- Minimum suggested width: about `760px`
- Best for sharper hero images on high-DPI screens: `1200px` to `1600px` wide

Current examples in this repo are close to that shape:

- `static/images/hodgepodge/polymarket.png` is `761 x 505`
- `static/images/hodgepodge/storybin.png` is `940 x 612`

### Supported formats

The site serves files from `static/` directly, so normal browser-supported formats work:

- `.png`
- `.jpg` / `.jpeg`
- `.webp`
- `.svg`
- `.gif`

Practical advice:

- Use `.png` for UI screenshots, charts, and dashboards
- Use `.jpg` or `.webp` for photos
- Use `.svg` for illustrations, diagrams, and vector artwork

### Where to upload

Put the cover file under:

```text
static/images/hodgepodge/
```

Example:

```text
static/images/hodgepodge/storybin.png
```

### How to reference the cover in a Hodgepodge post

Add these fields in the front matter:

```yaml
---
title: "Storybin"
date: 2026-03-13
categories: ["Hodgepodge"]
tags: ["webapp", "crawler", "storybin"]
image: "/images/hodgepodge/storybin.png"
imageAlt: "Storybin dashboard preview"
summary: "A live crawler that turns Traditional Chinese web novels into downloadable txt [WiP]"
---
```

### Cover checklist

- Prefer landscape images
- Keep the aspect ratio close to `3:2`
- Compress large screenshots before uploading
- Add a clear `imageAlt`
- Add a short `summary`, because it is shown in the Hodgepodge card

## Tweak styling

- CSS lives under `static/` (site-wide assets) and/or inside the theme at `themes/<theme-name>/static/`.
- Templates live under `layouts/` (site overrides) and/or inside the theme at `themes/<theme-name>/layouts/`.

If you need to override a theme template, add a file to `layouts/` with the same path as the theme template.

## Profile Icons: Upload, Change, Customize

The site currently shows GitHub/Email/LinkedIn icons to the right of the avatar, and a location icon in About > Contact.

### Update icon links and location text (no template edits)

Edit `config.toml` under `[params.profile]`:

```toml
[params.profile]
  github = "https://github.com/your-account"
  email = "mailto:you@example.com"
  linkedin = "https://www.linkedin.com/in/your-id/"
  location = "Your location text"
```

### Change avatar image

1. Put your image at `static/images/avatar.png` (or another path under `static/`).
2. Update:

```toml
[params.profile]
  avatar = "/images/avatar.png"
  avatarAlt = "Portrait of ..."
```

### Use your own custom icons

Option A (recommended): keep inline SVG icons and replace SVG paths in:

- `layouts/partials/profile-hero.html` (GitHub/Email/LinkedIn icons)
- `layouts/_default/single.html` (About location/email icons)

Option B: use image files.

1. Upload icon files to `static/icons/` (for example `static/icons/github.svg`).
2. Replace SVG blocks in templates with `<img src="/icons/github.svg" ...>` etc.

After any icon/template changes, run:

```sh
./scripts/check_posts_have_tags.sh
hugo --minify --cleanDestinationDir
./scripts/check_internal_links.sh public
```

## RSS feed for home page

The home page publishes RSS using Hugo's `outputs` setting in `config.toml` and a custom template in `layouts/index.xml`.

- `config.toml` enables RSS for the home page with:
  ```toml
  outputs = { home = ["HTML", "RSS"] }
  ```
- `layouts/index.xml` renders the RSS feed using `.Site.BaseURL`, `.Site.Title`, and the most recent items from the `posts` section.

After running `hugo`, the RSS feed is generated as `public/index.xml` and will be available at `<baseURL>/index.xml`.

## Deploy to GitHub Pages

1. Build the site:
   ```sh
   hugo
   ```
   The generated site will be in `public/`.
2. Publish `public/` to GitHub Pages. Common approaches:
   - Commit `public/` to the `gh-pages` branch and configure GitHub Pages to serve from that branch.
   - Or use GitHub Actions to run `hugo` with **Hugo Extended** and publish the `public/` directory as the Pages artifact.
   - If GitHub Pages is set to serve from the repository root on the default branch, it will look for a top-level `index.html`. Without one, GitHub Pages will fall back to rendering `README.md`, which is why you might see the "Personal home page for a raccoon" content instead of the Hugo site. In that case, switch Pages to the `gh-pages` branch (or `/docs`), or commit the generated `public/` output to the root so `index.html` is available.

If using a custom domain, configure it in the GitHub Pages settings and add the `CNAME` file in `static/` so it is included in `public/`.
