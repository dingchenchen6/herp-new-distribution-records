// ============================================================
// Build the CHNR data-paper manuscript (Scientific Data style,
// mirroring the CBNR manuscript). All quantitative statements
// come from docs/manuscript_stats.json — do not edit numbers here.
// 生成 CHNR 数据论文 DOCX；所有数字来自 manuscript_stats.json。
// ============================================================
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ImageRun, BorderStyle,
} = require("docx");

const ROOT = path.resolve(__dirname, "..");
const FIG = (f) => fs.readFileSync(path.join(ROOT, "figures", f));

const FONT = "Times New Roman";
const run = (t, o = {}) => new TextRun({ text: t, font: FONT, size: 22, ...o });
const ital = (t) => run(t, { italics: true });
const p = (children, o = {}) =>
  new Paragraph({ children: Array.isArray(children) ? children : [run(children)],
    spacing: { after: 160, line: 300 }, alignment: AlignmentType.JUSTIFIED, ...o });
const h1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1,
  spacing: { before: 240, after: 120 },
  children: [run(t, { bold: true, size: 26 })] });
const h2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2,
  spacing: { before: 200, after: 100 },
  children: [run(t, { bold: true, size: 23 })] });
const fig = (file, w, h) => new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { before: 120, after: 60 },
  children: [new ImageRun({ type: "png", data: FIG(file),
    transformation: { width: w, height: h } })] });
const legend = (label, text) => p([run(label, { bold: true }), run(" " + text)],
  { spacing: { after: 240 } });

// ---- Table 1 from CSV / 从 CSV 读取 Table 1 ----
const t1rows = fs.readFileSync(path.join(ROOT, "results/Table1_order_summary.csv"), "utf-8")
  .replace(/^﻿/, "").trim().split("\n").map((l) => l.split(","));
const T1HEAD = ["Class", "Order", "Newly recorded species", "New-record events",
  "Source papers", "% of events", "Coverage of Chinese species pool (%)"];
const cell = (t, bold = false) => new TableCell({
  width: { size: 1300, type: WidthType.DXA },
  borders: { top: { style: BorderStyle.SINGLE, size: 4 }, bottom: { style: BorderStyle.SINGLE, size: 4 },
    left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE } },
  children: [new Paragraph({ children: [run(t, { bold, size: 20 })] })] });
const table1 = new Table({
  columnWidths: [1300, 1300, 1300, 1300, 1300, 1300, 1300],
  width: { size: 9100, type: WidthType.DXA },
  rows: [new TableRow({ children: T1HEAD.map((t) => cell(t, true)) })].concat(
    t1rows.slice(1).map((r) => new TableRow({
      children: [r[0] === "两栖纲" ? "Amphibia" : "Reptilia", r[1], r[3], r[4], r[5], r[6], r[7] ?? ""]
        .map((t) => cell(String(t))) }))),
});

