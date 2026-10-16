"""Offline checks for bibliography-first AI selection and repository evidence."""
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ai_research_relevance import (classify_ai_work, link_openalex_metadata,
                                   scan_ai_bibliography, summarize_ai_scan)
from ai_research_sources import merge_official, normalize_official
import refresh_ai_research_observatory as pipeline


VENUE = {"id": "pldi", "name": "PLDI", "area": "Compilers", "rank": "A*",
         "ranking_scheme": "CORE", "edition": "2023", "rank_url": "https://example.org/rank",
         "source_id": "https://openalex.org/S1", "ai_native": False}


def row(title, doi=None, url="https://dblp.org/rec/conf/pldi/paper"):
    return {"title": title, "doi": doi, "url": url, "venue_id": "pldi", "event_year": 2025,
            "track_evidence": {"source": "DBLP", "issue": "PLDI"}}


class RelevanceTests(unittest.TestCase):
    def test_explicit_llm_inference_and_ml_compiler_titles_match(self):
        for title in ("Serving LLM Inference on GPUs", "An ML Compiler for Neural Networks",
                      "An AI Compiler for Sparse Models", "AI-Assisted Program Repair"):
            with self.subTest(title=title):
                decision, evidence = classify_ai_work(row(title), None, None)
                self.assertEqual(decision, "matched")
                self.assertTrue(evidence.startswith("ai-relevance-v1:"))

    def test_generic_gpu_and_compiler_titles_are_not_confirmed_ai(self):
        for title in ("GPU Scheduling in Datacenters", "Optimizing Compiler Passes"):
            with self.subTest(title=title):
                decision, _ = classify_ai_work(row(title), None, None)
                self.assertIn(decision, {"unresolved", "not-ai"})

    def test_metadata_can_resolve_ambiguous_title_only_when_explicit(self):
        paper = row("GPU Scheduling in Datacenters")
        self.assertEqual(classify_ai_work(paper, {"abstract": "We train large language models."}, None)[0], "matched")
        self.assertEqual(classify_ai_work(paper, {"abstract": "We optimize GPU inference for large language models."}, None)[0], "matched")
        self.assertEqual(classify_ai_work(paper, {"primary_topic": {"display_name": "Machine Learning"}}, None)[0], "matched")
        self.assertEqual(classify_ai_work(paper, {"abstract": "We schedule graphics workloads."}, None)[0], "unresolved")
        self.assertEqual(classify_ai_work(row("A faster filesystem"), None, None)[0], "not-ai")

    def test_incidental_or_negated_metadata_does_not_confirm_generic_gpu_title(self):
        paper = row("GPU Scheduling in Datacenters")
        cases = (
            {"keywords": [{"display_name": "Machine Learning"}]},
            {"topics": [{"display_name": "Machine Learning"}]},
            {"abstract": "Machine learning is outside scope; we schedule graphics jobs."},
            {"abstract": "We schedule GPU jobs, but do not train LLMs."},
            {"abstract": "We optimize GPU scheduling, while machine learning is mentioned as related work."},
            {"primary_topic": {"display_name": "Machine Learning"},
             "abstract": "Machine learning is outside scope; this is a graphics scheduler."},
            {"primary_topic": {"display_name": "Machine Learning"},
             "abstract": "ML is outside scope; this is a graphics scheduler."},
            {"abstract": "We train large language models. ML is outside scope for this system."},
        )
        for metadata in cases:
            with self.subTest(metadata=metadata):
                self.assertEqual(classify_ai_work(paper, metadata, None)[0], "unresolved")

    def test_reviewed_include_and_exclude_take_precedence_and_require_evidence(self):
        include = {"include": True, "review_note": "AI-assisted software engineering",
                   "evidence_url": "https://example.org/paper"}
        exclude = {"exclude": True, "review_note": "Not an AI paper",
                   "evidence_url": "https://example.org/paper"}
        self.assertEqual(classify_ai_work(row("A faster filesystem"), None, include),
                         ("matched", "ai-relevance-v1:review-include"))
        self.assertEqual(classify_ai_work(row("LLM inference"), None, exclude),
                         ("not-ai", "ai-relevance-v1:review-exclude"))
        with self.assertRaises(ValueError):
            classify_ai_work(row("A faster filesystem"), None, {**include, "evidence_url": "http://example.org"})
        with self.assertRaises(ValueError):
            pipeline.validate_review({**include, "exclude": True})

    def test_openalex_linking_uses_doi_then_unique_exact_title_and_never_changes_denominator(self):
        rows = [row("LLM Inference", "10.1145/ONE"),
                row("ML Compiler", url="https://dblp.org/rec/conf/pldi/two"),
                row("Unknown Paper", url="https://dblp.org/rec/conf/pldi/three")]
        works = [{"id": "https://openalex.org/W1", "doi": "https://doi.org/10.1145/one",
                  "title": "Different indexed title", "publication_year": 2026},
                 {"id": "https://openalex.org/W2", "title": "ML Compiler", "publication_year": 2025},
                 {"id": "https://openalex.org/W3", "title": "Unknown Paper", "doi": "https://doi.org/10.1/a",
                  "publication_year": 2025},
                 {"id": "https://openalex.org/W4", "title": "Unknown Paper", "doi": "https://doi.org/10.1/b",
                  "publication_year": 2025}]
        linked = link_openalex_metadata(rows, works)
        self.assertEqual([item["id"] if item else None for item in linked],
                         ["https://openalex.org/W1", "https://openalex.org/W2", None])
        self.assertEqual(len(rows), 3)

    def test_conflicting_doi_blocks_title_fallback(self):
        linked = link_openalex_metadata([row("ML Compiler", "10.1/right")],
                                         [{"id": "https://openalex.org/W2", "title": "ML Compiler",
                                           "doi": "https://doi.org/10.1/wrong", "publication_year": 2025}])
        self.assertEqual(linked, [None])

    def test_scan_counts_unclassified_rows_as_unknown_and_partial(self):
        rows = [row("LLM Inference"), row("GPU Scheduling"), row("Filesystem")]
        partial = summarize_ai_scan(rows, [("matched", "ai-relevance-v1:title-llm")])
        self.assertEqual(partial["ai_matched_count"], 1)
        self.assertEqual(partial["ai_reviewed_count"], 0)
        self.assertEqual(partial["ai_unresolved_count"], 2)
        self.assertEqual(partial["scanned_count"], 1)
        self.assertEqual(partial["eligible_count"], 3)
        self.assertEqual(partial["status"], "partial")
        unresolved = summarize_ai_scan(rows, [("matched", "ai-relevance-v1:review-include"),
                                              ("unresolved", "ai-relevance-v1:generic-systems"),
                                              ("not-ai", "ai-relevance-v1:no-evidence")])
        self.assertEqual(unresolved["ai_reviewed_count"], 1)
        self.assertEqual(unresolved["ai_unresolved_count"], 1)
        self.assertEqual(unresolved["status"], "partial")
        self.assertEqual(summarize_ai_scan([], [])["status"], "partial")
        complete = summarize_ai_scan(rows, [("matched", "ai-relevance-v1:review-include"),
                                            ("not-ai", "ai-relevance-v1:no-evidence"),
                                            ("not-ai", "ai-relevance-v1:no-evidence")])
        self.assertEqual(complete["status"], "complete")

    def test_scan_classifies_every_eligible_row_before_any_public_sample(self):
        rows = [row("GPU Scheduling"),
                row("LLM Inference", "10.1/llm", "https://dblp.org/rec/conf/pldi/two"),
                row("A faster filesystem", url="https://dblp.org/rec/conf/pldi/three")]
        works = [{"id": "https://openalex.org/W3", "title": "A faster filesystem",
                  "publication_year": 2025, "abstract": "A storage paper."}]
        reviews = {"https://doi.org/10.1/llm": {"exclude": True, "review_note": "Not AI",
                    "evidence_url": "https://example.org/llm"},
                   "https://openalex.org/W3": {"include": True, "review_note": "AI-assisted storage",
                    "evidence_url": "https://example.org/storage"}}
        decisions, summary = scan_ai_bibliography(rows, works, reviews)
        self.assertEqual([decision for decision, _ in decisions], ["unresolved", "not-ai", "matched"])
        self.assertEqual(summary["scanned_count"], 3)
        self.assertEqual(summary["ai_reviewed_count"], 2)
        self.assertEqual(summary["ai_matched_count"], 1)
        self.assertEqual(summary["status"], "partial")

    def test_bibliography_doi_review_survives_missing_openalex_metadata(self):
        rows = [row("GPU Scheduling", "10.1145/100", "https://dblp.org/rec/conf/pldi/one"),
                row("GPU Scheduling", "10.1145/101", "https://dblp.org/rec/conf/pldi/two")]
        reviews = {"https://openalex.org/W100": {"include": True,
            "bibliography_doi": "https://doi.org/10.1145/100", "review_note": "AI training scheduler",
            "evidence_url": "https://example.org/paper/100"}}
        decisions, summary = scan_ai_bibliography(rows, [], reviews)
        self.assertEqual(decisions[0], ("matched", "ai-relevance-v1:review-include"))
        self.assertEqual(decisions[1][0], "unresolved")
        self.assertEqual(summary["ai_reviewed_count"], 1)

    def test_bibliography_source_review_survives_missing_metadata_and_exclusion_wins(self):
        paper = row("GPU Scheduling", url="https://dblp.org/rec/conf/pldi/one")
        paper["source_urls"] = [paper["url"], "https://proceedings.example.org/pldi/one"]
        include = {"include": True, "bibliography_url": "https://proceedings.example.org/pldi/one",
                   "review_note": "AI system", "evidence_url": "https://example.org/include"}
        exclude = {"exclude": True, "review_note": "Not an AI study",
                   "evidence_url": "https://example.org/exclude"}
        decisions, _ = scan_ai_bibliography([paper], [], {"https://openalex.org/W100": include})
        self.assertEqual(decisions[0], ("matched", "ai-relevance-v1:review-include"))
        decisions, _ = scan_ai_bibliography([paper], [], {
            "https://openalex.org/W100": include, paper["url"]: exclude})
        self.assertEqual(decisions[0], ("not-ai", "ai-relevance-v1:review-exclude"))

    def test_review_aliases_need_explicit_publication_identifiers(self):
        review = {"include": True, "review_note": "AI system",
                  "evidence_url": "https://example.org/paper"}
        with self.assertRaises(ValueError):
            pipeline.validate_review({**review, "bibliography_url": "http://example.org/paper"})
        with self.assertRaises(ValueError):
            pipeline.validate_review({**review, "bibliography_doi": "GPU Scheduling"})


