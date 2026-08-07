#!/usr/bin/env Rscript

# ============================================================
# Figure 1a | 分纲省级新纪录计数地图 / Province-level counts of
# herp new records, mapped separately for Amphibia and Reptilia.
# 参照 CBNR Figure 2a 脚本改造（同投影、同图饰、含南海插图）。
# Adapted from the CBNR Figure 2a script (same projection,
# styling, ten-dash line and South China Sea inset).
# Input : data/CHNR_provincial_new_records.csv
# Output: output/Figure1a_Amphibia.(png|pdf),
#         output/Figure1a_Reptilia.(png|pdf), render log
# ============================================================

suppressPackageStartupMessages({
  library(dplyr)
  library(ggplot2)
  library(readr)
  library(readxl)
  library(stringr)
  library(sf)
  library(cowplot)
  library(ragg)
})

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

records_path <- file.path(repo_root, "data", "CHNR_provincial_new_records.csv")
mapping_path <- file.path(script_dir, "input", "province_name_mapping.xls")
china_shp_path <- file.path(script_dir, "input", "province_boundaries.shp")
ten_dash_path <- file.path(script_dir, "input", "ten_dash_line.shp")
output_dir <- file.path(script_dir, "output")
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

proj_crs <- "+proj=aea +lat_1=25 +lat_2=47 +lat_0=0 +lon_0=105 +datum=WGS84 +units=m +no_defs"

# 省名后缀剥离得到简名 / strip suffixes to short province names
strip_prov <- function(x) {
  str_replace(x, "((壮族|回族|维吾尔)?自治区|特别行政区|省|市)$", "")
}

province_offsets <- tibble::tribble(
  ~NAME, ~lon, ~lat,
  "北京市", 116.9, 40.35,
  "天津市", 118.9, 39.1,
  "上海市", 122.25, 31.0,
  "内蒙古自治区", 108.4, 41.7,
  "广东省", 112.6, 23.1,
  "香港特别行政区", 115.35, 22.15,
  "海南省", 110.2, 18.3
)

format_lon <- function(x) sprintf("%d°E", as.integer(x))
format_lat <- function(x) sprintf("%d°N", as.integer(x))

build_graticule_labels <- function(crs_string) {
  lon_breaks <- seq(75, 135, by = 15)
  lat_breaks <- seq(15, 60, by = 15)
  lon_labels <- st_as_sf(
    data.frame(lon = lon_breaks, lat = 12.2, label = format_lon(lon_breaks)),
    coords = c("lon", "lat"), crs = 4326
  ) %>%
    st_transform(crs_string) %>%
    mutate(x = st_coordinates(.)[, 1], y = st_coordinates(.)[, 2]) %>%
    st_drop_geometry()
  lat_labels <- st_as_sf(
    data.frame(lon = 74.0, lat = lat_breaks, label = format_lat(lat_breaks)),
    coords = c("lon", "lat"), crs = 4326
  ) %>%
    st_transform(crs_string) %>%
    mutate(x = st_coordinates(.)[, 1], y = st_coordinates(.)[, 2]) %>%
    mutate(y = ifelse(label == "15°N", y + 80000, y)) %>%
    st_drop_geometry()
  list(lon = lon_labels %>% filter(!label %in% c("75°E", "90°E")), lat = lat_labels)
}

theme_map <- function() {
  theme_minimal(base_family = "sans", base_size = 12) +
    theme(
      panel.grid.major = element_blank(),
      panel.grid.minor = element_blank(),
      axis.title = element_blank(),
      axis.text = element_blank(),
      axis.ticks = element_blank(),
      plot.title = element_blank(),
      legend.position = "none",
      plot.margin = margin(10, 12, 10, 12),
      panel.border = element_blank()
    )
}

china_raw <- st_read(china_shp_path, quiet = TRUE) %>% rename(NAME = name)
ten_dash_raw <- st_read(ten_dash_path, quiet = TRUE)
china <- st_transform(china_raw, proj_crs)
ten_dash <- st_transform(ten_dash_raw, proj_crs)

province_mapping <- read_excel(mapping_path) %>%
  transmute(NAME = trimws(as.character(NAME)),
            province_en = trimws(as.character(Province_EN))) %>%
  mutate(province_en = ifelse(province_en == "Tibet", "Xizang", province_en))

