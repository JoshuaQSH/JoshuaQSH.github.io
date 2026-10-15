(function (root) {
  "use strict";
  const COMPONENTS = { citation: "citation_percentile", venue: "prestige", award: "award", code: "code_available" };
  function score(paper, weights) {
    const selected = Object.entries(weights).filter(([, weight]) => weight > 0);
    const total = selected.reduce((sum, [, weight]) => sum + weight, 0);
    if (!total) return { value: null, coverage: 0, components: {} };
    let numerator = 0, available = 0, count = 0;
    const components = {};
    for (const [name, weight] of selected) {
      const raw = paper[COMPONENTS[name]];
      const value = (name === "award" || name === "code") && typeof raw === "boolean" ? Number(raw) : raw;
      if (typeof value !== "number" || !Number.isFinite(value) || value < 0 || value > 1) continue;
      components[name] = value;
      numerator += value * weight;
      available += weight;
      count++;
    }
    const coverage = available / total;
    return { value: count >= 2 && coverage >= 0.55 ? 6 * numerator / available : null, coverage, components };
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
  function trend(papers, weights, mode, lastCoveredYear) {
    const endYear = lastCoveredYear || Math.max(2020, ...papers.map(p => p.year || 2020));
    const years = Array.from({ length: endYear - 2019 }, (_, i) => 2020 + i);
    const sectors = ["Industry", "University", "Research Institute"];
    return years.map(year => {
      const yearPapers = papers.filter(p => p.year === year);
      const result = { year };
      const classified = yearPapers.filter(p => sectors.includes(p.first_author_sector));
      const impactTotal = classified.reduce((sum, p) => sum + (score(p, weights).value || 0), 0);
      for (const sector of sectors) {
        const members = classified.filter(p => p.first_author_sector === sector);
        result[sector] = mode === "share" ? (classified.length ? members.length / classified.length * 100 : 0)
          : mode === "impact" ? (impactTotal ? members.reduce((sum, p) => sum + (score(p, weights).value || 0), 0) / impactTotal * 100 : 0)
          : members.length;
      }
      result.count = yearPapers.length;
      return result;
    });
  }
  function geography(papers) {
    const countries = new Map();
    for (const paper of papers) {
      const codes = [...new Set(paper.countries || [])];
      for (const code of codes) countries.set(code, (countries.get(code) || 0) + 1 / codes.length);
    }
    return [...countries].map(([code, count]) => ({ code, count })).sort((a, b) => b.count - a.count);
  }
  root.AIResearchCore = { score, filterPapers, sectorStats, trend, geography };
})(typeof window !== "undefined" ? window : globalThis);