class RepositoryEvidenceTests(unittest.TestCase):
    def test_official_software_link_is_associated_but_access_unknown(self):
        paper_url = "https://proceedings.mlr.press/v267/a.html"
        official = normalize_official({"title": "LLM inference", "url": paper_url,
                                       "code_url": "https://github.com/org/repo"}, VENUE, 2025, "PMLR")
        self.assertEqual(official["repository_url"], "https://github.com/org/repo")
        self.assertEqual(official["repository_evidence_url"], paper_url)
        self.assertEqual(official["repository_association_status"], "paper-source")
        self.assertEqual(official["repository_access_status"], "unknown")
        merged = merge_official([{"id": "https://openalex.org/W1", "title": "LLM inference",
                                  "venue_id": "pldi", "year": 2025, "source": "OpenAlex"}], [official])
        self.assertEqual(merged[0]["repository_association_status"], "paper-source")

    def test_failed_repository_check_keeps_association_but_not_stale_metrics(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            venues, reviews, output = (root / name for name in ("venues.json", "reviews.json", "snapshot.json"))
            venue = {**VENUE, "id": "icml", "name": "ICML", "ai_native": True}
            paper_url = "https://proceedings.mlr.press/v267/a.html"
            repo_url = "https://github.com/org/repo"
            venues.write_text(json.dumps([venue]))
            reviews.write_text(json.dumps({paper_url: {"repository_url": repo_url,
                "repository_evidence_url": paper_url, "evidence_url": paper_url}}))
            prior = normalize_official({"title": "LLM inference", "url": paper_url,
                                        "code_url": None}, venue, 2025, "PMLR")
            prior["repository_url"] = repo_url
            prior["github"] = {"url": repo_url, "stars": 42, "pushed_at": "2026-01-01T00:00:00Z",
                               "checked_at": "2025-01-01T00:00:00Z"}
            output.write_text(json.dumps({"papers": [prior], "coverage": []}))
            raw = [{"title": "LLM inference", "url": paper_url, "code_url": None}]
            failure = HTTPError(repo_url, 404, "Not found", {}, io.BytesIO())
            with patch.multiple(pipeline, VENUES=venues, REVIEWS=reviews, OUTPUT=output), \
                 patch.object(pipeline, "fetch_official_index", return_value=(raw, "2026-10-15T00:00:00Z")), \
                 patch.object(pipeline, "fetch_github_metadata", side_effect=failure):
                pipeline.refresh(2025, 2025, 25, official_cap=1, github_cap=1, skip_openalex=True)
            paper = json.loads(output.read_text())["papers"][0]
            self.assertEqual(paper["repository_url"], repo_url)
            self.assertEqual(paper["repository_association_status"], "reviewed")
            self.assertEqual(paper["repository_access_status"], "unknown")
            self.assertIsNone(paper["github"])

    def test_failed_shared_repository_check_clears_stale_metrics_for_each_paper(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            venues, reviews, output = (root / name for name in ("venues.json", "reviews.json", "snapshot.json"))
            venue = {**VENUE, "id": "icml", "name": "ICML", "ai_native": True}
            repo_url = "https://github.com/org/shared"
            urls = [f"https://proceedings.mlr.press/v267/{name}.html" for name in ("a", "b")]
            venues.write_text(json.dumps([venue]))
            reviews.write_text(json.dumps({url: {"repository_url": repo_url,
                "repository_evidence_url": url, "evidence_url": url} for url in urls}))
            prior = [normalize_official({"title": f"LLM paper {index}", "url": url,
                "code_url": None}, venue, 2025, "PMLR") for index, url in enumerate(urls)]
            for paper in prior:
                paper["repository_url"] = repo_url
                paper["github"] = {"stars": 42, "checked_at": "2025-01-01T00:00:00Z"}
            output.write_text(json.dumps({"papers": prior, "coverage": []}))
            raw = [{"title": paper["title"], "url": paper["url"], "code_url": None} for paper in prior]
            failure = HTTPError(repo_url, 429, "Rate limited", {}, io.BytesIO())
            with patch.multiple(pipeline, VENUES=venues, REVIEWS=reviews, OUTPUT=output), \
                 patch.object(pipeline, "fetch_official_index", return_value=(raw, "2026-10-15T00:00:00Z")), \
                 patch.object(pipeline, "fetch_github_metadata", side_effect=failure) as fetch:
                pipeline.refresh(2025, 2025, 25, official_cap=2, github_cap=1, skip_openalex=True)
            self.assertEqual(fetch.call_count, 1)
            papers = json.loads(output.read_text())["papers"]
            self.assertEqual(len(papers), 2)
            self.assertTrue(all(paper["repository_access_status"] == "unknown" and
                                paper["github"] is None for paper in papers))


if __name__ == "__main__":
    unittest.main()
