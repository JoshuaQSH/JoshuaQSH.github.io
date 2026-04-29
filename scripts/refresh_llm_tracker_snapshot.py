#!/usr/bin/env python3

from __future__ import annotations

import copy
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "llm_pricing.json"
MODELS_URL = "https://artificialanalysis.ai/models"
PROVIDERS_URL = "https://artificialanalysis.ai/leaderboards/providers"
TOGETHER_GLM_URL = "https://www.together.ai/models/glm-5"
TOGETHER_LLAMA_URL = "https://www.together.ai/models/llama-4-maverick"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; home-page tracker refresh)"}
FRONTIER_START_DATE = "2021-01-01"
FRONTIER_SEED_ROWS = {
    "model_size": [
        {
            "date": "2021-01-11",
            "vendor": "Google Brain",
            "model": "Switch Transformer",
            "short_label": "Switch Transformer",
            "value": 1600.0,
            "source_url": "https://arxiv.org/abs/2101.03961",
            "source_label": "Switch Transformer paper",
            "detail_label": "Source",
            "note": "Sparse MoE model; total parameter count.",
        },
        {
            "date": "2021-06-01",
            "vendor": "BAAI",
            "model": "Wu Dao 2.0",
            "short_label": "Wu Dao 2.0",
            "value": 1750.0,
            "source_url": "https://www.baai.ac.cn/en/research",
            "source_label": "BAAI research page",
            "detail_label": "Source",
            "note": "Reported as the largest pre-trained model at launch; total parameter count.",
        },
        {
            "date": "2025-04-05",
            "vendor": "Meta",
            "model": "Llama 4 Behemoth",
            "short_label": "Llama 4 Behemoth",
            "value": 2000.0,
            "source_url": "https://ai.meta.com/blog/llama-4-multimodal-intelligence/",
            "source_label": "Meta Llama 4 announcement",
            "detail_label": "Source",
            "note": "Previewed research model; about 2T total parameters and 288B active parameters.",
        },
    ],
    "output_price": [
        {
            "date": "2021-01-01",
            "vendor": "OpenAI",
            "model": "davinci",
            "short_label": "davinci",
            "value": 60.0,
            "source_url": "https://fewald.net/machine-learning/2022/08/22/openai-api-price-reduction.html",
            "source_label": "OpenAI API price-reduction note",
            "detail_label": "Source",
            "note": "Legacy GPT-3 era price converted from $0.06 per 1K tokens.",
        },
        {
            "date": "2023-03-14",
            "vendor": "OpenAI",
            "model": "gpt-4-32k",
            "short_label": "GPT-4 32K",
            "value": 120.0,
            "source_url": "https://help.openai.com/en/articles/7127956-how-much-does-gpt-4-cost",
            "source_label": "OpenAI GPT-4 pricing help",
            "detail_label": "Source",
            "note": "Output price for the 32K GPT-4 API tier.",
        },
        {
            "date": "2025-02-27",
            "vendor": "OpenAI",
            "model": "gpt-4.5-preview",
            "short_label": "GPT-4.5 Preview",
            "value": 150.0,
            "source_url": "https://platform.openai.com/docs/models/gpt-4.5-preview",
            "source_label": "OpenAI GPT-4.5 model page",
            "detail_label": "Source",
            "note": "Deprecated research preview; output price at launch.",
        },
        {
            "date": "2025-03-19",
            "vendor": "OpenAI",
            "model": "o1-pro",
            "short_label": "o1-pro",
            "value": 600.0,
            "source_url": "https://platform.openai.com/docs/models/o1-pro",
            "source_label": "OpenAI o1-pro model page",
            "detail_label": "Source",
            "note": "Highest public text-output token price found in the reviewed sources.",
        },
    ],
}


