const state = {
  papers: [],
  filter: "all",
  source: "all",
  query: "",
  sortKey: "publication_date",
  sortDirection: "desc",
  expanded: new Set(),
};

const filterNames = {
  all: "全部主题",
  river: "河/溪",
  lake: "湖/库",
  pond: "塘",
  ditch: "沟/潮沟",
  oxygen: "溶解氧",
  carbon: "碳/甲烷",
  nutrient: "氮磷",
  microbe: "微生物",
};

const tagLabels = {
  river: "河/溪",
  lake: "湖/库",
  pond: "塘",
  ditch: "沟/潮沟",
  wetland: "湿地",
  sediment: "沉积物",
  oxygen: "溶解氧",
  metabolism: "代谢",
  carbon: "碳/甲烷",
  nutrient: "氮磷",
  microbe: "微生物",
  greenhouse: "温室气体",
};

const els = {
  lastUpdated: document.querySelector("#last-updated"),
  paperCount: document.querySelector("#paper-count"),
  sourceCount: document.querySelector("#source-count"),
  weekCount: document.querySelector("#week-count"),
  monthCount: document.querySelector("#month-count"),
  yearCount: document.querySelector("#year-count"),
  citationTotal: document.querySelector("#citation-total"),
  pdfCount: document.querySelector("#pdf-count"),
  metabolismCount: document.querySelector("#metabolism-count"),
  resultCount: document.querySelector("#result-count"),
  tbody: document.querySelector("#papers-body"),
  empty: document.querySelector("#empty-state"),
  search: document.querySelector("#search"),
  sourceSelect: document.querySelector("#source-filter"),
  chips: document.querySelectorAll(".chip"),
  sortButtons: document.querySelectorAll("[data-sort]"),
  graphTitle: document.querySelector("#graph-title"),
  graph: document.querySelector("#paper-graph"),
  graphDetail: document.querySelector("#graph-detail"),
};

fetch("data/papers.json", { cache: "no-store" })
  .then((response) => {
    if (!response.ok) {
      throw new Error("Paper data could not be loaded.");
    }
    return response.json();
  })
  .then((data) => {
    loadData(data);
  })
  .catch(() => {
    if (window.PAPER_TRACKER_DATA) {
      loadData(window.PAPER_TRACKER_DATA);
      return;
    }
    els.lastUpdated.textContent = "暂未更新";
    els.resultCount.textContent = "数据读取失败";
    els.empty.hidden = false;
  });

function loadData(data) {
  state.papers = data.papers || [];
  els.lastUpdated.textContent = formatDate(data.updated_at);
  updateSourceLabel(data);
  updateStats();
  populateSources();
  render();
}

els.search.addEventListener("input", (event) => {
  state.query = event.target.value.trim().toLowerCase();
  render();
});

els.sourceSelect.addEventListener("change", (event) => {
  state.source = event.target.value;
  render();
});

els.chips.forEach((chip) => {
  chip.addEventListener("click", () => {
    state.filter = chip.dataset.filter;
    els.chips.forEach((item) => item.classList.toggle("active", item === chip));
    render();
  });
});

els.sortButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const key = button.dataset.sort;
    if (state.sortKey === key) {
      state.sortDirection = state.sortDirection === "asc" ? "desc" : "asc";
    } else {
      state.sortKey = key;
      state.sortDirection = key === "title" ? "asc" : "desc";
    }
    render();
  });
});

els.tbody.addEventListener("click", (event) => {
  const row = event.target.closest("[data-paper-row]");
  if (!row || event.target.closest("a")) {
    return;
  }
  const id = row.dataset.paperRow;
  if (state.expanded.has(id)) {
    state.expanded.delete(id);
  } else {
    state.expanded.add(id);
  }
  const paper = state.papers.find((item) => String(item.id || item.doi || item.pmid || item.title) === id);
  if (paper) {
    renderGraph(paper);
  }
  render();
});

function updateSourceLabel(data) {
  const sources = data.sources || [data.source].filter(Boolean);
  els.sourceCount.textContent = sources.join(" + ") || "Semantic Scholar";
}

