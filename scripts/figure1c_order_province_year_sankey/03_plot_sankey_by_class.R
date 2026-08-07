#!/usr/bin/env Rscript

# ============================================================
# Figure 1c | 分纲 目->省->年 Sankey 图 / Order -> Province -> Year
# Sankey diagrams built separately for Amphibia and Reptilia.
# 复用 CBNR Figure 2c 的自制贝塞尔流带几何与版式；2000 年前的
# 少量早期文献合并为 "Pre-2000" 节点。
# Reuses the CBNR custom bezier-flow Sankey machinery; sparse
# pre-2000 publication years are pooled into a "Pre-2000" node.
# Input : data/CHNR_provincial_new_records.csv
#         ../figure1a_province_map/input/province_name_mapping.xls
# Output: output/Figure1c_Amphibia.(png|pdf),
#         output/Figure1c_Reptilia.(png|pdf), process tables, log
# ============================================================

suppressPackageStartupMessages({
  library(readxl)
  library(readr)
  library(dplyr)
  library(tidyr)
  library(stringr)
  library(ggplot2)
  library(purrr)
  library(showtext)
  library(sysfonts)
})

set.seed(1234)

get_script_path <- function() {
  cmd_args <- commandArgs(trailingOnly = FALSE)
  file_arg <- grep("^--file=", cmd_args, value = TRUE)
  if (length(file_arg) > 0) {
    return(normalizePath(sub("^--file=", "", file_arg[1]), mustWork = FALSE))
  }
  normalizePath(getwd(), mustWork = TRUE)
}

script_path <- get_script_path()
script_dir <- if (dir.exists(script_path)) script_path else dirname(script_path)
repo_root <- normalizePath(file.path(script_dir, "..", ".."), mustWork = TRUE)

plot_font_family <- "Arial"
plot_font_regular <- "/System/Library/Fonts/Supplemental/Arial.ttf"
plot_font_bold <- "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
if (file.exists(plot_font_regular) && file.exists(plot_font_bold)) {
  font_add(plot_font_family, regular = plot_font_regular, bold = plot_font_bold)
  showtext_auto()
} else {
  plot_font_family <- "sans"
}

records_path <- file.path(repo_root, "data", "CHNR_provincial_new_records.csv")
mapping_path <- file.path(repo_root, "scripts", "figure1a_province_map",
                          "input", "province_name_mapping.xls")
output_tables <- file.path(script_dir, "process")
output_figures <- file.path(script_dir, "output")
dir.create(output_tables, showWarnings = FALSE, recursive = TRUE)
dir.create(output_figures, showWarnings = FALSE, recursive = TRUE)

# 分纲目级配色（与 Figure 1b 一致）/ per-class order palettes (match Fig. 1b)
class_palettes <- list(
  Amphibia = c("Anura" = "#0E8FA8", "Caudata" = "#F06423", "Gymnophiona" = "#8B6FDD"),
  Reptilia = c("Squamata" = "#D9882B", "Testudines" = "#31B85C", "Crocodylia" = "#D31972")
)

save_plot_dual <- function(p, filename_no_ext, width = 30, height = 17, dpi = 420) {
  png_path <- file.path(output_figures, paste0(filename_no_ext, ".png"))
  pdf_path <- file.path(output_figures, paste0(filename_no_ext, ".pdf"))
  ggsave(png_path, p, width = width, height = height, dpi = dpi, bg = "white",
         device = ragg::agg_png, limitsize = FALSE)
  ggsave(pdf_path, p, width = width, height = height, bg = "white",
         device = "pdf", limitsize = FALSE)
}

build_node_positions <- function(values, levels, axis_name, x, gap = 3.2) {
  node_df <- tibble(name = levels) %>%
    left_join(values, by = "name") %>%
    mutate(value = replace_na(value, 0)) %>%
    filter(value > 0)
  node_df %>%
    mutate(
      ymin = lag(cumsum(value + gap), default = 0),
      ymax = ymin + value,
      y = (ymin + ymax) / 2,
      axis = axis_name,
      x = x
    )
}

