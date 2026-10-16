"""Offline contract tests for the ranked cross-area inventory and source rules."""

import json
import unittest
from collections import Counter
from pathlib import Path

from scripts.ai_research_venues import build_catalog


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/ai_research_observatory/cross_area_sources.json"
CATALOG = ROOT / "data/ai_research_observatory/venues.json"
REQUIRED = set("""pldi popl sosp osdi oopsla ppopp sc hpca asplos isca
usenix-atc eurosys cgo cc pact euro-par icdcs ipdps mlsys fse ase icse issta""".split())
AUDIT_ADDITIONS = {"micro", "hpdc", "ics", "socc", "sigmetrics", "cluster", "middleware",
                   "saner", "msr", "icst", "seams", "icpp"}
LEGACY = set("""aaai aamas acl acmmm aistats bmvc cade cikm coling colt cp cvpr
eacl ec ecai ecir ecml-pkdd eccv emnlp foga gecco hri icaps icassp iccbr iccv
icdm iclr icme icml icmr icra ijcar ijcai interspeech iros iswc jelia kdd
kr miccai naacl neurips ppsn recsys rss sat sdm sigir uai wacv wsdm www""".split())
YEARS = {str(year) for year in range(2020, 2027)}


class VenueInventoryTests(unittest.TestCase):
    def test_required_venues_and_legacy_ids_are_unique(self):
        rows = build_catalog()
        counts = Counter(row["id"] for row in rows)
        self.assertTrue(LEGACY | REQUIRED | AUDIT_ADDITIONS <= set(counts))
        self.assertTrue(all(count == 1 for count in counts.values()))
        self.assertEqual(len(LEGACY), 53)

    def test_new_rank_evidence_or_explicit_unranked_status(self):
        rows = {row["id"]: row for row in build_catalog()}
        for venue_id in REQUIRED | AUDIT_ADDITIONS:
            with self.subTest(venue_id=venue_id):
                row = rows[venue_id]
                self.assertFalse(row["ai_native"])
                self.assertEqual(row["source_rule_id"], venue_id)
                self.assertIn(row["area"], {"Systems", "Computer Architecture", "Compilers / Programming Languages", "Parallel / Distributed", "Software Engineering", "ML Systems"})
                if row["rank_status"] == "ranked":
                    self.assertTrue(row["rankings"])
                    self.assertEqual(set(row["ranking_evidence"]), set(row["rankings"]))
                    self.assertIn(row["rank"], {"A*", "A", "B"})
                    self.assertTrue(all(url.startswith("https://") for url in row["ranking_evidence"].values()))
                else:
                    self.assertEqual(row["rank_status"], "unranked-in-audited-lists")
                    self.assertIsNone(row["rank"])
                    self.assertEqual(row["rankings"], {})
                    self.assertTrue(row["ranking_evidence"])

    def test_generated_catalog_is_deterministic(self):
        self.assertEqual(json.loads(CATALOG.read_text()), build_catalog())

    def test_audited_additions_have_primary_rank_memberships(self):
        rows = {row["id"]: row for row in build_catalog()}
        expected = {
            "micro": {"CCF": "A"},
            "hpdc": {"CORE": "A", "CCF": "B"},
            "ics": {"CORE": "A", "CCF": "B"},
            "socc": {"CCF": "B"},
            "sigmetrics": {"CORE": "A*", "CCF": "B"},
            "cluster": {"CORE": "B", "CCF": "B"},
            "middleware": {"CORE": "A", "CCF": "B"},
            "saner": {"CORE": "A", "CCF": "B"},
            "msr": {"CORE": "A"},
            "icst": {"CORE": "A"},
            "seams": {"CORE": "A"},
            "icpp": {"CORE": "B", "CCF": "B"},
        }
        for venue_id, rankings in expected.items():
            with self.subTest(venue_id=venue_id):
                self.assertEqual(rows[venue_id]["rankings"], rankings)


