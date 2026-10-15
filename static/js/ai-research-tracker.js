(function () {
  "use strict";
  const root = document.querySelector(".research-tracker");
  if (!root) return;
  const ns = "http://www.w3.org/2000/svg";
  const years = Array.from({length: new Date().getFullYear() - 2019}, (_, i) => 2020 + i);
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
      const marker = svg("circle", {cx:x,cy:y,r:5,fill:color,class:"point",tabindex:"0",role:"button","aria-label":point.label}, node);
      marker.addEventListener("click", () => detail(point));
      marker.addEventListener("keydown", event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); detail(point); } });
      svg("title", {}, marker).textContent = point.label;
    }
  }

  function renderCounts(history) {
    const mode = $("research-count-mode").value;
    const node = $("research-count-chart"), legend = $("research-count-legend");
    empty(node); empty(legend);
    const metrics = mode === "both" ? ["submitted", "accepted"] : [mode];
    const values = history.counts.flatMap(row => metrics.map(metric => row[metric])).filter(Number.isFinite);
    const max = Math.max(1000, Math.ceil(Math.max(...values) / 5000) * 5000);
    const top = 18, bottom = 267, left = 56, right = 735;
    axes(node, top, bottom, left, right, max, "");
    for (const venue of history.conferences) {
      const key = document.createElement("span");
      const color = document.createElement("i"); color.className = "research-key"; color.style.setProperty("--key-color", venue.color);
      key.append(color, document.createTextNode(venue.name)); legend.appendChild(key);
      for (const metric of metrics) {
        const points = history.counts.filter(row => row.venue === venue.id).map(row => ({
          year:row.year,value:row[metric],row,
          label:`${venue.name} ${row.year}: ${fmt(row[metric])} ${metric}. ${row.scope}`
        }));
        line(node, points, venue.color, metric === "accepted" ? "accepted" : "", left,right,top,bottom,max, point => {
          const detail = $("research-count-detail"); empty(detail);
          detail.append(document.createTextNode(`${point.label} `));
          const link = document.createElement("a"); link.href = point.row.source; link.target = "_blank"; link.rel = "noopener noreferrer"; link.textContent = "Organizer source";
          detail.appendChild(link);
        });
      }
    }
    if (mode === "both") {
      legend.append(document.createTextNode("Solid: submitted · Dashed: accepted"));
    }
  }

  function renderLedger(history) {
    const tbody = $("research-count-rows"); empty(tbody);
    for (const row of [...history.counts].sort((a,b) => b.year - a.year || a.venue.localeCompare(b.venue))) {
      const tr = document.createElement("tr");
      const venue = history.conferences.find(item => item.id === row.venue);
      for (const value of [venue.name, row.year, fmt(row.submitted), fmt(row.accepted)]) {
        const td = document.createElement("td"); td.textContent = value; tr.appendChild(td);
      }
      const td = document.createElement("td"); td.append(document.createTextNode(`${row.scope} · `));
      const link = document.createElement("a"); link.href = row.source; link.target = "_blank"; link.rel = "noopener noreferrer"; link.textContent = "Organizer";
      td.appendChild(link); tr.appendChild(td); tbody.appendChild(tr);
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
        const papers = snapshot.papers.filter(p => p.year === year && p.first_author_sector === sector);
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
    const total = snapshot.papers.length;
    $("research-topic-detail").textContent = `${fmt(total)} tracked papers · snapshot ${new Date(snapshot.generated_at).toLocaleDateString("en-GB")} · point labels show each year's denominator`;
  }

  async function load(url) {
    const response = await fetch(url, {cache:"no-cache"});
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }
  Promise.all([load(root.dataset.historyUrl),load(root.dataset.observatoryUrl)]).then(([history,snapshot]) => {
    if (!Array.isArray(history.counts) || !Array.isArray(history.awards) || !Array.isArray(snapshot.papers)) throw new Error("Invalid dataset");
    renderCounts(history); renderLedger(history); renderAwards(history); renderTopics(snapshot);
    $("research-count-mode").addEventListener("change", () => renderCounts(history));
    $("research-topic").addEventListener("change", () => renderTopics(snapshot));
    $("research-status").textContent = `Conference figures reviewed ${history.reviewed_at} · publication sample updated ${new Date(snapshot.generated_at).toLocaleDateString("en-GB")}`;
  }).catch(() => { $("research-status").textContent = "The research datasets could not be loaded. Please retry later."; });
})();