add_stack_positions <- function(flow_data, node_data, axis_col, sort_cols, suffix) {
  flow_data %>%
    arrange(across(all_of(c(axis_col, sort_cols)))) %>%
    group_by(.data[[axis_col]]) %>%
    mutate(
      stack_ymin = lag(cumsum(n_records), default = 0),
      stack_ymax = stack_ymin + n_records
    ) %>%
    ungroup() %>%
    left_join(
      node_data %>% select(node_name = name, node_ymin = ymin),
      by = setNames("node_name", axis_col)
    ) %>%
    mutate(
      "{suffix}_ymin" := node_ymin + stack_ymin,
      "{suffix}_ymax" := node_ymin + stack_ymax
    ) %>%
    select(-stack_ymin, -stack_ymax, -node_ymin)
}

make_flow_polygon <- function(id, order_grp, x0, x1, y0min, y0max, y1min, y1max,
                              n = 36, knot.pos = 0.38) {
  t <- seq(0, 1, length.out = n)
  bezier <- function(p0, p1, p2, p3) {
    (1 - t)^3 * p0 + 3 * (1 - t)^2 * t * p1 + 3 * (1 - t) * t^2 * p2 + t^3 * p3
  }
  dx <- x1 - x0
  x <- bezier(x0, x0 + knot.pos * dx, x1 - knot.pos * dx, x1)
  smooth <- bezier(0, 0, 1, 1)
  upper <- tibble(x = x, y = y0max + (y1max - y0max) * smooth)
  lower <- tibble(x = rev(x), y = rev(y0min + (y1min - y0min) * smooth))
  bind_rows(upper, lower) %>%
    mutate(flow_id = id, order_grp = order_grp)
}

theme_ref <- function(base_size = 12, base_family = "sans") {
  theme_minimal(base_size = base_size, base_family = base_family) +
    theme(
      plot.title = element_text(face = "bold", size = base_size + 2, color = "black"),
      plot.subtitle = element_text(size = base_size, color = "#303030"),
      panel.grid = element_blank(),
      axis.text = element_blank(),
      axis.ticks = element_blank()
    )
}

# 省名后缀剥离 / strip province suffixes
strip_prov <- function(x) {
  str_replace(x, "((壮族|回族|维吾尔)?自治区|特别行政区|省|市)$", "")
}

province_mapping <- read_excel(mapping_path) %>%
  transmute(NAME = trimws(as.character(NAME)),
            province_en = trimws(as.character(Province_EN))) %>%
  mutate(province_en = ifelse(province_en == "Tibet", "Xizang", province_en),
         province_short = strip_prov(NAME))

records <- read_csv(records_path, show_col_types = FALSE) %>%
  transmute(
    class_en = recode(Class_CN, "两栖纲" = "Amphibia", "爬行纲" = "Reptilia"),
    species = coalesce(Scientific_name_COL_China_2026, Scientific_name_as_published,
                       Chinese_name_COL_China_2026, Chinese_name_as_published),
    order = str_squish(OrderLA_COL_China_2026),
    province_short = str_squish(New_distribution_province),
    year_num = suppressWarnings(as.integer(Source_publication_year))
  ) %>%
  left_join(province_mapping %>% select(province_short, province_en),
            by = "province_short") %>%
  mutate(year_lab = ifelse(!is.na(year_num) & year_num < 2000, "Pre-2000",
                           as.character(year_num))) %>%
  filter(!is.na(class_en), !is.na(order), !is.na(province_en), !is.na(year_lab))

