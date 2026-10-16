"""Offline checks for official proceedings and repository evidence."""
import unittest

from ai_research_sources import (merge_official, normalize_official, official_source, parse_neurips,
                                 parse_pmlr, parse_acl, parse_cvf, repo_slug, select_records)


VENUE = {"id": "icml", "name": "ICML", "area": "Machine Learning", "rank": "A*",
         "ranking_scheme": "CORE", "edition": "2023", "rank_url": "https://portal.core.edu.au/",
         "source_id": "https://openalex.org/S1"}


class OfficialSourceTests(unittest.TestCase):
    def test_acl_main_volume_excludes_other_tracks(self):
        html = '<a href=/2025.acl-long.1/><span>Real</span> paper</a><a href=/2025.acl-long.1.pdf>pdf</a><a href=/2025.findings-acl.2/>Finding</a>'
        rows = parse_acl(html, 2025)
        self.assertEqual([(row["title"], row["url"]) for row in rows],
                         [("Real paper", "https://aclanthology.org/2025.acl-long.1/")])
        emnlp = '<a href=/2025.emnlp-main.2/>Main paper</a><a href=/2025.findings-emnlp.2/>Finding</a>'
        self.assertEqual([row["title"] for row in parse_acl(emnlp, 2025, "emnlp")], ["Main paper"])

    def test_cvf_main_index_excludes_workshop_links(self):
        html = '<dt class="ptitle"><br><a href="/content/CVPR2025/html/A_CVPR_2025_paper.html">A &amp; B</a></dt><dd><input name="query_author" value="Ada Lovelace"></dd><dt class="ptitle"><a href="/content/CVPR2025_workshops/html/B.html">Workshop</a></dt>'
        rows = parse_cvf(html, "cvpr", 2025)
        self.assertEqual(rows, [{"title": "A & B", "url": "https://openaccess.thecvf.com/content/CVPR2025/html/A_CVPR_2025_paper.html", "first_author": "Ada Lovelace", "code_url": None}])
        legacy = '<dt class="ptitle"><a href="content_WACV_2020/html/A_WACV_2020_paper.html">Old paper</a></dt>'
        self.assertEqual(parse_cvf(legacy, "wacv", 2020)[0]["url"],
                         "https://openaccess.thecvf.com/content_WACV_2020/html/A_WACV_2020_paper.html")

    def test_icml_2026_uses_published_pmlr_volume(self):
        self.assertEqual(official_source("icml", 2026), ("PMLR", "https://proceedings.mlr.press/v306/"))
        self.assertEqual(official_source("aistats", 2026), ("PMLR", "https://proceedings.mlr.press/v300/"))
        self.assertEqual(official_source("colt", 2020), ("PMLR", "https://proceedings.mlr.press/v125/"))
        self.assertEqual(official_source("uai", 2026), ("PMLR", "https://proceedings.mlr.press/v337/"))
        self.assertIsNone(official_source("neurips", 2026))

    def test_neurips_only_main_conference_track(self):
        html = '''<li class="conference" data-track="conference"><div class="paper-content">
            <a title="paper title" href="/paper_files/paper/2022/hash/a-Abstract-Conference.html">A &amp; B</a>
            <span class="paper-authors">Ada Example, Bob Example</span></div></li>
            <li class="datasets_and_benchmarks_track" data-track="datasets_and_benchmarks_track">
            <a title="paper title" href="/paper_files/paper/2022/hash/b-Abstract-Datasets_and_Benchmarks_Track.html">Wrong track</a></li>'''
        rows = parse_neurips(html, 2022)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "A & B")
        self.assertEqual(rows[0]["first_author"], "Ada Example")
        self.assertTrue(rows[0]["url"].endswith("a-Abstract-Conference.html"))

    def test_neurips_old_main_track_has_no_track_label(self):
        html = '''<li class="" data-track="none"><a title="paper title"
            href="/paper_files/paper/2020/hash/a-Abstract.html">Old paper</a>
            <span class="paper-authors">Ada Example</span></li>'''
        self.assertEqual(len(parse_neurips(html, 2020)), 1)

    def test_pmlr_software_link_is_paper_specific(self):
        html = '''<div class="paper"><p class="title">First paper</p>
            <span class="authors">Ada Example,&nbsp;Bob Example</span>
            <p class="links">[<a href="https://proceedings.mlr.press/v267/a.html">abs</a>]
            [<a href="https://github.com/org/first">Software</a>]</p></div>
            <div class="paper"><p class="title">Second paper</p>
            <span class="authors">Cy Example</span>
            <p class="links">[<a href="https://proceedings.mlr.press/v267/b.html">abs</a>]</p></div>'''
        rows = parse_pmlr(html, 2025, 267)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["code_url"], "https://github.com/org/first")
        self.assertIsNone(rows[1]["code_url"])

    def test_official_only_record_keeps_unknown_impact_and_affiliation(self):
        raw = {"title": "A new method", "url": "https://proceedings.mlr.press/v267/a.html",
               "first_author": "Ada", "code_url": "https://github.com/org/first"}
        paper = normalize_official(raw, VENUE, 2025, "PMLR")
        self.assertIsNone(paper["citation_percentile"])
        self.assertIsNone(paper["citations"])
        self.assertEqual(paper["first_author_sector"], "Unknown")
        self.assertTrue(paper["code_available"])
        self.assertEqual(paper["repository_url"], "https://github.com/org/first")

    def test_title_merge_preserves_openalex_metadata_and_adds_proceedings(self):
        openalex = {"id": "https://openalex.org/W1", "title": "A New Method: Better Results",
                    "doi": None, "year": 2025, "venue_id": "icml", "citations": 12,
                    "citation_percentile": .6, "source": "OpenAlex"}
        official = normalize_official({"title": "A new method: better results", "first_author": "Ada",
            "url": "https://proceedings.mlr.press/v267/a.html", "code_url": "https://github.com/org/first"}, VENUE, 2025, "PMLR")
        merged = merge_official([openalex], [official])
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["id"], openalex["id"])
        self.assertEqual(merged[0]["citations"], 12)
        self.assertEqual(merged[0]["proceedings_url"], official["url"])
        self.assertEqual(merged[0]["repository_url"], "https://github.com/org/first")

    def test_even_sample_preserves_curated_url(self):
        rows = [{"url": f"https://example.org/{i}"} for i in range(10)]
        sample = select_records(rows, 3, {"https://example.org/4"})
        self.assertEqual(len(sample), 3)
        self.assertIn(rows[4], sample)

    def test_only_repository_root_is_queried(self):
        self.assertEqual(repo_slug("https://github.com/Owner/Repo/tree/main"), "Owner/Repo")
        self.assertIsNone(repo_slug("https://github.com/Owner"))
        self.assertIsNone(repo_slug("https://evil.example/Owner/Repo"))


if __name__ == "__main__":
    unittest.main()