def fetch_text(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.text


def decode_embedded_array(html: str, marker: str) -> list[dict[str, Any]]:
    marker_index = html.find(marker)
    if marker_index == -1:
        raise ValueError(f"Could not find marker {marker!r}")
    start = html.find("[", marker_index)
    if start == -1:
        raise ValueError(f"Could not find '[' after marker {marker!r}")
    decoded = html[start:].replace('\\"', '"')
    payload, _ = json.JSONDecoder().raw_decode(decoded)
    if not isinstance(payload, list):
        raise ValueError(f"Embedded payload for {marker!r} is not a list")
    return payload


def parse_together_model_prices(url: str) -> tuple[float, float]:
    text = fetch_text(url)

    def extract(label: str) -> float:
        pattern = re.compile(
            rf"{re.escape(label)}</div></div>.*?<span>\$(.*?)</span>.*?1M tokens",
            re.DOTALL,
        )
        match = pattern.search(text)
        if not match:
            raise ValueError(f"Could not parse {label!r} from {url}")
        return float(match.group(1))

    return extract("Input price"), extract("Output price")


def round_or_none(value: Any, digits: int = 2) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)


def format_usd(value: float | None) -> str:
    if value is None:
        return "-"
    return f"${value:.2f}"


def pretty_date(stamp: datetime) -> str:
    return stamp.strftime("%B %d, %Y").replace(" 0", " ")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def fetch_models() -> list[dict[str, Any]]:
    html = fetch_text(MODELS_URL)
    return decode_embedded_array(html, '\\"models\\":[{\\"additional_text\\"')


def upsert_api_rows(data: dict[str, Any]) -> None:
    glm_input, glm_output = parse_together_model_prices(TOGETHER_GLM_URL)
    llama_input, llama_output = parse_together_model_prices(TOGETHER_LLAMA_URL)

    rows = list(data.get("api_pricing", []))

    glm_row = {
        "vendor": "Together AI / Z AI",
        "product": "GLM-5",
        "unit": "USD per 1M tokens",
        "input_display": format_usd(glm_input),
        "input_value": glm_input,
        "cached_input_display": "-",
        "cached_input_value": None,
        "output_display": format_usd(glm_output),
        "output_value": glm_output,
        "notes": "Together AI's public serverless price for Z AI's GLM-5. The public model page does not list a separate cached-input rate.",
        "official_link": TOGETHER_GLM_URL,
        "source_label": "Together AI GLM-5 pricing",
    }
    llama_row = {
        "vendor": "Meta / Llama via Together AI",
        "product": "Llama 4 Maverick",
        "unit": "USD per 1M tokens",
        "input_display": format_usd(llama_input),
        "input_value": llama_input,
        "cached_input_display": "-",
        "cached_input_value": None,
        "output_display": format_usd(llama_output),
        "output_value": llama_output,
        "notes": "Meta's Llama 4 Maverick served through Together AI's public serverless API. Meta's public developer docs describe the model family, while Together AI exposes a comparable public token price.",
        "official_link": TOGETHER_LLAMA_URL,
        "source_label": "Together AI Llama 4 Maverick pricing",
    }

    def replace_or_insert(after_key: tuple[str, str], new_row: dict[str, Any]) -> None:
        key = (new_row["vendor"], new_row["product"])
        rows[:] = [
            row for row in rows if (row.get("vendor"), row.get("product")) != key
        ]
        try:
            index = next(
                i
                for i, row in enumerate(rows)
                if (row.get("vendor"), row.get("product")) == after_key
            )
            rows.insert(index + 1, new_row)
        except StopIteration:
            rows.append(new_row)

    replace_or_insert(("Qwen / Alibaba Cloud", "qwen-max-latest"), glm_row)
    replace_or_insert(("Together AI / Z AI", "GLM-5"), llama_row)
    data["api_pricing"] = rows

    history = data.setdefault("history_series", {})

    def maybe_append_point(
        key: str,
        label: str,
        source: str,
        note: str,
        model: str,
        input_miss: float | None,
        input_hit: float | None,
        output: float | None,
    ) -> None:
        series = history.setdefault(
            key,
            {
                "label": label,
                "currency": "USD per 1M tokens",
                "note": note,
                "points": [],
            },
        )
        series["label"] = label
        series["currency"] = "USD per 1M tokens"
        series["note"] = note
        points = list(series.get("points", []))
        latest = points[-1] if points else None
        snapshot = {
            "date": now_utc().date().isoformat(),
            "model": model,
            "input_miss": input_miss,
            "input_hit": input_hit,
            "output": output,
            "source": source,
        }
        if latest and all(latest.get(field) == snapshot[field] for field in ("model", "input_miss", "input_hit", "output", "source")):
            return
        points.append(snapshot)
        series["points"] = points

    maybe_append_point(
        key="together_glm",
        label="Together AI / GLM-5",
        source=TOGETHER_GLM_URL,
        note="Together AI's public GLM-5 model page. This history line grows only when Together AI's public GLM-5 price changes.",
        model="GLM-5",
        input_miss=glm_input,
        input_hit=None,
        output=glm_output,
    )
    maybe_append_point(
        key="meta_llama_together",
        label="Meta / Llama 4 Maverick (Together AI)",
        source=TOGETHER_LLAMA_URL,
        note="Public Together AI pricing for Meta's Llama 4 Maverick endpoint. This history line is a public comparable endpoint rather than Meta's first-party internal pricing.",
        model="Llama 4 Maverick",
        input_miss=llama_input,
        input_hit=None,
        output=llama_output,
    )


