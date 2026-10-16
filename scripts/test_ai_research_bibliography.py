"""Offline source-boundary tests for cross-area bibliographies."""
import io
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.ai_research_bibliography import collect_venue_year


def sparql_row(**values):
    return {key: {"type": "uri" if key in {"pub", "doi", "toc"} else "literal", "value": value}
            for key, value in values.items()}


def sparql_result(*rows):
    return io.BytesIO(json.dumps({"head": {"vars": ["pub", "title", "eventYear", "publicationYear",
                                                   "issue", "book", "toc", "doi", "type"]},
                              "results": {"bindings": rows}}).encode())


def rule(stream, family, edition, **extra):
    return {"dblp_stream": stream, "source_family": family, "excluded_material":
            ["workshops", "companion", "artifact", "editorial"], "years": {"2025": {
                "status": "unresolved", "track_scope": "main research papers",
                "official_url": None, **edition}}, **extra}


class BibliographyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cache = Path(self.temp.name)

    def test_journal_issue_selectors_exclude_other_issues_and_editorials(self):
        stream = "https://dblp.org/streams/journals/pacmpl"
        source = rule(stream, "acm-journal-issue", {"dblp_issues": ["POPL"],
                                                       "dblp_issue_field": "publishedInJournalVolumeIssue"})
        rows = sparql_result(
            sparql_row(pub="https://dblp.org/rec/journals/pacmpl/One25", title="Typed Effects",
                       publicationYear="2025", issue="POPL", type="http://purl.org/net/nknouf/ns/bibtex#Article",
                       doi="https://doi.org/10.1145/123"),
            sparql_row(pub="https://dblp.org/rec/journals/pacmpl/Two25", title="Other issue",
                       publicationYear="2025", issue="OOPSLA1", type="http://purl.org/net/nknouf/ns/bibtex#Article"),
            sparql_row(pub="https://dblp.org/rec/journals/pacmpl/Three25", title="Editorial",
                       publicationYear="2025", issue="POPL", type="http://purl.org/net/nknouf/ns/bibtex#Article"))
        with patch("scripts.ai_research_bibliography.urlopen", return_value=rows) as fetch:
            papers, coverage = collect_venue_year({"id": "popl"}, 2025, source, self.cache)
        self.assertEqual([paper["title"] for paper in papers], ["Typed Effects"])
        self.assertEqual(papers[0]["doi"], "10.1145/123")
        self.assertEqual(papers[0]["event_year"], 2025)
        self.assertEqual(papers[0]["track_evidence"]["issue"], "POPL")
        self.assertIsNone(coverage["main_track_total"])
        self.assertEqual(coverage["bibliography_total"], 1)
        self.assertEqual(coverage["scanned_count"], 1)
        self.assertEqual(coverage["status"], "partial")
        query = fetch.call_args.args[0].data.decode()
        self.assertIn(stream, query)
        self.assertIn('"POPL"', query)
        self.assertNotIn("OOPSLA1", query)
        self.assertIn("LIMIT 1001", query)

    def test_pacmse_fse_issue_does_not_count_issta_or_companion(self):
        source = rule("https://dblp.org/streams/journals/pacmse", "acm-journal-issue",
                      {"dblp_issues": ["FSE"], "dblp_issue_field": "publishedInJournalVolumeIssue"})
        rows = sparql_result(
            sparql_row(pub="https://dblp.org/rec/journals/pacmse/One25", title="Repairing Programs",
                       publicationYear="2025", issue="FSE", type="http://purl.org/net/nknouf/ns/bibtex#Article"),
            sparql_row(pub="https://dblp.org/rec/journals/pacmse/Two25", title="Testing Systems",
                       publicationYear="2025", issue="ISSTA", type="http://purl.org/net/nknouf/ns/bibtex#Article"),
            sparql_row(pub="https://dblp.org/rec/journals/pacmse/Three25", title="Companion paper",
                       publicationYear="2025", issue="FSE Companion", type="http://purl.org/net/nknouf/ns/bibtex#Article"))
        with patch("scripts.ai_research_bibliography.urlopen", return_value=rows):
            papers, coverage = collect_venue_year({"id": "fse"}, 2025, source, self.cache)
        self.assertEqual([paper["title"] for paper in papers], ["Repairing Programs"])
        self.assertEqual(coverage["bibliography_total"], 1)
        self.assertIsNone(coverage["main_track_total"])

    def test_pldi_transition_uses_only_pacmpl_pldi_issue_from_2023(self):
        manifest = json.loads((Path(__file__).resolve().parents[1] /
                               "data/ai_research_observatory/cross_area_sources.json").read_text())
        source = manifest["pldi"]
        self.assertEqual(source["years"]["2022"].get("dblp_stream", source["dblp_stream"]),
                         "https://dblp.org/streams/conf/pldi")
        for year in range(2023, 2027):
            with self.subTest(year=year):
                edition = source["years"][str(year)]
                self.assertEqual(edition["dblp_stream"], "https://dblp.org/streams/journals/pacmpl")
                self.assertEqual(edition["dblp_issues"], ["PLDI"])
        rows = sparql_result(sparql_row(pub="https://dblp.org/rec/journals/pacmpl/A25",
                                       title="Compiler Optimization", publicationYear="2025", issue="PLDI",
                                       type="http://purl.org/net/nknouf/ns/bibtex#Article"))
        with patch("scripts.ai_research_bibliography.urlopen", return_value=rows):
            papers, coverage = collect_venue_year({"id": "pldi"}, 2025, source, self.cache)
        self.assertEqual([paper["title"] for paper in papers], ["Compiler Optimization"])
        self.assertEqual(coverage["bibliography_total"], 1)

    def test_hpca_uses_the_international_conference_stream(self):
        manifest = json.loads((Path(__file__).resolve().parents[1] /
                               "data/ai_research_observatory/cross_area_sources.json").read_text())
        source = manifest["hpca"]
        self.assertEqual(source["dblp_stream"], "https://dblp.org/streams/conf/hpca")
        for edition in source["years"].values():
            self.assertIn("https://dblp.org/streams/conf/hpca", edition["provenance_urls"])
            self.assertNotIn("https://dblp.org/streams/conf/cnhpca", edition["provenance_urls"])

    def test_saner_series_stream_handles_old_record_keys_and_companion(self):
        manifest = json.loads((Path(__file__).resolve().parents[1] /
                               "data/ai_research_observatory/cross_area_sources.json").read_text())
        source = manifest["saner"]
        self.assertEqual(source["dblp_stream"], "https://dblp.org/streams/conf/saner")
        for edition in source["years"].values():
            self.assertIn("https://dblp.org/streams/conf/saner", edition["provenance_urls"])
        old = sparql_result(sparql_row(pub="https://dblp.org/rec/conf/wcre/A24", title="Old-key paper",
                                    eventYear="2024", publicationYear="2024", book="SANER",
                                    toc="https://dblp.org/db/conf/wcre/saner2024",
                                    type="http://purl.org/net/nknouf/ns/bibtex#Inproceedings"))
        with patch("scripts.ai_research_bibliography.urlopen", return_value=old) as fetch:
            old_papers, _ = collect_venue_year({"id": "saner"}, 2024, source, self.cache)
        self.assertEqual([paper["title"] for paper in old_papers], ["Old-key paper"])
        self.assertIn("https://dblp.org/streams/conf/saner", fetch.call_args.args[0].data.decode())
        rows = sparql_result(
            sparql_row(pub="https://dblp.org/rec/conf/saner/A25", title="Main paper",
                       eventYear="2025", publicationYear="2025", book="SANER",
                       toc="https://dblp.org/db/conf/saner/saner2025",
                       type="http://purl.org/net/nknouf/ns/bibtex#Inproceedings"),
            sparql_row(pub="https://dblp.org/rec/conf/saner/B25", title="Companion paper",
                       eventYear="2025", publicationYear="2025", book="SANER-C",
                       toc="https://dblp.org/db/conf/saner/saner2025c",
                       type="http://purl.org/net/nknouf/ns/bibtex#Inproceedings"))
        with patch("scripts.ai_research_bibliography.urlopen", return_value=rows):
            papers, coverage = collect_venue_year({"id": "saner"}, 2025, source, self.cache)
        self.assertEqual([paper["title"] for paper in papers], ["Main paper"])
        self.assertEqual(coverage["bibliography_total"], 1)
        self.assertNotIn("https://dblp.org/streams/conf/wcre", coverage["source_urls"])

    def test_proceedings_use_event_year_and_drop_workshop_containers(self):
        stream = "https://dblp.org/streams/conf/osdi"
        source = rule(stream, "usenix-proceedings", {})
        rows = sparql_result(
            sparql_row(pub="https://dblp.org/rec/conf/osdi/Main25", title="A Main Paper",
                       eventYear="2025", publicationYear="2026", book="OSDI",
                       toc="https://dblp.org/db/conf/osdi/osdi2025",
                       type="http://purl.org/net/nknouf/ns/bibtex#Inproceedings"),
            sparql_row(pub="https://dblp.org/rec/conf/osdi/Workshop25", title="A Workshop Paper",
                       eventYear="2025", publicationYear="2025", book="OSDI 2025 Workshops",
                       toc="https://dblp.org/db/conf/osdi/osdi2025w",
                       type="http://purl.org/net/nknouf/ns/bibtex#Inproceedings"),
            sparql_row(pub="https://dblp.org/rec/conf/osdi/Old25", title="Wrong event",
                       eventYear="2024", publicationYear="2025", book="OSDI",
                       type="http://purl.org/net/nknouf/ns/bibtex#Inproceedings"))
        with patch("scripts.ai_research_bibliography.urlopen", return_value=rows):
            papers, coverage = collect_venue_year({"id": "osdi"}, 2025, source, self.cache)
        self.assertEqual([paper["title"] for paper in papers], ["A Main Paper"])
        self.assertEqual(papers[0]["event_year"], 2025)
        self.assertEqual(coverage["bibliography_total"], 1)
        self.assertIsNone(coverage["main_track_total"])

    def test_workshop_toc_suffix_is_excluded_even_when_book_label_is_generic(self):
        source = rule("https://dblp.org/streams/conf/icpp", "acm-proceedings", {})
        rows = sparql_result(sparql_row(pub="https://dblp.org/rec/conf/icpp/W25", title="Workshop Work",
                                       eventYear="2025", publicationYear="2025", book="ICPP",
                                       toc="https://dblp.org/db/conf/icpp/icpp2025w",
                                       type="http://purl.org/net/nknouf/ns/bibtex#Inproceedings"))
        with patch("scripts.ai_research_bibliography.urlopen", return_value=rows):
            papers, coverage = collect_venue_year({"id": "icpp"}, 2025, source, self.cache)
        self.assertEqual(papers, [])
        self.assertIsNone(coverage["bibliography_total"])

    def test_root_industrial_proceedings_exclusion_uses_book_and_toc(self):
        source = rule("https://dblp.org/streams/conf/middleware", "acm-proceedings", {},
                      excluded_material=["industrial-track proceedings"])
        source["years"]["2024"] = source["years"].pop("2025")
        rows = sparql_result(
            sparql_row(pub="https://dblp.org/rec/conf/middleware/Main24", title="Main systems paper",
                       eventYear="2024", publicationYear="2024", book="Middleware",
                       toc="https://dblp.org/db/conf/middleware/middleware2024",
                       type="http://purl.org/net/nknouf/ns/bibtex#Inproceedings"),
            sparql_row(pub="https://dblp.org/rec/conf/middleware/Industry24", title="Industry systems paper",
                       eventYear="2024", publicationYear="2024", book="Middleware Industry",
                       toc="https://dblp.org/db/conf/middleware/middleware2024i",
                       type="http://purl.org/net/nknouf/ns/bibtex#Inproceedings"),
            sparql_row(pub="https://dblp.org/rec/conf/middleware/IndustryNoBook24", title="Industry TOC paper",
                       eventYear="2024", publicationYear="2024",
                       toc="https://dblp.org/db/conf/middleware/middleware2024i",
                       type="http://purl.org/net/nknouf/ns/bibtex#Inproceedings"))
        with patch("scripts.ai_research_bibliography.urlopen", return_value=rows):
            papers, coverage = collect_venue_year({"id": "middleware"}, 2024, source, self.cache)
        self.assertEqual([paper["title"] for paper in papers], ["Main systems paper"])
        self.assertEqual(coverage["bibliography_total"], 1)

    def test_edition_exclusions_apply_to_labelled_containers(self):
        source = rule("https://dblp.org/streams/conf/cloud", "acm-proceedings",
                      {"excluded_material": ["Industry Papers", "Short Research Papers", "Vision Papers"]})
        rows = sparql_result(
            sparql_row(pub="https://dblp.org/rec/conf/cloud/Main25", title="A full paper",
                       eventYear="2025", publicationYear="2025", book="SoCC Full Research Papers",
                       type="http://purl.org/net/nknouf/ns/bibtex#Inproceedings"),
            sparql_row(pub="https://dblp.org/rec/conf/cloud/Industry25", title="An industry paper",
                       eventYear="2025", publicationYear="2025", book="SoCC Industry Papers",
                       type="http://purl.org/net/nknouf/ns/bibtex#Inproceedings"),
            sparql_row(pub="https://dblp.org/rec/conf/cloud/Short25", title="A short paper",
                       eventYear="2025", publicationYear="2025", book="SoCC Short Research Papers",
                       type="http://purl.org/net/nknouf/ns/bibtex#Inproceedings"),
            sparql_row(pub="https://dblp.org/rec/conf/cloud/Vision25", title="A vision paper",
                       eventYear="2025", publicationYear="2025", book="SoCC Vision Papers",
                       type="http://purl.org/net/nknouf/ns/bibtex#Inproceedings"))
        with patch("scripts.ai_research_bibliography.urlopen", return_value=rows):
            papers, coverage = collect_venue_year({"id": "socc"}, 2025, source, self.cache)
        self.assertEqual([paper["title"] for paper in papers], ["A full paper"])
        self.assertEqual(coverage["bibliography_total"], 1)

    def test_configured_main_volume_excludes_side_tracks(self):
        source = rule("https://dblp.org/streams/conf/icse", "acm-proceedings", {},
                      dblp_book_labels=["ICSE"])
        rows = sparql_result(
            sparql_row(pub="https://dblp.org/rec/conf/icse/Main25", title="Main research",
                       eventYear="2025", publicationYear="2025", book="ICSE",
                       toc="https://dblp.org/db/conf/icse/icse2025",
                       type="http://purl.org/net/nknouf/ns/bibtex#Inproceedings"),
            sparql_row(pub="https://dblp.org/rec/conf/icse/NIER25", title="New ideas",
                       eventYear="2025", publicationYear="2025", book="ICSE (NIER)",
                       toc="https://dblp.org/db/conf/icse/nier2025",
                       type="http://purl.org/net/nknouf/ns/bibtex#Inproceedings"),
            sparql_row(pub="https://dblp.org/rec/conf/icse/SEIS25", title="Industry study",
                       eventYear="2025", publicationYear="2025", book="ICSE-SEIS",
                       toc="https://dblp.org/db/conf/icse/seis2025",
                       type="http://purl.org/net/nknouf/ns/bibtex#Inproceedings"))
        with patch("scripts.ai_research_bibliography.urlopen", return_value=rows):
            papers, coverage = collect_venue_year({"id": "icse"}, 2025, source, self.cache)
        self.assertEqual([paper["title"] for paper in papers], ["Main research"])
        self.assertEqual(coverage["bibliography_total"], 1)

    def test_configured_record_prefix_excludes_different_conference_on_shared_stream(self):
        source = rule("https://dblp.org/streams/conf/cloud", "acm-proceedings", {},
                      dblp_book_labels=["SoCC"],
                      dblp_record_prefix="https://dblp.org/rec/conf/cloud/")
        rows = sparql_result(
            sparql_row(pub="https://dblp.org/rec/conf/cloud/Main25", title="Cloud systems",
                       eventYear="2025", publicationYear="2025", book="SoCC",
                       toc="https://dblp.org/db/conf/cloud/socc2025",
                       type="http://purl.org/net/nknouf/ns/bibtex#Inproceedings"),
            sparql_row(pub="https://dblp.org/rec/conf/IEEEcloud/Wrong25", title="Other CLOUD",
                       eventYear="2025", publicationYear="2025", book="CLOUD",
                       toc="https://dblp.org/db/conf/IEEEcloud/cloud2025",
                       type="http://purl.org/net/nknouf/ns/bibtex#Inproceedings"))
        with patch("scripts.ai_research_bibliography.urlopen", return_value=rows):
            papers, coverage = collect_venue_year({"id": "socc"}, 2025, source, self.cache)
        self.assertEqual([paper["title"] for paper in papers], ["Cloud systems"])
        self.assertEqual(coverage["bibliography_total"], 1)

    def test_manifest_names_only_audited_main_volumes_and_socc_gaps(self):
        manifest = json.loads((Path(__file__).resolve().parents[1] /
                               "data/ai_research_observatory/cross_area_sources.json").read_text())
        for venue, labels in (("icse", ["ICSE"]), ("fse", ["ESEC/SIGSOFT FSE"]),
                              ("sc", ["SC"]), ("middleware", ["Middleware"])):
            self.assertEqual(manifest[venue]["dblp_book_labels"], labels)
        self.assertEqual(manifest["socc"]["dblp_record_prefix"],
                         "https://dblp.org/rec/conf/cloud/")
        for year in range(2020, 2027):
            with self.subTest(year=year):
                self.assertIn("track", manifest["socc"]["years"][str(year)]["match_rule"].lower())

    def test_future_2026_editions_are_not_published_counts(self):
        manifest = json.loads((Path(__file__).resolve().parents[1] /
                               "data/ai_research_observatory/cross_area_sources.json").read_text())
        for venue in ("pact", "micro", "sc", "socc", "middleware", "usenix-atc"):
            with self.subTest(venue=venue):
                edition = manifest[venue]["years"]["2026"]
                self.assertEqual(edition["status"], "not-yet-published")
                self.assertTrue(any(url.startswith("https://") and "dblp.org" not in url
                                    for url in edition["provenance_urls"]))

    def test_socc_generic_mixed_track_is_unresolved_not_eligible(self):
        manifest = json.loads((Path(__file__).resolve().parents[1] /
                               "data/ai_research_observatory/cross_area_sources.json").read_text())
        source = manifest["socc"]
        generic = sparql_result(sparql_row(pub="https://dblp.org/rec/conf/cloud/Unknown25",
                                           title="Unlabelled category", eventYear="2025",
                                           publicationYear="2025", book="SoCC",
                                           toc="https://dblp.org/db/conf/cloud/socc2025",
                                           type="http://purl.org/net/nknouf/ns/bibtex#Inproceedings"))
        with patch("scripts.ai_research_bibliography.urlopen", return_value=generic) as fetch:
            papers, coverage = collect_venue_year({"id": "socc"}, 2025, source, self.cache)
        fetch.assert_not_called()
        self.assertEqual(papers, [])
        self.assertEqual(coverage["status"], "unresolved")
        self.assertIsNone(coverage["main_track_total"])
        self.assertIsNone(coverage["bibliography_total"])
        self.assertIn("mixed", coverage["gap_reason"].lower())

    def test_doi_precedes_normalized_title_and_retains_source_links(self):
        source = rule("https://dblp.org/streams/conf/osdi", "usenix-proceedings", {})
        rows = sparql_result(
            sparql_row(pub="https://dblp.org/rec/conf/osdi/A25", title="A: New System",
                       eventYear="2025", publicationYear="2025", book="OSDI",
                       doi="https://doi.org/10.1145/ABC", type="http://purl.org/net/nknouf/ns/bibtex#Inproceedings"),
            sparql_row(pub="https://dblp.org/rec/conf/osdi/B25", title="Different Title",
                       eventYear="2025", publicationYear="2025", book="OSDI", doi="10.1145/abc",
                       type="http://purl.org/net/nknouf/ns/bibtex#Inproceedings"),
            sparql_row(pub="https://dblp.org/rec/conf/osdi/C25", title="A New System",
                       eventYear="2025", publicationYear="2025", book="OSDI",
                       type="http://purl.org/net/nknouf/ns/bibtex#Inproceedings"))
        with patch("scripts.ai_research_bibliography.urlopen", return_value=rows):
            papers, coverage = collect_venue_year({"id": "osdi"}, 2025, source, self.cache)
        self.assertEqual(coverage["bibliography_total"], 1)
        self.assertEqual(papers[0]["doi"], "10.1145/abc")
        self.assertEqual(len(papers[0]["source_urls"]), 3)

    def test_same_title_with_different_dois_remains_distinct(self):
        source = rule("https://dblp.org/streams/conf/osdi", "usenix-proceedings", {})
        rows = sparql_result(
            sparql_row(pub="https://dblp.org/rec/conf/osdi/A25", title="One System",
                       eventYear="2025", publicationYear="2025", book="OSDI",
                       doi="https://doi.org/10.1234/one",
                       type="http://purl.org/net/nknouf/ns/bibtex#Inproceedings"),
            sparql_row(pub="https://dblp.org/rec/conf/osdi/B25", title="One: System",
                       eventYear="2025", publicationYear="2025", book="OSDI",
                       doi="https://doi.org/10.1234/two",
                       type="http://purl.org/net/nknouf/ns/bibtex#Inproceedings"))
        with patch("scripts.ai_research_bibliography.urlopen", return_value=rows):
            papers, coverage = collect_venue_year({"id": "osdi"}, 2025, source, self.cache)
        self.assertEqual({paper["doi"] for paper in papers}, {"10.1234/one", "10.1234/two"})
        self.assertEqual(coverage["bibliography_total"], 2)

    def test_doi_less_title_does_not_bridge_conflicting_dois(self):
        source = rule("https://dblp.org/streams/conf/osdi", "usenix-proceedings", {})
        rows = sparql_result(
            sparql_row(pub="https://dblp.org/rec/conf/osdi/A25", title="One System",
                       eventYear="2025", publicationYear="2025", book="OSDI",
                       doi="https://doi.org/10.1234/one",
                       type="http://purl.org/net/nknouf/ns/bibtex#Inproceedings"),
            sparql_row(pub="https://dblp.org/rec/conf/osdi/B25", title="One: System",
                       eventYear="2025", publicationYear="2025", book="OSDI",
                       doi="https://doi.org/10.1234/two",
                       type="http://purl.org/net/nknouf/ns/bibtex#Inproceedings"),
            sparql_row(pub="https://dblp.org/rec/conf/osdi/C25", title="One System",
                       eventYear="2025", publicationYear="2025", book="OSDI",
                       type="http://purl.org/net/nknouf/ns/bibtex#Inproceedings"))
        with patch("scripts.ai_research_bibliography.urlopen", return_value=rows):
            papers, coverage = collect_venue_year({"id": "osdi"}, 2025, source, self.cache)
        self.assertEqual([paper["doi"] for paper in papers], ["10.1234/one", "10.1234/two", None])
        self.assertEqual(coverage["bibliography_total"], 3)

    def test_doi_less_title_before_conflicting_dois_stays_separate(self):
        source = rule("https://dblp.org/streams/conf/osdi", "usenix-proceedings", {})
        rows = sparql_result(
            sparql_row(pub="https://dblp.org/rec/conf/osdi/C25", title="One System",
                       eventYear="2025", publicationYear="2025", book="OSDI",
                       type="http://purl.org/net/nknouf/ns/bibtex#Inproceedings"),
            sparql_row(pub="https://dblp.org/rec/conf/osdi/A25", title="One: System",
                       eventYear="2025", publicationYear="2025", book="OSDI",
                       doi="https://doi.org/10.1234/one",
                       type="http://purl.org/net/nknouf/ns/bibtex#Inproceedings"),
            sparql_row(pub="https://dblp.org/rec/conf/osdi/B25", title="One System",
                       eventYear="2025", publicationYear="2025", book="OSDI",
                       doi="https://doi.org/10.1234/two",
                       type="http://purl.org/net/nknouf/ns/bibtex#Inproceedings"))
        with patch("scripts.ai_research_bibliography.urlopen", return_value=rows):
            papers, coverage = collect_venue_year({"id": "osdi"}, 2025, source, self.cache)
        self.assertEqual([paper["doi"] for paper in papers], [None, "10.1234/one", "10.1234/two"])
        self.assertEqual([len(paper["source_urls"]) for paper in papers], [1, 1, 1])
        self.assertEqual(coverage["bibliography_total"], 3)

    def test_not_held_skips_network_and_is_not_zero(self):
        source = rule("https://dblp.org/streams/conf/sosp", "acm-proceedings", {})
        source["years"]["2020"] = {"status": "not-held", "track_scope": "SOSP research papers",
                                   "gap_reason": "No SOSP meeting", "official_url": None,
                                   "provenance_urls": ["https://sosp.org/"]}
        with patch("scripts.ai_research_bibliography.urlopen") as fetch:
            papers, coverage = collect_venue_year({"id": "sosp"}, 2020, source, self.cache)
        fetch.assert_not_called()
        self.assertEqual(papers, [])
        self.assertEqual(coverage["status"], "not-held")
        self.assertIsNone(coverage["main_track_total"])
        self.assertIsNone(coverage["bibliography_total"])

    def test_program_match_rule_never_queries_whole_journal_stream(self):
        manifest = json.loads((Path(__file__).resolve().parents[1] /
                               "data/ai_research_observatory/cross_area_sources.json").read_text())
        with patch("scripts.ai_research_bibliography.urlopen") as fetch:
            papers, coverage = collect_venue_year({"id": "sigmetrics"}, 2025,
                                                  manifest["sigmetrics"], self.cache)
        fetch.assert_not_called()
        self.assertEqual(papers, [])
        self.assertEqual(coverage["status"], "unresolved")
        self.assertIsNone(coverage["bibliography_total"])
        self.assertIsNone(coverage["main_track_total"])
        self.assertIn("program", coverage["gap_reason"].lower())

    def test_conflicting_official_index_keeps_total_unknown(self):
        source = rule("https://dblp.org/streams/conf/osdi", "usenix-proceedings", {
            "official_url": "https://www.usenix.org/conference/osdi25/technical-sessions",
            "official_index_type": "usenix-technical-sessions", "official_index_verified": True})
        dblp = sparql_result(sparql_row(pub="https://dblp.org/rec/conf/osdi/A25", title="Paper A",
                                        eventYear="2025", publicationYear="2025", book="OSDI",
                                        type="http://purl.org/net/nknouf/ns/bibtex#Inproceedings"))
        official = io.BytesIO(b'''<article class="node node-paper view-mode-schedule"><h2>
            <a href="/conference/osdi25/presentation/a">Paper A</a></h2></article>
            <article class="node node-paper view-mode-schedule"><h2>
            <a href="/conference/osdi25/presentation/b">Paper B</a></h2></article>''')
        with patch("scripts.ai_research_bibliography.urlopen", side_effect=[dblp, official]):
            papers, coverage = collect_venue_year({"id": "osdi"}, 2025, source, self.cache)
        self.assertEqual(len(papers), 2)
        self.assertIsNone(coverage["main_track_total"])
        self.assertEqual(coverage["bibliography_total"], 1)
        self.assertEqual(coverage["status"], "unresolved")
        self.assertIn("conflict", coverage["gap_reason"].lower())

    def test_matching_official_index_verifies_only_the_main_track_total(self):
        manifest = json.loads((Path(__file__).resolve().parents[1] /
                               "data/ai_research_observatory/cross_area_sources.json").read_text())
        source = manifest["osdi"]
        edition = source["years"]["2025"]
        self.assertEqual(edition["official_index_type"], "usenix-technical-sessions")
        self.assertTrue(edition["official_index_verified"])
        dblp = sparql_result(sparql_row(pub="https://dblp.org/rec/conf/osdi/A25", title="Paper A",
                                        eventYear="2025", publicationYear="2025", book="OSDI",
                                        type="http://purl.org/net/nknouf/ns/bibtex#Inproceedings"))
        official = io.BytesIO(b'''<article class="node node-paper view-mode-schedule"><h2>
            <a href="/conference/osdi25/presentation/a">Paper A</a></h2></article>
            <article class="node node-paper view-mode-schedule"><h2>
            <a href="/conference/atc25/presentation/keynote">Joint keynote</a></h2></article>''')
        with patch("scripts.ai_research_bibliography.urlopen", side_effect=[dblp, official]):
            papers, coverage = collect_venue_year({"id": "osdi"}, 2025, source, self.cache)
        self.assertEqual(len(papers), 1)
        self.assertEqual(coverage["main_track_total"], 1)
        self.assertEqual(coverage["bibliography_total"], 1)
        self.assertEqual(coverage["status"], "verified")
        self.assertIn("https://www.usenix.org/conference/osdi25/presentation/a",
                      papers[0]["source_urls"])

    def test_official_format_change_is_error_not_zero(self):
        source = rule("https://dblp.org/streams/conf/osdi", "usenix-proceedings", {
            "official_url": "https://www.usenix.org/conference/osdi25/technical-sessions",
            "official_index_type": "usenix-technical-sessions", "official_index_verified": True})
        with patch("scripts.ai_research_bibliography.urlopen",
                   side_effect=[sparql_result(), io.BytesIO(b"<html>new layout</html>")]):
            papers, coverage = collect_venue_year({"id": "osdi"}, 2025, source, self.cache)
        self.assertEqual(papers, [])
        self.assertEqual(coverage["status"], "source-error")
        self.assertIsNone(coverage["main_track_total"])
        self.assertIsNone(coverage["bibliography_total"])

    def test_missing_journal_issue_binding_is_source_error(self):
        source = rule("https://dblp.org/streams/journals/pacmpl", "acm-journal-issue",
                      {"dblp_issues": ["POPL"], "dblp_issue_field": "publishedInJournalVolumeIssue"})
        rows = sparql_result(sparql_row(pub="https://dblp.org/rec/journals/pacmpl/A25",
                                       title="A research paper", publicationYear="2025",
                                       type="http://purl.org/net/nknouf/ns/bibtex#Article"))
        with patch("scripts.ai_research_bibliography.urlopen", return_value=rows):
            papers, coverage = collect_venue_year({"id": "popl"}, 2025, source, self.cache)
        self.assertEqual(papers, [])
        self.assertEqual(coverage["status"], "source-error")
        self.assertIsNone(coverage["bibliography_total"])

    def test_malformed_publication_year_is_source_error(self):
        source = rule("https://dblp.org/streams/conf/osdi", "usenix-proceedings", {})
        rows = sparql_result(sparql_row(pub="https://dblp.org/rec/conf/osdi/A25", title="Paper A",
                                       publicationYear="2025?", book="OSDI",
                                       type="http://purl.org/net/nknouf/ns/bibtex#Inproceedings"))
        with patch("scripts.ai_research_bibliography.urlopen", return_value=rows):
            papers, coverage = collect_venue_year({"id": "osdi"}, 2025, source, self.cache)
        self.assertEqual(papers, [])
        self.assertEqual(coverage["status"], "source-error")
        self.assertIsNone(coverage["bibliography_total"])

    def test_cache_reuses_bounded_response(self):
        source = rule("https://dblp.org/streams/conf/osdi", "usenix-proceedings", {})
        fixture = sparql_result(sparql_row(pub="https://dblp.org/rec/conf/osdi/A25", title="Paper A",
                                           eventYear="2025", publicationYear="2025", book="OSDI",
                                           type="http://purl.org/net/nknouf/ns/bibtex#Inproceedings"))
        with patch("scripts.ai_research_bibliography.urlopen", return_value=fixture) as fetch:
            first = collect_venue_year({"id": "osdi"}, 2025, source, self.cache)
            second = collect_venue_year({"id": "osdi"}, 2025, source, self.cache)
        self.assertEqual(first[0], second[0])
        self.assertEqual(fetch.call_count, 1)

    def test_stale_cache_refetches_mutable_index(self):
        source = rule("https://dblp.org/streams/conf/osdi", "usenix-proceedings", {})
        old = sparql_result(sparql_row(pub="https://dblp.org/rec/conf/osdi/A25", title="Paper A",
                                    eventYear="2025", publicationYear="2025", book="OSDI",
                                    type="http://purl.org/net/nknouf/ns/bibtex#Inproceedings"))
        current = sparql_result(sparql_row(pub="https://dblp.org/rec/conf/osdi/B25", title="Paper B",
                                        eventYear="2025", publicationYear="2025", book="OSDI",
                                        type="http://purl.org/net/nknouf/ns/bibtex#Inproceedings"))
        with patch("scripts.ai_research_bibliography.urlopen", side_effect=[old, current]) as fetch:
            collect_venue_year({"id": "osdi"}, 2025, source, self.cache)
            cache_file = next(self.cache.glob("bibliography-*.cache"))
            stale = time.time() - 25 * 3600
            os.utime(cache_file, (stale, stale))
            papers, _ = collect_venue_year({"id": "osdi"}, 2025, source, self.cache)
        self.assertEqual(fetch.call_count, 2)
        self.assertEqual([paper["title"] for paper in papers], ["Paper B"])


if __name__ == "__main__":
    unittest.main()