records <- read_csv(records_path, show_col_types = FALSE) %>%
  transmute(
    class_cn = Class_CN,
    class_en = recode(Class_CN, "两栖纲" = "Amphibia", "爬行纲" = "Reptilia"),
    province_short = str_squish(New_distribution_province)
  ) %>%
  filter(!is.na(class_en), !is.na(province_short))

name_lookup <- china_raw %>%
  st_drop_geometry() %>%
  transmute(NAME, province_short = strip_prov(NAME))

label_points <- st_point_on_surface(china_raw) %>%
  st_transform(4326) %>%
  mutate(lon = st_coordinates(.)[, 1], lat = st_coordinates(.)[, 2]) %>%
  st_drop_geometry() %>%
  select(NAME, lon, lat) %>%
  left_join(province_mapping, by = "NAME") %>%
  filter(!is.na(province_en), NAME != "澳门特别行政区") %>%
  left_join(province_offsets, by = "NAME", suffix = c("_default", "_override")) %>%
  mutate(
    lon_plot = ifelse(is.na(lon_override), lon_default, lon_override),
    lat_plot = ifelse(is.na(lat_override), lat_default, lat_override)
  ) %>%
  select(NAME, province_en, lon = lon_plot, lat = lat_plot)

label_points_sf <- st_as_sf(label_points, coords = c("lon", "lat"), crs = 4326) %>%
  st_transform(proj_crs) %>%
  mutate(x = st_coordinates(.)[, 1], y = st_coordinates(.)[, 2]) %>%
  st_drop_geometry()

graticule <- st_graticule(
  lon = seq(75, 135, by = 15), lat = seq(15, 60, by = 15),
  crs = st_crs(proj_crs), datum = st_crs(4326)
)
graticule_labels <- build_graticule_labels(proj_crs)

bbox_china <- st_bbox(china)
bbox_dash <- st_bbox(ten_dash)
main_xlim <- c(bbox_china["xmin"] - 0.03 * diff(bbox_china[c("xmin", "xmax")]),
               bbox_china["xmax"] + 0.02 * diff(bbox_china[c("xmin", "xmax")]))
main_ylim <- c(bbox_dash["ymin"] - 0.03 * diff(bbox_china[c("ymin", "ymax")]),
               bbox_china["ymax"] + 0.03 * diff(bbox_china[c("ymin", "ymax")]))
main_xlim_zoom <- c(main_xlim[1] + 0.03 * diff(main_xlim), main_xlim[2] - 0.055 * diff(main_xlim))
main_ylim_zoom <- c(main_ylim[1] + 0.17 * diff(main_ylim), main_ylim[2] - 0.03 * diff(main_ylim))
inset_bbox <- st_bbox(c(xmin = 105, xmax = 125, ymin = 3, ymax = 25), crs = st_crs(4326)) %>%
  st_as_sfc() %>%
  st_transform(proj_crs) %>%
  st_bbox()
fill_colours <- c("#3E94C9", "#5BA4CD", "#78B3D0", "#96C1D0", "#B2CCC9",
                  "#CDD6BF", "#E2DEB3", "#F1D38C", "#F3B35E", "#E97A3C")