function populateSources() {
  const sources = [...new Set(state.papers.map((paper) => paper.source).filter(Boolean))].sort();
  els.sourceSelect.innerHTML = [
    '<option value="all">全部来源</option>',
    ...sources.map((source) => `<option value="${escapeHtml(source)}">${escapeHtml(source)}</option>`),
  ].join("");
}

function updateStats() {
  const now = new Date();
  const oneWeekAgo = new Date(now);
  oneWeekAgo.setDate(now.getDate() - 7);
  const oneMonthAgo = new Date(now);
  oneMonthAgo.setMonth(now.getMonth() - 1);
  const oneYearAgo = new Date(now);
  oneYearAgo.setFullYear(now.getFullYear() - 1);

  els.paperCount.textContent = state.papers.length;
  els.weekCount.textContent = countSince(oneWeekAgo);
  els.monthCount.textContent = countSince(oneMonthAgo);
  els.yearCount.textContent = countSince(oneYearAgo);
  els.citationTotal.textContent = formatNumber(
    state.papers.reduce((sum, paper) => sum + Number(paper.citation_count || 0), 0)
  );
  els.pdfCount.textContent = state.papers.filter((paper) => paper.pdf_url).length;
  els.metabolismCount.textContent = state.papers.filter((paper) => paper.tags.includes("metabolism")).length;
}

function countSince(date) {
  return state.papers.filter((paper) => {
    const publicationDate = new Date(paper.publication_date);
    return paper.publication_date && !Number.isNaN(publicationDate.getTime()) && publicationDate >= date;
  }).length;
}

function render() {
  const filtered = sortPapers(state.papers.filter(matchesFilters));
  els.resultCount.textContent = `${filterNames[state.filter]} · ${filtered.length} 篇`;
  els.empty.hidden = filtered.length > 0;
  els.tbody.innerHTML = filtered.map(renderPaperRow).join("");
  updateSortIndicators();
}

