"""Offline checks for the observatory's cautious metadata pipeline."""
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from contextlib import contextmanager

sys.path.insert(0, str(Path(__file__).resolve().parent))

import refresh_ai_research_observatory as pipeline
from refresh_ai_research_observatory import classify_sector, deduplicate, normalize_work, score_components
from scripts.ai_research_venues import build_catalog


VENUE = {"id": "osdi", "name": "OSDI", "area": "Systems", "ai_native": False,
         "rank": "A", "ranking_scheme": "CCF", "prestige": 1,
         "source_id": "https://openalex.org/S1", "edition": "2022", "rank_url": "https://www.ccf.org.cn/"}


class ObservatoryTests(unittest.TestCase):
    def test_ranked_ai_catalog_and_year_grid(self):
        venues = json.loads(pipeline.VENUES.read_text())
        by_id = {venue["id"]: venue for venue in venues}
        self.assertEqual(len(by_id), len(venues))
        self.assertEqual(venues, build_catalog())
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
        self.assertIn("osdi", by_id)
        self.assertTrue(by_id["osdi"]["source_rule_id"])
        self.assertTrue(by_id["sigir"]["ai_native"])
        self.assertTrue(by_id["kdd"]["ai_native"])
        self.assertFalse(by_id["www"]["ai_native"])

    def test_published_snapshot_covers_every_catalog_year_without_fake_counts(self):
        snapshot = json.loads(pipeline.OUTPUT.read_text())
        venues = {venue["id"] for venue in snapshot["venues"]}
        catalog = {venue["id"] for venue in json.loads(pipeline.VENUES.read_text())}
        self.assertTrue(venues < catalog)  # Staged publication is not the final backfill.
        self.assertIn("osdi", catalog)
        self.assertGreaterEqual(len(catalog), 76)
        self.assertEqual({(row["venue_id"], row["year"]) for row in snapshot["coverage"]},
                         {(venue, year) for venue in venues for year in range(2020, 2027)})
        self.assertEqual(len(snapshot["coverage"]), len(venues) * 7)
        self.assertTrue(all(paper["venue_id"] in venues for paper in snapshot["papers"]))
        self.assertTrue(all(row.get("source_total") is None for row in snapshot["coverage"] if row["status"] == "unmapped"))
        highlights = json.loads((pipeline.ROOT / "data/ai_research_observatory/arxiv_highlights.json").read_text())
        self.assertTrue(all(item["url"].startswith("https://arxiv.org/abs/") for item in highlights))
        self.assertTrue(all(item["url"] not in {paper["url"] for paper in snapshot["papers"]} for item in highlights))

    @contextmanager
    def cross_area_fixture(self, old=None, reviews=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            venues = root / "venues.json"
            venue = {**VENUE, "source_id": None, "source_rule_id": "osdi"}
            venues.write_text(json.dumps([venue]))
            rules = root / "rules.json"
            rules.write_text(json.dumps({"osdi": {"years": {"2025": {"status": "unresolved"}}}}))
            review_path = root / "reviews.json"
            review_path.write_text(json.dumps(reviews or {}))
            manual = root / "manual.json"
            manual.write_text("[]")
            output = root / "snapshot.json"
            if old:
                output.write_text(json.dumps(old))
            with patch.multiple(pipeline, VENUES=venues, REVIEWS=review_path, MANUAL=manual,
                                FEATURED=manual, CROSS_AREA_SOURCES=rules, OUTPUT=output, CACHE=root / "cache"):
                yield output

    @staticmethod
    def bibliography_row(title, suffix, doi=None):
        url = f"https://dblp.org/rec/conf/osdi/{suffix}"
        return {"title": title, "doi": doi, "url": url, "source_urls": [url],
                "venue_id": "osdi", "event_year": 2025,
                "track_evidence": {"source": "DBLP", "stream": "https://dblp.org/streams/conf/osdi"}}

    @staticmethod
    def bibliography_coverage(status="verified"):
        return {"venue_id": "osdi", "year": 2025, "main_track_total": 4 if status == "verified" else None,
                "bibliography_total": 4, "scanned_count": 4, "status": status,
                "track_scope": "OSDI main research papers", "source_urls": ["https://dblp.org/streams/conf/osdi"],
                "checked_at": "2026-10-16T00:00:00+00:00", "gap_reason": None if status == "verified" else "not reconciled"}

    def test_cross_area_scans_all_rows_before_sampling_and_ignores_abstract_claim(self):
        rows = [self.bibliography_row("GPU Scheduling in Datacenters", "one", "10.1145/1"),
                self.bibliography_row("A faster filesystem", "two"),
                self.bibliography_row("LLM Inference on GPUs", "three", "10.1145/3"),
                self.bibliography_row("AI-Assisted Program Repair", "four")]
        works = [{"id": "https://openalex.org/W1", "doi": "https://doi.org/10.1145/1",
                  "title": rows[0]["title"], "publication_year": 2025,
                  "abstract": "We use a GPU scheduler and previous studies apply large language models."}]
        old = {"papers": [{**works[0], "venue_id": "osdi", "year": 2025}], "coverage": []}
        with self.cross_area_fixture(old) as output, \
             patch.object(pipeline, "collect_venue_year", return_value=(rows, self.bibliography_coverage())):
            pipeline.refresh(2025, 2025, 1, official_cap=0, github_cap=0, skip_openalex=True)
            snapshot = json.loads(output.read_text())
        coverage = snapshot["coverage"][0]
        self.assertEqual(coverage["main_track_total"], 4)
        self.assertEqual(coverage["bibliography_total"], 4)
        self.assertEqual(coverage["ai_matched_count"], 2)
        self.assertEqual(coverage["ai_unresolved_count"], 1)
        self.assertEqual(coverage["ai_scan_status"], "partial")
        self.assertTrue(coverage["partial"])
        self.assertEqual(coverage["scanned_count"], 4)
        self.assertEqual(coverage["sampled_papers"], 1)
        self.assertEqual(len(snapshot["papers"]), 1)
        self.assertNotEqual(snapshot["papers"][0]["title"], rows[0]["title"])

    def test_cross_area_unresolved_count_stays_unknown(self):
        coverage = self.bibliography_coverage("unresolved")
        coverage.update(bibliography_total=None, scanned_count=0)
        with self.cross_area_fixture() as output, \
             patch.object(pipeline, "collect_venue_year", return_value=([], coverage)):
            pipeline.refresh(2025, 2025, 1, official_cap=0, github_cap=0, skip_openalex=True)
            row = json.loads(output.read_text())["coverage"][0]
        self.assertEqual(row["status"], "unresolved")
        self.assertIsNone(row["main_track_total"])
        self.assertIsNone(row["bibliography_total"])
        self.assertIsNone(row["ai_matched_count"])

    def test_cross_area_source_failures_retain_prior_papers_and_counts(self):
        old_paper = {"id": "https://dblp.org/rec/conf/osdi/old", "url": "https://dblp.org/rec/conf/osdi/old",
                     "title": "LLM inference", "year": 2025, "venue_id": "osdi", "source": "DBLP",
                     "checked_at": "2026-10-01T00:00:00+00:00", "citations": None}
        old_row = {**self.bibliography_coverage(), "ai_matched_count": 1, "sampled_papers": 1}
        old = {"papers": [old_paper], "coverage": [old_row]}
        for failure in (HTTPError("https://dblp.org", 429, "rate limited", None, None), TimeoutError("timeout")):
            with self.subTest(failure=type(failure).__name__), self.cross_area_fixture(old) as output, \
                 patch.object(pipeline, "collect_venue_year", side_effect=failure):
                pipeline.refresh(2025, 2025, 1, official_cap=0, github_cap=0, skip_openalex=True)
                snapshot = json.loads(output.read_text())
                self.assertEqual(snapshot["papers"][0]["id"], old_paper["id"])
                row = snapshot["coverage"][0]
                self.assertEqual(row["status"], "source-error")
                self.assertTrue(row["stale"])
                self.assertEqual(row["last_successful_checked_at"], old_row["checked_at"])
                self.assertEqual(row["ai_matched_count"], 1)

    def test_cross_area_returned_source_error_keeps_prior_counts(self):
        old_paper = {"id": "https://dblp.org/rec/conf/osdi/old", "url": "https://dblp.org/rec/conf/osdi/old",
                     "title": "LLM inference", "year": 2025, "venue_id": "osdi", "source": "DBLP"}
        old_row = {**self.bibliography_coverage(), "ai_matched_count": 1}
        error_row = {**self.bibliography_coverage("source-error"), "bibliography_total": None,
                     "gap_reason": "DBLP: HTTP 429"}
        with self.cross_area_fixture({"papers": [old_paper], "coverage": [old_row]}) as output, \
             patch.object(pipeline, "collect_venue_year", return_value=([], error_row)):
            pipeline.refresh(2025, 2025, 1, official_cap=0, github_cap=0, skip_openalex=True)
            snapshot = json.loads(output.read_text())
        self.assertEqual(snapshot["papers"][0]["id"], old_paper["id"])
        self.assertEqual(snapshot["coverage"][0]["bibliography_total"], 4)
        self.assertEqual(snapshot["coverage"][0]["status"], "source-error")

    def test_first_cross_area_source_error_keeps_provenance_without_fake_zero(self):
        error_row = {**self.bibliography_coverage("source-error"), "bibliography_total": None,
                     "gap_reason": "DBLP: timeout"}
        with self.cross_area_fixture() as output, \
             patch.object(pipeline, "collect_venue_year", return_value=([], error_row)):
            pipeline.refresh(2025, 2025, 1, official_cap=0, github_cap=0, skip_openalex=True)
            row = json.loads(output.read_text())["coverage"][0]
        self.assertEqual(row["source_urls"], error_row["source_urls"])
        self.assertEqual(row["track_scope"], error_row["track_scope"])
        self.assertIsNone(row["main_track_total"])
        self.assertIsNone(row["ai_matched_count"])

    def test_cross_area_not_held_removes_old_paper_without_zeroing_unknown_counts(self):
        old_paper = {"id": "https://dblp.org/rec/conf/osdi/old", "url": "https://dblp.org/rec/conf/osdi/old",
                     "title": "LLM inference", "year": 2025, "venue_id": "osdi", "source": "DBLP"}
        not_held = {**self.bibliography_coverage("not-held"), "bibliography_total": None,
                    "scanned_count": 0, "gap_reason": "No OSDI meeting in this year"}
        with self.cross_area_fixture({"papers": [old_paper], "coverage": [self.bibliography_coverage()]}) as output, \
             patch.object(pipeline, "collect_venue_year", return_value=([], not_held)):
            pipeline.refresh(2025, 2025, 1, official_cap=0, github_cap=0, skip_openalex=True)
            snapshot = json.loads(output.read_text())
        self.assertEqual(snapshot["papers"], [])
        self.assertEqual(snapshot["coverage"][0]["status"], "not-held")
        self.assertIsNone(snapshot["coverage"][0]["main_track_total"])
        self.assertIsNone(snapshot["coverage"][0]["ai_matched_count"])

    def test_cross_area_repeated_refresh_does_not_duplicate_papers(self):
        rows = [self.bibliography_row("LLM Inference", "one", "10.1145/1")]
        coverage = {**self.bibliography_coverage(), "main_track_total": 1, "bibliography_total": 1,
                    "scanned_count": 1}
        with self.cross_area_fixture() as output, \
             patch.object(pipeline, "collect_venue_year", return_value=(rows, coverage)):
            pipeline.refresh(2025, 2025, 1, official_cap=0, github_cap=0, skip_openalex=True)
            pipeline.refresh(2025, 2025, 1, official_cap=0, github_cap=0, skip_openalex=True)
            snapshot = json.loads(output.read_text())
        self.assertEqual(len(snapshot["papers"]), 1)
        self.assertEqual(snapshot["coverage"][0]["sampled_papers"], 1)

    def test_cross_area_matched_openalex_work_keeps_paper_specific_evidence(self):
        bibliography = self.bibliography_row("LLM Inference on GPUs", "one", "10.1145/1")
        work = {"id": "https://openalex.org/W1", "doi": "https://doi.org/10.1145/1",
                "title": bibliography["title"], "publication_year": 2025, "type": "conference-paper",
                "cited_by_count": 17, "authorships": [{"author_position": "first",
                    "author": {"display_name": "Ada"}, "institutions": [{"type": "education",
                    "display_name": "University", "country_code": "GB"}]}]}
        coverage = {**self.bibliography_coverage(), "main_track_total": 1,
                    "bibliography_total": 1, "scanned_count": 1}
        old = {"papers": [{**work, "venue_id": "osdi", "year": 2025}], "coverage": []}
        with self.cross_area_fixture(old) as output, \
             patch.object(pipeline, "collect_venue_year", return_value=([bibliography], coverage)):
            pipeline.refresh(2025, 2025, 1, official_cap=0, github_cap=0, skip_openalex=True)
            snapshot = json.loads(output.read_text())
        paper = snapshot["papers"][0]
        self.assertEqual(paper["id"], work["id"])
        self.assertEqual(paper["first_author_sector"], "University")
        self.assertEqual(paper["citations"], 17)
        self.assertEqual(paper["venue_id"], "osdi")
        self.assertEqual(paper["year"], 2025)
        self.assertIn(bibliography["url"], {source["url"] for source in paper["sources"]})
        self.assertIn("DBLP", snapshot["source"])

    def test_cross_area_uses_fresh_structured_topic_before_sampling(self):
        bibliography = self.bibliography_row("GPU Scheduling in Datacenters", "one", "10.1145/1")
        metadata = {"id": "https://openalex.org/W1", "doi": "https://doi.org/10.1145/1",
                    "title": bibliography["title"], "publication_year": 2025,
                    "type": "conference-paper", "cited_by_count": 7,
                    "authorships": [{"author_position": "first", "institutions": [
                        {"type": "education", "display_name": "University"}]}],
                    "primary_topic": {"display_name": "Machine Learning"},
                    "abstract": "We use a GPU scheduler and previous studies apply large language models."}
        coverage = {**self.bibliography_coverage(), "main_track_total": 1,
                    "bibliography_total": 1, "scanned_count": 1}
        with self.cross_area_fixture() as output, \
             patch.object(pipeline, "collect_venue_year", return_value=([bibliography], coverage)), \
             patch.object(pipeline, "fetch_openalex_doi_batch", return_value=[metadata]):
            pipeline.refresh(2025, 2025, 1, official_cap=0, github_cap=0)
            snapshot = json.loads(output.read_text())
        self.assertEqual(snapshot["coverage"][0]["ai_matched_count"], 1)
        self.assertEqual(snapshot["coverage"][0]["scanned_count"], 1)
        self.assertEqual(snapshot["papers"][0]["topic_rule"], "ai-relevance-v1:metadata-primary-topic")
        self.assertEqual(snapshot["papers"][0]["first_author_sector"], "University")
        self.assertEqual(snapshot["papers"][0]["citations"], 7)

    def test_cross_area_metadata_429_keeps_prior_ai_counts_and_paper(self):
        bibliography = self.bibliography_row("GPU Scheduling in Datacenters", "one", "10.1145/1")
        old_paper = {"id": "https://dblp.org/rec/conf/osdi/old", "url": "https://dblp.org/rec/conf/osdi/old",
                     "title": "LLM inference", "year": 2025, "venue_id": "osdi", "source": "DBLP",
                     "checked_at": "2026-10-01T00:00:00+00:00", "citations": None}
        old_row = {**self.bibliography_coverage(), "ai_matched_count": 1, "sampled_papers": 1}
        old = {"papers": [old_paper], "coverage": [old_row]}
        with self.cross_area_fixture(old) as output, \
             patch.object(pipeline, "collect_venue_year", return_value=([bibliography], self.bibliography_coverage())), \
             patch.object(pipeline, "fetch_openalex_doi_batch", side_effect=pipeline.RateLimited("HTTP 429")):
            pipeline.refresh(2025, 2025, 1, official_cap=0, github_cap=0)
            snapshot = json.loads(output.read_text())
        self.assertEqual(snapshot["papers"][0]["id"], old_paper["id"])
        self.assertEqual(snapshot["coverage"][0]["ai_matched_count"], 1)
        self.assertEqual(snapshot["coverage"][0]["ai_scan_status"], "source-error")
        self.assertTrue(snapshot["coverage"][0]["stale"])

    def test_truncated_bibliography_does_not_replace_prior_ai_sample(self):
        old_paper = {"id": "https://dblp.org/rec/conf/osdi/old", "url": "https://dblp.org/rec/conf/osdi/old",
                     "title": "LLM inference", "year": 2025, "venue_id": "osdi", "source": "DBLP"}
        old_row = {**self.bibliography_coverage(), "ai_matched_count": 1, "sampled_papers": 1}
        partial = {**self.bibliography_coverage("partial"), "bibliography_total": None,
                   "scanned_count": 1, "gap_reason": "DBLP query exceeded row limit"}
        bibliography = self.bibliography_row("AI-Assisted Program Repair", "new")
        with self.cross_area_fixture({"papers": [old_paper], "coverage": [old_row]}) as output, \
             patch.object(pipeline, "collect_venue_year", return_value=([bibliography], partial)):
            pipeline.refresh(2025, 2025, 1, official_cap=0, github_cap=0, skip_openalex=True)
            snapshot = json.loads(output.read_text())
        self.assertEqual([paper["id"] for paper in snapshot["papers"]], [old_paper["id"]])
        self.assertEqual(snapshot["coverage"][0]["ai_matched_count"], 1)
        self.assertEqual(snapshot["coverage"][0]["ai_scan_status"], "partial")
        self.assertTrue(snapshot["coverage"][0]["stale"])

    def test_openalex_doi_batch_cache_and_secret_header(self):
        metadata = {"results": [{"id": "https://openalex.org/W1", "doi": "https://doi.org/10.1145/1"}],
                    "meta": {"count": 1}}
        with tempfile.TemporaryDirectory() as directory, patch.object(pipeline, "CACHE", Path(directory)), \
             patch.object(pipeline, "urlopen", return_value=io.BytesIO(json.dumps(metadata).encode())) as request:
            first = pipeline.fetch_openalex_doi_batch(["10.1145/1"], "private-test-key")
            second = pipeline.fetch_openalex_doi_batch(["10.1145/1"], "private-test-key")
            self.assertEqual(first, metadata["results"])
            self.assertEqual(second, first)
            self.assertEqual(request.call_count, 1)
            sent = request.call_args.args[0]
            self.assertIn("doi%3A10.1145%2F1", sent.full_url)
            self.assertNotIn("private-test-key", sent.full_url)
            self.assertEqual(sent.get_header("Authorization"), "Bearer private-test-key")

    def test_legacy_openalex_outage_keeps_last_known_count_and_paper(self):
        paper = {"id": "https://openalex.org/W5", "title": "LLM Inference", "year": 2025,
                 "venue_id": "osdi", "source": "OpenAlex", "citations": 3}
        old_row = {"venue_id": "osdi", "year": 2025, "source_total": 19,
                   "checked_at": "2026-10-01T00:00:00+00:00", "status": "sample"}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            venues, reviews, output = (root / name for name in ("venues.json", "reviews.json", "snapshot.json"))
            venues.write_text(json.dumps([VENUE])); reviews.write_text("{}")
            for error in (pipeline.RateLimited("HTTP 429"), TimeoutError("timeout")):
                with self.subTest(error=type(error).__name__):
                    output.write_text(json.dumps({"papers": [paper], "coverage": [old_row]}))
                    with patch.multiple(pipeline, VENUES=venues, REVIEWS=reviews, OUTPUT=output), \
                         patch.object(pipeline, "fetch_works", side_effect=error):
                        pipeline.refresh(2025, 2025, 1, official_cap=0, github_cap=0)
                    snapshot = json.loads(output.read_text())
                    self.assertEqual(snapshot["papers"][0]["id"], paper["id"])
                    coverage = snapshot["coverage"][0]
                    self.assertEqual(coverage["source_total"], 19)
                    self.assertTrue(coverage["stale"])
                    self.assertEqual(coverage["last_successful_checked_at"], old_row["checked_at"])
                    self.assertGreater(coverage["checked_at"], old_row["checked_at"])

    def test_cli_scoped_output_isolated_from_committed_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "snapshot.json"
            committed = pipeline.OUTPUT.read_bytes()
            command = ["python3", str(pipeline.ROOT / "scripts/refresh_ai_research_observatory.py"),
                       "--from-year", "2025", "--to-year", "2025", "--venues", "not-a-venue",
                       "--output", str(output), "--cache-dir", str(root / "cache"),
                       "--skip-openalex", "--official-cap", "0", "--github-cap", "0"]
            subprocess.run(command, check=True, cwd=pipeline.ROOT, capture_output=True, text=True)
            self.assertEqual(json.loads(output.read_text())["coverage"], [])
            self.assertEqual(pipeline.OUTPUT.read_bytes(), committed)

    def test_github_404_keeps_paper_but_clears_live_metrics(self):
        repo = "https://github.com/org/repo"
        paper_url = "https://proceedings.mlr.press/v267/paper.html"
        venue = {**VENUE, "id": "icml", "name": "ICML", "ai_native": True}
        old_paper = {"id": paper_url, "title": "LLM Inference", "year": 2025, "venue_id": "icml",
                     "source": "PMLR", "url": paper_url, "repository_url": repo,
                     "github": {"stars": 42, "pushed_at": "2026-01-01T00:00:00Z",
                                "checked_at": "2026-01-01T00:00:00+00:00"}}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            venues, reviews, output = (root / name for name in ("venues.json", "reviews.json", "snapshot.json"))
            venues.write_text(json.dumps([venue])); reviews.write_text("{}")
            output.write_text(json.dumps({"papers": [old_paper], "coverage": []}))
            with patch.multiple(pipeline, VENUES=venues, REVIEWS=reviews, OUTPUT=output), \
                 patch.object(pipeline, "fetch_official_index", side_effect=TimeoutError("timeout")), \
                 patch.object(pipeline, "fetch_github_metadata", side_effect=HTTPError(repo, 404, "Not found", None, None)):
                pipeline.refresh(2025, 2025, 1, official_cap=1, github_cap=1, skip_openalex=True)
            paper = json.loads(output.read_text())["papers"][0]
        self.assertEqual(paper["repository_access_status"], "unknown")
        self.assertIsNone(paper["github"])
        self.assertEqual(paper["id"], paper_url)
        self.assertTrue(paper["repository_checked_at"])

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

    def test_article_in_verified_conference_source_is_eligible(self):
        work = {"id": "https://openalex.org/W3", "title": "GPU inference for language models",
                "publication_year": 2025, "type": "article"}
        self.assertIsNotNone(normalize_work(work, VENUE))
        self.assertIsNone(normalize_work({**work, "type": "preprint"}, VENUE))

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

    def test_manual_article_with_verified_conference_source_is_retained(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            venues, reviews, manual, output = (root / name for name in ("venues.json", "reviews.json", "manual.json", "snapshot.json"))
            venues.write_text(json.dumps([VENUE]))
            reviews.write_text("{}")
            manual.write_text(json.dumps([{"id": "https://openalex.org/W7", "venue_id": "osdi", "year": 2025,
                "evidence_url": "https://example.org/proceedings"}]))
            work = {"id": "https://openalex.org/W7", "title": "GPU inference for LLMs", "publication_year": 2025,
                    "type": "article", "primary_location": {"source": {"id": VENUE["source_id"]}}}
            with patch.multiple(pipeline, VENUES=venues, REVIEWS=reviews, MANUAL=manual, OUTPUT=output), \
                 patch.object(pipeline, "fetch_works", return_value=([], 0, "2026-10-15T00:00:00+00:00", False)), \
                 patch.object(pipeline, "fetch_work_by_id", return_value=work):
                pipeline.refresh(2025, 2025, 25, official_cap=0, github_cap=0)
            self.assertEqual([p["id"] for p in json.loads(output.read_text())["papers"]], [work["id"]])

    def test_manual_work_rejects_non_conference_type(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            venues, reviews, manual, output = (root / name for name in ("venues.json", "reviews.json", "manual.json", "snapshot.json"))
            venues.write_text(json.dumps([VENUE]))
            reviews.write_text("{}")
            manual.write_text(json.dumps([{"id": "https://openalex.org/W7", "venue_id": "osdi", "year": 2025,
                "evidence_url": "https://example.org/proceedings"}]))
            work = {"id": "https://openalex.org/W7", "title": "GPU inference", "publication_year": 2025,
                    "type": "preprint", "primary_location": {"source": {"id": VENUE["source_id"]}}}
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

    def test_openalex_query_does_not_exclude_article_typed_conference_works(self):
        payload = {"meta": {"count": 1}, "results": []}
        with tempfile.TemporaryDirectory() as directory, patch.object(pipeline, "CACHE", Path(directory)), \
             patch.object(pipeline, "urlopen", return_value=io.BytesIO(json.dumps(payload).encode())) as request:
            pipeline.fetch_works(VENUE, 2025, 25, "")
            self.assertNotIn("type%3Aconference-paper", request.call_args.args[0].full_url)

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
