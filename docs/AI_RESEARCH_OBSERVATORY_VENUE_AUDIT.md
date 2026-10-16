# AI Research Observatory ranked-venue audit

Date: 2026-10-16. This is an inventory decision, not a bibliography or a
claim that all AI papers have been collected.

## Rule and ranking sources

The 53 legacy AI-facing IDs and 23 requested cross-area IDs stay in scope.
Additional series must have a primary ranked-list membership in the audited
boundary, an active full/regular research-paper series, and organizer evidence
that AI/ML systems or AI-assisted software engineering is a substantive main
research topic. An isolated AI paper, a workshop, an industry-only track, or
use of AI merely as an evaluation workload does not by itself qualify. This
rule screens *additional* series; it does not undo the user's named 23.

Screened the [CORE 2023 CSV export](https://portal.core.edu.au/conf-ranks/?by=all&source=CORE2023&do=Export),
particularly A*/A rows in 4606, 4612 and CSE, the CCF 2026
[architecture/parallel/systems](https://www.ccf.org.cn/Academic_Evaluation/ARCH_DCP_SS/)
and [software/systems/programming](https://www.ccf.org.cn/Academic_Evaluation/TCSE_SS_PDL/)
A/B conference lists, the [CCF AI list](https://www.ccf.org.cn/Academic_Evaluation/AI/),
and [TH-CPL AI A](https://numbda.cs.tsinghua.edu.cn/~yuwj/TH-CPL.pdf).
The latter two add no new ID beyond the legacy inventory. CORE labels such as
TBR are not promoted to ranks; CCF and CORE memberships are recorded separately.
The CCF list gives the disciplinary screening evidence below, not proof that
every paper at a venue is or is not AI research.

## Included after review

All rows below have `ai_native: false`, a source rule in
`cross_area_sources.json`, and unresolved 2020-2026 count cells until an
official main-track index is reconciled with the bibliography. A DBLP stream
is a candidate bibliography, not a verified main-track total.

| Series | Verified rank(s) | Organizer main-track evidence and boundary |
| --- | --- | --- |
| MICRO | CCF A; CORE 2023 TBR (not assigned) | [2025 main program](https://microarch.org/micro58/program/index.php) has Systems for AI/LLMs and accelerator research. Exclude posters, PhD forum and workshops. |
| HPDC | [CORE A](https://portal.core.edu.au/conf-ranks/33/), CCF B | [2025 technical program](https://hpdc.sci.utah.edu/2025/program.html) has a Model Training session; [organizer archive](https://hpdc.org/) distinguishes main conference from workshops. |
| ICS | [CORE A](https://portal.core.edu.au/conf-ranks/30/), CCF B | [2025 research call](https://hpcrl.github.io/ICS2025-webpage/call-for/call-for-papers.html) explicitly includes machine learning on large-scale systems. |
| SoCC | CCF B | [2025 research call](https://acmsocc.org/2025/papers.html) explicitly names systems for ML; count full research papers only, not short or industry papers. DBLP uses `conf/cloud`, not `conf/socc`. |
| SIGMETRICS | [CORE A*](https://portal.core.edu.au/conf-ranks/39/), CCF B | [2025 call](https://www.sigmetrics.org/sigmetrics2025/call_for_papers.html) has Systems for ML and a Learning track. Accepted papers appear in POMACS across publication years, with possible journal opt-outs. Match each event program to POMACS/opt-out papers; never count the entire journal volume or `conf/sigmetrics` stream. |
| IEEE Cluster | [CORE B](https://portal.core.edu.au/conf-ranks/632/), CCF B | [2025 research call](https://clustercomp.org/2025/papers/) explicitly covers ML training/inference cluster systems. Exclude workshops. |
| Middleware | [CORE A](https://portal.core.edu.au/conf-ranks/79/), CCF B | [2025 research call](https://middleware-conf.github.io/2025/calls/call-for-research-papers/) explicitly includes middleware for AI/ML. Exclude separately published industrial papers, demos and workshops. |
| SANER | [CORE A](https://portal.core.edu.au/conf-ranks/2280/), CCF B | [2025 research call](https://conf.researchr.org/track/saner-2025/saner-2025-papers) explicitly includes AI for software engineering. DBLP's historical stream is `conf/wcre`; exclude companion. |
| MSR | [CORE A](https://portal.core.edu.au/conf-ranks/711/); CCF C (not assigned) | [2025 technical call](https://2025.msrconf.org/track/msr-2025-technical-papers) explicitly accepts AI/ML for software engineering. Exclude data/tool showcase, challenge and industry tracks. |
| ICST | [CORE A](https://portal.core.edu.au/conf-ranks/1221/); CCF C (not assigned) | [2025 research call](https://conf.researchr.org/track/icst-2025/icst-2025-papers) explicitly includes AI-assisted testing. Exclude co-located AI workshops and non-research tracks. |
| SEAMS | [CORE A](https://portal.core.edu.au/conf-ranks/2281/) | [2025 research call](https://conf.researchr.org/track/seams-2025/seams-2025-research-track) explicitly includes AI/ML for adaptive software; use full research papers, not short papers. |
| ICPP | [CORE B](https://portal.core.edu.au/conf-ranks/1167/), CCF B | [2025 organizer program](https://icpp2025.sdsc.edu/) has an AI in Computing track. DBLP separates main `conf/icpp` from `conf/icppw` workshops. |

## Excluded after review

These are explicit *inventory* exclusions under the rule above, not assertions
that no AI-related individual papers appear there. Ranks are not copied to
excluded candidates. The CCF category pages and CORE export above provide
primary list membership and full venue names for the grouped decisions.

| Candidate(s) | Evidence-backed reason for this boundary decision |
| --- | --- |
| VEE | CCF B and [CORE B](https://portal.core.edu.au/conf-ranks/1262/), but the [steering scope](https://vee.sigops.org/) is virtual execution environments and the [DBLP series](https://dblp.org/db/conf/vee/index.html) ends at 2022. No active 2023-2026 research-edition rule can be supported. Do not mislabel later years as verified zero. |
| HiPEAC | CCF B. Its [DBLP series](https://dblp.org/db/conf/hipeac/index.html) includes workshop proceedings and links main research to TACO journal publication; a `conf/hipeac` count would not identify a stable full-paper main track. Excluded from this conference-year inventory, not from AI architecture research in general. |
| FAST, MSST, LISA | CCF A/B storage or systems-administration series by their official list descriptions. Their ranked identity is storage/operations, not a separately evidenced substantive AI-systems main track under this audit. An AI storage paper alone is insufficient. |
| DAC, FPGA, DATE, HOT CHIPS, ICCD, ICCAD, CODES+ISSS, ITC | CCF A/B design-automation, chip-design, testing or hardware-presentation series by the official list. AI accelerators can be application examples, but that does not turn those entire specialist tracks into the AI-systems research inventory. HOT CHIPS also does not supply the same regular full-paper conference boundary. |
| SPAA, PODC, DISC | Ranked parallel/distributed *algorithm-principles* series ([CCF](https://www.ccf.org.cn/Academic_Evaluation/ARCH_DCP_SS/); [CORE](https://portal.core.edu.au/conf-ranks/?by=all&source=CORE2023&do=Export)). Their primary identity is theory rather than implementation of AI systems; no organizer main AI-systems research area was verified here. |
| Performance, RTAS, RTSS, DSN | Performance evaluation, real-time and dependability specialties in the primary lists. No substantive organizer AI-systems main research area was verified; occasional ML evaluation or fault-tolerance applications do not meet the inclusion rule. |
| FM, ETAPS, VMCAI, SAS, CAV, ESOP, TACAS | Primary CCF/CORE descriptions identify formal methods, verification, static analysis or language theory. AI applications are not an evidenced substantive main research area in this audit. |
| ECOOP, ICFP, LCTES | Their CCF/CORE-ranked identity is object-oriented, functional or embedded programming languages. Unlike the requested PLDI/POPL/OOPSLA, organizer evidence in this audit did not establish a substantive AI compiler/systems main area. |
| ICPC, RE, CAiSE, MoDELS, ICSOC, ICSME, ICWS, ESEM, ISSRE, ECSA, ICSA, EASE, BPM | Primary list names and organizer research scopes are program comprehension, requirements, information systems, modeling, services, maintenance, empirical/reliability or software architecture. Individual AI papers or AI-only industry/workshop activity do not establish the main-track AI-for-SE identity required for an *additional* entry. |
| HotOS | CCF B and CORE A, but explicitly a [USENIX workshop](https://www.usenix.org/conference/hotos25), not a regular full-paper conference series in this inventory. |
| SIGCOMM, SenSys, CoNEXT, MobiCom, MobiSys, MobiHoc, MSWiM, INFOCOM, IPSN, IMC | CORE A*/A networking/mobile/sensor/measurement rows in 4606. This audit does not treat general networking and mobile infrastructure as within the approved AI systems/compiler/SE boundary merely because a paper uses ML. |
| SIGMOD, VLDB, CCS, NDSS | General database and security series outside the approved subject boundary; no rank or source rule is inferred for them. |

CP and WWW in those ranked lists are already among the legacy 53, not omissions.
The decisions can be revisited when a primary organizer CFP establishes a
substantive AI main research area or the user widens the subject boundary.
