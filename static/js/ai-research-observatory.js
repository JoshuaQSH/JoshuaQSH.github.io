(function () {
  "use strict";
  const core = window.AIResearchCore;
  const $ = id => document.getElementById(id);
  const number = n => new Intl.NumberFormat("en-GB", { maximumFractionDigits: 1 }).format(n);
  const countryName = code => { try { return new Intl.DisplayNames(["en"], { type: "region" }).of(code); } catch (_) { return code; } };
  const weights = { citation: 55, venue: 25, award: 15, code: 5 };
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
  let snapshot = null, page = 0;
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
    const counts = new Map();
    for (const p of papers) counts.set(p.year, (counts.get(p.year) || 0) + 1);
    const years = [...counts.keys()].sort((a, b) => a - b);
    const latest = years.at(-1), previous = years.at(-2);
    setText("aro-year-change", previous && counts.get(previous) ? `${Math.round(100 * (counts.get(latest) / counts.get(previous) - 1))}%` : "—");
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
  function renderTrend(papers) {
    const target = $("aro-trend-chart"), mode = $("aro-trend-mode").value;
    if (!papers.length) return emptyChart(target, "No papers match these filters.");
    const data = core.trend(papers, weights, mode, Math.max(...snapshot.coverage.map(c => c.year))), lines = ["Industry", "University", "Research Institute"];
    const maxValue = mode === "count" ? Math.max(1, ...data.flatMap(x => lines.map(s => x[s]))) : 100;
    const canvas = chartCanvas(target, "Annual tracked sample by first-author sector; gaps in source coverage make trends incomplete");
    const yearX = index => 58 + index * 480 / Math.max(1, data.length - 1);
    milestones.filter(([, events]) => events.length).forEach(([year, events]) => {
      const index = data.findIndex(d => d.year === Number(year));
      if (index < 0) return;
      const x = yearX(index);
      const mark = svg("line", { x1: x, x2: x, y1: 27, y2: 220, stroke: "var(--aro-industry)", "stroke-width": 1, "stroke-dasharray": "3 5", opacity: .42 });
      mark.appendChild(svg("title", {}, `${year}: ${events.map(event => event[0]).join(", ")}; contextual releases, not causes`));
      canvas.appendChild(mark);
    });
    for (let tick = 0; tick <= 4; tick++) {
      const y = 220 - tick * 44;
      canvas.appendChild(svg("line", { x1: 46, y1: y, x2: 545, y2: y, class: tick ? "aro-grid" : "aro-axis" }));
      canvas.appendChild(svg("text", { x: 38, y: y + 4, "text-anchor": "end" }, mode === "count" ? String(Math.round(maxValue * tick / 4)) : `${25 * tick}%`));
    }
    data.forEach((d, i) => canvas.appendChild(svg("text", { x: yearX(i), y: 243, "text-anchor": "middle" }, String(d.year))));
    lines.forEach((sector, s) => {
      const points = data.map((d, i) => `${yearX(i)},${220 - d[sector] / maxValue * 176}`).join(" ");
      canvas.appendChild(svg("polyline", { points, fill: "none", "stroke-width": 2.6, class: ["aro-industry", "aro-university", "aro-research"][s] }));
      data.forEach((d, i) => {
        const dot = svg("circle", { cx: yearX(i), cy: 220 - d[sector] / maxValue * 176, r: 3.5, class: ["aro-industry", "aro-university", "aro-research"][s] });
        dot.appendChild(svg("title", {}, `${d.year} ${sector}: ${number(d[sector])}${mode === "count" ? " tracked papers" : "%"}`));
        canvas.appendChild(dot);
      });
    });
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
    return [...papers].sort((a, b) => sort === "citations" ? b.citations - a.citations
      : sort === "newest" ? (b.year - a.year || String(b.date).localeCompare(String(a.date)))
      : sort === "title" ? a.title.localeCompare(b.title)
      : (core.score(b, weights).value ?? -1) - (core.score(a, weights).value ?? -1) || b.citations - a.citations);
  }
  function renderTable(papers) {
    const tbody = $("aro-table-body"); tbody.replaceChildren();
    const ordered = sortedPapers(papers), maxPage = Math.max(0, Math.ceil(ordered.length / pageSize) - 1);
    page = Math.min(page, maxPage);
    for (const paper of ordered.slice(page * pageSize, (page + 1) * pageSize)) {
      const row = node("tr"), titleCell = node("td"), button = node("button", paper.title);
      button.type = "button"; button.addEventListener("click", () => openDetail(paper));
      titleCell.append(button, node("small", `${paper.first_author} · ${(paper.first_author_affiliations || []).join("; ") || "Affiliation unknown"}`));
      row.append(titleCell, node("td", `${paper.venue} · ${paper.year}`), node("td", paper.first_author_sector),
        node("td", (paper.countries || []).join(", ") || "—"), node("td", paper.team_sector), node("td", paper.leadership),
        node("td", paper.compute_evidence || paper.resources || Object.values(paper.compute || {}).some(value => value !== null && value !== undefined && value !== "") ? "Reviewed" : "Unknown"),
        node("td", number(paper.citations)), node("td", core.score(paper, weights).value?.toFixed(2) ?? "—"));
      tbody.appendChild(row);
    }
    if (!ordered.length) { const row = node("tr"), cell = node("td", "No papers match these filters."); cell.colSpan = 9; row.appendChild(cell); tbody.appendChild(row); }
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
    detailRow(dl, "Citations", number(paper.citations)); detailRow(dl, "Citation percentile", paper.citation_percentile === null ? null : paper.citation_percentile.toFixed(3));
    detailRow(dl, "Venue ranking", `${paper.ranking.ranking_scheme} ${paper.ranking.edition} ${paper.ranking.rank}`);
    detailRow(dl, "Award", paper.award === null ? null : paper.award ? "Verified award" : "Reviewed: no award");
    detailRow(dl, "Public code", paper.code_available === null ? null : paper.code_available ? "Verified public code" : "Reviewed: unavailable");
    detailRow(dl, "Compute/resources", paper.resources); detailRow(dl, "Funding", paper.funding);
    for (const [key, label] of [["gpu_type", "GPU type"], ["gpu_count", "GPU count"], ["gpu_hours", "GPU-hours"],
      ["accelerator_type", "Accelerator"], ["training_flops", "Training FLOPs"], ["model_parameters", "Model parameters"], ["training_cost", "Training cost"]]) {
      detailRow(dl, label, paper.compute?.[key]);
    }
    detailRow(dl, "Score", result.value === null ? "Insufficient component coverage" : `${result.value.toFixed(2)} / 6`);
    detailRow(dl, "Score availability", `${Math.round(result.coverage * 100)}% of selected weight; ${Object.keys(result.components).join(", ") || "none"}`);
    detailRow(dl, "Topic rule", paper.topic_rule); detailRow(dl, "Metadata source", `${paper.source} · checked ${(paper.checked_at || "").slice(0, 10)}`);
    body.appendChild(dl);
    if (paper.abstract) { body.append(node("h3", "Abstract"), node("p", paper.abstract)); }
    const links = node("p");
    for (const [label, href] of [["OpenAlex metadata", paper.id], ["Rank evidence", paper.ranking.rank_url], ["Review evidence", paper.review?.evidence_url]]) {
      if (!href) continue; const link = node("a", label + " ↗"); link.href = safeHref(href); link.target = "_blank"; link.rel = "noopener noreferrer"; links.append(link, node("span", "  ·  "));
    }
    body.appendChild(links); $("aro-detail").showModal();
  }
  function renderCoverage() {
    const target = $("aro-coverage"); target.replaceChildren();
    for (const item of snapshot.coverage) {
      const row = node("div", null, "aro-coverage-row");
      row.append(node("span", item.venue), node("span", item.year),
        node("span", item.status === "error" ? `Error: ${item.error}` : item.status === "no-source-matches" ? "No matches for this OpenAlex source ID; not zero conference papers" : `${item.scanned} scanned / ${number(item.source_total)} source results; ${item.included} included${item.partial ? " · capped/partial" : " · source scan"}`, item.status === "error" || item.status === "no-source-matches" ? "aro-error" : ""));
      target.appendChild(row);
    }
  }
  function exportPapers(format) {
    const papers = sortedPapers(selected()).map(p => ({ ...p, current_score: core.score(p, weights).value }));
    const fields = ["id", "doi", "title", "year", "venue", "area", "first_author", "first_author_sector", "team_sector", "leadership", "countries", "citations", "citation_percentile", "current_score", "url"];
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
    renderStats(papers); renderBar(papers); renderTrend(papers); renderMap(papers); renderTable(papers);
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
  }
  async function init() {
    bind(); renderMilestones();
    try {
      const response = await fetch($("observatory").dataset.snapshot);
      if (!response.ok) throw new Error(`Snapshot HTTP ${response.status}`);
      snapshot = await response.json();
      if (!Array.isArray(snapshot.papers) || !Array.isArray(snapshot.coverage)) throw new Error("Invalid snapshot schema");
      selectOptions("aro-year", [...new Set(snapshot.papers.map(p => p.year))].sort());
      selectOptions("aro-area", [...new Set(snapshot.papers.map(p => p.area))].sort());
      selectOptions("aro-venue", snapshot.venues.map(v => v.id), id => snapshot.venues.find(v => v.id === id).name);
      selectOptions("aro-country", [...new Set(snapshot.papers.flatMap(p => p.countries || []))].sort(), countryName);
      renderCoverage(); render();
      const partial = snapshot.coverage.filter(c => c.partial && c.scanned).length,
        empty = snapshot.coverage.filter(c => !c.scanned && c.status !== "error").length,
        errors = snapshot.coverage.filter(c => c.status === "error").length;
      setText("aro-status", `OpenAlex snapshot · updated ${snapshot.generated_at.slice(0, 10)} · ${number(snapshot.papers.length)} records · ${partial} capped venue-years · ${empty} empty source matches · ${errors} fetch errors`);
    } catch (error) {
      setText("aro-status", `Could not load the real publication snapshot: ${error.message}. No demo records are substituted.`);
      emptyChart($("aro-sector-chart"), "Publication data unavailable.");
      emptyChart($("aro-trend-chart"), "Publication data unavailable.");
      $("aro-table-body").appendChild(node("tr")).appendChild(node("td", "Publication data unavailable."));
    }
  }
  init();
})();