def build_benchmark_snapshot(models: list[dict[str, Any]]) -> dict[str, Any]:
    ranked_models = sorted(
        [
            model
            for model in models
            if model.get("intelligence_index") is not None
            and not model.get("deleted")
            and not model.get("deprecated")
        ],
        key=lambda item: float(item["intelligence_index"]),
        reverse=True,
    )[:10]

    vendor_labels = {
        "Alibaba": "Qwen / Alibaba",
    }

    return {
        "note": "Top 10 current models by Artificial Analysis Intelligence Index. Prices and speeds below come from Artificial Analysis' benchmark snapshot, so they may differ from the manual API rows above when multiple deployments or reasoning modes exist.",
        "source_url": MODELS_URL,
        "source_label": "Artificial Analysis models leaderboard",
        "generated_at_pretty": pretty_date(now_utc()),
        "models": [
            {
                "vendor": vendor_labels.get(
                    model["model_creators"]["name"], model["model_creators"]["name"]
                ),
                "model": model["name"],
                "short_label": model["short_name"],
                "intelligence": round_or_none(model.get("intelligence_index")),
                "speed_tps": round_or_none(
                    (model.get("timescaleData") or {}).get("median_output_speed")
                ),
                "blended_price": round_or_none(model.get("price_1m_blended_3_to_1"), 4),
                "input_price": round_or_none(model.get("price_1m_input_tokens"), 4),
                "output_price": round_or_none(model.get("price_1m_output_tokens"), 4),
                "detail_url": f"https://artificialanalysis.ai{model['model_url']}",
                "detail_label": "Model details",
                "color": model["model_creators"].get("color") or "#1d4ed8",
            }
            for model in ranked_models
        ],
    }


