---
title: "LLM Pricing Tracker: API and Subscription Costs"
date: 2026-03-19
lastmod: 2026-09-25
summary: "A tracker for leading LLM API token prices and consumer subscriptions, with official links, repo snapshot refreshes, price-history charts, and live benchmark/provider snapshots."
tags: ["llm", "pricing", "api", "openai", "anthropic", "gemini", "copilot", "market-tracker"]
categories: ["AI", "Pricing"]
pinned: true
layout: "llm-pricing-tracker"
---

{{< llm-pricing-update-note >}}

This page tracks public pricing from official provider pages for major model vendors I regularly compare: OpenAI (GPT-6 Astra, Sol, and Luna), Google (Gemini 3.8 Flash and Gemma 4), Anthropic (Claude Fable 5.1, Opus 5.5, and Sonnet 5), xAI (Grok 4.7), DeepSeek (V4.1 Flash and V4 Pro), Qwen3.8 Max, Moonshot/Kimi (Kimi K3 and K2.7 Code), Xiaomi/MiMo V2.6, MiniMax M3, Together AI's GLM-5.3 endpoint, and GitHub Copilot. Claude Mythos 5.1 is listed separately as invitation-only.

API and subscription prices were manually reviewed on **September 25, 2026**. Benchmark refresh dates below are separate from this pricing review date.

A few quick cautions before using the numbers:

- API pricing and consumer subscription pricing are different products.
- Some vendors publish tiered pricing by context length, region, or prompt type.
- API rows use standard-service USD prices per one million text tokens unless explicitly marked otherwise. Cache reads, cache writes, storage, tool calls, taxes, and subscription allowances are different charges.
- DeepSeek chart values use peak prices; off-peak rates are half as much. Gemini 3.8 Flash's listed promotion ends on December 31, 2026. Qwen3.8 Max cache-hit prices require checking the Model Studio console and are not inferred from older models' discounts.
- When a vendor does not publicly expose a comparable token-billing number, I mark that clearly instead of guessing.
- The charts below use snapshots stored in this repo, including daily-refreshable Artificial Analysis benchmark/provider snapshots and manually curated pricing rows from official vendor pages.
- Historical points retain the price observed on that date, including earlier models and promotions. Benchmark scores can change when Artificial Analysis revises its evaluation suite; they are not a fixed year-to-year scale.
