(function () {
  "use strict";
  const core = window.AIResearchCore;
  const $ = id => document.getElementById(id);
  const number = n => new Intl.NumberFormat("en-GB", { maximumFractionDigits: 1 }).format(n);
  const countryName = code => { try { return new Intl.DisplayNames(["en"], { type: "region" }).of(code); } catch (_) { return code; } };
  const weights = { citation: 40, venue: 15, award: 10, code: 5, stars: 5, activity: 5, maintenance: 10, adoption: 10 };
  const sectors = ["Industry", "University", "Research Institute", "Joint"];
  const coords = { US:[-98,39],GB:[-3,54],CN:[104,35],CA:[-106,57],DE:[10,51],FR:[2,47],IN:[79,22],JP:[138,36],KR:[128,36],SG:[104,1.4],AU:[134,-25],CH:[8.2,47],NL:[5,52],IT:[12,42],ES:[-4,40],SE:[15,62],FI:[26,64],NO:[8,62],IL:[35,31],BR:[-51,-12],TW:[121,24],HK:[114,22],AT:[14,47],BE:[4.5,51],DK:[10,56],IE:[-8,53],NZ:[174,-41],PL:[19,52],RU:[90,59],AE:[54,24],TR:[35,39],ZA:[24,-29],SA:[45,24],MX:[-102,24],CZ:[15,49],PT:[-8,39],GR:[23,39],TH:[101,15],MY:[102,4],ID:[118,-3],VN:[107,16],EG:[30,27],PK:[69,30],IR:[54,32],UA:[32,49],LU:[6,50],HU:[19,47],RO:[25,45],CL:[-71,-33],CO:[-74,4] };
  const milestones = [
    ["2020", [["GPT-3", "https://openai.com/index/language-models-are-few-shot-learners/"]]],
    ["2022", [["ChatGPT", "https://openai.com/index/chatgpt/"]]],
    ["2023", [["LLaMA", "https://ai.meta.com/blog/large-language-model-llama-meta-ai/"], ["GPT-4", "https://openai.com/index/gpt-4-research/"]]],
    ["2024", [["Llama 3", "https://ai.meta.com/blog/meta-llama-3/"]]],
    ["2025", [["DeepSeek-R1", "https://github.com/deepseek-ai/DeepSeek-R1"], ["GPT-5", "https://openai.com/index/introducing-gpt-5/"]]],
    ["2026", []]
  ];
  let snapshot = null, catalog = [], page = 0;
  const pageSize = 20;

  function node(tag, text, cls) {
    const item = document.createElement(tag);
    if (text !== undefined && text !== null) item.textContent = String(text);
    if (cls) item.className = cls;
    return item;
  }
  function safeHref(value, fallback = "https://openalex.org/") {
    try {
      const url = new URL(value);
      return url.protocol === "https:" || url.protocol === "http:" ? url.href : fallback;
    } catch (_) { return fallback; }
  }
  function svg(tag, attrs, text) {
    const item = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [key, value] of Object.entries(attrs || {})) item.setAttribute(key, value);
    if (text !== undefined) item.textContent = text;
    return item;
  }
  function selectOptions(id, values, format) {
    const select = $(id);
    for (const value of values) {
      const option = node("option", format ? format(value) : value);
      option.value = value;
      select.appendChild(option);
    }
  }
  function filters() {
    return { year: $("aro-year").value, area: $("aro-area").value, venue: $("aro-venue").value,
      sector: $("aro-sector").value, country: $("aro-country").value, search: $("aro-search").value };
  }
  function selected() { return core.filterPapers(snapshot.papers, filters()); }
  function setText(id, value) { $(id).textContent = value; }
  function emptyChart(target, message) { target.replaceChildren(node("p", message, "aro-footnote")); }

  function renderStats(papers) {
    setText("aro-paper-count", number(papers.length));
    setText("aro-institution-count", number(new Set(papers.flatMap(p => p.all_institutions || [])).size));
    const classified = papers.filter(p => ["Industry", "University", "Research Institute"].includes(p.first_author_sector));
    const share = sector => classified.length ? `${Math.round(100 * classified.filter(p => p.first_author_sector === sector).length / classified.length)}%` : "—";
    setText("aro-industry-share", share("Industry"));
    setText("aro-university-share", share("University"));
    const scored = classified.map(p => ({ sector: p.first_author_sector, value: core.score(p, weights).value })).filter(x => x.value !== null);
    const total = scored.reduce((a, x) => a + x.value, 0);
    setText("aro-impact-share", total ? `${Math.round(100 * scored.filter(x => x.sector === "Industry").reduce((a, x) => a + x.value, 0) / total)}%` : "—");
    setText("aro-repo-count", number(new Set(papers.map(p => p.repository_url).filter(Boolean)).size));
    const reviewed = papers.filter(p => p.leadership !== "Unknown");
    setText("aro-leadership-note", `Leadership evidence: ${reviewed.length} of ${papers.length} filtered records have a reviewed classification. First-author and team sectors above are not leadership claims.`);
  }

  function chartCanvas(target, label) {
    const canvas = svg("svg", { viewBox: "0 0 560 270", role: "img", "aria-label": label, preserveAspectRatio: "xMidYMid meet" });
    target.replaceChildren(canvas);
    return canvas;
  }
  function renderBar(papers) {
    const target = $("aro-sector-chart");
    const stats = core.sectorStats(papers, weights);
    if (!papers.length) return emptyChart(target, "No papers match these filters.");
    const canvas = chartCanvas(target, "Mean 0 to 6 paper score by observed team sector");
    const colors = ["aro-industry", "aro-university", "aro-research", "aro-joint"];
    for (let tick = 0; tick <= 6; tick += 2) {
      const y = 220 - tick / 6 * 175;
      canvas.appendChild(svg("line", { x1: 42, y1: y, x2: 548, y2: y, class: tick ? "aro-grid" : "aro-axis" }));
      canvas.appendChild(svg("text", { x: 32, y: y + 4, "text-anchor": "end" }, String(tick)));
    }
    stats.forEach((row, i) => {
      const x = 80 + i * 125, h = (row.mean || 0) / 6 * 175;
      const rect = svg("rect", { x, y: 220 - h, width: 61, height: h, class: colors[i] });
      rect.appendChild(svg("title", {}, `${row.sector}: ${row.mean === null ? "no comparable scores" : row.mean.toFixed(2)}; ${row.scored} scored of ${row.count} tracked`));
      canvas.appendChild(rect);
      canvas.appendChild(svg("text", { x: x + 30, y: 236, "text-anchor": "middle" }, row.sector === "Research Institute" ? "Research inst." : row.sector));
      canvas.appendChild(svg("text", { x: x + 30, y: 253, "text-anchor": "middle" }, `${row.scored}/${row.count}`));
      if (row.mean !== null) canvas.appendChild(svg("text", { x: x + 30, y: 213 - h, "text-anchor": "middle" }, row.mean.toFixed(2)));
    });
    setText("aro-sector-note", "Score labels show scored papers / all tracked papers. Unknown leadership is not attributed to a sector.");
  }
  function trendCoveredYears() {
    const active = filters();
    const venueIds = new Set(catalog.filter(venue => (!active.venue || venue.id === active.venue)
      && (!active.area || venue.area === active.area)).map(venue => venue.id));
    const covered = snapshot.coverage.filter(row => venueIds.has(row.venue_id) && !row.stale
      && !["source-error", "error", "unresolved", "not-held", "not-yet-published", "unmapped", "no-index-records"].includes(row.status)
      && (row.ai_scan_status === "complete" || row.ai_scan_status === "partial" && row.sampled_papers > 0
        || !row.ai_scan_status && ["sample", "source-scan"].includes(row.status) && row.included > 0));
    return new Set(covered.map(row => row.year));
  }
  function trendTicks(range, mode) {
    if (mode === "share") return [0, 25, 50, 75, 100];
    if (range[0] === range[1]) return mode === "growth" ? [-1, 0, 1] : [0, 1];
    const target = (range[1] - range[0]) / 4;
    const base = 10 ** Math.floor(Math.log10(target));
    const steps = [1, 2, 2.5, 5, 10].map(multiplier => multiplier * base);
    const closest = steps.reduce((best, step) => Math.abs(step - target) < Math.abs(best - target) ? step : best);
    const step = mode === "count" ? Math.max(1, closest) : closest;
    const start = Math.floor(range[0] / step) * step;
    const end = Math.ceil(range[1] / step) * step;
    return Array.from({ length: Math.round((end - start) / step) + 1 }, (_, index) => Number((start + index * step).toPrecision(12)));
  }
  function renderTrend(papers, selectedYear) {
    const target = $("aro-trend-chart"), mode = $("aro-trend-mode").value;
    if (!papers.length) return emptyChart(target, "No papers match these filters.");
    const endYear = Math.max(2020, ...snapshot.coverage.map(row => row.year));
    const coveredYears = trendCoveredYears();
    const data = core.trend(papers, weights, mode, endYear, coveredYears);
    const counts = mode === "count" ? data : core.trend(papers, weights, "count", endYear, coveredYears);
    const lines = ["Industry", "University", "Research Institute"];
    if (!data.some(row => lines.some(sector => Number.isFinite(row[sector])))) {
      return emptyChart(target, "No sector-classified tracked papers with source coverage for these filters.");
    }
    const ticks = trendTicks(core.trendRange(data, mode), mode);
    const min = ticks[0], max = ticks.at(-1);
    const compact = target.clientWidth < 520;
    const viewWidth = compact ? 400 : 620;
    const plotLeft = compact ? 65 : 82, plotRight = compact ? 380 : 600;
    const axisLeft = compact ? 55 : 72, axisRight = compact ? 390 : 607;
    const canvas = svg("svg", { viewBox: `0 0 ${viewWidth} 270`, role: "img",
      "aria-label": "Annual tracked AI sample by first-author sector; gaps mark missing source coverage",
      preserveAspectRatio: "xMidYMid meet" });
    target.replaceChildren(canvas);
    const yearX = index => plotLeft + index * (plotRight - plotLeft) / Math.max(1, data.length - 1);
    const valueY = value => 220 - (value - min) / (max - min) * 176;
    const activeIndex = data.findIndex(row => String(row.year) === selectedYear);
    if (activeIndex >= 0) {
      const x = yearX(activeIndex);
      canvas.appendChild(svg("line", { x1: x, x2: x, y1: 36, y2: 220, class: "aro-trend-highlight" }));
    }
    milestones.filter(([, events]) => events.length).forEach(([year, events]) => {
      const index = data.findIndex(d => d.year === Number(year));
      if (index < 0) return;
      const x = yearX(index);
      const mark = svg("line", { x1: x, x2: x, y1: 36, y2: 220, stroke: "var(--aro-industry)", "stroke-width": 1, "stroke-dasharray": "3 5", opacity: .42 });
      mark.appendChild(svg("title", {}, `${year}: ${events.map(event => event[0]).join(", ")}; contextual releases, not causes`));
      canvas.appendChild(mark);
    });
    ticks.forEach((value, index) => {
      const y = valueY(value);
      canvas.appendChild(svg("line", { x1: axisLeft, y1: y, x2: axisRight, y2: y, class: index ? "aro-grid" : "aro-axis" }));
      canvas.appendChild(svg("text", { x: compact ? 48 : 64, y: y + 4, "text-anchor": "end" }, `${number(value)}${mode === "count" ? "" : "%"}`));
    });
    if (mode === "growth" && min < 0 && max > 0) {
      const zero = svg("line", { x1: axisLeft, y1: valueY(0), x2: axisRight, y2: valueY(0), class: "aro-trend-zero" });
      zero.appendChild(svg("title", {}, "0% year-over-year growth"));
      canvas.appendChild(zero);
    }
    data.forEach((d, i) => canvas.appendChild(svg("text", { x: yearX(i), y: 243, "text-anchor": "middle",
      class: i === activeIndex ? "aro-year-selected" : "" }, String(d.year))));
    lines.forEach((sector, s) => {
      const color = ["aro-industry", "aro-university", "aro-research"][s];
      for (const segment of core.lineSegments(data, sector)) {
        if (segment.length < 2) continue;
        const points = segment.map(row => `${yearX(data.indexOf(row))},${valueY(row[sector])}`).join(" ");
        canvas.appendChild(svg("polyline", { points, fill: "none", "stroke-width": 1.6, class: color }));
      }
      data.forEach((d, i) => {
        if (!Number.isFinite(d[sector])) return;
        const rawCount = counts[i][sector], denominator = counts[i].classifiedCount;
        const measure = mode === "count" ? `${number(d[sector])} tracked classified AI papers`
          : `${number(d[sector])}% ${mode === "share" ? "publication share" : "year-over-year growth"}`;
        const previous = mode === "growth" ? `; previous year ${data[i - 1].year} ${sector}: ${counts[i - 1][sector]} papers` : "";
        const dot = svg("circle", { cx: yearX(i), cy: valueY(d[sector]), r: i === activeIndex ? 2.8 : 2.2, class: color });
        dot.appendChild(svg("title", {}, `${d.year} ${sector}: ${measure}; raw count ${rawCount} of ${denominator} sector-classified tracked AI papers${previous}`));
        canvas.appendChild(dot);
      });
    });
    target.scrollLeft = activeIndex < 0 ? 0
      : Math.max(0, yearX(activeIndex) * canvas.getBoundingClientRect().width / viewWidth - target.clientWidth / 2);
  }
  function renderMap(papers) {
    const target = $("aro-map"), list = $("aro-map-list"), countries = core.geography(papers);
    target.replaceChildren(); list.replaceChildren(); $("aro-institution-list").replaceChildren();
    if (!countries.length) list.appendChild(node("p", "No first-author countries in this selection.", "aro-footnote"));
    const max = countries[0]?.count || 1;
    for (const { code, count } of countries) {
      const row = node("button"); row.type = "button";
      row.append(node("span", countryName(code)), node("b", number(count)));
      row.title = `Filter papers with first-author affiliation in ${countryName(code)}`;
      row.addEventListener("click", () => { $("aro-country").value = code; page = 0; render(); });
      list.appendChild(row);
      if (!coords[code]) continue;
      const bySector = new Map(["Industry", "University", "Research Institute"].map(sector => [sector, 0]));
      for (const paper of papers) if ((paper.countries || []).includes(code) && bySector.has(paper.first_author_sector)) {
        bySector.set(paper.first_author_sector, bySector.get(paper.first_author_sector) + 1 / new Set(paper.countries).size);
      }
      const ordered = [...bySector].sort((a, b) => b[1] - a[1]);
      const leading = ordered[0][1] > ordered[1][1] ? ordered[0][0] : null;
      const dotClass = leading === "Industry" ? "industry" : leading === "University" ? "university" : leading ? "research" : "neutral";
      const [lon, lat] = coords[code], dot = node("button", "", `aro-map-dot ${dotClass}`);
      dot.type = "button"; dot.style.left = `${(lon + 180) / 360 * 100}%`; dot.style.top = `${(85 - lat) / 145 * 100}%`;
      const size = 8 + 21 * Math.sqrt(count / max); dot.style.width = `${size}px`; dot.style.height = `${size}px`;
      dot.title = `${countryName(code)}: ${number(count)} fractional papers${leading ? `; ${leading} is the most frequent classified first-author sector` : "; no unique classified-sector leader"}`; dot.setAttribute("aria-label", dot.title);
      dot.addEventListener("click", () => { $("aro-country").value = code; page = 0; render(); }); target.appendChild(dot);
    }
    const institutionCounts = new Map();
    for (const paper of papers) for (const name of new Set(paper.all_institutions || [])) institutionCounts.set(name, (institutionCounts.get(name) || 0) + 1);
    const institutions = [...institutionCounts].sort((a, b) => b[1] - a[1]).slice(0, 12), institutionList = $("aro-institution-list");
    institutionList.replaceChildren();
    for (const [name, count] of institutions) {
      const button = node("button", `${name} · ${count}`); button.type = "button";
      button.title = `Search papers linked to ${name}`;
      button.addEventListener("click", () => { $("aro-search").value = name; page = 0; render(); document.getElementById("aro-papers-title").scrollIntoView({ behavior: "smooth" }); });
      institutionList.appendChild(button);
    }
  }
  function renderMilestones() {
    const target = $("aro-milestone-list");
    for (const [year, events] of milestones) {
      const item = node("div", null, "aro-milestone"); item.appendChild(node("strong", year));
      for (const [title, url] of events) { const link = node("a", title + " ↗"); link.href = url; link.target = "_blank"; link.rel = "noopener noreferrer"; item.appendChild(link); }
      if (!events.length) item.appendChild(node("span", "Research watch"));
      target.appendChild(item);
    }
  }
  function sortedPapers(papers) {
    const sort = $("aro-sort").value;
    return [...papers].sort((a, b) => sort === "citations" ? (b.citations ?? -1) - (a.citations ?? -1)
      : sort === "newest" ? (b.year - a.year || String(b.date).localeCompare(String(a.date)))
      : sort === "title" ? a.title.localeCompare(b.title)
      : (core.score(b, weights).value ?? -1) - (core.score(a, weights).value ?? -1) || (b.citations ?? -1) - (a.citations ?? -1));
  }
  function renderTable(papers) {
    const tbody = $("aro-table-body"); tbody.replaceChildren();
    const ordered = sortedPapers(papers), maxPage = Math.max(0, Math.ceil(ordered.length / pageSize) - 1);
    page = Math.min(page, maxPage);
    for (const paper of ordered.slice(page * pageSize, (page + 1) * pageSize)) {
      const row = node("tr"), titleCell = node("td"), button = node("button", paper.title);
      const scored = core.score(paper, weights);
      button.type = "button"; button.addEventListener("click", () => openDetail(paper));
      titleCell.append(button, node("small", `${paper.first_author} · ${(paper.first_author_affiliations || []).join("; ") || "Affiliation unknown"}`));
      row.append(titleCell, node("td", `${paper.venue} · ${paper.year}`), node("td", paper.first_author_sector),
        node("td", (paper.countries || []).join(", ") || "—"), node("td", paper.team_sector), node("td", paper.leadership),
        node("td", paper.github?.stars == null ? (paper.repository_url ? "Linked · stars unknown" : "Unknown") : number(paper.github.stars)),
        node("td", paper.adoption_status || "Unknown"), node("td", paper.maintenance_status && paper.maintenance_status !== "Unknown"
          ? (core.score(paper, { maintenance: 1 }).components.maintenance === undefined ? "Review due" : paper.maintenance_status) : "Unknown"),
        node("td", paper.citations == null ? "Unknown" : number(paper.citations)),
        node("td", scored.value === null ? "—" : `${scored.value.toFixed(2)} · ${Math.round(scored.coverage * 100)}%`));
      tbody.appendChild(row);
    }
    if (!ordered.length) { const row = node("tr"), cell = node("td", "No papers match these filters."); cell.colSpan = 11; row.appendChild(cell); tbody.appendChild(row); }
    setText("aro-page-status", `${ordered.length ? page * pageSize + 1 : 0}–${Math.min(ordered.length, (page + 1) * pageSize)} of ${ordered.length}`);
    $("aro-prev").disabled = page === 0; $("aro-next").disabled = page >= maxPage;
  }
  function detailRow(dl, label, value) {
    dl.append(node("dt", label), node("dd", value === null || value === undefined || value === "" ? "Unknown / not reviewed" : value));
  }
  function openDetail(paper) {
    const body = $("aro-detail-content"), result = core.score(paper, weights);
    body.replaceChildren(node("div", `${paper.venue} · ${paper.year}`, "aro-eyebrow"), node("h2", paper.title));
    const url = node("a", "Open original paper ↗"); url.href = safeHref(paper.url || paper.id, safeHref(paper.id)); url.target = "_blank"; url.rel = "noopener noreferrer"; body.appendChild(url);
    const dl = node("dl");
    detailRow(dl, "First author", paper.first_author); detailRow(dl, "Affiliation", (paper.first_author_affiliations || []).join("; "));
    detailRow(dl, "First-author sector", paper.first_author_sector); detailRow(dl, "Team affiliations", paper.team_sector);
    detailRow(dl, "Leadership", paper.leadership); detailRow(dl, "Corresponding", (paper.corresponding_authors || []).map(a => a.name).join(", "));
    detailRow(dl, "Senior author", paper.senior_author); detailRow(dl, "Countries", (paper.countries || []).map(countryName).join(", "));
    detailRow(dl, "Senior affiliation", (paper.senior_author_affiliations || []).join("; "));
    detailRow(dl, "Citations", paper.citations == null ? null : number(paper.citations)); detailRow(dl, "Citation percentile", paper.citation_percentile == null ? null : paper.citation_percentile.toFixed(3));
    detailRow(dl, "Venue ranking", `${paper.ranking.ranking_scheme} ${paper.ranking.edition} ${paper.ranking.rank}`);
    detailRow(dl, "Award", paper.award === null ? null : paper.award ? "Verified award" : "Reviewed: no award");
    detailRow(dl, "Public code", paper.code_available == null ? null : paper.code_available ? "Linked in proceedings or reviewed" : "Reviewed: unavailable");
    detailRow(dl, "GitHub repository", paper.repository_url ? paper.repository_url.replace("https://github.com/", "") : null);
    detailRow(dl, "GitHub stars", paper.github?.stars == null ? null : `${number(paper.github.stars)} · checked ${paper.github.checked_at.slice(0, 10)}`);
    detailRow(dl, "Latest repo push", paper.github?.pushed_at ? `${paper.github.pushed_at.slice(0, 10)}${paper.github.archived ? " · archived" : ""}` : null);
    detailRow(dl, "Use / adoption", paper.adoption_status === "Unknown" || !paper.adoption_status ? null : paper.adoption_status);
    detailRow(dl, "Maintenance review", paper.maintenance_status === "Unknown" || !paper.maintenance_status ? null : `${paper.maintenance_status} · as of ${paper.review?.date || "unknown"}${core.score(paper, { maintenance: 1 }).components.maintenance === undefined ? " · review due" : ""}`);
    detailRow(dl, "Compute/resources", paper.resources); detailRow(dl, "Funding", paper.funding);
    for (const [key, label] of [["gpu_type", "GPU type"], ["gpu_count", "GPU count"], ["gpu_hours", "GPU-hours"],
      ["accelerator_type", "Accelerator"], ["training_flops", "Training FLOPs"], ["model_parameters", "Model parameters"], ["training_cost", "Training cost"]]) {
      detailRow(dl, label, paper.compute?.[key]);
    }
    detailRow(dl, "Score", result.value === null ? "Insufficient component coverage" : `${result.value.toFixed(2)} / 6`);
    detailRow(dl, "Score availability", `${Math.round(result.coverage * 100)}% of selected weight; ${Object.keys(result.components).join(", ") || "none"}`);
    detailRow(dl, "Topic rule", paper.topic_rule); detailRow(dl, "Metadata sources", (paper.sources || [{ provider: paper.source }]).map(s => s.provider).join(" + "));
    body.appendChild(dl);
    if (paper.abstract) { body.append(node("h3", "Abstract"), node("p", paper.abstract)); }
    const links = node("p");
    for (const [label, href] of [["Proceedings", paper.proceedings_url], ["OpenAlex metadata", String(paper.id).startsWith("https://openalex.org/") ? paper.id : null],
      ["Code", paper.code_url], ["Repository", paper.repository_url], ["Code association evidence", paper.repository_evidence_url || paper.code_evidence_url],
      ["Adoption evidence", paper.adoption_evidence_url], ["Maintenance evidence", paper.maintenance_evidence_url],
      ["Rank evidence", paper.ranking.rank_url], ["Review evidence", paper.review?.evidence_url]]) {
      if (!href) continue; const link = node("a", label + " ↗"); link.href = safeHref(href); link.target = "_blank"; link.rel = "noopener noreferrer"; links.append(link, node("span", "  ·  "));
    }
    body.appendChild(links); $("aro-detail").showModal();
  }
  function renderCoverage() {
    const target = $("aro-coverage"); target.replaceChildren();
    const cells = new Map(snapshot.coverage.map(item => [`${item.venue_id}:${item.year}`, item]));
    const yearFilter = Number($("aro-coverage-year").value);
    const years = yearFilter ? [yearFilter] : Array.from({ length: new Date().getFullYear() - 2019 }, (_, index) => 2020 + index);
    for (const venue of coverageVenues()) for (const year of years) {
      const item = cells.get(`${venue.id}:${year}`);
      const row = node("div", null, "aro-coverage-row");
      const parts = [];
      if (!item) parts.push("not yet available in the published snapshot");
      else {
        parts.push(item.status || "unresolved");
        if (item.stale) parts.push("stale; last successful check " + (item.last_successful_checked_at?.slice(0, 10) || "unknown"));
        if (item.partial) parts.push("partial coverage");
        if (Number.isFinite(item.main_track_total)) parts.push(`${item.status === "verified" && !item.stale ? "verified" : "last known"} main-track: ${number(item.main_track_total)}`);
        if (Number.isFinite(item.bibliography_total)) parts.push(`bibliography: ${number(item.bibliography_total)} indexed records${item.stale ? " (last known)" : ""}`);
        if (Number.isFinite(item.ai_matched_count)) parts.push(`observed AI matches: ${number(item.ai_matched_count)} / ${Number.isFinite(item.scanned_count) ? number(item.scanned_count) : "unknown"} scanned eligible records${item.ai_scan_status && item.ai_scan_status !== "complete" ? ` (${item.ai_scan_status})` : ""}${item.stale ? " (last known)" : ""}`);
        if (Number.isFinite(item.ai_unresolved_count)) parts.push(`${number(item.ai_unresolved_count)} AI decisions unresolved`);
        if (Number.isFinite(item.sampled_papers)) parts.push(`${number(item.sampled_papers)} sampled AI papers`);
        if (Number.isFinite(item.source_total)) parts.push(`OpenAlex: ${number(item.source_total)} indexed matches, not a proceedings census`);
        if (Number.isFinite(item.scanned)) parts.push(`${number(item.scanned)} OpenAlex sampled records (legacy sample, not AI scan)`);
        if (Number.isFinite(item.official_total)) parts.push(`${item.official_provider || "publisher"} index: ${number(item.official_total)} records, not verified main-track`);
        if (Number.isFinite(item.official_sampled)) parts.push(`${number(item.official_sampled)} publisher sampled records (legacy sample, not AI scan)`);
        if (item.track_scope) parts.push(`track: ${item.track_scope}`);
        if (item.gap_reason || item.error) parts.push(item.gap_reason || item.error);
        if (item.checked_at) parts.push(`checked ${item.checked_at.slice(0, 10)}`);
      }
      const detail = node("span", parts.join(" · "), item?.status === "source-error" || item?.status === "error" ? "aro-error" : "");
      for (const url of [...new Set([...(item?.source_urls || []), item?.source_url, item?.official_url, item?.source_id].filter(Boolean))]) {
        const link = node("a", "Source ↗"); link.href = safeHref(url); link.target = "_blank"; link.rel = "noopener noreferrer";
        link.setAttribute("aria-label", `Source for ${venue.name} ${year}`);
        detail.append(node("span", " · "), link);
      }
      row.append(node("span", venue.name), node("span", year), detail);
      target.appendChild(row);
    }
  }
  function coverageVenues() {
    const venue = $("aro-coverage-venue").value, area = $("aro-coverage-area").value, rank = $("aro-coverage-rank").value;
    return catalog.filter(item => (!venue || item.id === venue) && (!area || item.area === area) &&
      (!rank || (rank === "unranked" ? !Object.keys(item.rankings || {}).length : Object.values(item.rankings || {}).includes(rank))));
  }
  function renderRankedVenues() {
    const target = $("aro-ranked-venues"); target.replaceChildren();
    const years = $("aro-coverage-year").value ? [Number($("aro-coverage-year").value)] : Array.from({ length: new Date().getFullYear() - 2019 }, (_, index) => 2020 + index);
    for (const venue of coverageVenues()) {
      const row = node("div", null, "aro-venue-row");
      row.append(node("strong", venue.name), node("span", venue.area));
      const ranks = node("span");
      for (const scheme of ["CORE", "CCF", "TH-CPL"]) {
        if (!venue.rankings?.[scheme]) continue;
        const link = node("a", `${scheme} ${venue.rankings[scheme]}`);
        link.href = safeHref(venue.ranking_urls[scheme]); link.target = "_blank"; link.rel = "noopener noreferrer";
        ranks.append(link, document.createTextNode(" "));
      }
      row.append(ranks);
      const cells = years.map(year => snapshot.coverage.find(item => item.venue_id === venue.id && item.year === year));
      const verified = cells.filter(item => item?.status === "verified" && !item.stale && Number.isFinite(item.main_track_total)).length;
      const bibliography = cells.filter(item => item && !item.stale && Number.isFinite(item.bibliography_total) && !(item.status === "verified" && Number.isFinite(item.main_track_total))).length;
      const legacy = cells.filter(item => item && !item.stale && !Number.isFinite(item.main_track_total) &&
        !Number.isFinite(item.bibliography_total) && (item.source_total > 0 || item.official_total > 0)).length;
      row.append(node("span", `${verified} verified · ${bibliography} bibliography · ${legacy} legacy index · ${cells.length - verified - bibliography - legacy} gaps`)); target.append(row);
    }
  }
  function exportPapers(format) {
    const papers = sortedPapers(selected()).map(p => {
      const scored = core.score(p, weights);
      return { ...p, github_stars: p.github?.stars ?? null, github_checked_at: p.github?.checked_at ?? null,
        github_pushed_at: p.github?.pushed_at ?? null, current_score: scored.value, score_coverage: scored.coverage };
    });
    const fields = ["id", "doi", "title", "year", "venue", "area", "first_author", "first_author_sector", "team_sector", "leadership", "countries", "citations", "citation_percentile", "code_url", "repository_url", "github_stars", "github_checked_at", "github_pushed_at", "adoption_status", "adoption_evidence_url", "maintenance_status", "maintenance_evidence_url", "current_score", "score_coverage", "url"];
    const csvCell = value => `"${String(Array.isArray(value) ? value.join("; ") : value ?? "").replaceAll('"', '""')}"`;
    const content = format === "json" ? JSON.stringify({ exported_at: new Date().toISOString(), scope: snapshot.scope, papers }, null, 2)
      : [fields.join(","), ...papers.map(p => fields.map(key => csvCell(p[key])).join(","))].join("\r\n");
    const blob = new Blob([content], { type: format === "json" ? "application/json" : "text/csv;charset=utf-8" });
    const anchor = node("a"); anchor.href = URL.createObjectURL(blob); anchor.download = `ai-research-observatory.${format}`; anchor.click();
    setTimeout(() => URL.revokeObjectURL(anchor.href), 1000);
  }
  function render() {
    if (!snapshot) return;
    const papers = selected();
    const active = filters();
    const trendPapers = core.filterPapers(snapshot.papers, { ...active, year: "" });
    renderStats(papers); renderBar(papers); renderTrend(trendPapers, active.year); renderMap(papers); renderTable(papers);
  }
  function bind() {
    for (const id of ["aro-year", "aro-area", "aro-venue", "aro-sector", "aro-country", "aro-trend-mode", "aro-sort"]) $(id).addEventListener("change", () => { page = 0; render(); });
    $("aro-search").addEventListener("input", () => { page = 0; render(); });
    $("aro-reset").addEventListener("click", () => { for (const id of ["aro-year", "aro-area", "aro-venue", "aro-sector", "aro-country", "aro-search"]) $(id).value = ""; page = 0; render(); });
    $("aro-prev").addEventListener("click", () => { page--; renderTable(selected()); });
    $("aro-next").addEventListener("click", () => { page++; renderTable(selected()); });
    for (const key of Object.keys(weights)) $("aro-w-" + key).addEventListener("input", event => {
      weights[key] = Number(event.target.value); event.target.nextElementSibling.value = weights[key] + "%"; render();
    });
    $("aro-export-csv").addEventListener("click", () => exportPapers("csv"));
    $("aro-export-json").addEventListener("click", () => exportPapers("json"));
    $("aro-detail-close").addEventListener("click", () => $("aro-detail").close());
    $("aro-detail").addEventListener("click", event => { if (event.target === $("aro-detail")) $("aro-detail").close(); });
    for (const id of ["aro-coverage-venue", "aro-coverage-area", "aro-coverage-rank", "aro-coverage-year"]) {
      $(id).addEventListener("change", () => { renderCoverage(); renderRankedVenues(); });
    }
  }
  async function init() {
    bind(); renderMilestones();
    try {
      const response = await fetch($("observatory").dataset.snapshot);
      if (!response.ok) throw new Error(`Snapshot HTTP ${response.status}`);
      snapshot = await response.json();
      if (!Array.isArray(snapshot.papers) || !Array.isArray(snapshot.coverage)) throw new Error("Invalid snapshot schema");
      catalog = JSON.parse($("ai-research-catalog-data").textContent);
      if (!Array.isArray(catalog)) throw new Error("Invalid venue catalog");
      selectOptions("aro-year", [...new Set(snapshot.papers.map(p => p.year))].sort());
      selectOptions("aro-area", [...new Set([...catalog.map(v => v.area), ...snapshot.papers.map(p => p.area)])].sort());
      selectOptions("aro-venue", catalog.map(v => v.id), id => catalog.find(v => v.id === id).name);
      selectOptions("aro-country", [...new Set(snapshot.papers.flatMap(p => p.countries || []))].sort(), countryName);
      selectOptions("aro-coverage-venue", catalog.map(v => v.id), id => catalog.find(v => v.id === id).name);
      selectOptions("aro-coverage-area", [...new Set(catalog.map(v => v.area))].sort());
      selectOptions("aro-coverage-year", Array.from({ length: new Date().getFullYear() - 2019 }, (_, index) => 2020 + index));
      renderCoverage(); renderRankedVenues(); render();
      const verified = snapshot.coverage.filter(c => c.status === "verified" && !c.stale && Number.isFinite(c.main_track_total)).length,
        errors = snapshot.coverage.filter(c => ["source-error", "error"].includes(c.status) || c.official_status === "error").length,
        bibliography = snapshot.coverage.filter(c => Number.isFinite(c.bibliography_total) && !c.stale && c.status !== "verified").length,
        legacy = snapshot.coverage.filter(c => !c.stale && !Number.isFinite(c.main_track_total) && !Number.isFinite(c.bibliography_total) && (c.source_total > 0 || c.official_total > 0)).length,
        gaps = catalog.length * (new Date().getFullYear() - 2019) - verified - bibliography - legacy,
        linkedRepos = new Set(snapshot.papers.map(p => p.repository_url).filter(Boolean)),
        checkedRepos = new Set(snapshot.papers.filter(p => p.github).map(p => p.repository_url));
      setText("aro-status", `Updated ${snapshot.generated_at.slice(0, 10)} · ${catalog.length} ranked series including ${catalog.filter(v => v.source_rule_id).length} new cross-area series · ${number(snapshot.papers.length)} tracked AI records · ${verified} verified main-track venue-years · ${bibliography} bibliography-only years · ${legacy} legacy index years · ${gaps} gaps · ${checkedRepos.size}/${linkedRepos.size} GitHub links checked · ${errors} source errors`);
    } catch (error) {
      setText("aro-status", `Could not load the real publication snapshot: ${error.message}. No demo records are substituted.`);
      emptyChart($("aro-sector-chart"), "Publication data unavailable.");
      emptyChart($("aro-trend-chart"), "Publication data unavailable.");
      $("aro-table-body").appendChild(node("tr")).appendChild(node("td", "Publication data unavailable."));
    }
  }
  init();
})();
