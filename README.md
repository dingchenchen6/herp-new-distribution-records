# China Herpetofauna New Record dataset (CHNR)

**中国两栖爬行动物省级新分布纪录数据集（v0.1，构建于 2026-08-07）**

A literature-derived, taxonomically standardized and georeferenced dataset of
provincial-level new distribution records of amphibians and reptiles in China,
built with the same event definition, cleaning pipeline and package layout as the
companion bird dataset **CBNR** (*A dataset of provincial-level new distribution
records for birds in China from 2000 to 2025*; Zenodo:
[10.5281/zenodo.20809949](https://doi.org/10.5281/zenodo.20809949)).

> **Status: public release candidate (v1.0, manuscript drafted, pre-submission).**
> 数据为工作版，尚未正式发表；`audit_quality_control/03` 中"排除-待人工判定"
> 条目已完成基于网盘原文的终审裁定（见 audit_quality_control/06_manual_adjudication/，仅10行遗留人工项）。The third-party Catalogue of Life China checklist is
> **not** redistributed here — see `source_data/README_data_sources.md`.

## Highlights / 数据概况

| Component | Amphibia 两栖纲 | Reptilia 爬行纲 | Total |
|---|---|---|---|
| Provincial new-record events 省级新纪录事件 | 213 (158 spp) | 224 (130 spp) | **437 events, 288 spp, 32 provincial units** |
| New species descriptions 新种描述条目 | 240 | 132 | **375** |
| Georeferenced events 具坐标事件 (WGS84) | 186 | 179 | 365 |

- The analytical unit is a **species × province first record** (as in CBNR); the
  earliest publication per species–province combination is retained and later
  re-documentations are logged, not deleted.
- Taxonomy is harmonized against the **Catalogue of Life China 2026 Annual
  Checklist** (Chordata); names as published are preserved side-by-side with
  accepted names, and every non-exact match carries an auditable method tag.
- All 2,228 source rows receive an explicit keep/exclude verdict
  (`audit_quality_control/03_record_screening/`), including contamination
  screening (non-herp taxa, foreign records, survey-inventory rows, companion
  species in taxonomic papers).

## Repository structure / 目录结构

```
data/                       # CHNR release tables (CSV UTF-8 + Excel bundle + field dictionary)
├── CHNR_provincial_new_records.csv   # clean event table (437 rows × 43 fields)
├── CHNR_new_species.csv              # companion new-species table (375 rows)
├── CHNR_metadata.csv                 # field dictionary (CN/EN)
└── CHNR_v1.0.xlsx                    # bundled workbook incl. summary sheets
source_data/                # inputs: merged source table (8.7), revised & audited
                            # workbook, and the COL China 2026 Chordata checklist
audit_quality_control/      # CBNR-style stepwise audit trail
├── 02_taxonomy_harmonisation/        # matches needing review
├── 03_record_screening/              # per-row verdicts for all 2,228 source rows
├── 04_coordinate_georeferencing/     # parsed coords, province-consistency audit,
│                                     # gazetteer completion log
└── 05_duplicate_review/              # species×province earliest-publication rule
scripts/
├── pipeline/               # 01 taxonomy matching → 02 coordinate parsing →
│                           # 03 revised workbook → 04 CHNR build → 05 summaries
├── figure1a_province_map/  # per-class province choropleths (R, sf)
├── figure1b_record_points/ # per-class georeferenced event maps (R, sf)
└── figure1c_order_province_year_sankey/  # per-class Order→Province→Year Sankey
figures/                    # final figures, one set per class (PNG 300–420 dpi + PDF)
results/                    # per-class descriptive summaries (order/province/year)
docs/                       # build summary and processing notes
```

## Reproducing the release / 复现流程

```bash
cd scripts/pipeline
python3 01_match_species.py      # 名录多层匹配 / layered taxonomy matching
python3 02_parse_coords.py       # 坐标解析校验 / coordinate parsing & screening
python3 03_assemble_output.py    # 修订完善版工作簿 / revised audited workbook
python3 04_chnr_build.py         # CHNR 事件表+审计包 / event tables + audit trail
python3 06a_build_iucn_reference.py  # IUCN 最新名录参照（本地DwC包）/ IUCN reference
python3 06b_parse_china_redlist.py  # 中国红色名录2020解析 / China Red List parse
python3 06c_parse_npwa2021.py    # 2021保护名录解析 / protection list parse
python3 06d_conservation_join.py # 四列保护状态接入 / conservation join
python3 05_summary_stats.py      # 分纲汇总 / per-class summaries
cd ..
Rscript figure1a_province_map/01_plot_province_maps_by_class.R
Rscript figure1b_record_points/02_plot_record_points_by_class.R
Rscript figure1c_order_province_year_sankey/03_plot_sankey_by_class.R
```

Python ≥3.9 with `pandas`, `openpyxl`, `geopandas`, `shapely`;
R ≥4.3 with `sf`, `ggplot2`, `dplyr`, `readr`, `readxl`, `cowplot`, `ragg`,
`showtext`, `purrr`. Amphibians and reptiles are analyzed and plotted
**separately** throughout (per-class figures and summary tables).

## Methods in brief / 方法要点

1. **Source revision.** The merged herp table (2,231 rows) was audited cell-by-cell:
   3 header artifact rows removed; 1,155 blank taxonomy/name cells filled from the
   checklist; 1,893 checklist-inconsistent cells corrected with full change logs;
   coordinates unified to WGS84 decimal degrees (swapped pairs fixed, 12 localities
   gazetteer-georeferenced with source and precision notes).
2. **Taxonomic harmonization.** Layered matching (exact Latin → exact Chinese incl.
   checklist aliases → trinomial reduction → fused-name repair → curated synonyms →
   epithet-stem inference guarded by order/family compatibility and an established
   genus-transfer whitelist → genus-level fallback → constrained fuzzy Chinese).
3. **Event screening.** Every row classified as provincial new-record event, new
   species description, or excluded (non-herp, foreign, genus-level, survey
   inventory, companion species, undeterminable), with reasons.
4. **Duplicate resolution.** Species × province events deduplicated by earliest
   publication year; ties flagged for manual review (CBNR rule).
5. **Geography.** Point-in-polygon province assignment and consistency screening
   against the province boundary layer; multi-province reports split into
   per-province events with coordinates assigned only to the containing province.
6. **Conservation status.** Four fields are populated by a guarded join cascade
   (exact Latin → published Latin → exact Chinese → epithet-stem restricted to
   same genus, established genus-transfer pairs, or Chinese-name corroboration):
   - `IUCN_RED_LIST` — categories from the IUCN Red List's own latest
     checklist distribution (DwC archive dated 2026-07-28, retrieved
     2026-08-08; synonym-aware matching against IUCN's accepted names and
     18k herp synonyms; one gap back-filled from a GBIF API snapshot).
     Species absent from the IUCN checklist are coded NE (not evaluated),
     so the field is 100% populated. The archive itself is not
     redistributed here (IUCN terms) — re-fetch via
     `hosted-datasets.gbif.org/datasets/iucn/iucn-latest.zip`.
   - `CHINA_RED_LIST` + `Scientific_name_ChinaRedList` + `Endemic_to_China` —
     中国生物多样性红色名录—脊椎动物卷(2020)（生态环境部·中国科学院公告
     2023年第15号 official PDF; 1,029 herp entries parsed with category and
     endemism columns; the list's own Latin name is kept so synonym
     relationships stay visible; 81% of event rows).
   - `China_Protection_Class` — 国家重点保护野生动物名录(2021年第3号公告)，
     parsed from a structured transcription and spot-validated against the
     official scanned PDF (187 herp entries incl. the genus-level 闭壳龟属
     entry; 36 protected event rows: 4 Class I, 32 Class II).
   The full join audit is in `source_data/conservation/conservation_join_audit.csv`.

## Known limitations / 已知局限

- Provincial "firstness" is approximated by earliest publication year and has not
  yet been verified article-by-article against an authoritative herpetological
  baseline (planned against 中国两栖爬行动物名录 / AmphibiaChina).
- 755 rows await manual adjudication (500 companion-species rows from taxonomic
  papers; 255 rows without record-type evidence) — see
  `audit_quality_control/03_record_screening/`.
- Conservation-status fields remain blank for taxa described after the 2020
  Red List assessment window (legitimately unassessed) and for names not yet
  resolvable against the reference lists (see the join audit in
  `source_data/conservation/`).
- Cross-linking to Frost's *Amphibian Species of the World* and the *Reptile
  Database* is planned but not yet implemented.

## Provenance & credits / 来源与致谢

- Pipeline, package layout and figure styling follow the CBNR dataset and its
  Zenodo release by Ding et al.; figure scripts are adapted from the CBNR
  reproduction scripts.
- Province boundaries and ten-dash line follow the standard map
  (审图号 GS(2019)1822), as used in the CBNR release; maps use an Albers
  equal-area projection with a South China Sea inset.
- Taxonomic backbone: Catalogue of Life China 2026 Annual Checklist (Chordata),
  obtained from <http://www.sp2000.org.cn/>. The checklist file itself is not
  redistributed; see `source_data/README_data_sources.md` for how to obtain it
  when re-running the matching step.

## License / 许可

Code: MIT (intended). Data: CC BY 4.0 intended upon formal release, consistent
with CBNR. 正式发布前请勿外传数据表。
