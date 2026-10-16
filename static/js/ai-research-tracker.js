(function () {
  "use strict";
  const root = document.querySelector(".research-tracker");
  if (!root) return;
  const ns = "http://www.w3.org/2000/svg";
  const years = Array.from({length: 7}, (_, i) => 2020 + i);
  const topicRules = {
    language: /\b(?:llms?|language models?|transformers?|tokens?|prompts?|retrieval|text generation|instruction tuning)\b/i,
    vision: /\b(?:vision|image|visual|video|segmentation|object detection|3d|diffusion)\b/i,
    systems: /\b(?:gpu|accelerator|kernel|compiler|distributed|inference|serving|memory|parallel)\b/i,
    learning: /\b(?:reinforcement learning|optimization|gradient|self.supervis|representation learning|training)\b/i
  };
  const $ = id => document.getElementById(id);
  const svg = (name, attrs, parent) => {
    const node = document.createElementNS(ns, name);
    for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
    parent.appendChild(node);
    return node;
  };
  const text = (parent, x, y, value, anchor = "middle") => {
    const node = svg("text", {x, y, class: "tick", "text-anchor": anchor}, parent);
    node.textContent = value;
  };
  const empty = node => { while (node.firstChild) node.removeChild(node.firstChild); };
  const fmt = number => number == null ? "—" : new Intl.NumberFormat("en-GB").format(number);
  const catalog = JSON.parse($("ai-research-catalog-data").textContent);
  let trackedCatalog = [];
  let trackedIds = new Set();
  const sourceUrls = row => [...new Set([...(row?.source_urls || []), row?.source_url, row?.official_url, row?.source_id].filter(url => /^https?:\/\//.test(url)))];
  const rowFor = (snapshot, venueId, year) => snapshot.coverage.find(row => row.venue_id === venueId && row.year === year);
  const mainCount = row => row?.status === "verified" && !row.stale && Number.isFinite(row.main_track_total) ? row.main_track_total : null;
  const bibliographyCount = row => row && !row.stale && Number.isFinite(row.bibliography_total) ? row.bibliography_total : null;
  const aiCount = row => row && !row.stale && Number.isFinite(row.ai_matched_count) ? row.ai_matched_count : null;
  const legacyOpenAlexCount = row => row && !row.stale && row.source_total > 0 ? row.source_total : null;
  const legacyPublisherCount = row => row && !row.stale && row.official_total > 0 ? row.official_total : null;
  const legacyCount = row => row && !row.stale && mainCount(row) === null && bibliographyCount(row) === null &&
    (row.source_total > 0 || row.official_total > 0);
  const availability = row => row ? `${legacyCount(row) ? "legacy index only · " : ""}${row.status || "unresolved"}${row.stale ? " · stale" : ""}${row.gap_reason ? ` · ${row.gap_reason}` : ""}` : "not yet available in the published snapshot";
  const xAt = (year, left, width) => left + (year - 2020) * width / (years.length - 1);

  function axes(node, top, bottom, left, right, max, suffix) {
    const width = right - left;
    const height = bottom - top;
    svg("line", {x1:left,y1:bottom,x2:right,y2:bottom,class:"axis"}, node);
    svg("line", {x1:left,y1:top,x2:left,y2:bottom,class:"axis"}, node);
    for (let i = 0; i <= 4; i++) {
      const y = bottom - i * height / 4;
      if (i) svg("line", {x1:left,y1:y,x2:right,y2:y,class:"grid"}, node);
      text(node, left - 9, y + 4, fmt(Math.round(i * max / 4)) + suffix, "end");
    }
    for (const year of years) text(node, xAt(year, left, width), bottom + 20, year);
  }

  function line(node, points, color, className, left, right, top, bottom, max, detail) {
    const pointByYear = new Map(points.map(point => [point.year, point]));
    const yAt = value => bottom - value / max * (bottom - top);
    let previous = null;
    const markers = [];
    for (const year of years) {
      const point = pointByYear.get(year);
      if (!point || point.value == null) { previous = null; continue; }
      const x = xAt(year, left, right - left), y = yAt(point.value);
      if (previous) svg("line", {x1:previous.x,y1:previous.y,x2:x,y2:y,stroke:color,class:`series ${className}`}, node);
      markers.push({x,y,point});
      previous = {x,y};
    }
    for (const {x,y,point} of markers) {
      const marker = svg("circle", {cx:x,cy:y,r:5,fill:color,class:`point ${className}`,tabindex:"0",role:"button","aria-label":point.label}, node);
      marker.addEventListener("click", () => detail(point));
      marker.addEventListener("keydown", event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); detail(point); } });
      svg("title", {}, marker).textContent = point.label;
    }
  }

  const countStatus = {verified:"Verified",partial:"Partial",unverified:"Not reported",pending:"Pending", "not-held":"Not held"};

  function renderCounts(history) {
    const mode = $("research-count-mode").value;
    const metrics = mode === "both" ? ["submitted", "accepted"] : [mode];
    const byId = new Map(history.conferences.map(venue => [venue.id, venue]));
    history.fields.forEach((field, index) => {
      const node = $(`research-field-chart-${index}`), legend = $(`research-field-legend-${index}`);
      empty(node); empty(legend);
      const fieldRows = history.counts.filter(row => field.venues.includes(row.venue));
      const values = fieldRows.flatMap(row => metrics.map(metric => row[metric])).filter(Number.isFinite);
      const largest = Math.max(0, ...values);
      const step = largest > 10000 ? 5000 : largest > 1000 ? 1000 : largest > 100 ? 100 : 25;
      const max = Math.max(step, Math.ceil(largest / step) * step);
      const top = 18, bottom = 267, left = 56, right = 735;
      axes(node, top, bottom, left, right, max, "");
      for (const venueId of field.venues) {
        const venue = byId.get(venueId);
        const key = document.createElement("span");
        const swatch = document.createElement("i"); swatch.className = "research-key"; swatch.style.setProperty("--key-color", venue.color);
        key.append(swatch, document.createTextNode(venue.name)); legend.appendChild(key);
        for (const metric of metrics) {
          const points = fieldRows.filter(row => row.venue === venueId).map(row => ({
            year:row.year,value:row[metric],row,metric,
            label:`${venue.name} ${row.year}: ${fmt(row[metric])} ${metric}. ${row.scope}`
          }));
          line(node, points, venue.color, metric === "accepted" ? "accepted" : "", left,right,top,bottom,max, point => {
            const detail = $(`research-field-detail-${index}`); empty(detail);
            detail.append(document.createTextNode(`${point.label} `));
            const link = document.createElement("a"); link.href = point.row[`${point.metric}_source`];
            link.target = "_blank"; link.rel = "noopener noreferrer"; link.textContent = "Organizer source";
            detail.appendChild(link);
          });
        }
      }
      if (mode === "both") legend.append(document.createTextNode("Solid: submitted · Dashed: accepted"));
      const gaps = years.map(year => {
        const missing = fieldRows.filter(row => row.year === year && metrics.some(metric => row[metric] == null)).length;
        return missing ? `${year}: ${missing}/${field.venues.length}` : "";
      }).filter(Boolean);
      const notHeld = fieldRows.filter(row => row.status === "not-held").map(row => `${byId.get(row.venue).name} ${row.year}`);
      $(`research-field-gaps-${index}`).textContent = gaps.length
        ? `Gaps by year (venues without verified ${mode === "both" ? "figures" : mode}): ${gaps.join(" · ")}. ${notHeld.length ? `Not held: ${notHeld.join(", ")}. ` : ""}Every venue-year is labeled in the source ledger.`
        : "All years have verified figures.";
    });
  }

  function renderLedger(history) {
    const byId = new Map(history.conferences.map(venue => [venue.id, venue]));
    history.fields.forEach((field, index) => {
      const tbody = $(`research-field-rows-${index}`); empty(tbody);
      for (const venueId of field.venues) for (const row of history.counts.filter(item => item.venue === venueId)) {
        const tr = document.createElement("tr");
        for (const value of [byId.get(venueId).name, row.year,
          row.submitted == null ? countStatus[row.status] : fmt(row.submitted),
          row.accepted == null ? countStatus[row.status] : fmt(row.accepted)]) {
          const td = document.createElement("td"); td.textContent = value; tr.appendChild(td);
        }
        const detail = document.createElement("td"); detail.append(document.createTextNode(`${countStatus[row.status]} · ${row.scope}`));
        for (const [metric, source] of [["Submitted",row.submitted_source],["Accepted",row.accepted_source],["Schedule",row.status_source]]) {
          if (!source) continue;
          const link = document.createElement("a"); link.href = source; link.target = "_blank"; link.rel = "noopener noreferrer"; link.textContent = metric;
          detail.append(document.createTextNode(" · "),link);
        }
        tr.appendChild(detail); tbody.appendChild(tr);
      }
    });
  }

  function renderIndex(snapshot) {
    const venue = trackedCatalog.find(v => v.id === $("research-index-venue").value);
    if (!venue) return;
    const chart = $("research-index-chart"); empty(chart);
    const rows = years.map(year => ({year, row: rowFor(snapshot, venue.id, year)}));
    const values = rows.flatMap(({row}) => [mainCount(row), bibliographyCount(row), aiCount(row), legacyOpenAlexCount(row), legacyPublisherCount(row)]).filter(Number.isFinite);
    const max = Math.max(100, Math.ceil(Math.max(0, ...values) / 500) * 500);
    const top = 18, bottom = 267, left = 56, right = 735;
    axes(chart, top, bottom, left, right, max, "");
    for (const [kind, color, label, valueFor] of [
      ["main-track", "#c33e42", "verified main-track papers", mainCount],
      ["ai-matched", "#367580", "observed AI matches", aiCount],
      ["bibliography", "#a86824", "bibliography records (not verified main-track)", row => mainCount(row) === null ? bibliographyCount(row) : null],
      ["legacy-openalex", "#77549b", "OpenAlex source matches (legacy index, not main-track)", legacyOpenAlexCount],
      ["legacy-publisher", "#2d7957", "publisher index entries (legacy index, not main-track)", legacyPublisherCount]
    ]) {
      line(chart, rows.map(({year, row}) => ({year, value:valueFor(row), row,
        label:`${venue.name} ${year}: ${fmt(valueFor(row))} ${label}${kind === "ai-matched" ? ` among ${fmt(row?.scanned_count ?? row?.eligible_count)} scanned eligible records${row?.ai_scan_status === "partial" ? "; partial scan" : ""}` : ""}${row?.track_scope ? `; ${row.track_scope}` : ""}`})), color, kind, left, right, top, bottom, max, point => {
        const detail = $("research-index-detail"); empty(detail);
        detail.append(document.createTextNode(`${point.label}. ${availability(point.row)}. Not an organizer acceptance count. `));
        for (const url of sourceUrls(point.row)) {
          const link = document.createElement("a"); link.href = url; link.target = "_blank"; link.rel = "noopener noreferrer";
          link.textContent = "Inspect source"; link.setAttribute("aria-label", `Inspect ${venue.name} ${point.year} source`);
          detail.append(link, document.createTextNode(" "));
        }
      });
    }
    const verified = rows.filter(({row}) => mainCount(row) !== null).length;
    const fallback = rows.filter(({row}) => mainCount(row) === null && bibliographyCount(row) !== null).length;
    const legacy = rows.filter(({row}) => legacyCount(row)).length;
    const gaps = rows.filter(({row}) => mainCount(row) === null && bibliographyCount(row) === null && !legacyCount(row))
      .map(({year, row}) => `${year} ${availability(row)}`);
    $("research-index-detail").textContent = `${venue.name}: ${verified} verified main-track years; ${fallback} bibliography-only years; ${legacy} legacy index years shown as source matches, not organizer acceptances. ${gaps.length ? `Gaps: ${gaps.join("; ")}.` : "No unresolved calendar gaps."}`;
    const tbody = $("research-index-rows"); empty(tbody);
    for (const {year, row} of rows) {
      const tr = document.createElement("tr");
      for (const value of [year, availability(row), fmt(mainCount(row)), fmt(bibliographyCount(row)),
        aiCount(row) === null ? "—" : `${fmt(aiCount(row))} / ${fmt(row.scanned_count ?? row.eligible_count)} scanned${row.ai_scan_status === "partial" ? " · partial" : ""}`]) {
        const td = document.createElement("td"); td.textContent = value; tr.append(td);
      }
      const source = document.createElement("td"); source.append(document.createTextNode(row?.track_scope || "Track scope unverified"));
      if (Number.isFinite(row?.source_total)) source.append(document.createTextNode(` · OpenAlex source matches: ${fmt(row.source_total)}${row.stale ? " (last known)" : ""}; not verified main-track`));
      if (Number.isFinite(row?.official_total)) source.append(document.createTextNode(` · publisher index entries: ${fmt(row.official_total)}${row.stale ? " (last known)" : ""}; not verified main-track`));
      for (const url of sourceUrls(row)) {
        const link = document.createElement("a"); link.href = url; link.target = "_blank"; link.rel = "noopener noreferrer";
        link.textContent = "Source"; link.setAttribute("aria-label", `Source for ${venue.name} ${year}`);
        source.append(document.createTextNode(" · "), link);
      }
      tr.append(source); tbody.append(tr);
    }
  }

  function renderCatalog(snapshot) {
    const area = $("research-catalog-area").value;
    const rank = $("research-catalog-rank").value;
    const year = Number($("research-catalog-year").value);
    const tbody = $("research-catalog-rows"); empty(tbody);
    for (const venue of trackedCatalog.filter(item => (!area || item.area === area) &&
      (!rank || (rank === "unranked" ? !Object.keys(item.rankings || {}).length : Object.values(item.rankings || {}).includes(rank))))) {
      const tr = document.createElement("tr");
      for (const value of [venue.name, venue.area]) {
        const td = document.createElement("td"); td.textContent = value; tr.append(td);
      }
      for (const scheme of ["CORE", "CCF", "TH-CPL"]) {
        const td = document.createElement("td");
        if (venue.rankings?.[scheme]) {
          const link = document.createElement("a"); link.href = venue.ranking_urls[scheme];
          link.target = "_blank"; link.rel = "noopener noreferrer"; link.textContent = venue.rankings[scheme]; td.append(link);
        } else td.textContent = "—";
        tr.append(td);
      }
      const rows = (year ? [year] : years).map(cellYear => rowFor(snapshot, venue.id, cellYear));
      const verified = rows.filter(row => mainCount(row) !== null).length;
      const fallback = rows.filter(row => mainCount(row) === null && bibliographyCount(row) !== null).length;
      const legacy = rows.filter(legacyCount).length;
      const td = document.createElement("td"); td.textContent = year
        ? legacy ? rows[0].official_total > 0
          ? `publisher index: ${fmt(rows[0].official_total)} entries; not verified main-track`
          : `OpenAlex source: ${fmt(rows[0].source_total)} matches; not verified main-track`
          : availability(rows[0])
        : `${verified} verified · ${fallback} bibliography · ${legacy} legacy index · ${rows.length - verified - fallback - legacy} gaps`;
      td.title = "Verified main-track, bibliography-only, and unresolved calendar years; not organizer acceptances";
      tr.append(td); tbody.append(tr);
    }
  }

  function renderAwards(history) {
    const counts = new Map();
    for (const award of history.awards) for (const topic of award.topics) counts.set(topic, (counts.get(topic) || 0) + 1);
    const cloud = $("research-cloud"), list = $("research-awards"); empty(cloud); empty(list);
    for (const [topic, count] of [...counts].sort((a,b) => b[1] - a[1] || a[0].localeCompare(b[0]))) {
      const term = document.createElement("span"); term.textContent = topic;
      term.style.fontSize = `${Math.min(1.8, 1 + .22 * count)}rem`;
      term.title = `${count} selected award paper${count === 1 ? "" : "s"}`;
      cloud.appendChild(term);
    }
    for (const award of history.awards) {
      const item = document.createElement("div"); item.className = "research-award";
      const meta = document.createElement("p"); meta.textContent = `${award.venue} ${award.year} · ${award.award} · ${award.field}`;
      const link = document.createElement("a"); link.href = award.source; link.target = "_blank"; link.rel = "noopener noreferrer"; link.textContent = award.title;
      const topics = document.createElement("small"); topics.textContent = award.topics.join(" · ");
      item.append(meta,link,topics); list.appendChild(item);
    }
  }

  function renderTopics(snapshot) {
    const node = $("research-topic-chart"); empty(node);
    const rule = topicRules[$("research-topic").value];
    const groups = ["Industry", "University"].map((sector, index) => ({
      sector, color:index ? "#367580" : "#be7b26",
      points: years.map(year => {
        const papers = snapshot.papers.filter(p => trackedIds.has(p.venue_id) && p.year === year && p.first_author_sector === sector);
        const hits = papers.filter(p => rule.test(p.title || "")).length;
        return {year,value:papers.length ? 100 * hits / papers.length : null,hits,total:papers.length,
          label:`${sector} ${year}: ${hits} of ${papers.length} sampled papers (${papers.length ? (100 * hits / papers.length).toFixed(1) : "n/a"}%)`};
      })
    }));
    const observed = groups.flatMap(group => group.points.map(point => point.value)).filter(Number.isFinite);
    const max = Math.max(10, Math.ceil(Math.max(0,...observed) / 10) * 10);
    const top = 18, bottom = 235, left = 56, right = 735;
    axes(node,top,bottom,left,right,max,"%");
    for (const group of groups) line(node,group.points,group.color,"",left,right,top,bottom,max,point => {
      $("research-topic-detail").textContent = point.label;
    });
    const total = snapshot.papers.filter(p => trackedIds.has(p.venue_id)).length;
    $("research-topic-detail").textContent = `${fmt(total)} tracked papers · snapshot ${new Date(snapshot.generated_at).toLocaleDateString("en-GB")} · point labels show each year's denominator`;
  }

  async function load(url) {
    const response = await fetch(url, {cache:"no-cache"});
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }
  Promise.all([load(root.dataset.historyUrl),load(root.dataset.observatoryUrl)]).then(([history,snapshot]) => {
    if (!Array.isArray(history.counts) || !Array.isArray(history.fields) || !Array.isArray(history.awards) || !Array.isArray(snapshot.papers)) throw new Error("Invalid dataset");
    trackedIds = new Set(history.fields.flatMap(field => field.venues));
    trackedCatalog = catalog.filter(venue => trackedIds.has(venue.id));
    for (const venue of trackedCatalog) {
      const option = document.createElement("option"); option.value = venue.id; option.textContent = venue.name;
      $("research-index-venue").append(option);
    }
    $("research-index-venue").value = "neurips";
    for (const area of [...new Set(trackedCatalog.map(venue => venue.area))].sort()) {
      const option = document.createElement("option"); option.value = area; option.textContent = area;
      $("research-catalog-area").append(option);
    }
    for (const year of years) {
      const option = document.createElement("option"); option.value = year; option.textContent = year;
      $("research-catalog-year").append(option);
    }
    renderCounts(history); renderLedger(history); renderIndex(snapshot); renderCatalog(snapshot); renderAwards(history); renderTopics(snapshot);
    $("research-count-mode").addEventListener("change", () => renderCounts(history));
    $("research-index-venue").addEventListener("change", () => renderIndex(snapshot));
    $("research-catalog-area").addEventListener("change", () => renderCatalog(snapshot));
    $("research-catalog-rank").addEventListener("change", () => renderCatalog(snapshot));
    $("research-catalog-year").addEventListener("change", () => renderCatalog(snapshot));
    $("research-topic").addEventListener("change", () => renderTopics(snapshot));
    const coverage = snapshot.coverage.filter(row => trackedIds.has(row.venue_id));
    const verified = coverage.filter(row => mainCount(row) !== null).length;
    const fallback = coverage.filter(row => mainCount(row) === null && bibliographyCount(row) !== null).length;
    $("research-status").textContent = `Organizer figures reviewed ${history.reviewed_at} · sample updated ${new Date(snapshot.generated_at).toLocaleDateString("en-GB")} · ${trackedCatalog.length} selected conferences · ${verified} verified main-track venue-years · ${fallback} bibliography-only venue-years · legacy index matches remain separately labelled`;
  }).catch(() => { $("research-status").textContent = "The research datasets could not be loaded. Please retry later."; });
})();
