---
title: "Hello, Hugo"
date: 2024-01-01
summary: First submission of the Hugo page, demo for testing."
categories: ["Notes"]
tags: ["hugo", "initpost"]
---

A short hello world post to verify the Posts section renders as expected.

## How to test Hugo build locally


```bash
cd ~/home-page
./scripts/check_posts_have_tags.sh
~/.local/bin/hugo --minify
./scripts/check_internal_links.sh public
```

If all pass, start local preview:

```bash
cd ~/home-page
~/.local/bin/hugo server --bind 127.0.0.1 --port 1313 --disableFastRender
```

If `~/.local/bin/hugo` is already in your `PATH`, you can replace it with just `hugo`.