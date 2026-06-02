const state = {
  papers: [],
  filter: "all",
  source: "all",
  query: "",
  sortKey: "publication_date",
  sortDirection: "desc",
  expanded: new Set(),
  page: 1,
  pageSize: 50,
};

const filterNames = {
  all: "全部主题",
  river: "河/溪",
  lake: "湖/库",
  pond: "塘",
  ditch: "沟/潮沟",
  oxygen: "溶解氧",
  isotope: "同位素",
  model: "模型",
  sensor: "高频监测",
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
  isotope: "同位素",
  model: "模型",
  sensor: "高频监测",
  microbe: "微生物",
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
  semanticCount: document.querySelector("#semantic-count"),
  resultCount: document.querySelector("#result-count"),
  tbody: document.querySelector("#papers-body"),
  empty: document.querySelector("#empty-state"),
  search: document.querySelector("#search"),
  sourceSelect: document.querySelector("#source-filter"),
  chips: document.querySelectorAll(".chip"),
  sortButtons: document.querySelectorAll("[data-sort]"),
  prevPage: document.querySelector("#prev-page"),
  nextPage: document.querySelector("#next-page"),
  pageStatus: document.querySelector("#page-status"),
  pageSize: document.querySelector("#page-size"),
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
  state.page = 1;
  render();
});

els.sourceSelect.addEventListener("change", (event) => {
  state.source = event.target.value;
  state.page = 1;
  render();
});

els.chips.forEach((chip) => {
  chip.addEventListener("click", () => {
    state.filter = chip.dataset.filter;
    state.page = 1;
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
    state.page = 1;
    render();
  });
});

els.prevPage.addEventListener("click", () => {
  state.page = Math.max(1, state.page - 1);
  render();
});

els.nextPage.addEventListener("click", () => {
  state.page += 1;
  render();
});

els.pageSize.addEventListener("change", (event) => {
  state.pageSize = Number(event.target.value) || 50;
  state.page = 1;
  render();
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
  els.semanticCount.textContent = state.papers.filter((paper) => paper.semantic_scholar).length;
}

function countSince(date) {
  return state.papers.filter((paper) => {
    const publicationDate = new Date(paper.publication_date);
    return paper.publication_date && !Number.isNaN(publicationDate.getTime()) && publicationDate >= date;
  }).length;
}

function render() {
  const filtered = sortPapers(state.papers.filter(matchesFilters));
  const totalPages = Math.max(1, Math.ceil(filtered.length / state.pageSize));
  state.page = Math.min(state.page, totalPages);
  const start = (state.page - 1) * state.pageSize;
  const pageItems = filtered.slice(start, start + state.pageSize);
  els.resultCount.textContent = `${filterNames[state.filter]} · ${filtered.length} 篇`;
  els.empty.hidden = filtered.length > 0;
  els.tbody.innerHTML = pageItems.map(renderPaperRow).join("");
  els.pageStatus.textContent = `第 ${state.page} / ${totalPages} 页`;
  els.prevPage.disabled = state.page <= 1;
  els.nextPage.disabled = state.page >= totalPages;
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
          ${renderRelatedSection(paper)}
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

function renderRelatedSection(paper) {
  const related = getRelatedPapers(paper);
  const s2 = paper.semantic_scholar || {};
  const externalIds = s2.external_ids || {};
  const semanticUrl = paper.url || (s2.paper_id ? `https://www.semanticscholar.org/paper/${s2.paper_id}` : "");
  return `
    <section class="related-panel" aria-label="相似文章和 Semantic Scholar 信息">
      <div class="related-panel-head">
        <h4>相似文章与 S2 信息</h4>
        <p>${escapeHtml(related.caption)}</p>
      </div>
      <div class="s2-info-grid">
        <div>
          <span>Semantic Scholar</span>
          ${semanticUrl ? `<a href="${escapeHtml(semanticUrl)}" target="_blank" rel="noreferrer">打开论文页</a>` : "<strong>暂无链接</strong>"}
        </div>
        <div><span>DOI</span><strong>${escapeHtml(paper.doi || externalIds.DOI || "暂无")}</strong></div>
        <div><span>PMID</span><strong>${escapeHtml(paper.pmid || externalIds.PubMed || "暂无")}</strong></div>
        <div><span>开放 PDF</span>${paper.pdf_url ? `<a href="${escapeHtml(paper.pdf_url)}" target="_blank" rel="noreferrer">打开 PDF</a>` : "<strong>暂无</strong>"}</div>
      </div>
      <div class="related-list">
        ${related.items.length ? related.items.map(renderRelatedCard).join("") : '<p class="empty-state">暂时没有可显示的相似文章。</p>'}
      </div>
    </section>
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

function getRelatedPapers(paper) {
  const s2 = paper.semantic_scholar || {};
  const recommendations = (s2.recommendations || []).slice(0, 8);
  if (recommendations.length) {
    return {
      caption: "来自 Semantic Scholar Recommendations API。",
      items: recommendations,
    };
  }
  const items = state.papers
    .filter((candidate) => candidate !== paper)
    .map((candidate) => ({
      paper: candidate,
      score: sharedTagScore(paper, candidate),
    }))
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score || Number(b.paper.citation_count || 0) - Number(a.paper.citation_count || 0))
    .slice(0, 8)
    .map((item) => item.paper);
  return {
    caption: "暂未带有 S2 Recommendations 数据，先按本库标签相似度排序。",
    items,
  };
}

function sharedTagScore(a, b) {
  const left = new Set(a.tags || []);
  return (b.tags || []).reduce((sum, tag) => sum + (left.has(tag) ? 1 : 0), 0);
}

function renderRelatedCard(item) {
  const authors = item.authors?.map ? item.authors.map((author) => typeof author === "string" ? author : author.name).filter(Boolean).slice(0, 3).join(", ") : "";
  const url = item.url || (item.paper_id ? `https://www.semanticscholar.org/paper/${item.paper_id}` : "");
  return `
    <article class="related-card">
      <h5>${escapeHtml(item.title || "Untitled")}</h5>
    ${authors ? `<p>${escapeHtml(authors)}</p>` : ""}
      <div class="related-meta">
        ${item.year || item.publication_date ? `<span>${escapeHtml(item.year || item.publication_date)}</span>` : ""}
        ${item.venue || item.journal ? `<span>${escapeHtml(item.venue || item.journal)}</span>` : ""}
        <span>引用 ${escapeHtml(formatNumber(item.citation_count || 0))}</span>
      </div>
      ${item.abstract ? `<p class="related-abstract">${escapeHtml(item.abstract.slice(0, 220))}${item.abstract.length > 220 ? "..." : ""}</p>` : ""}
      <div class="related-links">
        ${url ? `<a href="${escapeHtml(url)}" target="_blank" rel="noreferrer">Semantic Scholar</a>` : ""}
        ${item.pdf_url ? `<a href="${escapeHtml(item.pdf_url)}" target="_blank" rel="noreferrer">PDF</a>` : ""}
      </div>
    </article>
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
