#!/usr/bin/env python3
"""Methods schematic for the locally-consistent syncmer mapper paper.
Produces a vector PDF (and PNG preview) of the six-stage pipeline.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle, Circle
import matplotlib.font_manager as fm
import numpy as np

plt.rcParams.update({
    "font.size": 9,
    "font.family": "DejaVu Sans",
    "svg.fonttype": "none",
})

# ---- palette (print / grayscale friendly) -------------------------------
C_BOX   = "#f4f6f9"
C_EDGE  = "#33475b"
C_ACC   = "#2c6fbb"   # accent blue
C_ACC2  = "#c0392b"   # accent red
C_GREY  = "#8a97a6"
C_LBLUE = "#dbe7f5"
C_LRED  = "#f6dcd8"
C_TXT   = "#1f2a36"

fig, ax = plt.subplots(figsize=(13.6, 7.2))
ax.set_xlim(0, 136)
ax.set_ylim(0, 72)
ax.axis("off")

def box(x, y, w, h, fc=C_BOX, ec=C_EDGE, lw=1.3, r=0.025, z=2):
    p = FancyBboxPatch((x, y), w, h,
                       boxstyle=f"round,pad=0.2,rounding_size={r*min(w,h)*6}",
                       fc=fc, ec=ec, lw=lw, zorder=z)
    ax.add_patch(p)
    return p

def title(x, y, n, txt):
    badge = Circle((x+2.4, y), 1.7, fc=C_ACC, ec="none", zorder=5)
    ax.add_patch(badge)
    ax.text(x+2.4, y, str(n), ha="center", va="center", color="white",
            fontsize=10, fontweight="bold", zorder=6)
    ax.text(x+5.6, y, txt, ha="left", va="center", color=C_TXT,
            fontsize=10.5, fontweight="bold", zorder=6)

def cap(x, y, txt, w):
    ax.text(x, y, txt, ha="left", va="top", color=C_TXT, fontsize=8.3,
            wrap=True, zorder=6)

def arrow(x1, y1, x2, y2, color=C_EDGE, lw=1.8, style="-|>", mut=14):
    a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style,
                        mutation_scale=mut, lw=lw, color=color, zorder=4,
                        shrinkA=0, shrinkB=0)
    ax.add_patch(a)

# =========================================================================
# TOP HEADER
# =========================================================================
ax.text(68, 70.4, "A hierarchy of locally-consistent syncmer blocks",
        ha="center", va="center", fontsize=13, fontweight="bold", color=C_TXT)

# Phase banners
box(2, 40.5, 84, 28.5, fc="#ffffff", ec=C_GREY, lw=1.0, r=0.012, z=1)
ax.text(4, 67.6, "Shared encoding  (applied identically to reference and read)",
        ha="left", va="center", fontsize=9.5, style="italic", color=C_GREY)

box(2, 2.5, 132, 35.5, fc="#ffffff", ec=C_GREY, lw=1.0, r=0.012, z=1)
ax.text(4, 36.6, "Indexing  (reference)   +   Mapping  (read)",
        ha="left", va="center", fontsize=9.5, style="italic", color=C_GREY)

# =========================================================================
# STAGE 1 — open syncmers
# =========================================================================
x1, y1, w1, h1 = 5, 44, 24, 21
box(x1, y1, w1, h1)
title(x1+1.5, y1+h1-2.6, 1, "Open syncmers")
# illustrate: a sequence line, a k-mer window, central s-mer minimizer
seq_y = y1+12
ax.plot([x1+2, x1+w1-2], [seq_y, seq_y], color=C_GREY, lw=2, zorder=3)
# window
ax.add_patch(Rectangle((x1+5, seq_y-1.6), 9, 3.2, fc="none", ec=C_ACC, lw=1.4, zorder=4))
ax.text(x1+9.5, seq_y+3.0, "k-mer", ha="center", fontsize=7, color=C_ACC)
ax.add_patch(Rectangle((x1+8.7, seq_y-1.0), 2.6, 2.0, fc=C_ACC2, ec="none", zorder=5))
ax.text(x1+10, seq_y-2.9, "min s-mer\n at centre", ha="center", va="top",
        fontsize=6.3, color=C_ACC2)
# selected syncmer dots
for dx in [3, 9.5, 16, 20]:
    ax.add_patch(Circle((x1+2+dx, seq_y-6.0), 0.7, fc=C_ACC, ec="none", zorder=5))
ax.text(x1+w1/2, y1+2.0, "sparse, reproducible\n~1/(k-s+1) seeds", ha="center",
        va="center", fontsize=7.2, color=C_TXT)

arrow(x1+w1, y1+h1/2, x1+w1+4.0, y1+h1/2)

# =========================================================================
# STAGE 2 — LCP -> L1 blocks
# =========================================================================
x2 = x1+w1+4.0
box(x2, y1, w1, h1)
title(x2+1.5, y1+h1-2.6, 2, "LCP → blocks")
by = y1+12
dots = np.linspace(x2+3, x2+w1-3, 9)
for dx in dots:
    ax.add_patch(Circle((dx, by), 0.7, fc=C_GREY, ec="none", zorder=5))
# group into blocks via brackets
groups = [(0,2),(3,4),(5,8)]
cols = [C_ACC, C_ACC2, C_ACC]
for (a,b),c in zip(groups, cols):
    xa, xb = dots[a]-1.2, dots[b]+1.2
    ax.add_patch(FancyBboxPatch((xa, by-2.4), xb-xa, 4.8,
                 boxstyle="round,pad=0.1,rounding_size=0.8",
                 fc="none", ec=c, lw=1.4, zorder=4))
ax.text(x2+w1/2, y1+3.2, "content-only rules:\nminima, maxima, runs", ha="center",
        va="center", fontsize=7.2, color=C_TXT)

arrow(x2+w1, y1+h1/2, x2+w1+4.0, y1+h1/2)

# =========================================================================
# STAGE 3 — recursive hierarchy
# =========================================================================
x3 = x2+w1+4.0
box(x3, y1, w1, h1)
title(x3+1.5, y1+h1-2.6, 3, "Hierarchy L1–L6")
# pyramid of shrinking rows
base_y = y1+4.5
levels = [("L1", 16, C_LBLUE), ("L2", 12, "#cfe0f2"),
          ("L3", 8.5, "#bcd4ee"), ("L4–L6", 5, "#a9c8e9")]
for i,(lab,wd,c) in enumerate(levels):
    yy = base_y + i*3.0
    cx = x3+w1/2
    ax.add_patch(Rectangle((cx-wd/2, yy), wd, 2.4, fc=c, ec=C_EDGE, lw=0.8, zorder=4))
    ax.text(cx, yy+1.2, lab, ha="center", va="center", fontsize=6.6, color=C_TXT)
ax.text(x3+w1-1.5, base_y+6, "×2.3×\nper level", ha="right", va="center",
        fontsize=6.6, color=C_GREY)

# =========================================================================
# downward arrows into indexing/mapping phase
# =========================================================================
# reference branch (left) and read branch (right) emerge from hierarchy
arrow(x3+w1/2-4, y1, x2+6, 38.2, color=C_ACC)      # to index
arrow(x3+w1/2+4, y1, 70, 38.2, color=C_ACC2)       # to anchoring
ax.text(x2+2.5, 39.6, "reference blocks", ha="left", va="bottom",
        fontsize=7, color=C_ACC, rotation=0)
ax.text(64, 39.6, "read blocks", ha="left", va="bottom",
        fontsize=7, color=C_ACC2)

# =========================================================================
# STAGE 4 — index  (bottom-left)
# =========================================================================
x4, y4, w4, h4 = 5, 6, 26, 31
box(x4, y4, w4, h4, fc=C_LBLUE)
title(x4+1.5, y4+h4-2.6, 4, "Index")
# struct-of-arrays table
cols3 = ["hash", "chr", "pos"]
tx, ty, cw = x4+3.5, y4+h4-9, 6.2
for j,cn in enumerate(cols3):
    ax.text(tx+j*cw+cw/2, ty+2.2, cn, ha="center", fontsize=7.4,
            fontweight="bold", color=C_TXT)
rows = [("a3f1","1","812k"),("b09c","1","5.1M"),("c7d2","7","44k"),("e1aa","X","2.9M")]
for r,row in enumerate(rows):
    yy = ty - r*3.0
    for j,val in enumerate(row):
        ax.add_patch(Rectangle((tx+j*cw, yy-1.2), cw-0.6, 2.4,
                     fc="white", ec=C_GREY, lw=0.6, zorder=4))
        ax.text(tx+j*cw+(cw-0.6)/2, yy, val, ha="center", va="center",
                fontsize=6.6, color=C_TXT, zorder=5)
ax.text(x4+w4/2, y4+2.2, "sorted by hash · 13 B/entry\nlevels ≥ 3 only → ~10× smaller",
        ha="center", va="center", fontsize=7.2, color=C_TXT)

arrow(x4+w4, y4+h4/2, x4+w4+4.0, y4+h4/2)

# =========================================================================
# STAGE 5 — anchoring + voting (bottom-middle)
# =========================================================================
x5 = x4+w4+4.0
w5, h5 = 33, 31
box(x5, y4, w5, h5, fc=C_LRED)
title(x5+1.5, y4+h4-2.6, 5, "Anchor → vote")
# dotplot
gx, gy, gw, gh = x5+4, y4+6, 18, 18
ax.add_patch(Rectangle((gx, gy), gw, gh, fc="white", ec=C_GREY, lw=0.8, zorder=3))
ax.text(gx+gw/2, gy-1.7, "reference pos", ha="center", fontsize=6.6, color=C_GREY)
ax.text(gx-1.6, gy+gh/2, "read pos", ha="center", fontsize=6.6, color=C_GREY,
        rotation=90)
rng = np.random.default_rng(7)
# diagonal cluster (true locus)
t = np.linspace(0.15, 0.85, 14)
ax.scatter(gx+ (t+rng.normal(0,0.012,t.size))*gw,
           gy+ (t+rng.normal(0,0.012,t.size))*gh,
           s=14, c=C_ACC2, zorder=5, edgecolors="none")
# scattered noise anchors
ax.scatter(gx+rng.uniform(0.05,0.95,9)*gw, gy+rng.uniform(0.05,0.95,9)*gh,
           s=9, c=C_GREY, zorder=4, edgecolors="none", alpha=0.7)
ax.text(gx+gw+1.0, gy+gh*0.72, "heaviest\ndiagonal\nwins", ha="left", va="center",
        fontsize=6.8, color=C_ACC2)
ax.text(x5+w5/2, y4+2.2, "conservation-of-mass weights · gap → MAPQ\n(diagonal voting)",
        ha="center", va="center", fontsize=7.2, color=C_TXT)

arrow(x5+w5, y4+h4/2, x5+w5+4.0, y4+h4/2)

# =========================================================================
# STAGE 6 — optional CIGAR (bottom-right)
# =========================================================================
x6 = x5+w5+4.0
w6, h6 = 31, 31
box(x6, y4, w6, h6)
title(x6+1.5, y4+h4-2.6, 6, "CIGAR (optional)")
# two aligned tracks with a gap
ax_y = y4+h6-13
for k,(yy,c) in enumerate([(ax_y, C_ACC),(ax_y-3.0, C_ACC2)]):
    ax.plot([x6+4, x6+12], [yy, yy], color=c, lw=2.4, zorder=4)
    ax.plot([x6+15, x6+w6-3], [yy, yy], color=c, lw=2.4, zorder=4)
ax.add_patch(Rectangle((x6+12, ax_y-3.3), 3, 3.6, fc="none", ec=C_GREY,
             lw=1.0, ls=(0,(2,1)), zorder=4))
ax.text(x6+13.5, ax_y-5.4, "banded\naffine gap", ha="center", va="top",
        fontsize=6.6, color=C_GREY)
ax.text(x6+w6/2, y4+5.6, "anchors emitted directly;\nonly short gaps aligned", ha="center",
        va="center", fontsize=7.2, color=C_TXT)
ax.text(x6+w6/2, y4+2.0, "PAF  (+ cg:Z:)", ha="center", va="center",
        fontsize=7.6, fontweight="bold", color=C_TXT)

plt.tight_layout(pad=0.4)
out_pdf = "/sessions/magical-practical-babbage/mnt/hifibenchmark/results/plots/pipeline.pdf"
out_png = "/sessions/magical-practical-babbage/mnt/hifibenchmark/results/plots/pipeline.png"
fig.savefig(out_pdf, bbox_inches="tight")
fig.savefig(out_png, dpi=170, bbox_inches="tight")
print("wrote", out_pdf, out_png)