class SourceManifestTests(unittest.TestCase):
    def setUp(self):
        self.rules = json.loads(MANIFEST.read_text())

    def test_every_required_venue_has_all_years_and_provenance(self):
        self.assertTrue(REQUIRED | AUDIT_ADDITIONS <= set(self.rules))
        for venue_id, rule in self.rules.items():
            with self.subTest(venue_id=venue_id):
                self.assertTrue(rule["dblp_stream"].startswith("https://dblp.org/streams/"))
                self.assertTrue(rule["source_family"])
                self.assertEqual(set(rule["years"]), YEARS)
                for year, edition in rule["years"].items():
                    with self.subTest(venue_id=venue_id, year=year):
                        self.assertIn("official_url", edition)
                        self.assertTrue(edition["track_scope"])
                        self.assertIn(edition["status"], {"unresolved", "not-held", "not-yet-published"})
                        self.assertTrue(edition["provenance_urls"])
                        self.assertTrue(all(url.startswith("https://") for url in edition["provenance_urls"]))
                        if edition["official_url"]:
                            self.assertIn(edition["official_url"], edition["provenance_urls"])
                        if edition["status"] != "not-held":
                            self.assertTrue(edition["gap_reason"])

    def test_sosp_non_meeting_years_follow_primary_schedule(self):
        years = self.rules["sosp"]["years"]
        for year in ("2020", "2022"):
            self.assertEqual(years[year]["status"], "not-held")
            self.assertIsNone(years[year]["official_url"])
            self.assertIn("https://sosp.org/", years[year]["provenance_urls"])
        for year in ("2021", "2023", "2024", "2025", "2026"):
            self.assertNotEqual(years[year]["status"], "not-held")

    def test_journal_issues_are_edition_specific(self):
        for year in YEARS:
            self.assertEqual(self.rules["popl"]["years"][year]["dblp_issues"], ["POPL"])
        self.assertEqual(self.rules["oopsla"]["years"]["2020"]["dblp_issues"], ["OOPSLA"])
        self.assertEqual(self.rules["oopsla"]["years"]["2022"]["dblp_issues"], ["OOPSLA1", "OOPSLA2"])
        for venue_id, year, issue in (("fse", "2024", "FSE"), ("fse", "2026", "FSE"), ("issta", "2025", "ISSTA")):
            edition = self.rules[venue_id]["years"][year]
            self.assertEqual(edition["dblp_stream"], "https://dblp.org/streams/journals/pacmse")
            self.assertEqual(edition["dblp_issue_field"], "publishedInJournalVolumeIssue")
            self.assertEqual(edition["dblp_issues"], [issue])
        self.assertEqual(self.rules["issta"]["years"]["2024"]["dblp_stream"], "https://dblp.org/streams/conf/issta")

    def test_nonobvious_dblp_stream_keys(self):
        self.assertEqual(self.rules["pact"]["dblp_stream"], "https://dblp.org/streams/conf/IEEEpact")
        self.assertEqual(self.rules["hpca"]["dblp_stream"], "https://dblp.org/streams/conf/cnhpca")
        self.assertEqual(self.rules["ipdps"]["dblp_stream"], "https://dblp.org/streams/conf/ipps")
        self.assertEqual(self.rules["usenix-atc"]["dblp_stream"], "https://dblp.org/streams/conf/usenix")
        self.assertEqual(self.rules["mlsys"]["source_family"], "mlsys-proceedings")

    def test_audited_additions_have_bounded_source_rules(self):
        streams = {
            "micro": "conf/micro", "hpdc": "conf/hpdc", "ics": "conf/ics",
            "socc": "conf/cloud", "cluster": "conf/cluster",
            "middleware": "conf/middleware", "sigmetrics": "journals/pomacs",
            "saner": "conf/wcre", "msr": "conf/msr", "icst": "conf/icst",
            "seams": "conf/seams", "icpp": "conf/icpp",
        }
        for venue_id, path in streams.items():
            with self.subTest(venue_id=venue_id):
                self.assertEqual(self.rules[venue_id]["dblp_stream"], f"https://dblp.org/streams/{path}")
        self.assertIn("conf/sigmetrics", " ".join(self.rules["sigmetrics"]["related_dblp_streams"]))
        self.assertIn("POMACS", self.rules["sigmetrics"]["year_basis"])
        self.assertIn("Industry Papers", self.rules["socc"]["years"]["2025"]["excluded_material"])
        self.assertIn("industrial-track proceedings", self.rules["middleware"]["excluded_material"])

    def test_audited_2025_organizer_provenance(self):
        official_programs = {
            "micro": "https://microarch.org/micro58/program/index.php",
            "hpdc": "https://hpdc.sci.utah.edu/2025/program.html",
        }
        for venue_id, url in official_programs.items():
            with self.subTest(venue_id=venue_id):
                edition = self.rules[venue_id]["years"]["2025"]
                self.assertEqual(edition["official_url"], url)
                self.assertIn(url, edition["provenance_urls"])
                self.assertEqual(edition["status"], "unresolved")
        for venue_id in AUDIT_ADDITIONS:
            with self.subTest(venue_id=venue_id):
                edition = self.rules[venue_id]["years"]["2025"]
                self.assertGreater(len(edition["provenance_urls"]), 1)

    def test_2026_atc_publisher_transition_and_osdi_track(self):
        atc = self.rules["usenix-atc"]["years"]["2026"]
        self.assertEqual(atc["status"], "not-yet-published")
        self.assertEqual(atc["source_family"], "acm-proceedings")
        self.assertIsNone(atc["dblp_stream"])
        self.assertIn("https://sigops.org/s/conferences/atc/2026/", atc["provenance_urls"])
        self.assertIn("Operational Systems", self.rules["osdi"]["years"]["2026"]["excluded_material"])


if __name__ == "__main__":
    unittest.main()