build_sankey_for_class <- function(cls_en) {
  pal <- class_palettes[[cls_en]]
  clean <- records %>%
    filter(class_en == cls_en) %>%
    distinct(species, order, province_en, year_lab) %>%
    rename(province = province_en)

  order_rank <- clean %>% count(order, name = "n_records") %>% arrange(desc(n_records), order)
  province_rank <- clean %>% count(province, name = "n_records") %>% arrange(desc(n_records), province)
  year_levels <- clean %>%
    distinct(year_lab) %>%
    mutate(y = ifelse(year_lab == "Pre-2000", -Inf, suppressWarnings(as.numeric(year_lab)))) %>%
    arrange(desc(y)) %>%
    pull(year_lab)

  sankey_df <- clean %>%
    mutate(
      order_grp = factor(order, levels = order_rank$order),
      province_grp = factor(province, levels = province_rank$province),
      year_f = factor(year_lab, levels = year_levels)
    ) %>%
    arrange(order_grp, province_grp, year_f, species) %>%
    transmute(order_grp, province_grp, year_f, n_records = 1,
              flow_id = row_number(), province_in_shuffle = runif(n()))

  write.csv(sankey_df,
            file.path(output_tables, paste0("chnr_sankey_", tolower(cls_en), ".csv")),
            row.names = FALSE, fileEncoding = "UTF-8")

  sankey_palette <- pal[names(pal) %in% levels(sankey_df$order_grp)]

  node_gap <- 10
  node_width <- 0.035
  flow_gap <- node_width / 2
  axis_x_order <- 1
  axis_x_province <- 1.92
  axis_x_year <- 3
  order_display_levels <- rev(levels(sankey_df$order_grp))
  province_display_levels <- rev(levels(sankey_df$province_grp))
  year_display_levels <- levels(sankey_df$year_f)

  order_nodes <- build_node_positions(
    sankey_df %>% group_by(name = order_grp) %>% summarise(value = sum(n_records), .groups = "drop"),
    order_display_levels, "Order", axis_x_order, gap = node_gap)
  province_nodes <- build_node_positions(
    sankey_df %>% group_by(name = province_grp) %>% summarise(value = sum(n_records), .groups = "drop"),
    province_display_levels, "Province", axis_x_province, gap = node_gap)
  year_nodes <- build_node_positions(
    sankey_df %>% group_by(name = year_f) %>% summarise(value = sum(n_records), .groups = "drop"),
    year_display_levels, "Year", axis_x_year, gap = node_gap)

  province_palette <- setNames(
    colorRampPalette(c("#FF6A00", "#F5A900", "#F0D978", "#54D3BD", "#3BA7D6", "#007FA3"))(nrow(province_nodes)),
    province_nodes$name)
  year_palette <- setNames(
    colorRampPalette(c("#FF6A00", "#F5A900", "#F0D978", "#54D3BD", "#3BA7D6", "#007FA3"))(nrow(year_nodes)),
    year_nodes$name)
  node_palette <- c(
    setNames(sankey_palette[as.character(order_nodes$name)],
             paste("Order", order_nodes$name, sep = "__")),
    setNames(province_palette[as.character(province_nodes$name)],
             paste("Province", province_nodes$name, sep = "__")),
    setNames(year_palette[as.character(year_nodes$name)],
             paste("Year", year_nodes$name, sep = "__")))
  plot_palette <- c(sankey_palette, node_palette)

  nodes <- bind_rows(order_nodes, province_nodes, year_nodes) %>%
    mutate(
      label = as.character(name),
      node_key = paste(axis, name, sep = "__"),
      label_x = case_when(
        axis == "Order" ~ x - node_width * 1.4,
        axis == "Province" ~ x + node_width * 0.65,
        TRUE ~ x + node_width * 0.9
      ),
      label_hjust = if_else(axis == "Order", 1, 0),
      label_size = 26
    )

  flow_positions <- sankey_df %>%
    mutate(
      order_rank_display = match(as.character(order_grp), order_display_levels),
      province_rank_display = match(as.character(province_grp), province_display_levels),
      year_rank_display = match(as.character(year_f), year_display_levels)
    ) %>%
    add_stack_positions(order_nodes, "order_grp",
                        c("province_rank_display", "year_rank_display"), "order") %>%
    add_stack_positions(province_nodes, "province_grp",
                        c("province_in_shuffle"), "province_in") %>%
    add_stack_positions(province_nodes, "province_grp",
                        c("year_rank_display", "order_rank_display"), "province_out") %>%
    add_stack_positions(year_nodes, "year_f",
                        c("province_rank_display", "order_rank_display"), "year")

  flow_polygons_12 <- pmap_dfr(
    list(flow_positions$flow_id, as.character(flow_positions$order_grp),
         flow_positions$order_ymin, flow_positions$order_ymax,
         flow_positions$province_in_ymin, flow_positions$province_in_ymax),
    \(flow_id, order_grp, y0min, y0max, y1min, y1max) {
      make_flow_polygon(paste0(flow_id, "_12"), order_grp,
                        axis_x_order + flow_gap, axis_x_province - flow_gap,
                        y0min, y0max, y1min, y1max)
    })
  flow_polygons_23 <- pmap_dfr(
    list(flow_positions$flow_id, as.character(flow_positions$order_grp),
         flow_positions$province_out_ymin, flow_positions$province_out_ymax,
         flow_positions$year_ymin, flow_positions$year_ymax),
    \(flow_id, order_grp, y0min, y0max, y1min, y1max) {
      make_flow_polygon(paste0(flow_id, "_23"), order_grp,
                        axis_x_province + flow_gap, axis_x_year - flow_gap,
                        y0min, y0max, y1min, y1max)
    })
  flow_polygons <- bind_rows(flow_polygons_12, flow_polygons_23)

  plot_ymax <- max(nodes$ymax) + node_gap
  axis_label_y <- -0.035 * plot_ymax
  axis_labels <- tibble(
    x = c(axis_x_order, axis_x_province, axis_x_year),
    y = axis_label_y,
    label = c("Order", "Province", "Year"))
  class_label <- tibble(x = 0.62, y = plot_ymax * 0.985, label = cls_en)

  p_sankey <- ggplot() +
    geom_polygon(data = flow_polygons,
                 aes(x = x, y = y, group = flow_id, fill = order_grp),
                 alpha = 0.4, color = NA) +
    geom_rect(data = nodes %>% filter(axis == "Order"),
              aes(xmin = x - node_width / 2, xmax = x + node_width / 2,
                  ymin = ymin, ymax = ymax, fill = node_key),
              color = "white", linewidth = 0.28) +
    geom_segment(data = nodes %>% filter(axis %in% c("Province", "Year")),
                 aes(x = x, xend = x, y = ymin, yend = ymax),
                 color = "black", linewidth = 0.75, lineend = "butt") +
    geom_text(data = nodes,
              aes(x = label_x, y = y, label = label, size = label_size,
                  hjust = label_hjust),
              color = "black", family = plot_font_family, lineheight = 0.92) +
    geom_text(data = axis_labels, aes(x = x, y = y, label = label),
              color = "black", family = plot_font_family, fontface = "bold", size = 38) +
    geom_text(data = class_label, aes(x = x, y = y, label = label),
              color = "black", family = plot_font_family,
              fontface = "bold.italic", size = 42, hjust = 0) +
    scale_size_identity() +
    scale_fill_manual(values = plot_palette, guide = "none") +
    scale_x_continuous(breaks = NULL, limits = c(0.25, 3.38), expand = c(0, 0)) +
    scale_y_continuous(limits = c(axis_label_y * 1.6, plot_ymax * 1.02),
                       expand = c(0.01, 0.01)) +
    labs(x = NULL, y = NULL) +
    theme_ref(base_size = 28, base_family = plot_font_family)

  save_plot_dual(p_sankey, paste0("Figure1c_", cls_en))
  nrow(clean)
}

log_lines <- c(paste0("Records: ", records_path))
for (cls in c("Amphibia", "Reptilia")) {
  n <- build_sankey_for_class(cls)
  log_lines <- c(log_lines, paste0(cls, ": ", n, " unique order-province-year flows"))
}
writeLines(log_lines, con = file.path(output_figures, "Figure1c_render_log.txt"))
cat(paste(log_lines, collapse = "\n"), "\n")
