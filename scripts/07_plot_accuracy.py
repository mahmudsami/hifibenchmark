#!/usr/bin/env python3
"""
Plot accuracy and precision from results/csv/results.csv.

One figure PER METRIC (grouped by metric, not by genome):
    results/plots/accuracy.png   and   results/plots/precision.png
Each: rows = error rate, cols = genome, x-axis = read length (kb), line = mapper.
"""
from _plot_grid import load_rows, plot_metric


def main():
    rows = load_rows()
    plot_metric(rows, "accuracy",  "Accuracy (%)",  pct=True)
    plot_metric(rows, "precision", "Precision (%)", pct=True)


if __name__ == "__main__":
    main()
