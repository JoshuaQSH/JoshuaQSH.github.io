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

## Coffee Wall Guide

The coffee wall is driven by one content file, one data file, and the brand image folder:

- page content and cover: `content/hodgepodge/coffee-wall.md`
- coffee data: `data/coffee_wall.json`
- page layout and interactions: `layouts/hodgepodge/coffee-wall.html`
- brand logos: `static/images/coffee-brand/`

### What each file controls

- `content/hodgepodge/coffee-wall.md`
  - title
  - Hodgepodge card summary
  - cover image
  - intro copy on the page
- `data/coffee_wall.json`
  - brands
  - coffee variants
  - farm / notes / roast / grind / weight
  - how many bags of that coffee you have already finished
- `layouts/hodgepodge/coffee-wall.html`
  - node layout
  - hover panel
  - styling
  - metrics shown on the page

### Edit the page text or cover

Open:

```text
content/hodgepodge/coffee-wall.md
```

The front matter controls the title, summary, and cover:

```yaml
---
title: "Coffee Wall"
image: "/images/hodgepodge/Coffee_Wall.png"
imageAlt: "My blood type is COFFEE"
summary: "An coffee wall with branch trails for each bag, and hover details for roast, grind, and farm notes."
layout: "coffee-wall"
---
```

The Markdown body below the front matter controls the intro paragraphs on the page.

### Add a new coffee brand

1. Upload the brand image into:

```text
static/images/coffee-brand/
```

2. Open:

```text
data/coffee_wall.json
```

3. Add a new object inside the top-level `brands` array.

Example:

```json
{
  "id": "sample-roaster",
  "name": "Sample Roaster",
  "location": "York, UK",
  "image": "/images/coffee-brand/sample-roaster.png",
  "accent": "#ef4444",
  "variants": [
    {
      "id": "house-espresso",
      "name": "House Espresso",
      "farm": "Brazil",
      "process": "Natural",
      "producer": "",
      "notes": "Dark chocolate, cherry",
      "roast": "Medium/Dark",
      "grind": "Beans",
      "weightGrams": 250,
      "consumedBags": 0
    }
  ]
}
```

Tips:

- Keep `id` values lowercase and kebab-case
- `image` must start with `/images/coffee-brand/`
- `accent` can be any CSS hex color like `#4ade80`
- `weightGrams` controls the node sizing on the wall

### Add a new coffee bean under an existing brand

Open `data/coffee_wall.json`, find the brand, and add another item inside its `variants` array.

Example:

```json
{
  "id": "new-lot",
  "name": "New Lot",
  "farm": "Finca Example, Colombia",
  "region": "Huila",
  "process": "Washed",
  "producer": "Example Producer",
  "notes": "Cacao, plum, orange peel",
  "roast": "Medium",
  "grind": "Beans",
  "weightGrams": 250,
  "consumedBags": 0
}
```

### Change how many bags you have consumed

Each coffee variant now has a `consumedBags` field:

```json
"consumedBags": 3
```

This means you have finished 3 bags of that coffee.

To update it:

1. Open `data/coffee_wall.json`
2. Find the coffee variant you want
3. Change only the number in `consumedBags`

Example:

```json
{
  "id": "butter-blend",
  "name": "Butter Blend",
  "weightGrams": 454,
  "consumedBags": 4
}
```

Notes:

- `consumedBags` is a history counter
- it does **not** change the node size
- node size still comes from `weightGrams`
- the coffee wall now shows finished-bag totals in the metrics, detail panel, and shelf totals

### Remove a coffee

Delete the relevant object from the `variants` array.

If you want to remove a whole brand, delete the whole brand object from `brands`.

### Rebuild and test after editing

From the repo root:

```sh
./scripts/check_posts_have_tags.sh
hugo --minify --cleanDestinationDir
./scripts/check_internal_links.sh public
```

Then open the page locally:

```text
/hodgepodge/coffee-wall/
```

## Don't Starve Menu Guide

The food menu is driven by a content file, a data file, and the food-menu image folder:

- page content and cover: `content/hodgepodge/partner-menu.md`
- menu data: `data/partner_menu.json`
- page layout and identity gate: `layouts/hodgepodge/partner-menu.html`
- banner, login frame/button, and category PNG logos: `static/images/food_menu/`

To add a dish, open `data/partner_menu.json`, find the category inside `categories`, and add an item to its `items` array:

```json
{
  "name": "新菜名"
}
```

The current categories are `肉类`, `鱼类`, `蛋类`, `蔬菜`, `汤类`, `主食`, `饮品`, `甜点`, and `零食`. Each category has a `logo` path that should point to a transparent PNG under `static/images/food_menu/`.

## Photo Album Guide

The photo album page is powered by three places:

- raw uploads: `photo_album_raw/`
- published web images: `static/images/photo-album/`
- timeline data: `data/photo_album.json`

The page itself lives at:

- `content/hodgepodge/photo-album.md`

The timeline layout and styling live at:

- `layouts/hodgepodge/photo-album.html`
- `layouts/_default/baseof.html`

### Update the compressed photos

1. Put your original photos into `photo_album_raw/`.
2. Keep the filenames clean, because the file name becomes the photo title on the page.
3. Run:

```sh
python3 scripts/prepare_photo_album.py
```

4. This regenerates:
   - compressed web copies in `static/images/photo-album/`
   - timeline data in `data/photo_album.json`
   - and removes stale published `.jpg` files if their raw originals were deleted
5. Rebuild and test:

```sh
./scripts/check_posts_have_tags.sh
hugo --minify --cleanDestinationDir
./scripts/check_internal_links.sh public
```

### Change a photo's details

If you want to edit the title, camera details, or display time for one photo:

1. Open `data/photo_album.json`
2. Find the matching entry
3. Edit fields such as:
   - `title`
   - `marker`
   - `display_date`
   - `camera`
   - `lens`
   - `aperture`
   - `iso`
   - `exposure_time`
   - `alt`

Example:

```json
{
  "title": "Aurora over York",
  "marker": "Oct 2024",
  "display_date": "Oct 11, 2024 07:16",
  "camera": "Sony ILCE-7M4",
  "lens": "FE 24-105mm F4 G OSS",
  "aperture": "f/4",
  "iso": "1600",
  "exposure_time": "1/5s"
}
```

Note:
- The script keeps manual edits for existing entries, as long as the generated image path stays the same
- If you rename the raw photo file, the generated image path will change too, so recheck the matching entry after regeneration

### Add or remove photos

To add photos:

1. Drop new originals into `photo_album_raw/`
2. Run:

```sh
python3 scripts/prepare_photo_album.py
```

To remove photos:

1. Delete the original from `photo_album_raw/`
2. Run the same script again
3. Confirm the matching compressed file and JSON entry are gone

### Change the album cover shown on the Hodgepodge page

Edit the front matter in `content/hodgepodge/photo-album.md`:

```yaml
image: "/images/photo-album/aurora-shout-out-to-c-xia.jpg"
imageAlt: "Aurora over a dark landscape"
summary: "My personal photo gallery for fun."
```

### Change the album page text

Edit:

- `content/hodgepodge/photo-album.md`

This controls:

- the summary shown on the Hodgepodge card
- the intro text on the album page
- the poem quote

### Tweak the page layout

If you want to change the timeline structure or card content:

1. Edit `layouts/hodgepodge/photo-album.html`
2. Rebuild with Hugo

If you want to change spacing, colors, borders, or the timeline line/dots:

1. Edit the `.photo-album-*` CSS rules in `layouts/_default/baseof.html`
2. Rebuild with Hugo

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
