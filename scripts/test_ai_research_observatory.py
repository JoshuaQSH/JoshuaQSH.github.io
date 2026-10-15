"""Offline checks for the observatory's cautious metadata pipeline."""
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import refresh_ai_research_observatory as pipeline
from refresh_ai_research_observatory import classify_sector, deduplicate, normalize_work, score_components


VENUE = {"id": "osdi", "name": "OSDI", "area": "Systems", "ai_native": False,
         "rank": "A", "ranking_scheme": "CCF", "prestige": 1,
         "source_id": "https://openalex.org/S1", "edition": "2022", "rank_url": "https://www.ccf.org.cn/"}


class ObservatoryTests(unittest.TestCase):
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
