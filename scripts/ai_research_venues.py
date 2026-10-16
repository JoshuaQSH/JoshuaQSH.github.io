"""Pinned AI-facing and cross-area inventory from CORE 2023, CCF 2026, TH-CPL 2019.

OpenAlex source IDs are an independently reviewed retrieval aid, not proof that
its works_count equals an organizer's accepted-paper count.

Inventory audit (2026-10-16): the 53 existing AI-facing IDs remain intact.
CCF's 2026 AI A list is covered by those IDs. Additional ranked cross-area
decisions, organizer evidence and explicit exclusions are recorded in
docs/AI_RESEARCH_OBSERVATORY_VENUE_AUDIT.md. The CORE 2023 export and CCF
2026 lists are ranking evidence; subject area never implies a rank.
"""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/ai_research_observatory/venues.json"
CORE_URL = "https://portal.core.edu.au/conf-ranks/?by=all&page=1&search=&sort=arank&source=CORE2023"
CCF_URL = "https://lib.ecnu.edu.cn/_upload/article/files/e2/d9/dd45764345088869915f6b3617a4/28891f1f-eb8a-4000-a279-6e7141d92488.pdf"
THCPL_URL = "https://numbda.cs.tsinghua.edu.cn/~yuwj/TH-CPL.pdf"

# CORE rows with 2020 FoR 4602, 4603 or 4611. SIGGRAPH (computer graphics)
# and SIGSPATIAL (geographic information systems) are excluded by the user's
# AI-area boundary. Cross-area AI research venues are added separately below.
CORE_ASTAR = "aaai aamas acl acmmm colt cvpr ec eccv emnlp icaps iccv icdm iclr icml icra ijcai kdd kr neurips"
CORE_A = "uai wacv icme ijcar interspeech jelia miccai ppsn ecml-pkdd naacl bmvc hri iros sat eacl wsdm aistats cade cikm cp ecai foga gecco"
CCF_A = "aaai neurips acl cvpr iccv icml iclr"
CCF_B = "colt emnlp ecai eccv icra icaps iccbr coling kr uai aamas ppsn naacl ijcai"
CCF_A_CROSS = "kdd sigir acmmm www"
CCF_B_CROSS = "cikm wsdm ecml-pkdd iswc icdm recsys sdm icmr icassp icme"
THCPL_A = "cvpr iccv icml acl eccv colt neurips aaai emnlp icra iclr rss"
# AI-facing retrieval/recommendation venues whose CORE FoR is outside 4602/03/11.
ADDITIONAL = "sigir recsys ecir iswc www sdm"
ADDITIONAL_CORE = {"sigir": "A*", "www": "A*", "recsys": "A", "ecir": "A", "iswc": "A", "sdm": "A"}

AREAS = {
    "AI / ML": "aaai aamas colt ec icaps iclr icml ijcai kr neurips uai ppsn aistats sat cade cp ecai foga gecco ijcar jelia iccbr",
    "Computer Vision": "cvpr eccv iccv wacv bmvc miccai",
    "LLMs / NLP": "acl emnlp naacl eacl coling interspeech icassp",
    "Robotics": "icra iros hri rss",
    "Multimedia": "acmmm icme icmr",
    "Data Mining / Retrieval": "icdm kdd wsdm cikm ecml-pkdd sigir recsys ecir iswc www sdm",
}
AI_ADJACENT = set("ec acmmm icme cikm iswc www".split())

# Identifiers with a clearly named venue source; unmapped series remain visible
# in the catalog but are not queried by a misleading keyword or generic source.
SOURCES = {
    "aaai": "S4210191458", "aamas": "S4306417597", "acl": "S4363608652",
    "acmmm": "S4363608757", "colt": "S4306418075", "cvpr": "S4210176548",
    "ec": "S4363608973", "eccv": "S4306418318", "emnlp": "S4363608991",
    "icaps": "S4387283601", "iccv": "S4363607764", "iclr": "S4306419637",
    "icml": "S4306419644", "icra": "S4210217939", "ijcai": "S4306419999",
    "kdd": "S7407088418", "kr": "S4306420732", "neurips": "S4363606243",
    "uai": "S4306421103", "wacv": "S4363607736", "icme": "S4363607799",
    "ijcar": "S4306420000", "interspeech": "S4393918409", "jelia": "S4306418329",
    "miccai": "S4306420499", "ppsn": "S4306420682", "naacl": "S4363608774",
    "bmvc": "S7407088578", "hri": "S4363608246", "iros": "S4363608614",
    "sat": "S4306421062", "eacl": "S4306418011", "wsdm": "S4363608885",
    "aistats": "S4306419146", "cade": "S4306418023", "cikm": "S7407085931",
    "cp": "S4306420726", "ecai": "S4306418308", "foga": "S4306422346",
    "gecco": "S4363608932", "iccbr": "S4306419182", "coling": "S4306419219",
    "rss": "S4306420803", "sigir": "S4363608773", "recsys": "S7407086088",
    "ecir": "S4306418323", "iswc": "S4306420056", "www": "S4363608783",
}
NAMES = {"neurips": "NeurIPS", "ecml-pkdd": "ECML PKDD", "recsys": "RecSys",
         "interspeech": "Interspeech", "www": "The Web Conference", "acmmm": "ACM MM"}

