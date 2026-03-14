---
title: "Storybin"
date: 2026-03-13
categories: ["Hodgepodge"]
tags: ["webapp", "crawler", "storybin"]
image: "/images/hodgepodge/storybin.png"
imageAlt: "Storybin dashboard preview"
summary: "A live crawler that turns Traditional Chinese web novels into downloadable txt [WiP]"
---

**Storybin** is a lightweight web app for searching and downloading Chinese web novels as clean `.txt` files. It combines a **FastAPI backend** with a **static frontend**, and was built to index novel metadata, support **keyword**, **associative-word**, and **fuzzy search**, and generate **Simplified Chinese** text downloads for indexed books.

> [!NOTE]
> Good for Kindle. `epub` work in progress.

The project also includes a persistent caching layer, so indexed novel metadata can be stored in **SQLite** locally or **PostgreSQL** in deployment environments such as Render. The frontend is designed for simple, fast browsing, while the backend handles indexing, search, metadata storage, and text conversion.

Link: https://joshuaqsh.github.io/Storybin/

> [!WARNING]
> Right now, Storybin aims to fetch https://www.xbanxia.cc/. However, this websit has Cloudflare to prevent automated access, scraping, and attacks (bots, DDoS, credential stuffing, etc.). Bypassing Cloudflare is hard and I am still working on it. Stay tuned!