# Hugo Usage Guide

## Install Hugo

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

For other platforms or the extended version, see https://gohugo.io/installation/.

## Run the local server

From the repo root, run:

```sh
hugo server
```

The site will be available at http://localhost:1313/ and will live-reload as you edit files.

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

## Add categories/tags

Use the `categories` and `tags` arrays in your front matter:

```toml
categories = ["hugo", "site"]
tags = ["theme", "design", "notes"]
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

## Tweak styling

- CSS lives under `static/` (site-wide assets) and/or inside the theme at `themes/<theme-name>/static/`.
- Templates live under `layouts/` (site overrides) and/or inside the theme at `themes/<theme-name>/layouts/`.

If you need to override a theme template, add a file to `layouts/` with the same path as the theme template.

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
   - Or use GitHub Actions to run `hugo` and publish the `public/` directory as the Pages artifact.

If using a custom domain, configure it in the GitHub Pages settings and add the `CNAME` file in `static/` so it is included in `public/`.