CCF_ARCH_URL = "https://www.ccf.org.cn/Academic_Evaluation/ARCH_DCP_SS/"
CCF_SOFTWARE_URL = "https://www.ccf.org.cn/Academic_Evaluation/TCSE_SS_PDL/"
CORE_EXPORT_URL = "https://portal.core.edu.au/conf-ranks/?by=all&source=CORE2023&do=Export"

# id: display name, area, CORE 2023 portal row/rank, CCF 2026 rank/category.
# The single unranked row is explicit; no rank is derived from area or neighbors.
CROSS_AREA = {
    "pldi": ("PLDI", "Compilers / Programming Languages", 84, "A*", "A", CCF_SOFTWARE_URL),
    "popl": ("POPL", "Compilers / Programming Languages", 82, "A*", "A", CCF_SOFTWARE_URL),
    "sosp": ("SOSP", "Systems", 48, "A*", "A", CCF_SOFTWARE_URL),
    "osdi": ("OSDI", "Systems", 1842, "A*", "A", CCF_SOFTWARE_URL),
    "oopsla": ("OOPSLA", "Compilers / Programming Languages", 18, "A", "A", CCF_SOFTWARE_URL),
    "ppopp": ("PPoPP", "Parallel / Distributed", 1691, "B", "A", CCF_ARCH_URL),
    "sc": ("SC", "Parallel / Distributed", 77, "A", "A", CCF_ARCH_URL),
    "hpca": ("HPCA", "Computer Architecture", 1386, "A*", "A", CCF_ARCH_URL),
    "asplos": ("ASPLOS", "Computer Architecture", 147, "A*", "A", CCF_ARCH_URL),
    "isca": ("ISCA", "Computer Architecture", 32, "A*", "A", CCF_ARCH_URL),
    "usenix-atc": ("USENIX ATC / ACM SIGOPS ATC", "Systems", 1838, "A", "A", CCF_ARCH_URL),
    "eurosys": ("EuroSys", "Systems", 525, "A", "A", CCF_ARCH_URL),
    "cgo": ("CGO", "Compilers / Programming Languages", 1362, "A", "B", CCF_ARCH_URL),
    "cc": ("CC", "Compilers / Programming Languages", 936, "B", None, None),
    "pact": ("PACT", "Computer Architecture", 1165, "B", "B", CCF_ARCH_URL),
    "euro-par": ("Euro-Par", "Parallel / Distributed", 2022, "B", "B", CCF_ARCH_URL),
    "icdcs": ("ICDCS", "Parallel / Distributed", 1002, "A", "B", CCF_ARCH_URL),
    "ipdps": ("IPDPS", "Parallel / Distributed", 688, "A", "B", CCF_ARCH_URL),
    "mlsys": ("MLSys", "ML Systems", None, None, None, None),
    "fse": ("FSE", "Software Engineering", 52, "A*", "A", CCF_SOFTWARE_URL),
    "ase": ("ASE", "Software Engineering", 279, "A*", "A", CCF_SOFTWARE_URL),
    "icse": ("ICSE", "Software Engineering", 1209, "A*", "A", CCF_SOFTWARE_URL),
    "issta": ("ISSTA", "Software Engineering", 1412, "A", "A", CCF_SOFTWARE_URL),
    "micro": ("MICRO", "Computer Architecture", None, None, "A", CCF_ARCH_URL),
    "hpdc": ("HPDC", "Parallel / Distributed", 33, "A", "B", CCF_ARCH_URL),
    "ics": ("ICS", "Parallel / Distributed", 30, "A", "B", CCF_ARCH_URL),
    "socc": ("SoCC", "Systems", None, None, "B", CCF_ARCH_URL),
    "sigmetrics": ("SIGMETRICS", "Systems", 39, "A*", "B", CCF_ARCH_URL),
    "cluster": ("IEEE Cluster", "Parallel / Distributed", 632, "B", "B", CCF_ARCH_URL),
    "middleware": ("Middleware", "Systems", 79, "A", "B", CCF_SOFTWARE_URL),
    "saner": ("SANER", "Software Engineering", 2280, "A", "B", CCF_SOFTWARE_URL),
    "msr": ("MSR", "Software Engineering", 711, "A", None, None),
    "icst": ("ICST", "Software Engineering", 1221, "A", None, None),
    "seams": ("SEAMS", "Software Engineering", 2281, "A", None, None),
    "icpp": ("ICPP", "Parallel / Distributed", 1167, "B", "B", CCF_ARCH_URL),
}


