# Aquatic Metabolism Paper Tracker

这是一个面向“水生系统 AND 代谢”的 Semantic Scholar 静态论文追踪网页，结构参考了 `chengzhuangchen-resistome-paper-tracker`：首页读取 `data/papers.json`，支持搜索、来源筛选、主题筛选、表格排序和展开摘要。

## 研究范围

- 水体类型：river、stream、creek、lake、reservoir、pond、ditch、canal、tidal creek、wetland、sediment、hyporheic zone
- 代谢过程：ecosystem metabolism、gross primary production、ecosystem respiration、dissolved oxygen、reaeration
- 元素与通量：carbon、CO2、methane、nitrogen、phosphorus、nutrient cycling、greenhouse gas
- 微生物过程：microbial metabolism、methanotrophy、decomposition、carbon use efficiency

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
python scripts/update_papers.py --retmax 300 --merge-existing
```

数据源只使用 Semantic Scholar。如果有 Semantic Scholar API key，可以通过环境或 GitHub Actions secret 传入：

```bash
python scripts/update_papers.py --semantic-api-key YOUR_KEY --merge-existing
```

## Semantic Scholar 增强信息与图谱

如果你有 Semantic Scholar API key，可以在本地把已有题录增强成“可点击详情 + citation graph”：

```bash
set SEMANTIC_SCHOLAR_API_KEY=你的key
python scripts/enrich_semantic_scholar.py --limit 80 --edge-limit 12
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

网页中点击表格里的论文，会在下方显示一个小型引用图谱。

部署到 GitHub 后，把 API key 添加为仓库 Secret：

```text
SEMANTIC_SCHOLAR_API_KEY
```

路径：

```text
Settings → Secrets and variables → Actions → New repository secret
```

之后 workflow 会自动执行两步：

1. 更新 Semantic Scholar 题录。
2. 用同一个 key 补充 TLDR、fields、authors、references、citations，并生成网页里的 citation graph 数据。

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