def build_scale_price_frontier(models: list[dict[str, Any]]) -> dict[str, Any]:
    def valid_model(model: dict[str, Any]) -> bool:
        return (
            bool(model.get("release_date"))
            and not model.get("deleted")
            and not model.get("deprecated")
        )

    def model_url(model: dict[str, Any]) -> str:
        return f"https://artificialanalysis.ai{model['model_url']}"

    def build_milestones(
        seed_key: str,
        value_key: str,
        minimum: float,
        digits: int,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = copy.deepcopy(FRONTIER_SEED_ROWS[seed_key])
        seen: set[tuple[str, str, float]] = set()
        for row in rows:
            seen.add((row["date"], row["short_label"], float(row["value"])))
        for model in models:
            value = model.get(value_key)
            if value is None or not valid_model(model):
                continue
            numeric = float(value)
            if numeric < minimum:
                continue
            key = (model["release_date"], model["short_name"], numeric)
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "date": model["release_date"],
                    "vendor": model["model_creators"]["name"],
                    "model": model["name"],
                    "short_label": model["short_name"],
                    "value": round(numeric, digits),
                    "detail_url": model_url(model),
                    "source_url": model_url(model),
                    "source_label": "Artificial Analysis model details",
                    "detail_label": "Model details",
                }
            )

        rows.sort(key=lambda item: (item["date"], item["value"], item["short_label"]))
        best = float("-inf")
        milestones: list[dict[str, Any]] = []
        for row in rows:
            if row["value"] > best:
                best = row["value"]
                milestones.append(row)
        return milestones

    return {
        "note": "Milestone lines start in 2021 and combine curated source-backed historical records with the latest Artificial Analysis model metadata. Model size uses total disclosed parameters, so sparse MoE and dense models are not quality-equivalent. Output-token price uses public USD text-token API prices and excludes tool-call, image, audio, video, and subscription pricing.",
        "source_url": MODELS_URL,
        "source_label": "Artificial Analysis models",
        "generated_at_pretty": pretty_date(now_utc()),
        "start_date": FRONTIER_START_DATE,
        "default_metric": "model_size",
        "metrics": {
            "model_size": {
                "label": "Largest disclosed LLM size",
                "description": "Running record of the largest publicly disclosed total parameter count since 2021.",
                "y_label": "Parameters",
                "unit": "B parameters",
                "value_format": "parameters",
                "rows": build_milestones("model_size", "parameters", minimum=100, digits=3),
            },
            "output_price": {
                "label": "Most expensive output token",
                "description": "Running record of the highest reviewed public text-output token price since 2021.",
                "y_label": "Output price",
                "unit": "USD per 1M output tokens",
                "value_format": "usd",
                "rows": build_milestones("output_price", "price_1m_output_tokens", minimum=0.0001, digits=4),
            },
        },
    }


def build_provider_leaderboard() -> dict[str, Any]:
    html = fetch_text(PROVIDERS_URL)
    host_models = decode_embedded_array(html, '\\"hostsModels\\":[{\\"id\\"')
    valid_rows = [
        row
        for row in host_models
        if isinstance(row, dict)
        and row.get("host")
        and row.get("model")
        and not row.get("deleted")
        and not row["host"].get("deleted")
        and not row["model"].get("deleted")
    ]

    metrics = {
        "intelligence": {
            "label": "Intelligence Index",
            "description": "Higher is better. Ranked by each provider's strongest currently benchmarked endpoint.",
            "higher_is_better": True,
            "extractor": lambda row: row["model"].get("intelligence_index"),
        },
        "price": {
            "label": "Blended price",
            "description": "Lower is better. Ranked by the provider's lowest currently benchmarked blended USD price (3:1 input/output mix).",
            "higher_is_better": False,
            "extractor": lambda row: row.get("price_1m_blended_3_to_1"),
        },
        "latency": {
            "label": "Latency",
            "description": "Lower is better. Ranked by median time to first token for the provider's fastest currently benchmarked endpoint.",
            "higher_is_better": False,
            "extractor": lambda row: (row.get("timescaleData") or {}).get(
                "median_time_to_first_chunk"
            ),
        },
        "context_window": {
            "label": "Context window",
            "description": "Higher is better. Ranked by the provider's largest currently benchmarked context window.",
            "higher_is_better": True,
            "extractor": lambda row: row.get("context_window_tokens"),
        },
    }

    metric_payloads: dict[str, Any] = {}
    for key, metric in metrics.items():
        best_by_provider: dict[str, tuple[float, dict[str, Any]]] = {}
        for row in valid_rows:
            value = metric["extractor"](row)
            if value is None:
                continue
            provider = row["host"]["name"]
            current = best_by_provider.get(provider)
            numeric = float(value)
            if current is None:
                best_by_provider[provider] = (numeric, row)
                continue
            current_value = current[0]
            if metric["higher_is_better"] and numeric > current_value:
                best_by_provider[provider] = (numeric, row)
            elif not metric["higher_is_better"] and numeric < current_value:
                best_by_provider[provider] = (numeric, row)

        ranked = sorted(
            best_by_provider.values(),
            key=lambda item: item[0],
            reverse=metric["higher_is_better"],
        )[:25]
        metric_payloads[key] = {
            "label": metric["label"],
            "description": metric["description"],
            "higher_is_better": metric["higher_is_better"],
            "rows": [
                {
                    "rank": rank,
                    "provider": row["host"]["name"],
                    "model": row["model"]["short_name"],
                    "value": round_or_none(value, 6),
                    "detail_url": f"https://artificialanalysis.ai{row['hosts_url']}",
                    "detail_label": "Provider details",
                }
                for rank, (value, row) in enumerate(ranked, start=1)
            ],
        }

    return {
        "default_metric": "intelligence",
        "generated_at_pretty": pretty_date(now_utc()),
        "source_url": PROVIDERS_URL,
        "source_label": "Artificial Analysis provider leaderboard",
        "note": "Each provider rank uses that provider's best currently benchmarked endpoint for the selected metric, so the representative model can change across metrics.",
        "metrics": metric_payloads,
    }


