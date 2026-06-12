#!/usr/bin/env python3
"""
Patch a run_timed metrics JSON with the true peak RSS parsed from a tool's log.

Dockerized mappers report their peak memory to stderr in one of two ways:
    BLEND / mapquik          : "Peak RSS: <x> GB" / "Maximum RSS: <x>GB"
    minimap2 / syncmer-hifi  : run under `/usr/bin/time -v`, which prints
                               "Maximum resident set size (kbytes): <N>"
Host psutil only sees the Docker client process, so we overwrite peak_rss_mb
with the value reported from inside the container.

Usage:
    python3 parse_peak_rss.py <metrics.json> <tool_log.txt>

If no RSS line is found, the metrics file is left unchanged.
"""
import sys, os, re, json

# "Peak RSS: 6.39 GB", "Maximum RSS: 6.5396843GB", "... 512 MB"
RSS_RE  = re.compile(r"(?:Peak|Maximum)\s+RSS:\s*([\d.]+)\s*([GM])B", re.IGNORECASE)
# GNU time -v: "Maximum resident set size (kbytes): 6712345"
TIME_RE = re.compile(r"Maximum resident set size \(kbytes\):\s*(\d+)", re.IGNORECASE)


def parse_peak_mb(log_path: str):
    """Return the largest reported peak RSS in MB, or None."""
    best = None
    with open(log_path, "rt", errors="replace") as f:
        for line in f:
            mb = None
            m = RSS_RE.search(line)
            if m:
                val = float(m.group(1))
                mb = val * 1024 if m.group(2).upper() == "G" else val
            else:
                t = TIME_RE.search(line)
                if t:
                    mb = int(t.group(1)) / 1024.0
            if mb is not None:
                best = mb if best is None else max(best, mb)
    return best


def main():
    if len(sys.argv) != 3:
        sys.exit("Usage: parse_peak_rss.py <metrics.json> <tool_log.txt>")

    metrics_path, log_path = sys.argv[1], sys.argv[2]
    if not os.path.exists(log_path):
        print(f"  (no log {log_path}; leaving memory as-is)")
        return

    peak_mb = parse_peak_mb(log_path)
    if peak_mb is None:
        print(f"  (no 'Peak/Maximum RSS' line in {log_path}; leaving memory as-is)")
        return

    with open(metrics_path) as f:
        metrics = json.load(f)
    metrics["peak_rss_mb"] = round(peak_mb, 1)
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"  peak_rss_mb ← {peak_mb:.1f} MB (from container log)")


if __name__ == "__main__":
    main()