const children = [
  new Paragraph({ alignment: AlignmentType.LEFT, spacing: { after: 200 },
    children: [run("A curated dataset of provincial-level new distribution records and newly described species of amphibians and reptiles in China", { bold: true, size: 30 })] }),
  p([run("Chenchen Ding", { bold: true }), run("1"), run("*"),
    run("  [co-author list and affiliations to be confirmed by the corresponding author]", { italics: true, color: "808080" })]),
  p("1 Institute of Ecology and State Key Laboratory for Vegetation Structure, Function and Construction, College of Urban and Environmental Sciences, Peking University, Beijing 100871, China"),
  p("*Correspondence: chenchen.ding@pku.edu.cn"),

  h1("Abstract"),
  p("Amphibians and reptiles are among the most threatened and most rapidly re-circumscribed vertebrates, yet their documented distributions remain strikingly incomplete, a persistent expression of the Wallacean shortfall. New distribution records published in local-language journals continually update where species actually occur, but they are scattered, taxonomically heterogeneous and rarely propagated into global biodiversity infrastructures. Here we present the China Herpetofauna New Record dataset (CHNR), a peer-reviewed literature-derived, taxonomically standardized and georeferenced dataset for Chinese amphibians and reptiles. The core release comprises 437 validated provincial-level new-record events, representing 288 resolved species in 4 orders, 30 families and 108 genera across 32 provincial-level administrative units, compiled from 340 source publications (publication years 1930–2026; 90.6% since 2000). A companion table documents 375 records of newly described species (1822–2025; 97.3% since 2000; 311 publications). Scientific names are harmonized to the Catalogue of Life China 2026 Annual Checklist while preserving the names as published, and every record carries four conservation-status fields cross-linked to the IUCN Red List, China's Biodiversity Red List (2020), the National Key Protected Wildlife List (2021) and national endemism. All cleaning decisions are reproducible from scripted pipelines with row-level audit tables. CHNR provides an empirical basis for updating herpetofaunal distribution knowledge, diagnosing survey bias, and supporting monitoring and conservation planning."),

  h1("Background & Summary"),
  p("Reliable knowledge of species' spatiotemporal distributions underpins biogeography, macroecology and conservation planning, yet occurrence information remains incomplete and uneven across taxa, space and time — the Wallacean shortfall (refs 1–3). The deficit is particularly consequential for amphibians and reptiles: globally, 40.7% of amphibians and 21.1% of reptiles are threatened with extinction (refs 4,5), while both groups combine low vagility, small ranges and fast-moving taxonomy, so that expert range maps and aggregated databases lag behind the primary literature (refs 6,7)."),
  p("China supports an exceptionally diverse and rapidly growing herpetofauna. The Catalogue of Life China 2026 Annual Checklist recognizes 769 amphibian and 729 reptile species, and 17.1% of amphibian and 10.2% of reptile species on the national checklist as of 2019 had been described or newly recorded within the preceding five years alone (ref 8), a pace of discovery that has since continued (ref 9). China's official Biodiversity Red List assessments classify 43.1% of amphibians and 29.7% of reptiles as threatened (ref 10), figures well above global averages. New provincial records and species descriptions therefore accumulate rapidly, but they are dispersed across Chinese-language zoological journals, use heterogeneous taxonomy at publication time, and are only slowly and partially incorporated into infrastructures such as GBIF or the IUCN Red List (refs 3,6)."),
  p("Building on the China Bird New Record dataset (CBNR), which established an event-based, audit-trailed workflow for provincial-level new records of birds (ref 11), we compiled the analogous resource for amphibians and reptiles. Because taxonomic discovery is a far larger component of distributional knowledge in herpetology than in ornithology, CHNR releases two coupled products: a provincial new-record event table for species already known from China, and a companion table of newly described species with their type localities. Together they provide a transparent, reusable evidence base for range updates, survey-gap diagnosis and conservation assessment."),

  h1("Methods"),
  h2("Scope and event definition"),
  p("The core analytical unit of the event table is a species–province event: the first formally documented occurrence of a known species in a Chinese provincial-level administrative unit, reported in peer-reviewed literature. Records identified only to genus, records outside China, records of non-target taxa, and re-documentation of a species–province combination already established by an earlier publication were excluded from the event table but retained in audit tables. Newly described species (including species described from China with their type localities) are treated as a distinct record class and released in the companion new-species table rather than being mixed with provincial events. Unlike CBNR, the temporal scope was not restricted to 2000 onwards: the event table spans source publication years 1930–2026, with a median of 2018 and 90.6% of events published since 2000."),
  h2("Literature compilation and screening"),
  p("Candidate records were compiled from peer-reviewed publications retrieved through the China National Knowledge Infrastructure (CNKI) and Google Scholar, supplemented by systematic screening of major Chinese zoological journals (e.g., Chinese Journal of Zoology, Sichuan Journal of Zoology, Chinese Journal of Wildlife) and of the herpetological literature aggregated in Zootaxa, ZooKeys and Asian Herpetological Research. From 2,228 compiled candidate rows, screening assigned 556 rows to the provincial-event class and 672 rows to the new-species class, excluded 245 rows (non-target taxa such as fishes, invertebrates and plants introduced by upstream compilation; foreign records without Chinese relevance; unrecoverable rows), and initially set aside 755 rows for manual adjudication. These were subsequently resolved by evidence-based triage and verification against the archived source PDFs: 680 rows were excluded with documented reasons (rows without provincial information, foreign records, re-documentations, survey entries and companion-species records in taxonomic papers), one verified provincial event was recovered (Diploderma chapaense for Yunnan, a first record arising from a misidentification correction), 16 rows were flagged as probable overlooked new-species entries pending confirmation, and 10 rows remain under review; every verdict and its rationale is preserved row-by-row in the screening log and the adjudication ledger (audit tables 03 and 06). Multi-province reports were split into per-province events, and species–province duplicates were resolved by retaining the earliest publication (231 later re-documentation rows moved to audit table 05), yielding 437 validated events."),
  h2("Taxonomic harmonization"),
  p("Scientific names were harmonized to the Catalogue of Life China 2026 Annual Checklist through a layered, scripted matcher: exact Latin-name match; exact Chinese-name match including the checklist's bracketed and slash-separated aliases; trinomial-to-binomial subspecies merging; repair of fused or misspelt Latin names; a curated synonym map; and epithet-stem inference for genus transfers, guarded by order- and family-compatibility checks plus a whitelist of established genus splits (e.g., Megophrys–Boulenophrys, Tylototriton–Yaotriton, Japalura–Diploderma). Names as published are always preserved in dedicated columns, and 52 row-level taxonomic corrections are logged in audit table 02. Inference-based matches carry explicit review flags. Of the 437 events, 423 rows resolve to 288 checklist species; 14 rows (13 distinct names) remain at published-name level, annotated with the reason (checklist gaps, unresolved synonyms, or one record — 'Hu Wa' from Xinjiang, probably Pelophylax ridibundus — lacking both a Latin name and a source citation)."),
  h2("Georeferencing and spatial screening"),
  p("Coordinates reported in source papers were converted to WGS84 decimal degrees from decimal, degree–minute and degree–minute–second formats, tolerating full-width characters and range expressions (ranges take midpoints, flagged). Latitude–longitude swaps were detected and corrected (5 cases), and coordinates inconsistent with the stated province against provincial bounding boxes were flagged for review (37 flags, resolved or annotated in audit table 04). Where only a locality name was available, coordinates were assigned from type descriptions, published gazetteers or OpenStreetMap, with the source and precision (site to county level) recorded per row in the Coordinate_basis field; province-only records were left without coordinates rather than being assigned centroids. In the released event table, 83.5% of rows carry coordinates (253 from the source publication, 111 georeferenced or supplemented, 16 rows from multi-province splitting intentionally without points), and 93.1% of new-species records carry type-locality coordinates."),
  h2("Field harmonization"),
  p("Habitat descriptions were harmonized into twelve base categories (forest; stream/river; wetland/still water; shrubland/grassland; farmland/plantation; artificial habitat; alpine scree/rocky terrain; cave; desert/sand; coastal/marine; mixed; other), with multi-habitat reports encoded as composite mixed categories; original wording is retained in Habitat_raw (63% of events categorized). Evidence types were standardized to specimen, photograph/live observation, molecular, acoustic and combinations thereof. Altitude was parsed to numeric metres (60.1% of events), and discovery dates to ISO format where recoverable (70.4%). Publication metadata comprise the standard citation, authors, year, journal and DOI (54% of events; DOIs are uncommon among older Chinese-journal papers)."),
  h2("Conservation status"),
  p("Four conservation fields were joined per species through a guarded cascade (exact Latin → published Latin → exact Chinese name → epithet stem restricted to the same genus, whitelisted genus transfers or Chinese-name corroboration), with every join step logged. IUCN Red List categories were taken from the IUCN Red List's own latest checklist distribution (Darwin Core archive dated 28 July 2026, retrieved 8 August 2026), matched against IUCN accepted names and c. 18,000 herpetological synonyms; species absent from the IUCN checklist are coded NE, so the field is fully populated. Categories and the endemism column were parsed from the official PDF of the China Biodiversity Red List — Vertebrates (2020) using a coordinate-anchored table parser (1,029 amphibian and reptile entries recovered, matching the checklist totals), and the Red List's own binomial is kept in a dedicated column so that synonym relationships remain visible. Protection classes follow the National Key Protected Wildlife List (2021), parsed from a structured transcription and spot-validated page-by-page against the official scanned announcement (187 herpetological entries including the genus-level Cuora listing)."),
  h2("Reproducibility"),
  p("The release is produced by a fully scripted pipeline (Python for matching, parsing, coordinate handling and conservation joins; R for figures), with intermediate decisions written to five audit tables (taxonomy review, record screening, coordinate parsing/audit/completion, duplicate resolution). Re-running the numbered scripts regenerates the release end-to-end from the source workbook."),

  h1("Data Records"),
  p("The CHNR release is organized as a core event table, a companion new-species table, a field dictionary and audit tables, distributed as UTF-8 CSV files and a bundled Excel workbook in the public repository (https://github.com/dingchenchen6/herp-new-distribution-records), with an archival copy to be deposited on Zenodo upon acceptance."),
  p("CHNR_provincial_new_records.csv contains 437 events with 44 fields covering taxonomy (names as published; Catalogue of Life China 2026 names; the China Red List's binomial; class, order, family, genus in Chinese and Latin; match method and note), spatial context (new-distribution province and its basis, discovery sites, WGS84 coordinates and their basis, altitude), temporal context (discovery date raw and parsed, publication year), ecological context (habitat raw and categorized), evidence (evidence type, voucher), record typology, duplicate-group identifier, four conservation fields, and full source metadata."),
  p("CHNR_new_species.csv contains 375 newly described species records with 31 analogous fields centred on type localities (province, coordinates, altitude, habitat, holotype/paratype evidence) and description metadata; 85.3% of these species are already incorporated in the Catalogue of Life China 2026, the remainder being very recent descriptions."),
  p("Audit tables 02–05 (taxonomy review, n = 52 corrections; record screening, n = 2,228 verdicts; coordinate parsing, audit and completion logs; duplicate resolution, n = 231 re-documentation rows and the new-species deduplication log) preserve row-level provenance from the source workbook (Source_row) through every cleaning decision."),

  h1("Data Overview"),
  p("Events are dominated by Squamata (221 events, 127 species) and Anura (195 events, 145 species), together 95.2% of events, with smaller contributions from Caudata (17 events) and Testudines (3 events); no provincial events involve Crocodylia or Gymnophiona (Table 1). Newly recorded species represent 22.0% (Anura), 12.3% (Caudata), 18.8% (Squamata) and 6.2% (Testudines) of the corresponding Chinese species pools, indicating that even the best-surveyed groups continue to yield distributional novelty. Spatially, events concentrate in the southwestern and southern mountain systems — Yunnan (61), Guizhou (42), Guangxi (40), Guangdong (37), Hubei and Hunan (26 each) — consistent with high herpetofaunal richness, karst and montane habitat complexity, and intensified recent survey effort (Figures 1 and 2). Temporally, events rise steeply after 2010 (73.4% of events published since 2010), mirroring the expansion of provincial surveys, molecular identification and integrative taxonomy (Figure 3). Among assessed events, 23.2% involve species listed as threatened (VU, EN or CR) on China's Biodiversity Red List, 36 events involve nationally protected species (4 Class I, 32 Class II), and 158 events (resolved to 107 species) involve Chinese endemics — so a substantial fraction of distributional novelty concerns exactly the taxa of highest conservation concern."),
  p([run("Table 1 | ", { bold: true }), run("Summary of provincial-level new-record events by order in the CHNR release. Coverage is the percentage of species in the Catalogue of Life China 2026 pool of that order with at least one validated event.")]),
  table1,
  new Paragraph({ children: [run("")] }),
  fig("Figure1a_Amphibia.png", 300, 260), fig("Figure1a_Reptilia.png", 300, 260),
  legend("Figure 1 |", "Provincial counts of validated new-record events for amphibians (top) and reptiles (bottom). Warmer colours indicate more events; the South China Sea inset and the ten-dash line follow the standard base map."),
  fig("Figure1b_Amphibia.png", 300, 260), fig("Figure1b_Reptilia.png", 300, 260),
  legend("Figure 2 |", "Georeferenced localities of new-record events coloured by order, for amphibians (top) and reptiles (bottom)."),
  fig("Figure1c_Amphibia.png", 310, 230), fig("Figure1c_Reptilia.png", 310, 230),
  legend("Figure 3 |", "Alluvial diagrams linking order, new-distribution province and publication year for amphibian (top) and reptile (bottom) events; ribbon width is proportional to event counts."),

  h1("Technical Validation"),
  p("Validation operated at four levels. (1) Taxonomic consistency: all names were passed through the layered matcher against the Catalogue of Life China 2026; 52 row-level corrections (misassigned families/genera, fused names, spelling variants) are logged, inference-based matches carry review flags, and cross-checks among Chinese names, published Latin names and checklist names left 14 event rows unresolved, each annotated with the reason. (2) Spatial plausibility: every coordinate was parsed and screened against the national extent and the stated province; 5 latitude–longitude swaps were corrected, 37 province-inconsistent or out-of-range values were flagged and resolved or annotated, and two clusters of displaced type-locality coordinates were restored from the original descriptions. (3) Event-level duplicate control: species–province combinations are unique in the release, with the 231 later re-documentation rows preserved in the audit log; 91 surviving events carry their duplicate-group identifier. (4) Conservation joins: IUCN categories obtained from the IUCN checklist distribution were cross-checked against an independent GBIF API snapshot (7 discrepancies, all reflecting IUCN updates or archive gaps, reconciled and documented); the China Red List parser recovered 515 reptile and 514 amphibian entries, matching the published checklist totals (511 and 515), with spot checks against known categories; the protection-list transcription was validated page-by-page against the official scanned PDF. Remaining limitations — one record without a source citation, 14 unresolved names, 54% DOI coverage and 83.5% coordinate coverage — are documented and traceable rather than silently imputed."),

  h1("Usage Notes"),
  p("CHNR supports provincial faunal updates, range-edge and range-shift analyses, survey-gap and sampling-bias diagnosis, integrative taxonomic history studies and conservation planning. Three caveats apply. First, a provincial new record is an administrative-unit event: it indicates newly documented presence, not colonization date, occupancy or abundance, and its timing conflates ecological change with observation effort. Second, herpetological taxonomy moves quickly; the release freezes the Catalogue of Life China 2026 as its backbone while preserving names as published and the Red List's binomials, so users can re-harmonize to other backbones (e.g., Frost's Amphibian Species of the World, the Reptile Database) via the provided name columns. Third, the new-species table documents descriptions, not subsequent range knowledge; type localities should not be treated as full ranges. The dataset integrates readily with AmphibiaChina, the Reptile Database, GBIF occurrence data, trait compilations and spatial covariates via the standardized name and coordinate fields."),

  h1("Data availability"),
  p("The dataset, audit tables, figures and documentation are openly available at https://github.com/dingchenchen6/herp-new-distribution-records (v1.0). An archival snapshot will be deposited on Zenodo with a versioned DOI upon manuscript acceptance. Third-party reference datasets (Catalogue of Life China 2026; the IUCN checklist distribution) are not redistributed; retrieval instructions are documented in the repository."),
  h1("Code availability"),
  p("All pipeline scripts (Python 3.9: taxonomic matching, coordinate parsing, dataset assembly, conservation joins, statistics; R 4.5.1: figures) are versioned in the same repository under scripts/, with the exact run order documented in the README."),

  h1("References"),
  ...[
    "1. Hortal, J. et al. Seven shortfalls that beset large-scale knowledge of biodiversity. Annu. Rev. Ecol. Evol. Syst. 46, 523–549 (2015).",
    "2. Meyer, C., Kreft, H., Guralnick, R. & Jetz, W. Global priorities for an effective information basis of biodiversity distributions. Nat. Commun. 6, 8221 (2015).",
    "3. Troudet, J. et al. Taxonomic bias in biodiversity data and societal preferences. Sci. Rep. 7, 9132 (2017).",
    "4. Luedtke, J. A. et al. Ongoing declines in the world's amphibians in the face of the Second Global Amphibian Assessment. Nature 622, 308–314 (2023).",
    "5. Cox, N. et al. A global reptile assessment highlights shared conservation needs of tetrapods. Nature 605, 285–290 (2022).",
    "6. Roll, U. et al. The global distribution of tetrapods reveals a need for targeted reptile conservation. Nat. Ecol. Evol. 1, 1677–1682 (2017).",
    "7. Jetz, W. & Pyron, R. A. The interplay of past diversification and evolutionary isolation with present imperilment across the amphibian tree of life. Nat. Ecol. Evol. 2, 850–858 (2018).",
    "8. Wang, K. et al. The updated checklists of amphibians and reptiles of China. Biodivers. Sci. 28, 189–218 (2020).",
    "9. AmphibiaChina. The database of Chinese amphibians. Kunming Institute of Zoology, CAS. http://www.amphibiachina.org (accessed August 2026).",
    "10. Ministry of Ecology and Environment & Chinese Academy of Sciences. China Biodiversity Red List — Vertebrates (2020). Announcement No. 15 of 2023 (2023).",
    "11. Ding, C. et al. A dataset of provincial-level new distribution records for birds in China from 2000 to 2025. Zenodo https://doi.org/10.5281/zenodo.20759735 (2026).",
    "12. Catalogue of Life China. 2026 Annual Checklist of Catalogue of Life China. The Biodiversity Committee of the Chinese Academy of Sciences. http://www.sp2000.org.cn (2026).",
    "13. IUCN. The IUCN Red List of Threatened Species (latest checklist distribution, archive of 28 July 2026). https://www.iucnredlist.org (2026).",
    "14. National Forestry and Grassland Administration & Ministry of Agriculture and Rural Affairs. National Key Protected Wildlife List. Announcement No. 3 of 2021 (2021).",
    "15. Jiang, Z. et al. Red List of China's Vertebrates. Biodivers. Sci. 24, 500–551 (2016).",
    "16. Cai, B., Wang, Y., Chen, Y. & Li, J. A revised taxonomy for Chinese reptiles. Biodivers. Sci. 23, 365–382 (2015).",
    "17. Fei, L., Ye, C. & Jiang, J. Colored Atlas of Chinese Amphibians and Their Distributions (Sichuan Publishing House of Science and Technology, 2012).",
    "18. Zhao, E. & Adler, K. Herpetology of China (Society for the Study of Amphibians and Reptiles, 1993).",
    "19. Uetz, P., Freed, P., Aguilar, R. & Hošek, J. (eds). The Reptile Database. http://www.reptile-database.org (accessed August 2026).",
    "20. Frost, D. R. Amphibian Species of the World: an Online Reference. American Museum of Natural History. https://amphibiansoftheworld.amnh.org (accessed August 2026).",
    "21. Wieczorek, J. et al. Darwin Core: an evolving community-developed biodiversity data standard. PLoS ONE 7, e29715 (2012).",
    "22. Chapman, A. D. & Wieczorek, J. R. Georeferencing Best Practices (GBIF Secretariat, 2020).",
    "23. Zizka, A. et al. CoordinateCleaner: standardized cleaning of occurrence records from biological collection databases. Methods Ecol. Evol. 10, 744–751 (2019).",
  ].map((t) => p(t, { alignment: AlignmentType.LEFT, spacing: { after: 80 } })),

  h1("Acknowledgements"),
  p("[To be completed: funding, data contributors and survey teams.]"),
  h1("Author contributions"),
  p("[To be completed after the author list is confirmed.] C.D. conceived the dataset, designed and implemented the curation pipeline, performed validation and wrote the manuscript."),
  h1("Competing interests"),
  p("The authors declare no competing interests."),
];

const doc = new Document({
  styles: { default: { document: { run: { font: FONT, size: 22 } } } },
  sections: [{ properties: {}, children }],
});
Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(path.join(__dirname, "CHNR_manuscript_ScientificData_draft.docx"), buf);
  console.log("written: CHNR_manuscript_ScientificData_draft.docx");
});