def strip_generated_dates(payload: dict[str, Any]) -> dict[str, Any]:
    clone = copy.deepcopy(payload)
    for key in ("generated_at", "generated_at_pretty", "generated_at_iso"):
        clone.pop(key, None)
    if isinstance(clone.get("benchmark_snapshot"), dict):
        clone["benchmark_snapshot"].pop("generated_at_pretty", None)
    if isinstance(clone.get("provider_leaderboard"), dict):
        clone["provider_leaderboard"].pop("generated_at_pretty", None)
    if isinstance(clone.get("scale_price_frontier"), dict):
        clone["scale_price_frontier"].pop("generated_at_pretty", None)
    return clone


def main() -> None:
    current = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    updated = copy.deepcopy(current)

    updated["summary_note"] = (
        "This tracker loads the latest repo snapshot. The button below checks GitHub "
        "for a newer snapshot at most once per day in this browser; official pricing "
        "pages can still change between repo refreshes."
    )

    models = fetch_models()

    upsert_api_rows(updated)
    updated["benchmark_snapshot"] = build_benchmark_snapshot(models)
    updated["scale_price_frontier"] = build_scale_price_frontier(models)
    updated["provider_leaderboard"] = build_provider_leaderboard()

    if strip_generated_dates(updated) != strip_generated_dates(current):
        stamp = now_utc()
        updated["generated_at"] = stamp.date().isoformat()
        updated["generated_at_pretty"] = pretty_date(stamp)
        updated["generated_at_iso"] = stamp.replace(microsecond=0).isoformat()
        updated["benchmark_snapshot"]["generated_at_pretty"] = pretty_date(stamp)
        updated["scale_price_frontier"]["generated_at_pretty"] = pretty_date(stamp)
        updated["provider_leaderboard"]["generated_at_pretty"] = pretty_date(stamp)
    else:
        updated["generated_at"] = current.get("generated_at")
        updated["generated_at_pretty"] = current.get("generated_at_pretty")
        updated["generated_at_iso"] = current.get("generated_at_iso")
        updated["benchmark_snapshot"]["generated_at_pretty"] = current.get(
            "benchmark_snapshot", {}
        ).get("generated_at_pretty", current.get("generated_at_pretty"))
        updated["scale_price_frontier"]["generated_at_pretty"] = current.get(
            "scale_price_frontier", {}
        ).get("generated_at_pretty", current.get("generated_at_pretty"))
        updated["provider_leaderboard"]["generated_at_pretty"] = current.get(
            "provider_leaderboard", {}
        ).get("generated_at_pretty", current.get("generated_at_pretty"))

    DATA_PATH.write_text(
        json.dumps(updated, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Refreshed {DATA_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
