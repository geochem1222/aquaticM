# Aquatic Metabolism Paper Tracker

这是一个面向“水生系统 AND 代谢”的 Semantic Scholar 静态论文追踪网页，结构参考了 `chengzhuangchen-resistome-paper-tracker`：首页读取 `data/papers.json`，支持搜索、来源筛选、主题筛选、表格排序和展开摘要。

## 研究范围

- 水体类型：river、stream、creek、lake、reservoir、pond、ditch、canal、tidal creek、wetland、sediment、hyporheic zone
- 代谢过程：ecosystem metabolism、gross primary production、ecosystem respiration、dissolved oxygen、reaeration
- 方法与观测：oxygen time series、sensor monitoring、stable isotopes、isotope tracing、Bayesian models、reactive transport models
- 微生物过程：microbial metabolism、biofilm metabolism、decomposition

## 本地预览

```bash
python -m http.server 8000
```

然后打开：

```text
http://localhost:8000
```

## 自动更新

默认更新脚本：

```bash
python scripts/update_papers.py --retmax 5000 --refresh-limit 800 --merge-existing
```

数据源只使用 Semantic Scholar。默认使用 Semantic Scholar `paper/search/bulk`，并用 `paper/batch` 批量回填 TLDR、fields、引用数、参考文献数、开放 PDF 等详情；这样比 ranked search 更容易覆盖老文献和高被引文献。脚本会复用已有 `data/papers.json` 作为缓存：库还没满 5000 条时继续补库，库已经较完整时每次只抓取默认 800 条新候选再与旧库合并，避免每天全量请求。

如果有 Semantic Scholar API key，可以通过环境或 GitHub Actions secret 传入：

```bash
python scripts/update_papers.py --semantic-api-key YOUR_KEY --merge-existing
```

## Semantic Scholar 增强信息与相似文章

如果你有 Semantic Scholar API key，可以在本地把已有题录增强成“可点击详情 + 相似文章推荐”：

```bash
set SEMANTIC_SCHOLAR_API_KEY=你的key
python scripts/enrich_semantic_scholar.py --limit 5000 --edge-detail-limit 300 --edge-limit 12 --stale-days 30
```

增强后，每条论文会尽量补充：

- TLDR
- fields of study / S2 fields of study
- publication types
- authors with Semantic Scholar author IDs
- open access PDF
- citation count / influential citation count / reference count
- 参考文献节点
- 引用本文节点

网页不会运行 Python。Python 只在本地或 GitHub Actions 更新阶段把增强结果写入 `data/papers.json` / `data/papers.js`；网页只读取这些静态 JSON 数据并渲染。

网页中点击表格里的论文，会在摘要下方显示 Semantic Scholar 信息和相似文章：

- 如果该论文已有 Semantic Scholar 增强数据，显示 Recommendations API 返回的相似文章。
- 如果暂时没有增强数据，显示同库论文的主题相似文章。

增强脚本也带缓存：每条论文会记录 `detail_enriched_at` 和 `edges_enriched_at`，默认 30 天内不会重复请求同一批详情、引用关系和相似文章。

部署到 GitHub 后，把 API key 添加为仓库 Secret：

```text
SEMANTIC_SCHOLAR_API_KEY
```

路径：

```text
Settings → Secrets and variables → Actions → New repository secret
```

之后 workflow 会自动执行两步：

1. 用 Semantic Scholar bulk search 维护最多 5000 条题录，缓存已存在题录，每次默认只补 800 条新候选。
2. 用同一个 key 通过 batch API 补充 TLDR、fields、authors、citation/reference counts，并为前 300 条需要刷新或缺失数据的重点论文补充 references、citations、Recommendations API 相似文章，生成网页详情区所需的静态 JSON 数据。

## 数据文件

网页数据位于：

```text
data/papers.json
```

建议由 `scripts/update_papers.py` 从 Semantic Scholar 生成。`scripts/import_seed_csv.py` 仅作为手工补充工具保留。

## Google Scholar 作为补充来源

不建议把 Google Scholar 做成 GitHub Actions 的自动抓取来源；它没有公开检索 API，自动抓取容易触发验证码、限流或访问限制。更稳妥的方式是：在浏览器里手动搜索，用类似 `goku-xmu/google-scholar-assistant` 的扩展导出 CSV / RIS，再导入本站数据。

本项目附带一个轻量导出器：

```text
tools/google-scholar-exporter.html
```

打开后把“导出 Scholar 当前页”拖到书签栏。之后在 Google Scholar 搜索结果页点击该书签，会下载当前页可见结果的 CSV、RIS 和 JSON。它只读取当前页面，不自动翻页。

导入手工导出的 Google Scholar CSV 或 RIS：

```bash
python scripts/import_google_scholar_export.py exported-results.csv
python scripts/import_google_scholar_export.py exported-results.ris
```

导入后会同时更新：

```text
data/papers.json
data/papers.js
```
