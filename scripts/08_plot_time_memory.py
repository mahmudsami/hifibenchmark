#!/usr/bin/env python3
"""
Plot mapping time and peak memory from results/csv/results.csv.

One figure PER METRIC (grouped by metric, not by genome):
    results/plots/map_time.png   and   results/plots/peak_rss.png
Each: rows = error rate, cols = genome, x-axis = read length (kb), line = mapper.
"""
from _plot_grid import load_rows, plot_metric


def main():
    rows = load_rows()
    plot_metric(rows, "map_time_s",  "Mapping time (s)", logy=True, out_name="map_time")
    plot_metric(rows, "peak_rss_mb", "Peak RSS (GB)", scale=1 / 1024.0, logy=True, out_name="peak_rss")


if __name__ == "__main__":
    main()