plot_one_class <- function(cls_en) {
  counts <- records %>%
    filter(class_en == cls_en) %>%
    count(province_short, name = "total_new_records") %>%
    inner_join(name_lookup, by = "province_short")

  china_plot <- china %>% left_join(counts, by = "NAME")
  fill_limits <- range(counts$total_new_records, na.rm = TRUE)
  china_inset <- st_crop(china_plot, inset_bbox)
  ten_dash_inset <- st_crop(ten_dash, inset_bbox)

  number_map <- ggplot() +
    geom_sf(data = graticule, color = "#9A9A9A", linewidth = 0.22, linetype = "dashed") +
    geom_sf(data = china_plot, aes(fill = total_new_records), color = "#000000", linewidth = 0.12) +
    geom_sf(data = ten_dash, color = "#6E6E6E", linewidth = 0.45, fill = NA) +
    geom_text(data = label_points_sf, aes(x = x, y = y, label = province_en),
              family = "sans", size = 3.85, color = "black") +
    geom_text(data = graticule_labels$lon, aes(x = x, y = y, label = label),
              family = "sans", size = 3.2, color = "#555555", vjust = 1.5) +
    geom_text(data = graticule_labels$lat, aes(x = x, y = y, label = label),
              family = "sans", size = 3.2, color = "#555555", angle = 90) +
    annotate("text", x = main_xlim_zoom[1] + 0.015 * diff(main_xlim_zoom),
             y = main_ylim_zoom[2] - 0.025 * diff(main_ylim_zoom),
             label = cls_en, family = "sans", fontface = "bold.italic",
             size = 6.4, hjust = 0, color = "black") +
    coord_sf(crs = st_crs(proj_crs), xlim = main_xlim_zoom, ylim = main_ylim_zoom,
             expand = FALSE, clip = "off") +
    scale_fill_gradientn(colours = fill_colours, limits = fill_limits, na.value = "white") +
    theme_map()

  number_inset <- ggplot() +
    geom_sf(data = china_inset, aes(fill = total_new_records), color = "#000000", linewidth = 0.12) +
    geom_sf(data = ten_dash_inset, color = "#6E6E6E", linewidth = 0.4, fill = NA) +
    coord_sf(crs = st_crs(proj_crs),
             xlim = c(inset_bbox["xmin"], inset_bbox["xmax"]),
             ylim = c(inset_bbox["ymin"], inset_bbox["ymax"]), expand = FALSE) +
    scale_fill_gradientn(colours = fill_colours, limits = fill_limits, na.value = "white") +
    theme_void(base_family = "sans", base_size = 12) +
    theme(legend.position = "none",
          panel.border = element_rect(color = "black", fill = NA, linewidth = 0.9))

  legend_gradient <- tibble::tibble(
    ymin = seq(fill_limits[1], fill_limits[2] - diff(fill_limits) / 199, length.out = 200),
    ymax = seq(fill_limits[1] + diff(fill_limits) / 199, fill_limits[2], length.out = 200),
    fill_value = seq(fill_limits[1], fill_limits[2], length.out = 200)
  )
  number_legend <- ggplot() +
    geom_rect(data = legend_gradient,
              aes(xmin = 0, xmax = 0.14, ymin = ymin, ymax = ymax, fill = fill_value),
              color = NA) +
    annotate("text", x = 0, y = fill_limits[2] + diff(fill_limits) * 0.06,
             label = "Number of new records", hjust = 0, vjust = 0,
             family = "sans", fontface = "bold", size = 5.3) +
    annotate("text", x = 0.18, y = fill_limits[2] - diff(fill_limits) * 0.07,
             label = as.character(fill_limits[2]), hjust = 0, vjust = 0.5,
             family = "sans", size = 4.2) +
    annotate("text", x = 0.18, y = fill_limits[1] + diff(fill_limits) * 0.012,
             label = as.character(fill_limits[1]), hjust = 0, vjust = 0.5,
             family = "sans", size = 4.2) +
    scale_fill_gradientn(colours = fill_colours, limits = fill_limits, guide = "none") +
    coord_cartesian(xlim = c(0, 0.3),
                    ylim = c(fill_limits[1] + diff(fill_limits) * 0.05,
                             fill_limits[2] + diff(fill_limits) * 0.08),
                    expand = FALSE, clip = "off") +
    theme_void(base_family = "sans", base_size = 12)

  combined <- ggdraw() +
    draw_plot(number_map, x = -0.03, y = 0, width = 1, height = 1) +
    draw_plot(number_legend, x = 0.085, y = 0.05, width = 0.11, height = 0.19) +
    draw_plot(number_inset, x = 0.81, y = 0.015, width = 0.165, height = 0.275)

  fn <- file.path(output_dir, paste0("Figure1a_", cls_en))
  ggsave(paste0(fn, ".png"), combined, width = 10.24, height = 7.68, dpi = 300,
         device = ragg::agg_png, bg = "white")
  ggsave(paste0(fn, ".pdf"), combined, width = 10.24, height = 7.68,
         device = "pdf", bg = "white")
  counts
}

log_lines <- c(paste0("Records: ", records_path))
for (cls in c("Amphibia", "Reptilia")) {
  counts <- plot_one_class(cls)
  log_lines <- c(log_lines,
                 paste0(cls, ": ", sum(counts$total_new_records), " events across ",
                        nrow(counts), " provinces; max = ",
                        max(counts$total_new_records)))
}
writeLines(log_lines, con = file.path(output_dir, "Figure1a_render_log.txt"))
cat(paste(log_lines, collapse = "\n"), "\n")
