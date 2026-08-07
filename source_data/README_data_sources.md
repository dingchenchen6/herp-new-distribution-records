# Source data notes / 源数据说明

## Included files / 仓库内文件

- `两栖爬行动物数据合并表-8.7最新版.xlsx` — merged source table (project-internal).
- `两栖爬行动物数据合并表-8.7修订完善版.xlsx` — revised and audited workbook
  produced by `scripts/pipeline/01–03`; every change is logged in its
  `修订日志` sheet.

## Not redistributed / 不随仓库分发

- `动物界-脊索动物门-2026-10714.xlsx` — the Catalogue of Life China 2026
  Annual Checklist (Chordata) used as the taxonomic backbone.
  该第三方名录文件不随公开仓库分发。复现 `scripts/pipeline/01_match_species.py`
  前请自行获取并放入本目录（文件名保持不变）：
  - Official source / 官方来源: 中国生物物种名录 (Catalogue of Life China),
    <http://www.sp2000.org.cn/>（按年度下载 动物界-脊索动物门 数据）。
  - The pipeline expects columns: 物种拉丁名/物种中文名/界~属中拉名/审核专家。

All downstream products (`data/`, `audit_quality_control/`, `figures/`,
`results/`) are already built and versioned here, so the checklist file is
only needed when re-running the taxonomy-matching step from scratch.
