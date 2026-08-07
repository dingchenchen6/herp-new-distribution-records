#!/usr/bin/env Rscript

# ============================================================
# Figure 1b | 分纲新纪录点位图（按目着色）/ Georeferenced new-record
# events mapped separately for Amphibia and Reptilia, coloured by
# order. 参照 CBNR Figure 2b 风格（同投影/十段线/南海插图）。
# Adapted from the CBNR Figure 2b styling.
# Input : data/CHNR_provincial_new_records.csv
# Output: output/Figure1b_Amphibia.(png|pdf),
#         output/Figure1b_Reptilia.(png|pdf), render log
# ============================================================

suppressPackageStartupMessages({
  library(dplyr)
  library(ggplot2)
  library(readr)
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
china_shp_path <- file.path(script_dir, "input", "province_boundaries.shp")
ten_dash_path <- file.path(script_dir, "input", "ten_dash_line.shp")
output_dir <- file.path(script_dir, "output")
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

proj_crs <- "+proj=aea +lat_1=25 +lat_2=47 +lat_0=0 +lon_0=105 +datum=WGS84 +units=m +no_defs"

# 分纲目级配色（与 Figure 1c 保持一致）/ per-class order palettes
class_palettes <- list(
  Amphibia = c("Anura" = "#0E8FA8", "Caudata" = "#F06423", "Gymnophiona" = "#8B6FDD"),
  Reptilia = c("Squamata" = "#D9882B", "Testudines" = "#31B85C", "Crocodylia" = "#D31972")
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
      legend.title = element_text(face = "bold", size = 16, margin = margin(b = 8)),
      legend.text = element_text(size = 13, face = "italic"),
      legend.key.height = unit(16, "pt"),
      legend.key.width = unit(20, "pt"),
      legend.background = element_blank(),
      plot.margin = margin(10, 12, 10, 12),
      panel.border = element_blank()
    )
}

china <- st_read(china_shp_path, quiet = TRUE) %>%
  rename(NAME = name) %>%
  st_transform(proj_crs)
ten_dash <- st_read(ten_dash_path, quiet = TRUE) %>% st_transform(proj_crs)

records <- read_csv(records_path, show_col_types = FALSE) %>%
  transmute(
    class_en = recode(Class_CN, "两栖纲" = "Amphibia", "爬行纲" = "Reptilia"),
    order = str_squish(OrderLA_COL_China_2026),
    longitude = suppressWarnings(as.numeric(Longitude)),
    latitude = suppressWarnings(as.numeric(Latitude))
  ) %>%
  filter(!is.na(class_en), !is.na(order), !is.na(longitude), !is.na(latitude))

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
ten_dash_inset <- st_crop(ten_dash, inset_bbox)
china_inset <- st_crop(china, inset_bbox)

plot_one_class <- function(cls_en) {
  pal <- class_palettes[[cls_en]]
  pts <- records %>%
    filter(class_en == cls_en) %>%
    mutate(order = factor(order, levels = names(pal))) %>%
    st_as_sf(coords = c("longitude", "latitude"), crs = 4326, remove = FALSE) %>%
    st_transform(proj_crs)
  pts_inset <- st_crop(pts, inset_bbox)

  main_map <- ggplot() +
    geom_sf(data = graticule, color = "#9A9A9A", linewidth = 0.22, linetype = "dashed") +
    geom_sf(data = china, fill = "white", color = "#000000", linewidth = 0.12) +
    geom_sf(data = ten_dash, color = "#6E6E6E", linewidth = 0.45, fill = NA) +
    geom_sf(data = pts, aes(color = order), size = 1.6, alpha = 0.9) +
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
    scale_color_manual(values = pal, drop = TRUE, name = "Order") +
    guides(color = guide_legend(override.aes = list(size = 5, alpha = 1),
                                title.position = "top")) +
    theme_map() +
    theme(legend.position = c(0.02, 0.06), legend.justification = c(0, 0),
          legend.direction = "vertical")

  inset_map <- ggplot() +
    geom_sf(data = china_inset, fill = "white", color = "#000000", linewidth = 0.12) +
    geom_sf(data = ten_dash_inset, color = "#6E6E6E", linewidth = 0.4, fill = NA) +
    geom_sf(data = pts_inset, aes(color = order), size = 1.3, alpha = 0.9) +
    coord_sf(crs = st_crs(proj_crs),
             xlim = c(inset_bbox["xmin"], inset_bbox["xmax"]),
             ylim = c(inset_bbox["ymin"], inset_bbox["ymax"]), expand = FALSE) +
    scale_color_manual(values = pal, drop = TRUE) +
    theme_void(base_family = "sans", base_size = 12) +
    theme(legend.position = "none",
          panel.border = element_rect(color = "black", fill = NA, linewidth = 0.9))

  combined <- ggdraw() +
    draw_plot(main_map, x = -0.03, y = 0, width = 1, height = 1) +
    draw_plot(inset_map, x = 0.81, y = 0.015, width = 0.165, height = 0.275)

  fn <- file.path(output_dir, paste0("Figure1b_", cls_en))
  ggsave(paste0(fn, ".png"), combined, width = 10.24, height = 7.68, dpi = 300,
         device = ragg::agg_png, bg = "white")
  ggsave(paste0(fn, ".pdf"), combined, width = 10.24, height = 7.68,
         device = "pdf", bg = "white")
  nrow(pts)
}

log_lines <- c(paste0("Records: ", records_path))
for (cls in c("Amphibia", "Reptilia")) {
  n <- plot_one_class(cls)
  log_lines <- c(log_lines, paste0(cls, ": ", n, " georeferenced events plotted"))
}
writeLines(log_lines, con = file.path(output_dir, "Figure1b_render_log.txt"))
cat(paste(log_lines, collapse = "\n"), "\n")
