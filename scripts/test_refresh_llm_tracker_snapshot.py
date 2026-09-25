import gzip
import hashlib
import json
import unittest
from unittest.mock import patch

import requests
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

import refresh_llm_tracker_snapshot as tracker


def response(payload, key):
    result = requests.Response()
    result.status_code = 200
    result._content = AESGCM(key).encrypt(
        hashlib.sha256(key).digest()[:12],
        gzip.compress(json.dumps(payload).encode()),
        None,
    )
    return result


class ModelRefreshTests(unittest.TestCase):
    def test_full_manifest_not_initial_sample_supplies_rankings(self):
        key = bytes(range(32))
        manifests = [
            {"path": "/data/providers.txt", "key": key.hex()},
            {"path": "/data/models.txt", "key": key.hex()},
        ]
        model = {
            "slug": "example-max", "name": 'Example "Max"',
            "shortName": "Example Max", "intelligenceIndex": 57.62237,
            "creator": {"name": "Example", "color": "#111111"},
            "timescaleData": {"medianOutputSpeed": 45.678},
            "price1mInputTokens": 4, "price1mOutputTokens": 20,
            "price1mBlended7To2To1": 3.01,
            "releaseDate": "2026-09-01", "parameters": 2800,
            "isOpenWeights": True, "deprecated": False,
        }
        initial_models = [dict(model, slug=f"sample-{index}", intelligenceIndex=10)
                          for index in range(25)]
        flight = ''.join(
            '<script>self.__next_f.push(' + json.dumps([1, json.dumps({
                "manifest": manifest, "initialModels": initial_models,
            })]) + ')</script>'
            for manifest in manifests
        )
        with patch.object(tracker, 'fetch_text', return_value=flight), patch.object(
            tracker.requests, 'get', side_effect=[
                response([{"name": "Provider endpoint"}], key),
                response({"models": initial_models + [model]}, key),
            ],
        ):
            models, full = tracker.fetch_models()
        self.assertTrue(full)
        self.assertEqual(len(models), 26)
        row = tracker.build_benchmark_snapshot(models)["models"][0]
        self.assertEqual(row["model"], 'Example "Max"')
        self.assertEqual(row["intelligence"], 57.62)
        self.assertEqual(row["speed_tps"], 45.68)
        self.assertEqual(row["blended_price"], 8)
        self.assertEqual(row["detail_url"], "https://artificialanalysis.ai/models/example-max")
        self.assertEqual(models[0]["parameters"], 2800)
        self.assertTrue(models[0]["is_open_weights"])

    def test_missing_prices_stay_unknown_and_deprecated_models_are_excluded(self):
        key = bytes(range(32))
        flight = '<script>self.__next_f.push(' + json.dumps([1, json.dumps({
            "manifest": {"path": "/data/models.txt", "key": key.hex()},
        })]) + ')</script>'
        rows = [
            {"slug": "unknown-price", "name": "Unknown price", "shortName": "Unknown",
             "creator": {"name": "Example"}, "intelligenceIndex": 52.1,
             "timescaleData": None, "price1mInputTokens": None,
             "price1mOutputTokens": 10, "deprecated": False},
            {"slug": "retired", "name": "Retired", "shortName": "Retired",
             "creator": {"name": "Example"}, "intelligenceIndex": 99,
             "deprecated": True},
        ]
        with patch.object(tracker, 'fetch_text', return_value=flight), patch.object(
            tracker.requests, 'get', return_value=response({"models": rows}, key),
        ):
            models, _ = tracker.fetch_models()
        snapshot = tracker.build_benchmark_snapshot(models)["models"]
        self.assertEqual(len(snapshot), 1)
        self.assertIsNone(snapshot[0]["blended_price"])
        self.assertIsNone(snapshot[0]["speed_tps"])

    def test_legacy_feed_does_not_substitute_old_hardcoded_prices(self):
        html = '<script type="application/ld+json">' + json.dumps({
            "@type": "Dataset", "name": "Artificial Analysis Intelligence Index",
            "data": [{"detailsUrl": "/models/claude-opus-5", "label": "Claude Opus 5",
                      "intelligenceIndex": 51}],
        }) + '</script>'
        with patch.object(tracker, 'fetch_text', return_value=html):
            models, full = tracker.fetch_models()
        self.assertFalse(full)
        row = tracker.build_benchmark_snapshot(models)["models"][0]
        self.assertIsNone(row["input_price"])
        self.assertIsNone(row["output_price"])
        self.assertIsNone(row["blended_price"])

    def test_empty_manifest_fails_instead_of_publishing_an_empty_snapshot(self):
        key = bytes(range(32))
        html = '<script>self.__next_f.push(' + json.dumps([1, json.dumps({
            "manifest": {"path": "/data/models.txt", "key": key.hex()},
        })]) + ')</script>'
        with patch.object(tracker, 'fetch_text', return_value=html), patch.object(
            tracker.requests, 'get', return_value=response({"models": []}, key),
        ), self.assertRaisesRegex(ValueError, "empty or invalid"):
            tracker.fetch_models()

    def test_current_glm_refresh_replaces_previous_row_without_duplicates(self):
        data = {"api_pricing": [
            {"vendor": "Qwen / Alibaba Cloud", "product": "qwen3.8-max"},
            {"vendor": "Together AI / Z AI", "product": "GLM-5.2"},
        ]}
        with patch.object(tracker, 'parse_together_model_prices', return_value=(1.4, 0.26, 4.4)):
            tracker.upsert_api_rows(data)
            tracker.upsert_api_rows(data)
        self.assertEqual([row["product"] for row in data["api_pricing"]],
                         ["qwen3.8-max", "GLM-5.3"])
        self.assertEqual(len(data["history_series"]["together_glm"]["points"]), 1)

    def test_open_weight_history_keeps_verified_weights_release_date(self):
        key = bytes(range(32))
        model = {
            "name": "Kimi K3 (high)", "shortName": "Kimi K3 (high)",
            "release": {"name": "Kimi K3"}, "releaseDate": "2026-07-16",
            "parameters": 2800, "isOpenWeights": True,
            "creator": {"name": "Moonshot AI"}, "slug": "kimi-k3-high",
        }
        html = '<script>self.__next_f.push(' + json.dumps([1, json.dumps({
            "manifest": {"path": "/data/models.txt", "key": key.hex()},
        })]) + ')</script>'
        with patch.object(tracker, 'fetch_text', return_value=html), patch.object(
            tracker.requests, 'get', return_value=response({"models": [model]}, key),
        ):
            models, _ = tracker.fetch_models()
        rows = tracker.build_scale_price_frontier(models)["metrics"]["model_size"]["rows"]
        self.assertEqual(rows[-1]["date"], "2026-07-27")
        self.assertEqual(rows[-1]["source_url"], "https://github.com/MoonshotAI/Kimi-K3")
        self.assertEqual(rows[-1]["value"], 2800)


if __name__ == '__main__':
    unittest.main()