def build_catalog():
    rankings = {}
    for scheme, rank, names in (("CORE", "A*", CORE_ASTAR), ("CORE", "A", CORE_A),
                                ("CCF", "A", CCF_A), ("CCF", "B", CCF_B),
                                ("CCF", "A", CCF_A_CROSS), ("CCF", "B", CCF_B_CROSS),
                                ("TH-CPL", "A", THCPL_A)):
        for name in names.split():
            rankings.setdefault(name, {})[scheme] = rank
    for name in ADDITIONAL.split():
        rankings.setdefault(name, {})["CORE"] = ADDITIONAL_CORE[name]
    areas = {name: area for area, names in AREAS.items() for name in names.split()}
    if set(areas) != set(rankings):
        raise ValueError(f"Area mapping differs from catalog: {set(areas) ^ set(rankings)}")
    rows = []
    for name in sorted(rankings):
        ranks = rankings[name]
        scheme = "CORE" if "CORE" in ranks else "CCF" if "CCF" in ranks else "TH-CPL"
        rank = ranks[scheme]
        url = (CORE_URL.replace("search=", f"search={quote(name)}") if scheme == "CORE"
               else CCF_URL if scheme == "CCF" else THCPL_URL)
        source = SOURCES.get(name)
        rows.append({"id": name, "name": NAMES.get(name, name.upper()), "area": areas[name],
                     "ai_native": name not in AI_ADJACENT,
                     "source_id": f"https://openalex.org/{source}" if source else None,
                     "source_name": None, "ranking_scheme": scheme,
                     "edition": "2023" if scheme == "CORE" else "2026" if scheme == "CCF" else "2019",
                     "rank": rank, "rank_url": url, "rankings": ranks,
                     "ranking_urls": {"CORE": CORE_URL, "CCF": CCF_URL, "TH-CPL": THCPL_URL}})
    for venue_id, (display_name, area, core_row, core_rank, ccf_rank, ccf_url) in CROSS_AREA.items():
        ranks = {}
        evidence = {}
        if core_rank:
            ranks["CORE"] = core_rank
            evidence["CORE"] = f"https://portal.core.edu.au/conf-ranks/{core_row}/"
        if ccf_rank:
            ranks["CCF"] = ccf_rank
            evidence["CCF"] = ccf_url
        primary = "CORE" if core_rank else "CCF" if ccf_rank else None
        rows.append({
            "id": venue_id, "name": display_name, "area": area,
            "ai_native": False, "source_id": None, "source_name": None,
            "source_rule_id": venue_id,
            "rank_status": "ranked" if primary else "unranked-in-audited-lists",
            "ranking_scheme": primary,
            "edition": "2023" if primary == "CORE" else "2026" if primary else None,
            "rank": ranks.get(primary), "rank_url": evidence.get(primary),
            "rankings": ranks, "ranking_urls": evidence,
            "ranking_evidence": evidence if evidence else {
                "CORE": CORE_EXPORT_URL,
                "CCF": "https://www.ccf.org.cn/Academic_Evaluation/By_category/",
                "TH-CPL": THCPL_URL,
            },
        })
    return sorted(rows, key=lambda row: row["id"])


if __name__ == "__main__":
    OUTPUT.write_text(json.dumps(build_catalog(), indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {len(build_catalog())} AI-facing venues to {OUTPUT}")
