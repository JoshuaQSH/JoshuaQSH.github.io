"""Offline checks for the observatory's cautious metadata pipeline."""
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

import refresh_ai_research_observatory as pipeline
from refresh_ai_research_observatory import classify_sector, deduplicate, normalize_work, score_components


VENUE = {"id": "osdi", "name": "OSDI", "area": "Systems", "ai_native": False,
         "rank": "A", "ranking_scheme": "CCF", "prestige": 1,
         "source_id": "https://openalex.org/S1", "edition": "2022", "rank_url": "https://www.ccf.org.cn/"}


class ObservatoryTests(unittest.TestCase):
    def test_ranked_ai_catalog_and_year_grid(self):
        venues = json.loads(pipeline.VENUES.read_text())
        by_id = {venue["id"]: venue for venue in venues}
        self.assertEqual(len(by_id), len(venues))
        for ids, scheme, rank in (
            ("aaai aamas acl acmmm colt cvpr ec eccv emnlp icaps iccv icdm iclr icml icra ijcai kdd kr neurips", "CORE", "A*"),
            ("uai wacv icme ijcar interspeech jelia miccai ppsn ecml-pkdd naacl bmvc hri iros sat eacl wsdm aistats cade cikm cp ecai foga gecco", "CORE", "A"),
            ("aaai neurips acl cvpr iccv icml iclr", "CCF", "A"),
            ("colt emnlp ecai eccv icra icaps iccbr coling kr uai aamas ppsn naacl ijcai", "CCF", "B"),
            ("kdd sigir acmmm www", "CCF", "A"),
            ("cikm wsdm ecml-pkdd iswc icdm recsys sdm icmr icassp icme", "CCF", "B"),
            ("cvpr iccv icml acl eccv colt neurips aaai emnlp icra iclr rss", "TH-CPL", "A"),
        ):
            for venue_id in ids.split():
                self.assertIn(venue_id, by_id)
                self.assertEqual(by_id[venue_id]["rankings"][scheme], rank)
        self.assertNotIn("siggraph", by_id)
        self.assertNotIn("sigspatial", by_id)
        self.assertNotIn("osdi", by_id)
        self.assertTrue(by_id["sigir"]["ai_native"])
        self.assertTrue(by_id["kdd"]["ai_native"])
        self.assertFalse(by_id["www"]["ai_native"])

    def test_published_snapshot_covers_every_catalog_year_without_fake_counts(self):
        snapshot = json.loads(pipeline.OUTPUT.read_text())
        venues = {venue["id"] for venue in snapshot["venues"]}
        self.assertEqual(venues, {venue["id"] for venue in json.loads(pipeline.VENUES.read_text())})
        self.assertEqual({(row["venue_id"], row["year"]) for row in snapshot["coverage"]},
                         {(venue, year) for venue in venues for year in range(2020, 2027)})
        self.assertEqual(len(snapshot["coverage"]), len(venues) * 7)
        self.assertTrue(all(paper["venue_id"] in venues for paper in snapshot["papers"]))
        self.assertTrue(all(row.get("source_total") is None for row in snapshot["coverage"] if row["status"] == "unmapped"))
        highlights = json.loads((pipeline.ROOT / "data/ai_research_observatory/arxiv_highlights.json").read_text())
        self.assertTrue(all(item["url"].startswith("https://arxiv.org/abs/") for item in highlights))
        self.assertTrue(all(item["url"] not in {paper["url"] for paper in snapshot["papers"]} for item in highlights))

    def test_missing_index_source_is_explicit_not_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            venues, reviews, output = (root / name for name in ("venues.json", "reviews.json", "snapshot.json"))
            venues.write_text(json.dumps([{**VENUE, "source_id": None}]))
            reviews.write_text("{}")
            with patch.multiple(pipeline, VENUES=venues, REVIEWS=reviews, OUTPUT=output), \
                 patch.object(pipeline, "fetch_works") as fetch:
                pipeline.refresh(2020, 2021, 25, official_cap=0, github_cap=0)
            self.assertEqual(fetch.call_count, 0)
            rows = json.loads(output.read_text())["coverage"]
            self.assertEqual([row["year"] for row in rows], [2020, 2021])
            self.assertTrue(all(row["status"] == "unmapped" and row["source_total"] is None for row in rows))

    def test_conference_history_has_sourced_consistent_records(self):
        history = json.loads((pipeline.ROOT / "static/data/ai-research-conference-history.json").read_text())
        venue_ids = {venue["id"] for venue in history["conferences"]}
        keys = [(row["venue"], row["year"]) for row in history["counts"]]
        self.assertEqual(len(keys), len(set(keys)))
        for row in history["counts"]:
            self.assertIn(row["venue"], venue_ids)
            self.assertGreaterEqual(row["year"], 2020)
            self.assertTrue(row["source"].startswith("https://"))
            self.assertIsInstance(row["scope"], str)
            for field in ("submitted", "accepted"):
                if row[field] is not None:
                    self.assertGreater(row[field], 0)
            if row["submitted"] is not None and row["accepted"] is not None:
                self.assertLessEqual(row["accepted"], row["submitted"])
        for award in history["awards"]:
            self.assertTrue(award["source"].startswith("https://"))
            self.assertTrue(award["topics"])

    def test_paper_specific_dual_affiliation_is_mixed(self):
        self.assertEqual(classify_sector([{"type": "company"}, {"type": "education"}]), "Mixed")
        self.assertEqual(classify_sector([]), "Unknown")

    def test_broad_venue_requires_ai_topic_and_preserves_unknowns(self):
        base = {"id": "https://openalex.org/W1", "title": "A faster filesystem", "publication_year": 2024}
        self.assertIsNone(normalize_work(base, VENUE))
        base["title"] = "Efficient LLM inference on GPU clusters"
        p = normalize_work(base, VENUE)
        self.assertEqual(p["leadership"], "Unknown")
        self.assertIsNone(p["award"])
        self.assertIsNone(p["code_available"])
        self.assertIsNone(p["citation_percentile"])
        self.assertEqual(p["topic_rule"], "title-keyword")

    def test_cross_sector_does_not_imply_leadership(self):
        w = {"id": "https://openalex.org/W2", "title": "GPU inference", "publication_year": 2025,
             "authorships": [{"author_position": "first", "author": {"display_name": "A"},
                              "institutions": [{"type": "education", "display_name": "U", "country_code": "GB"}]},
                             {"author_position": "last", "institutions": [{"type": "company", "display_name": "C"}]}]}
        p = normalize_work(w, VENUE)
        self.assertEqual(p["team_sector"], "Joint")
        self.assertEqual(p["first_author_sector"], "University")
        self.assertEqual(p["leadership"], "Unknown")

    def test_doi_dedup_and_review_override(self):
        a = {"id": "https://openalex.org/W1", "doi": "https://doi.org/10.1/X", "citations": 10}
        b = {"id": "https://openalex.org/W2", "doi": "https://doi.org/10.1/x", "citations": 20}
        self.assertEqual([p["id"] for p in deduplicate([a, b, b])], ["https://openalex.org/W2"])

    def test_score_components_only_verified(self):
        p = {"citation_percentile": .8, "prestige": 1, "award": None, "code_available": None}
        self.assertEqual(score_components(p), {"citation": .8, "venue": 1})

    def test_review_rejects_unverified_or_invalid_claims(self):
        with self.assertRaises(ValueError):
            pipeline.validate_review({"leadership": "Industry-led", "evidence_url": ""})
        with self.assertRaises(ValueError):
            pipeline.validate_review({"award": "yes", "evidence_url": "https://example.org/evidence"})
        with self.assertRaises(ValueError):
            pipeline.validate_review({"exclude": "yes", "evidence_url": "https://example.org/evidence"})
        pipeline.validate_review({"exclude": True, "review_note": "Workshop paper", "evidence_url": "https://example.org/evidence"})
        with self.assertRaises(ValueError):
            pipeline.validate_review({"repository_url": "https://github.com/org/repo", "evidence_url": "https://example.org/paper"})
        with self.assertRaises(ValueError):
            pipeline.validate_review({"adoption_status": "production", "adoption_evidence_url": "", "evidence_url": "https://example.org/paper"})
        with self.assertRaises(ValueError):
            pipeline.validate_review({"maintenance_status": "active", "maintenance_evidence_url": "https://github.com/org/repo/releases", "evidence_url": "https://example.org/paper"})
        pipeline.validate_review({"adoption_status": "integration", "adoption_evidence_url": "https://example.org/integration",
            "maintenance_status": "active", "maintenance_evidence_url": "https://github.com/org/repo/releases",
            "repository_url": "https://github.com/org/repo", "repository_evidence_url": "https://example.org/paper",
            "date": "2026-10-15", "evidence_url": "https://example.org/paper"})

    def test_official_proceedings_add_records_not_in_openalex(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            venues, reviews, output = (root / name for name in ("venues.json", "reviews.json", "snapshot.json"))
            venue = {**VENUE, "id": "icml", "name": "ICML", "ai_native": True}
            venues.write_text(json.dumps([venue])); reviews.write_text("{}")
            official = [{"title": "An ICML paper on GPU inference", "url": "https://proceedings.mlr.press/v267/a.html",
                         "first_author": "Ada", "code_url": "https://github.com/org/repo"},
                        {"title": "Another ICML paper", "url": "https://proceedings.mlr.press/v267/b.html",
                         "first_author": "Bob", "code_url": None}]
            with patch.multiple(pipeline, VENUES=venues, REVIEWS=reviews, OUTPUT=output), \
                 patch.object(pipeline, "fetch_official_index", return_value=(official, "2026-10-15T00:00:00+00:00")), \
                 patch.object(pipeline, "fetch_works", return_value=([], 0, "2026-10-15T00:00:00+00:00", False)):
                pipeline.refresh(2025, 2025, 25, official_cap=2, github_cap=0)
            snapshot = json.loads(output.read_text())
            self.assertEqual(len(snapshot["papers"]), 2)
            self.assertEqual(snapshot["coverage"][0]["official_total"], 2)
            self.assertEqual(snapshot["papers"][0]["first_author_sector"], "Unknown")

    def test_official_source_error_preserves_prior_records(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            venues, reviews, output = (root / name for name in ("venues.json", "reviews.json", "snapshot.json"))
            venue = {**VENUE, "id": "icml", "name": "ICML", "ai_native": True}
            venues.write_text(json.dumps([venue])); reviews.write_text("{}")
            old = {"id": "https://proceedings.mlr.press/v267/a.html", "title": "A paper", "year": 2025,
                   "venue_id": "icml", "source": "PMLR", "citations": None}
            output.write_text(json.dumps({"papers": [old], "coverage": []}))
            with patch.multiple(pipeline, VENUES=venues, REVIEWS=reviews, OUTPUT=output), \
                 patch.object(pipeline, "fetch_official_index", side_effect=RuntimeError("network down")), \
                 patch.object(pipeline, "fetch_works", return_value=([], 0, "2026-10-15T00:00:00+00:00", False)):
                pipeline.refresh(2025, 2025, 25, official_cap=2, github_cap=0)
            self.assertEqual(json.loads(output.read_text())["papers"][0]["id"], old["id"])

    def test_official_failure_preserves_merged_proceedings_link(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            venues, reviews, output = (root / name for name in ("venues.json", "reviews.json", "snapshot.json"))
            venue = {**VENUE, "id": "icml", "name": "ICML", "ai_native": True}
            venues.write_text(json.dumps([venue])); reviews.write_text("{}")
            work = {"id": "https://openalex.org/W10", "title": "A verified ICML paper", "publication_year": 2025, "type": "conference-paper"}
            official_url = "https://proceedings.mlr.press/v267/verified.html"
            raw = [{"title": work["title"], "url": official_url, "first_author": "Ada", "code_url": None}]
            with patch.multiple(pipeline, VENUES=venues, REVIEWS=reviews, OUTPUT=output), \
                 patch.object(pipeline, "fetch_works", return_value=([work], 1, "2026-10-15T00:00:00Z", False)), \
                 patch.object(pipeline, "fetch_official_index", side_effect=[(raw, "2026-10-15T00:00:00Z"), RuntimeError("offline")]):
                pipeline.refresh(2025, 2025, 25, official_cap=1, github_cap=0)
                pipeline.refresh(2025, 2025, 25, official_cap=1, github_cap=0)
            paper = json.loads(output.read_text())["papers"][0]
            self.assertEqual(paper["id"], work["id"])
            self.assertEqual(paper["proceedings_url"], official_url)

    def test_reviewed_github_snapshot_survives_refresh(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            venues, reviews, output = (root / name for name in ("venues.json", "reviews.json", "snapshot.json"))
            venue = {**VENUE, "id": "icml", "name": "ICML", "ai_native": True}
            paper_url = "https://proceedings.mlr.press/v306/example.html"
            repo_url = "https://github.com/org/repo"
            venues.write_text(json.dumps([venue]))
            reviews.write_text(json.dumps({paper_url: {"repository_url": repo_url,
                "repository_evidence_url": paper_url, "evidence_url": paper_url}}))
            raw = [{"title": "Example paper", "url": paper_url, "first_author": "Ada", "code_url": None}]
            github = {"url": repo_url, "stars": 23, "pushed_at": "2026-10-01T00:00:00Z",
                      "checked_at": "2026-10-15T00:00:00Z", "archived": False, "fork": False}
            with patch.multiple(pipeline, VENUES=venues, REVIEWS=reviews, OUTPUT=output), \
                 patch.object(pipeline, "fetch_official_index", return_value=(raw, "2026-10-15T00:00:00Z")), \
                 patch.object(pipeline, "fetch_github_metadata", return_value=github) as fetch:
                pipeline.refresh(2026, 2026, 25, official_cap=1, github_cap=1, skip_openalex=True)
                pipeline.refresh(2026, 2026, 25, official_cap=1, github_cap=0, skip_openalex=True)
            self.assertEqual(fetch.call_count, 1)
            self.assertEqual(json.loads(output.read_text())["papers"][0]["github"]["stars"], 23)

    def test_reviewed_exclusion_survives_refresh(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            venues, reviews, output = (root / name for name in ("venues.json", "reviews.json", "snapshot.json"))
            venues.write_text(json.dumps([VENUE]))
            reviews.write_text(json.dumps({"https://openalex.org/W1": {"exclude": True, "review_note": "Not a main paper",
                "evidence_url": "https://example.org/proceedings"}}))
            work = {"id": "https://openalex.org/W1", "title": "GPU inference", "publication_year": 2025, "type": "conference-paper"}
            with patch.multiple(pipeline, VENUES=venues, REVIEWS=reviews, OUTPUT=output), \
                 patch.object(pipeline, "fetch_works", return_value=([work], 1, "2026-10-15T00:00:00+00:00", False)):
                pipeline.refresh(2025, 2025, 25)
            self.assertEqual(json.loads(output.read_text())["papers"], [])

    def test_manual_work_is_verified_and_retained(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            venues, reviews, manual, output = (root / name for name in ("venues.json", "reviews.json", "manual.json", "snapshot.json"))
            venues.write_text(json.dumps([VENUE]))
            reviews.write_text("{}")
            manual.write_text(json.dumps([{"id": "https://openalex.org/W7", "venue_id": "osdi", "year": 2025,
                "evidence_url": "https://example.org/proceedings"}]))
            work = {"id": "https://openalex.org/W7", "title": "GPU inference for LLMs", "publication_year": 2025,
                    "type": "conference-paper", "primary_location": {"source": {"id": VENUE["source_id"]}}}
            with patch.multiple(pipeline, VENUES=venues, REVIEWS=reviews, MANUAL=manual, OUTPUT=output), \
                 patch.object(pipeline, "fetch_works", return_value=([], 0, "2026-10-15T00:00:00+00:00", False)), \
                 patch.object(pipeline, "fetch_work_by_id", return_value=work):
                pipeline.refresh(2025, 2025, 25)
            papers = json.loads(output.read_text())["papers"]
            self.assertEqual([p["id"] for p in papers], [work["id"]])
            self.assertEqual(papers[0]["manual_evidence_url"], "https://example.org/proceedings")

    def test_manual_work_rejects_non_conference_type(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            venues, reviews, manual, output = (root / name for name in ("venues.json", "reviews.json", "manual.json", "snapshot.json"))
            venues.write_text(json.dumps([VENUE]))
            reviews.write_text("{}")
            manual.write_text(json.dumps([{"id": "https://openalex.org/W7", "venue_id": "osdi", "year": 2025,
                "evidence_url": "https://example.org/proceedings"}]))
            work = {"id": "https://openalex.org/W7", "title": "GPU inference", "publication_year": 2025,
                    "type": "article", "primary_location": {"source": {"id": VENUE["source_id"]}}}
            with patch.multiple(pipeline, VENUES=venues, REVIEWS=reviews, MANUAL=manual, OUTPUT=output), \
                 patch.object(pipeline, "fetch_works", return_value=([], 0, "2026-10-15T00:00:00+00:00", False)), \
                 patch.object(pipeline, "fetch_work_by_id", return_value=work):
                with self.assertRaises(RuntimeError):
                    pipeline.refresh(2025, 2025, 25)

    def test_openalex_response_cache_avoids_second_request(self):
        payload = {"meta": {"count": 12}, "results": [{"id": "https://openalex.org/W1"}]}
        with tempfile.TemporaryDirectory() as directory, patch.object(pipeline, "CACHE", Path(directory)), \
             patch.object(pipeline, "urlopen", return_value=io.BytesIO(json.dumps(payload).encode())) as request:
            first = pipeline.fetch_works(VENUE, 2025, 25, "")
            second = pipeline.fetch_works(VENUE, 2025, 25, "")
            self.assertEqual(first[1], 12)
            self.assertFalse(first[3])
            self.assertTrue(second[3])
            self.assertEqual(request.call_count, 1)

    def test_openalex_key_is_sent_in_header_not_url(self):
        payload = {"meta": {"count": 1}, "results": []}
        with tempfile.TemporaryDirectory() as directory, patch.object(pipeline, "CACHE", Path(directory)), \
             patch.object(pipeline, "urlopen", return_value=io.BytesIO(json.dumps(payload).encode())) as request:
            pipeline.fetch_works(VENUE, 2025, 25, "private-test-key")
            sent = request.call_args.args[0]
            self.assertNotIn("private-test-key", sent.full_url)
            self.assertEqual(sent.get_header("Authorization"), "Bearer private-test-key")

    def test_manual_openalex_lookup_keeps_key_out_of_url(self):
        with patch.object(pipeline, "urlopen", return_value=io.BytesIO(b'{}')) as request:
            pipeline.fetch_work_by_id("https://openalex.org/W7", "private-test-key")
            sent = request.call_args.args[0]
            self.assertNotIn("private-test-key", sent.full_url)
            self.assertEqual(sent.get_header("Authorization"), "Bearer private-test-key")

    def test_invalid_openalex_key_aborts_without_retries(self):
        denied = HTTPError("https://api.openalex.org/works", 403, "Forbidden", None, None)
        with tempfile.TemporaryDirectory() as directory, patch.object(pipeline, "CACHE", Path(directory)), \
             patch.object(pipeline, "urlopen", side_effect=denied) as request, \
             patch.object(pipeline.time, "sleep"):
            with self.assertRaisesRegex(RuntimeError, "authentication"):
                pipeline.fetch_works(VENUE, 2025, 25, "private-test-key")
            self.assertEqual(request.call_count, 1)

    def test_invalid_openalex_key_does_not_publish_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            venues, reviews, output = (root / name for name in ("venues.json", "reviews.json", "snapshot.json"))
            venues.write_text(json.dumps([VENUE]))
            reviews.write_text("{}")
            with patch.multiple(pipeline, VENUES=venues, REVIEWS=reviews, OUTPUT=output), \
                 patch.object(pipeline, "fetch_works", side_effect=pipeline.AuthenticationFailed("OpenAlex authentication failed")):
                with self.assertRaisesRegex(RuntimeError, "authentication"):
                    pipeline.refresh(2025, 2025, 25, official_cap=0, github_cap=0)
            self.assertFalse(output.exists())

    def test_review_survives_metadata_refresh(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            venues, reviews, output = (root / name for name in ("venues.json", "reviews.json", "snapshot.json"))
            venues.write_text(json.dumps([VENUE]))
            reviews.write_text(json.dumps({"https://openalex.org/W1": {"leadership": "Joint", "award": True,
                "reviewer": "Curator", "date": "2026-10-15", "evidence_url": "https://example.org/paper"}}))
            work = {"id": "https://openalex.org/W1", "title": "GPU inference for LLMs", "publication_year": 2025,
                "type": "conference-paper", "cited_by_count": 4}
            with patch.multiple(pipeline, VENUES=venues, REVIEWS=reviews, OUTPUT=output), \
                 patch.object(pipeline, "fetch_works", side_effect=lambda *_: ([work], 20, "2026-10-15T00:00:00+00:00", False)):
                pipeline.refresh(2025, 2025, 25)
                work["cited_by_count"] = 14
                pipeline.refresh(2025, 2025, 25)
            paper = json.loads(output.read_text())["papers"][0]
            self.assertEqual(paper["citations"], 14)
            self.assertEqual(paper["leadership"], "Joint")
            self.assertTrue(paper["award"])

    def test_successful_year_refresh_replaces_old_sample(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            venues, reviews, output = (root / name for name in ("venues.json", "reviews.json", "snapshot.json"))
            venues.write_text(json.dumps([VENUE]))
            reviews.write_text("{}")
            first = {"id": "https://openalex.org/W1", "title": "GPU inference", "type": "conference-paper", "publication_year": 2025}
            second = {"id": "https://openalex.org/W2", "title": "GPU training", "type": "conference-paper", "publication_year": 2025}
            batches = iter([([first], 30, "2026-10-15T00:00:00+00:00", False),
                            ([second], 30, "2026-10-15T01:00:00+00:00", False)])
            with patch.multiple(pipeline, VENUES=venues, REVIEWS=reviews, OUTPUT=output), \
                 patch.object(pipeline, "fetch_works", side_effect=lambda *_: next(batches)):
                pipeline.refresh(2025, 2025, 25)
                pipeline.refresh(2025, 2025, 25)
            self.assertEqual([p["id"] for p in json.loads(output.read_text())["papers"]], [second["id"]])


if __name__ == "__main__":
    unittest.main()
