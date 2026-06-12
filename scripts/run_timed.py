#!/usr/bin/env python3
"""
Run a shell command, measure wall time and peak RSS, write JSON metrics.

Usage:
    python3 run_timed.py <metrics.json> <cmd> [args...]

The command's stdout is inherited (redirect it in the calling shell if needed).
Requires: psutil  (pip install psutil)
"""
import json, sys, time, threading, subprocess

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    print("Warning: psutil not installed — memory tracking disabled. Run: pip install psutil",
          file=sys.stderr)


def _poll_rss(pid: int, peak: list, stop: threading.Event, interval: float = 0.1) -> None:
    """Background thread: track peak RSS bytes of the process tree.

    Samples immediately, then every `interval` seconds, so even very short
    runs record at least one measurement.
    """
    try:
        proc = psutil.Process(pid)
        while True:
            try:
                rss = proc.memory_info().rss
                for child in proc.children(recursive=True):
                    try:
                        rss += child.memory_info().rss
                    except psutil.NoSuchProcess:
                        pass
                peak[0] = max(peak[0], rss)
            except psutil.NoSuchProcess:
                break
            if stop.is_set():
                break
            time.sleep(interval)
    except Exception:
        pass


def run_timed(metrics_path: str, cmd: list) -> int:
    peak = [0]
    stop = threading.Event()

    t0 = time.perf_counter()
    proc = subprocess.Popen(cmd)

    if HAS_PSUTIL:
        mon = threading.Thread(target=_poll_rss, args=(proc.pid, peak, stop), daemon=True)
        mon.start()

    proc.wait()
    elapsed = time.perf_counter() - t0

    stop.set()
    if HAS_PSUTIL:
        mon.join(timeout=2.0)

    metrics = {
        "wall_time_s": round(elapsed, 3),
        "peak_rss_mb": round(peak[0] / 1024 / 1024, 1) if HAS_PSUTIL else None,
        "exit_code": proc.returncode,
    }

    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)

    return proc.returncode


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("Usage: run_timed.py <metrics.json> <cmd> [args...]")

    rc = run_timed(sys.argv[1], sys.argv[2:])
    if rc != 0:
        print(f"Command exited with code {rc}", file=sys.stderr)
    sys.exit(rc)
