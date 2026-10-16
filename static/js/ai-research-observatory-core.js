(function (root) {
  "use strict";
  const COMPONENTS = { citation: "citation_percentile", venue: "prestige", award: "award", code: "code_available" };
  function ageDays(value, now) {
    const date = Date.parse(value);
    return Number.isFinite(date) ? Math.max(0, (now.getTime() - date) / 86400000) : null;
  }
  function evidenceValue(paper, name, now) {
    if (name === "stars" || name === "activity") {
      const repo = paper.github;
      const checkedAge = ageDays(repo?.checked_at, now);
      if (!repo || checkedAge === null || checkedAge > 45 || repo.fork === true) return null;
      if (name === "stars") return Number.isInteger(repo.stars) && repo.stars >= 0
        ? Math.min(1, Math.log1p(repo.stars) / Math.log1p(1000)) : null;
      const pushedAge = ageDays(repo.pushed_at, now);
      return pushedAge === null ? null : repo.archived ? 0 : Math.max(0, Math.min(1, (365 - pushedAge) / 185));
    }
    if (name === "maintenance") return paper.maintenance_evidence_url && ageDays(paper.review?.date, now) !== null
      && ageDays(paper.review.date, now) <= 365
      ? ({ active: 1, inactive: 0 }[paper.maintenance_status] ?? null) : null;
    if (name === "adoption") return paper.adoption_evidence_url
      ? ({ integration: .6, pilot: .35, production: 1 }[paper.adoption_status] ?? null) : null;
    const raw = paper[COMPONENTS[name]];
    return (name === "award" || name === "code") && typeof raw === "boolean" ? Number(raw) : raw;
  }
  function omissionReason(paper, name, now) {
    if (name === "stars" || name === "activity") {
      if (!paper.github) return "No verified GitHub snapshot";
      const checkedAge = ageDays(paper.github.checked_at, now);
      if (checkedAge === null) return "GitHub check date unavailable";
      if (checkedAge > 45) return "GitHub check older than 45 days";
      if (paper.github.fork === true) return "Fork metrics excluded";
      return name === "stars" ? "GitHub stars unavailable" : "Latest repository push unavailable";
    }
    if (name === "maintenance") {
      if (!paper.maintenance_evidence_url) return "Maintenance evidence not reviewed";
      const reviewAge = ageDays(paper.review?.date, now);
      if (reviewAge === null) return "Maintenance review date unavailable";
      if (reviewAge > 365) return "Maintenance review older than 365 days";
      return "Maintenance status unknown";
    }
    if (name === "adoption") return paper.adoption_evidence_url
      ? "Adoption status unknown" : "Adoption evidence not reviewed";
    return ({ citation: "Citation percentile unavailable", venue: "Venue prestige unavailable",
      award: "Award status not reviewed", code: "Code availability not reviewed" })[name] || "Component unavailable";
  }
  function score(paper, weights, now = new Date()) {
    const selected = Object.entries(weights).filter(([, weight]) => weight > 0);
    const total = selected.reduce((sum, [, weight]) => sum + weight, 0);
    if (!total) return { value: null, coverage: 0, components: {}, breakdown: [] };
    let numerator = 0, available = 0, count = 0;
    const components = {}, breakdown = [];
    for (const [name, weight] of selected) {
      const value = evidenceValue(paper, name, now);
      if (typeof value !== "number" || !Number.isFinite(value) || value < 0 || value > 1) {
        breakdown.push({ name, weight, value: null, contribution: null, included: false, reason: omissionReason(paper, name, now) });
        continue;
      }
      components[name] = value;
      const contribution = value * weight;
      breakdown.push({ name, weight, value, contribution, included: true, reason: null });
      numerator += contribution;
      available += weight;
      count++;
    }
    const coverage = available / total;
    const enoughEvidence = count >= 2 && coverage >= .55
      || count >= 4 && coverage >= .5 && "code" in components && ("adoption" in components || "maintenance" in components);
    return { value: enoughEvidence ? 6 * numerator / available : null, coverage, components, breakdown };
  }
  function filterPapers(papers, filters) {
    const needle = (filters.search || "").trim().toLowerCase();
    return papers.filter(p => (!filters.year || String(p.year) === filters.year)
      && (!filters.area || p.area === filters.area)
      && (!filters.venue || p.venue_id === filters.venue)
      && (!filters.sector || p.first_author_sector === filters.sector || (filters.sector === "Joint" && p.team_sector === "Joint"))
      && (!filters.country || (p.countries || []).includes(filters.country))
      && (!needle || [p.title, p.first_author, p.venue, ...(p.first_author_affiliations || []), ...(p.all_institutions || [])]
        .some(value => String(value || "").toLowerCase().includes(needle))));
  }
  function sectorStats(papers, weights) {
    const sectors = ["Industry", "University", "Research Institute", "Joint"];
    return sectors.map(sector => {
      const members = papers.filter(p => p.team_sector === sector);
      const scored = members.map(p => score(p, weights).value).filter(v => v !== null);
      return { sector, count: members.length, scored: scored.length,
        mean: scored.length ? scored.reduce((a, b) => a + b, 0) / scored.length : null };
    });
  }
  function trend(papers, weights, mode, lastCoveredYear, usableYears) {
    const endYear = lastCoveredYear || Math.max(2020, ...papers.map(p => p.year || 2020));
    const years = Array.from({ length: endYear - 2019 }, (_, i) => 2020 + i);
    const sectors = ["Industry", "University", "Research Institute"];
    const counts = years.map(year => {
      const yearPapers = papers.filter(p => p.year === year);
      const classified = yearPapers.filter(p => sectors.includes(p.first_author_sector));
      const result = { year, count: yearPapers.length, classifiedCount: classified.length };
      for (const sector of sectors) {
        result[sector] = usableYears && !usableYears.has(year) ? null
          : classified.filter(p => p.first_author_sector === sector).length;
      }
      return result;
    });
    return counts.map((row, index) => {
      const result = { ...row };
      for (const sector of sectors) {
        if (mode === "share") result[sector] = row[sector] !== null && row.classifiedCount
          ? row[sector] / row.classifiedCount * 100 : null;
        if (mode === "growth") {
          const previous = counts[index - 1]?.[sector];
          result[sector] = row[sector] !== null && row.classifiedCount > 0 && previous > 0
            ? (row[sector] - previous) / previous * 100 : null;
        }
      }
      return result;
    });
  }
  function trendSelection(papers, coverage, catalog, filters) {
    const selectedPapers = filterPapers(papers, { ...filters, year: "", sector: "" });
    const venueIds = new Set(catalog.filter(venue => (!filters.venue || venue.id === filters.venue)
      && (!filters.area || venue.area === filters.area)).map(venue => venue.id));
    const eligible = coverage.filter(row => (!filters.venue || row.venue_id === filters.venue) && !row.stale
      && !["source-error", "error", "unresolved", "not-held", "not-yet-published", "unmapped", "no-index-records"].includes(row.status)
      && (row.ai_scan_status === "complete" || row.ai_scan_status === "partial" && row.sampled_papers > 0
        || !row.ai_scan_status && ["sample", "source-scan"].includes(row.status) && row.included > 0));
    const eligibleCells = new Set(eligible.map(row => `${row.venue_id}:${row.year}`));
    const paperVenueIds = new Set(selectedPapers.filter(paper => eligibleCells.has(`${paper.venue_id}:${paper.year}`))
      .map(paper => paper.venue_id));
    const usable = eligible.filter(row => venueIds.has(row.venue_id) || paperVenueIds.has(row.venue_id));
    const cells = new Set(usable.map(row => `${row.venue_id}:${row.year}`));
    return {
      papers: selectedPapers.filter(paper => cells.has(`${paper.venue_id}:${paper.year}`)),
      usableYears: new Set(usable.map(row => row.year))
    };
  }
  function trendSeries(sector) {
    const sectors = ["Industry", "University", "Research Institute"];
    return sector ? sectors.filter(item => item === sector) : sectors;
  }
  function lineSegments(data, sector) {
    const segments = [];
    let current = [];
    for (const row of data) {
      if (Number.isFinite(row[sector])) current.push(row);
      else if (current.length) { segments.push(current); current = []; }
    }
    if (current.length) segments.push(current);
    return segments;
  }
  function trendRange(data, mode) {
    const sectors = ["Industry", "University", "Research Institute"];
    const values = data.flatMap(row => sectors.map(sector => row[sector])).filter(Number.isFinite);
    if (mode === "share") return [0, 100];
    if (mode === "growth") return [Math.min(0, ...values), Math.max(0, ...values)];
    return [0, Math.max(0, ...values)];
  }
  function geography(papers) {
    const countries = new Map();
    for (const paper of papers) {
      const codes = [...new Set(paper.countries || [])];
      for (const code of codes) countries.set(code, (countries.get(code) || 0) + 1 / codes.length);
    }
    return [...countries].map(([code, count]) => ({ code, count })).sort((a, b) => b.count - a.count);
  }
  root.AIResearchCore = { score, filterPapers, sectorStats, trend, trendSelection, trendSeries, lineSegments, trendRange, geography };
})(typeof window !== "undefined" ? window : globalThis);