function matchesFilters(paper) {
  const text = [
    paper.title,
    paper.abstract,
    paper.journal,
    paper.authors?.join(" "),
    paper.doi,
    paper.pmid,
    paper.source,
    paper.citation_count,
    paper.reference_count,
    paper.tags?.join(" "),
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();

  const matchesText = !state.query || text.includes(state.query);
  const matchesTag = state.filter === "all" || paper.tags.includes(state.filter);
  const matchesSource = state.source === "all" || paper.source === state.source;
  return matchesText && matchesTag && matchesSource;
}

function sortPapers(papers) {
  return [...papers].sort((a, b) => {
    const left = getSortValue(a, state.sortKey);
    const right = getSortValue(b, state.sortKey);
    const result = left.localeCompare(right, undefined, { numeric: true, sensitivity: "base" });
    return state.sortDirection === "asc" ? result : -result;
  });
}

function getSortValue(paper, key) {
  if (key === "authors") {
    return paper.authors?.[0] || "";
  }
  if (key === "citation_count" || key === "reference_count") {
    return String(Number(paper[key] || 0)).padStart(8, "0");
  }
  return String(paper[key] || "");
}

function renderPaperRow(paper) {
  const id = paper.id || paper.doi || paper.pmid || paper.title;
  const authors = paper.authors?.slice(0, 3).join(", ") || "作者待更新";
  const moreAuthors = paper.authors?.length > 3 ? " 等" : "";
  const tags = (paper.tags || [])
    .map((tag) => `<span class="tag">${tagLabels[tag] || tag}</span>`)
    .join("");
  const expanded = state.expanded.has(id);
  const doiLink = paper.doi ? `https://doi.org/${encodeURIComponent(paper.doi)}` : "";
  const primaryUrl = paper.url || doiLink;

  return `
    <tr class="paper-row" data-paper-row="${escapeHtml(id)}" aria-expanded="${expanded}">
      <td class="date-cell">${escapeHtml(formatDate(paper.publication_date))}</td>
      <td>
        <strong class="paper-title">${escapeHtml(paper.title || "Untitled")}</strong>
        <div class="paper-tags">${tags}</div>
      </td>
      <td>${escapeHtml(authors + moreAuthors)}</td>
      <td>${escapeHtml(paper.journal || "Unknown")}</td>
      <td class="citation-cell">${escapeHtml(formatNumber(paper.citation_count || 0))}</td>
      <td class="citation-cell">${escapeHtml(formatNumber(paper.reference_count || 0))}</td>
      <td><span class="source-pill">${escapeHtml(paper.source || "Unknown")}</span></td>
      <td class="link-cell">
        ${primaryUrl ? `<a href="${primaryUrl}" target="_blank" rel="noreferrer">打开</a>` : ""}
        ${paper.pdf_url ? `<a href="${paper.pdf_url}" target="_blank" rel="noreferrer">PDF</a>` : ""}
        ${doiLink && doiLink !== primaryUrl ? `<a href="${doiLink}" target="_blank" rel="noreferrer">DOI</a>` : ""}
      </td>
    </tr>
    <tr class="detail-row ${expanded ? "open" : ""}">
      <td colspan="8">
        <div class="detail-panel">
          ${renderSemanticSummary(paper)}
          <p>${escapeHtml(paper.abstract || "暂无摘要。")}</p>
          <dl>
            <div><dt>DOI</dt><dd>${renderDoi(paper.doi)}</dd></div>
            <div><dt>PMID</dt><dd>${escapeHtml(paper.pmid || "无")}</dd></div>
            <div><dt>高影响引用</dt><dd>${escapeHtml(formatNumber(paper.influential_citation_count || 0))}</dd></div>
            <div><dt>数据库 ID</dt><dd>${escapeHtml(paper.id || "暂无")}</dd></div>
          </dl>
        </div>
      </td>
    </tr>
  `;
}

function renderSemanticSummary(paper) {
  const s2 = paper.semantic_scholar || {};
  const fields = [
    ...(s2.fields_of_study || []),
    ...(s2.s2_fields_of_study || []).map((item) => item.category).filter(Boolean),
  ];
  const uniqueFields = [...new Set(fields)].slice(0, 6);
  if (!s2.tldr && !uniqueFields.length && !s2.publication_types?.length) {
    return "";
  }
  return `
    <div class="semantic-box">
      ${s2.tldr ? `<p><strong>TLDR</strong> ${escapeHtml(s2.tldr)}</p>` : ""}
      ${uniqueFields.length ? `<p><strong>Fields</strong> ${escapeHtml(uniqueFields.join(" · "))}</p>` : ""}
      ${s2.publication_types?.length ? `<p><strong>Type</strong> ${escapeHtml(s2.publication_types.join(" · "))}</p>` : ""}
    </div>
  `;
}

function renderGraph(paper) {
  const s2 = paper.semantic_scholar || {};
  const references = (s2.references || paper.references || []).slice(0, 8);
  const citations = (s2.citations || []).slice(0, 8);
  els.graphTitle.textContent = paper.title || "Semantic Scholar 论文图谱";

  if (!references.length && !citations.length) {
    els.graph.innerHTML = '<div class="empty-state">这篇论文还没有增强图谱数据。运行 enrich_semantic_scholar.py 后可显示参考文献和引用网络。</div>';
    els.graphDetail.innerHTML = renderGraphDetail(paper, null);
    return;
  }

  const width = 760;
  const height = 390;
  const center = { x: width / 2, y: height / 2, item: paper, type: "center" };
  const refNodes = references.map((item, index) => polarNode(item, "reference", index, references.length, 180, center, -120, 120));
  const citeNodes = citations.map((item, index) => polarNode(item, "citation", index, citations.length, 180, center, 60, 300));
  const nodes = [center, ...refNodes, ...citeNodes];
  const edges = [...refNodes, ...citeNodes];

  els.graph.innerHTML = `
    <svg class="graph-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="引用关系图">
      ${edges.map((node) => `<line class="graph-edge" x1="${center.x}" y1="${center.y}" x2="${node.x}" y2="${node.y}"></line>`).join("")}
      ${nodes.map(renderGraphNode).join("")}
    </svg>
  `;
  els.graph.querySelectorAll("[data-node-index]").forEach((node) => {
    node.addEventListener("click", () => {
      els.graphDetail.innerHTML = renderGraphDetail(paper, nodes[Number(node.dataset.nodeIndex)]);
    });
  });
  els.graphDetail.innerHTML = renderGraphDetail(paper, center);
}

function polarNode(item, type, index, total, radius, center, startDeg, endDeg) {
  const span = total <= 1 ? 0 : (endDeg - startDeg) / (total - 1);
  const deg = startDeg + span * index;
  const rad = (deg * Math.PI) / 180;
  return {
    x: center.x + Math.cos(rad) * radius,
    y: center.y + Math.sin(rad) * radius,
    item,
    type,
  };
}

function renderGraphNode(node, index) {
  const title = node.item.title || "Untitled";
  const shortTitle = title.length > 34 ? `${title.slice(0, 34)}...` : title;
  const cls = `graph-node ${node.type}`;
  const radius = node.type === "center" ? 18 : 12;
  const labelY = node.type === "center" ? node.y + 36 : node.y + 27;
  return `
    <g class="${cls}" data-node-index="${index}">
      <circle cx="${node.x}" cy="${node.y}" r="${radius}"></circle>
      <text x="${node.x}" y="${labelY}" text-anchor="middle">${escapeHtml(shortTitle)}</text>
    </g>
  `;
}

function renderGraphDetail(rootPaper, node) {
  const item = node?.item || rootPaper;
  const typeLabel = node?.type === "reference" ? "参考文献" : node?.type === "citation" ? "引用本文" : "当前论文";
  const s2 = rootPaper.semantic_scholar || {};
  const tldr = node?.type === "center" && s2.tldr ? `<p><strong>TLDR</strong> ${escapeHtml(s2.tldr)}</p>` : "";
  const authors = item.authors?.map ? item.authors.map((author) => typeof author === "string" ? author : author.name).filter(Boolean).slice(0, 4).join(", ") : "";
  const fields = [
    ...(s2.fields_of_study || []),
    ...(s2.s2_fields_of_study || []).map((field) => field.category).filter(Boolean),
  ];
  return `
    <h3>${escapeHtml(typeLabel)}</h3>
    <p><strong>${escapeHtml(item.title || "Untitled")}</strong></p>
    ${authors ? `<p>${escapeHtml(authors)}</p>` : ""}
    ${item.year || item.publication_date ? `<p>年份：${escapeHtml(item.year || item.publication_date)}</p>` : ""}
    ${item.venue || item.journal ? `<p>来源：${escapeHtml(item.venue || item.journal)}</p>` : ""}
    ${typeof item.citation_count !== "undefined" ? `<p>引用：${escapeHtml(formatNumber(item.citation_count))}</p>` : ""}
    ${tldr}
    ${node?.type === "center" && fields.length ? `<p>领域：${escapeHtml([...new Set(fields)].slice(0, 6).join(" · "))}</p>` : ""}
    ${item.url ? `<p><a href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer">打开 Semantic Scholar</a></p>` : ""}
  `;
}

function renderDoi(doi) {
  if (!doi) {
    return "暂无";
  }
  const safeDoi = escapeHtml(doi);
  return `<a href="https://doi.org/${encodeURIComponent(doi)}" target="_blank" rel="noreferrer">${safeDoi}</a>`;
}

function formatNumber(value) {
  return new Intl.NumberFormat("zh-CN").format(Number(value || 0));
}

function updateSortIndicators() {
  els.sortButtons.forEach((button) => {
    const active = button.dataset.sort === state.sortKey;
    button.dataset.active = String(active);
    button.querySelector("span").textContent = active ? (state.sortDirection === "asc" ? "↑" : "↓") : "";
  });
}

function formatDate(value) {
  if (!value) {
    return "日期待更新";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleDateString("zh-CN", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
