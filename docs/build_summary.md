# China Herpetofauna New Record dataset (CHNR) v0.1

中国两栖爬行动物省级新分布纪录数据集（草稿版 v0.1，2026-08-07）。
本包参照 CBNR（China Bird New Record dataset, Ding et al., Zenodo 10.5281/zenodo.20809949）
的事件定义、清洗流程与包结构，由《两栖爬行动物数据合并表-8.7修订完善版.xlsx》构建。

## 事件定义 / Event definition
分析单元为 物种×省级行政区 的首次文献记录（同 CBNR）。新种描述单列为伴随表；
非两爬类群、国外记录、属级记录、区系调查清单行、"其他/再发现"类记录均排除并留痕。

## 目录 / Folder overview
- dataset/
  - CHNR_provincial_new_records.csv  清洁省级新纪录事件表（436 行，287 种，32 省级单元）
  - CHNR_new_species.csv             新种描述伴随表（375 种级条目）
  - CHNR_metadata.csv                字段词典
  - CHNR_v0.1.xlsx                   汇总工作簿（含按目/省汇总表）
- audit_quality_control/
  - 02_taxonomy_harmonisation/  分类匹配需复核行
  - 03_record_screening/        全部 2228 源行的去留判定日志（事件表 556；新种表 672；排除 245；排除-待人工判定 755）
  - 04_coordinate_georeferencing/  坐标解析、省界一致性审计（37 行不一致）与地名补全日志
  - 05_duplicate_review/        物种×省份去重日志（最早发表年规则；移除 140 行、91 组）与新种表去重日志
- scripts/chnr_build.py         本包构建脚本（上游：match_species.py / parse_coords.py / assemble_output.py，
                                见 NEW DISTRIBUTION RECORDS/herp_table_revision/）

## 与 CBNR 的差异 / Deviations from CBNR
1. 分类主干仅用《中国生物物种名录》2026（脊索动物门）；未做 Frost ASW / Reptile Database 交叉，
   scientific_name_as_published 保留发表名以便后续对接。
2. 亚种级省级记录未删除，以 Reported_rank 标记（CBNR 为直接排除）。
3. 时间范围未截断（含 1978 等早期文献；CBNR 限 2000–2025）。
4. 保护状态四列为空占位，待接入中国脊椎动物红色名录、国家重点保护名录与特有性表。
5. 省级"首次性"未逐篇对照权威底本核验，暂以物种×省份最早发表年近似；
   待人工判定桶（755 行：新种文献伴随物种 500、类型无线索 255）需人工过一遍。

## 已知局限 / Known caveats
- 名录未匹配的事件行（Scientific_name_COL_China_2026 为空）见 02 审计表，多为异名待考或名录未收录。
- 坐标以原文为准；文字地名地理编码行的精度见修订版"坐标备注"（<5 km 至县级不等）。
- 37 行坐标落点省份与标注省份不一致（04_2），需逐行核实。

数据许可建议 CC BY 4.0（与 CBNR 一致）。
