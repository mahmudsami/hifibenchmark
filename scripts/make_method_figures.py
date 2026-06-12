#!/usr/bin/env python3
"""Author clean, Inkscape-editable SVG toy figures for the Methods section:
  (A) open-syncmer selection
  (B) LCP rules + recursive block hierarchy
Also exports PDF (for LaTeX) and PNG (preview) via cairosvg.
Outputs -> hifibenchmark/method_figures/
"""
import os, cairosvg

OUT = "/sessions/magical-practical-babbage/mnt/hifibenchmark/method_figures"
os.makedirs(OUT, exist_ok=True)

INK="#1f2a36"; BLUE="#2c6fbb"; RED="#c0392b"; GREY="#8a97a6"
LBLUE="#dbe7f5"; LRED="#f6dcd8"; LGREY="#eef1f5"; GREEN="#2e7d52"; LGREEN="#d8ece1"
GOLD="#b8860b"; LGOLD="#f3e6c4"
FONT='font-family="DejaVu Sans, Arial, sans-serif"'

def esc(s): return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
def rect(x,y,w,h,fill="white",stroke=INK,sw=1.4,rx=3):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
def txt(x,y,s,fs=15,fill=INK,anchor="middle",weight="normal",style="normal",mono=False):
    fam='font-family="DejaVu Sans Mono, monospace"' if mono else FONT
    return (f'<text x="{x}" y="{y}" font-size="{fs}" fill="{fill}" text-anchor="{anchor}" '
            f'font-weight="{weight}" font-style="{style}" {fam}>{esc(s)}</text>')
def line(x1,y1,x2,y2,stroke=INK,sw=1.4,dash=""):
    d=f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{sw}"{d}/>'
def arrow(x1,y1,x2,y2,stroke=INK,sw=2.0):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{sw}" marker-end="url(#ah)"/>'
def tri(cx,y,fill=GREEN,sz=7):
    return f'<path d="M {cx-sz} {y} L {cx+sz} {y} L {cx} {y+sz*1.3} Z" fill="{fill}"/>'

DEFS=(f'<defs><marker id="ah" markerWidth="9" markerHeight="9" refX="7" refY="3.2" orient="auto">'
      f'<path d="M0,0 L7,3.2 L0,6.4 Z" fill="{INK}"/></marker></defs>')

def cells(x0,y,vals,cw=40,ch=38,fills=None,strokes=None,fs=16,mono=True,weight="bold"):
    s=[]; centers=[]
    for i,v in enumerate(vals):
        x=x0+i*cw
        f = (fills[i] if fills else "white")
        st= (strokes[i] if strokes else INK)
        s.append(rect(x,y,cw-4,ch,fill=f,stroke=st))
        s.append(txt(x+(cw-4)/2,y+ch/2+6,str(v),fs=fs,weight=weight,mono=mono))
        centers.append(x+(cw-4)/2)
    return "".join(s),centers

def bracket(xL,xR,y,label,color=BLUE):
    h=7
    d=f'M {xL} {y-h} L {xL} {y} L {xR} {y} L {xR} {y-h}'
    s=f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2"/>'
    if label:
        s+=txt((xL+xR)/2,y+18,label,fs=12,fill=color,weight="bold")
    return s

# =====================================================================
# FIGURE A — open-syncmer selection  (with traceable s-mer hashes)
# =====================================================================
_O={'A':0,'C':1,'G':2,'T':3}
def smer_hashes(seq, s=2):
    return [_O[seq[i]]*4+_O[seq[i+1]] for i in range(len(seq)-s+1)]
def syncmer_starts(seq, k=4, s=2, t=1):
    h=smer_hashes(seq,s); out=[]
    for i in range(len(seq)-k+1):
        win=h[i:i+k-s+1]
        if win.index(min(win))==t: out.append(i)
    return out

def hashrow(x0, cw, y, hashes, decide=(), changed=()):
    out=[]
    for i,hv in enumerate(hashes):
        mx=x0+i*cw+(cw-4)/2 + cw/2   # midpoint between cell i and i+1 (the 2-mer)
        dec=i in decide; chg=i in changed
        fill=LGREEN if dec else (LRED if chg else "white")
        stroke=RED if chg else (GREEN if dec else GREY)
        out.append(rect(mx-15,y,30,20,fill=fill,stroke=stroke,sw=1.3,rx=3))
        out.append(txt(mx,y+14,str(hv),fs=11,weight="bold",mono=True))
    return "".join(out)

def figure_A():
    W,H=900,440
    s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" {FONT}>',
       DEFS, rect(0,0,W,H,fill="white",stroke="white",sw=0)]
    s.append(txt(W/2,30,"Open-syncmer selection",fs=21,weight="bold"))
    s.append(txt(W/2,52,"k = 4,  s = 2,  central offset t = 1   —   pick a k-mer iff the middle of its three s-mer hashes is the smallest",
                 fs=13,fill=GREY))

    seq="CAGTACGTGATC"; x0=84; cw=46; yseq=92
    H1=smer_hashes(seq); sel=syncmer_starts(seq)
    decide=[i+1 for i in sel]   # the deciding centre s-mer of each selected window
    s+=[txt(x0+i*cw+(cw-4)/2,yseq-8,str(i),fs=10,fill=GREY) for i in range(len(seq))]
    cs,centers=cells(x0,yseq,list(seq),cw=cw,ch=40)
    s.append(cs)
    # example window @0 outline
    wx0=x0-2; wx1=x0+4*cw-4+2
    s.append(f'<rect x="{wx0}" y="{yseq-3}" width="{wx1-wx0}" height="46" rx="4" fill="none" stroke="{BLUE}" stroke-width="2.2"/>')
    s.append(txt((wx0+wx1)/2, yseq-24, "example k-mer window", fs=12, fill=BLUE, weight="bold"))
    # s-mer hash row
    s.append(txt(x0-16, yseq+58, "s-mer", fs=9.5, fill=GREY, anchor="end"))
    s.append(txt(x0-16, yseq+69, "hashes", fs=9.5, fill=GREY, anchor="end"))
    s.append(hashrow(x0,cw,yseq+50,H1,decide=decide))
    # selected start markers
    for st in sel: s.append(tri(centers[st], yseq+44, fill=GREEN))
    s.append(txt(W-26, yseq+16, "▲ selected syncmer (start)", fs=12, fill=GREEN, anchor="end", weight="bold"))
    s.append(txt(W-26, yseq+32, "starts: 0, 3, 8", fs=12, fill=GREEN, anchor="end"))
    s.append(txt(W-26, yseq+62, "green = smallest hash,", fs=11, fill=GREEN, anchor="end"))
    s.append(txt(W-26, yseq+77, "sitting in the middle", fs=11, fill=GREEN, anchor="end"))
    # worked example note
    s.append(txt(x0, yseq+100,
                 "e.g. window 0–3 has s-mer hashes (4, 2, 11) → the smallest, 2, is in the middle → SELECT;",
                 fs=12, fill=INK, anchor="start"))
    s.append(txt(x0, yseq+118,
                 "window 1–4 has (2, 11, 12) → smallest is at the left, not the middle → skip.",
                 fs=12, fill=GREY, anchor="start"))

    # ---- error-tolerance row ----
    yr=296
    read="CAGTACATGATC"; mpos=6
    H2=smer_hashes(read); sel2=syncmer_starts(read)
    decide2=[i+1 for i in sel2]
    changed=[i for i in range(len(H2)) if i<len(H1) and H2[i]!=H1[i]]
    s.append(txt(x0, yr-16, "the same read with one substitution (base 6: G→A):", fs=12.5, fill=GREY, anchor="start", weight="bold"))
    fills=["white"]*len(read); strokes=[INK]*len(read); fills[mpos]=LRED; strokes[mpos]=RED
    cr,centers2=cells(x0,yr,list(read),cw=cw,ch=40,fills=fills,strokes=strokes)
    s.append(cr)
    s.append(txt(centers2[mpos], yr-6, "error", fs=10, fill=RED, weight="bold"))
    s.append(txt(x0-16, yr+58, "s-mer", fs=9.5, fill=GREY, anchor="end"))
    s.append(txt(x0-16, yr+69, "hashes", fs=9.5, fill=GREY, anchor="end"))
    s.append(hashrow(x0,cw,yr+50,H2,decide=decide2,changed=changed))
    for st in sel2:
        col = GOLD if st not in sel else GREEN
        s.append(tri(centers2[st], yr+44, fill=col))
    s.append(txt(W-26, yr+62, "red outline = hash", fs=11, fill=RED, anchor="end"))
    s.append(txt(W-26, yr+77, "changed by the error", fs=11, fill=RED, anchor="end"))
    s.append(txt(W/2, yr+100,
                 "only the two s-mers spanning base 6 change (hashes at 5, 6); syncmers 0, 3, 8 stay identical and a new one appears at 5",
                 fs=12, fill=INK))
    s.append(txt(W/2, yr+119,
                 "local selection → an error perturbs only the k-mers whose window spans it",
                 fs=12, fill=GREY, style="italic"))
    s.append("</svg>")
    return "".join(s)

# =====================================================================
# FIGURE B — LCP rules + recursive hierarchy
# =====================================================================
def figure_B():
    W,H=880,700
    s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" {FONT}>',
       DEFS, rect(0,0,W,H,fill="white",stroke="white",sw=0)]
    s.append(txt(W/2,30,"Locally-consistent parsing into a block hierarchy",fs=21,weight="bold"))

    # ---------- Part 1: the four rules ----------
    s.append(txt(40,62,"(a)  Four content-only rules identify block boundaries",fs=14,weight="bold",anchor="start"))
    pw=200; px=[30,30+pw+6,30+2*(pw+6),30+3*(pw+6)]; py=78; cw=30; ch=30
    def mini(panelx,title,vals,hi,color,lfill,note,splits=None):
        out=[rect(panelx,py,pw,124,fill="white",stroke=GREY,sw=1.1,rx=6)]
        out.append(txt(panelx+pw/2,py+20,title,fs=12.5,weight="bold",fill=color))
        n=len(vals); gx=panelx+(pw-n*cw)/2; gy=py+34
        fills=[lfill if i in hi else "white" for i in range(n)]
        strokes=[color if i in hi else INK for i in range(n)]
        cc,ctr=cells(gx,gy,vals,cw=cw,ch=ch,fills=fills,strokes=strokes,fs=12)
        out.append(cc)
        if splits is None:
            out.append(bracket(gx+1,gx+n*cw-5,gy+ch+12,"1 block",color=color))
        else:
            for j,(a,b) in enumerate(splits):
                yy=gy+ch+10+(6 if j%2 else 0)
                out.append(bracket(gx+a*cw+1,gx+b*cw+cw-5,yy,"",color=color))
            out.append(txt(panelx+pw/2,gy+ch+34,"≤3-unit blocks",fs=10,fill=color,weight="bold"))
        out.append(txt(panelx+pw/2,py+116,note,fs=10.5,fill=GREY))
        return "".join(out)
    s.append(mini(px[0],"Local minimum",["5","2","8"],[1],BLUE,LBLUE,"x > y < z"))
    s.append(mini(px[1],"Local maximum",["2","8","3"],[1],RED,LRED,"x < y > z (no min neighbour)"))
    s.append(mini(px[2],"Repetition (RINT)",["5","4","4","4","7"],[1,2,3],GREEN,LGREEN,"run kept whole (low-complexity)"))
    s.append(mini(px[3],"Monotone (SSEQ)",["0","2","4","6","8"],[0,1,2,3,4],GOLD,LGOLD,
                  "split by DCT (keeps sizes even)",splits=[(0,1),(1,3),(3,4)]))

    # ---------- Part 2: recursive hierarchy ----------
    s.append(txt(40,258,"(b)  Re-parsing block hashes builds a hierarchy: ~2.3× fewer, ~2.3× longer per level",
                 fs=14,weight="bold",anchor="start"))

    cwH=58
    # L1
    L1=[3,1,5,2,6,2,7,1,8,2,9]; x0=78; yL1=306
    s.append(txt(x0-14,yL1+22,"L1",fs=14,weight="bold",anchor="end",fill=INK))
    s.append(txt(x0-14,yL1+38,"syncmer",fs=9,anchor="end",fill=GREY))
    s.append(txt(x0-14,yL1+48,"hashes",fs=9,anchor="end",fill=GREY))
    cc,c1=cells(x0,yL1,L1,cw=cwH,ch=40,fs=15)
    s.append(cc)
    L1blocks=[(0,2),(2,4),(4,6),(6,8),(8,10)]
    for k,(a,b) in enumerate(L1blocks):
        col = BLUE if k%2==0 else GREEN
        yoff = 0 if k%2==0 else 13
        xL=x0+a*cwH-1; xR=x0+b*cwH+(cwH-4)+1
        s.append(bracket(xL,xR,yL1+50+yoff,"",color=col))
    for sh in [2,4,6,8]:
        s.append(f'<circle cx="{c1[sh]}" cy="{yL1+20}" r="15" fill="none" stroke="{RED}" stroke-width="1.6" stroke-dasharray="3,2"/>')
    s.append(txt(x0, yL1+92, "dashed = unit shared by 2 blocks → contributes mass ½ to each (conservation of mass)",
                 fs=11.5, fill=RED, anchor="start"))

    s.append(arrow(x0+(cwH*5)/2, yL1+104, x0+(cwH*5)/2, yL1+128, stroke=GREY))
    s.append(txt(x0+(cwH*5)/2+170, yL1+120, "hash each block → next-level alphabet", fs=11.5, fill=GREY))

    # L2
    L2=[42,61,54,13,40]; yL2=452; x0b=x0+cwH
    s.append(txt(x0b-14,yL2+22,"L2",fs=14,weight="bold",anchor="end",fill=INK))
    cc,c2=cells(x0b,yL2,L2,cw=cwH,ch=40,fs=15,fills=[LGREY]*5,strokes=[GREY]*5)
    s.append(cc)
    for k,(a,b) in enumerate([(0,1),(2,4)]):
        col = BLUE if k%2==0 else GREEN
        xL=x0b+a*cwH-1; xR=x0b+b*cwH+(cwH-4)+1
        s.append(bracket(xL,xR,yL2+50,"",color=col))
    s.append(arrow(x0b+(cwH*5)/2, yL2+64, x0b+(cwH*5)/2, yL2+88, stroke=GREY))

    # L3
    L3=[69,77]; yL3=556; x0c=x0b+cwH
    s.append(txt(x0c-14,yL3+22,"L3",fs=14,weight="bold",anchor="end",fill=INK))
    cc,c3=cells(x0c,yL3,L3,cw=cwH,ch=40,fs=15,fills=[LGOLD]*2,strokes=[GOLD]*2)
    s.append(cc)
    s.append(bracket(x0c-1, x0c+(cwH-4)+cwH+1, yL3+50,"",color=GOLD))
    s.append(arrow(x0c+(cwH*2)/2, yL3+62, x0c+(cwH*2)/2, yL3+86, stroke=GREY))
    s.append(rect(x0c+(cwH*2)/2-32, yL3+88, 64, 30, fill=LBLUE, stroke=BLUE))
    s.append(txt(x0c+(cwH*2)/2, yL3+108, "root", fs=13, weight="bold", fill=BLUE))

    s.append(txt(W-30, yL1+22, "11 units", fs=12, fill=GREY, anchor="end"))
    s.append(txt(W-30, yL2+22, "5 blocks", fs=12, fill=GREY, anchor="end"))
    s.append(txt(W-30, yL3+22, "2 blocks", fs=12, fill=GREY, anchor="end"))

    s.append("</svg>")
    return "".join(s)

# =====================================================================
# FIGURE C — block matching against the index + fallback to finer levels
# =====================================================================
def check(cx,cy,color=GREEN,sz=7):
    return (f'<path d="M {cx-sz} {cy} L {cx-sz*0.2} {cy+sz*0.7} L {cx+sz} {cy-sz*0.8}" '
            f'fill="none" stroke="{color}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>')
def cross(cx,cy,color=RED,sz=6):
    return (f'<path d="M {cx-sz} {cy-sz} L {cx+sz} {cy+sz} M {cx+sz} {cy-sz} L {cx-sz} {cy+sz}" '
            f'stroke="{color}" stroke-width="2.6" stroke-linecap="round"/>')

def figure_C():
    W,H=900,560
    s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" {FONT}>',
       DEFS, rect(0,0,W,H,fill="white",stroke="white",sw=0)]
    s.append(txt(W/2,30,"Block matching and fallback to finer levels",fs=21,weight="bold"))
    s.append(txt(W/2,52,"a read is placed by matching its blocks to the reference index: coarse blocks anchor directly; finer blocks recover error-hit regions",
                 fs=12.5,fill=GREY))

    xerr=434
    # ---- (a) coarse-block lookup ----
    s.append(txt(36,86,"(a)  look up each coarse (L2) block of the read in the reference index (by its 64-bit hash)",
                 fs=14,weight="bold",anchor="start"))
    xL,xR=150,730; yread=100
    s.append(txt(xL-12,yread+16,"read",fs=12,anchor="end",weight="bold"))
    s.append(rect(xL,yread,xR-xL,22,fill="#f4f6f9",stroke=GREY,sw=1.2,rx=4))
    s.append(line(xerr,yread-2,xerr,yread+72,stroke=RED,sw=1.6,dash="4,3"))
    s.append(txt(xerr+10,yread+15,"error",fs=11,fill=RED,weight="bold",anchor="start"))
    yb=yread+34; bh=34
    coarse=[("B1",150,344,True,"found → anchor @100"),
            ("B2",352,544,False,"hash changed → absent"),
            ("B3",552,730,True,"found → anchor @300")]
    for name,a,b,ok,res in coarse:
        fill=LGREEN if ok else LRED; stroke=GREEN if ok else RED
        s.append(rect(a,yb,b-a,bh,fill=fill,stroke=stroke,sw=1.8,rx=5))
        s.append(txt((a+b)/2,yb+16,name,fs=14,weight="bold"))
        s.append(txt((a+b)/2,yb+29,"L2 block",fs=9,fill=GREY))
        cy=yb+bh+20
        (s.append(check(a+12,cy-4)) if ok else s.append(cross(a+12,cy-4)))
        s.append(txt(a+26,cy,res,fs=11,fill=(GREEN if ok else RED),weight="bold",anchor="start"))

    # ---- (b) fallback ----
    yh2=yb+86
    s.append(txt(36,yh2,"(b)  fallback: split the unmatched B2 into its finer (L1) children — the error reaches only one",
                 fs=14,weight="bold",anchor="start"))
    # split connectors from B2 to children
    s.append(arrow(500, yb+bh+34, 500, yh2+18, stroke=GREY,sw=1.6))
    yc=yh2+30; ch2=30
    kids=[("c1",352,420,True),("c2",424,472,False),("c3",476,544,True)]
    for name,a,b,ok in kids:
        fill=LGOLD if ok else LRED; stroke=GOLD if ok else RED
        s.append(rect(a,yc,b-a,ch2,fill=fill,stroke=stroke,sw=1.7,rx=5))
        s.append(txt((a+b)/2,yc+14,name,fs=12,weight="bold"))
        s.append(txt((a+b)/2,yc+25,"L1",fs=8,fill=GREY))
    s.append(line(xerr,yc-4,xerr,yc+ch2+4,stroke=RED,sw=1.6,dash="4,3"))
    # combined result (per-child labels would collide on these narrow blocks)
    ry=yc+ch2+20
    s.append(check(360,ry-4,color=GOLD))
    s.append(txt(376,ry,"c1 & c3 match → two anchors recovered",fs=11,fill=GOLD,weight="bold",anchor="start"))
    s.append(cross(360,ry+18,color=RED))
    s.append(txt(376,ry+22,"c2 spans the error → skipped",fs=11,fill=RED,weight="bold",anchor="start"))

    # ---- (c) colinear anchors → placement ----
    yh3=ry+48
    s.append(txt(36,yh3,"(c)  the recovered anchors are colinear on the read–reference diagonal → the read is placed",
                 fs=14,weight="bold",anchor="start"))
    # sentence
    sx=60; sy=yh3+28
    for i,ln in enumerate([
        "Coarse blocks give unique anchors cheaply.",
        "An error breaks the coarse block over it,",
        "but its shorter children avoid the error and",
        "still match — recovering the locus with",
        "continuous coverage across the error."]):
        s.append(txt(sx,sy+i*20,ln,fs=12.5,anchor="start",fill=(INK if i==0 else GREY)))
    # dotplot
    gx,gy,gw,gh=575,yh3+18,150,150
    s.append(rect(gx,gy,gw,gh,fill="white",stroke=GREY,sw=1.1))
    s.append(txt(gx+gw/2,gy+gh+18,"reference position",fs=10,fill=GREY))
    s.append(f'<text x="{gx-14}" y="{gy+gh/2}" font-size="10" fill="{GREY}" text-anchor="middle" transform="rotate(-90 {gx-14} {gy+gh/2})" {FONT}>read position</text>')
    s.append(line(gx+0.10*gw, gy+gh-0.10*gh, gx+0.92*gw, gy+gh-0.92*gh, stroke=BLUE, sw=1.4, dash="5,3"))
    pts=[(0.16,GREEN,"B1"),(0.44,GOLD,"c1"),(0.6,GOLD,"c3"),(0.86,GREEN,"B3")]
    for f,c,lab in pts:
        cx=gx+f*gw; cyp=gy+gh-f*gh
        s.append(f'<circle cx="{cx}" cy="{cyp}" r="4.5" fill="{c}" stroke="white" stroke-width="1"/>')
    s.append(txt(gx+18,gy+22,"one diagonal",fs=10,fill=BLUE,weight="bold",anchor="start"))
    s.append(txt(gx+gw+12,gy+12,"● coarse anchor",fs=10.5,fill=GREEN,anchor="start"))
    s.append(txt(gx+gw+12,gy+28,"● fallback anchor",fs=10.5,fill=GOLD,anchor="start"))
    s.append("</svg>")
    return "".join(s)

# =====================================================================
# FIGURE D — DCT split of a monotone run (Cole–Vishkin 3-colouring)
# =====================================================================
def _dct_rounds(vals):
    m=len(vals); coin=list(vals); rounds=[list(coin)]
    while max(coin)>=6:
        nxt=[0]*m
        for i in range(m-1):
            x=coin[i]^coin[i+1]; p=(x & -x).bit_length()-1
            nxt[i]=2*p+((coin[i]>>p)&1)
        nxt[m-1]=1 if nxt[m-2]==0 else 0
        coin=nxt; rounds.append(list(coin))
    pre=list(coin); col=list(coin)
    for v in (3,4,5):
        for i in range(m):
            if col[i]!=v: continue
            l=col[i-1] if i>0 else 99; r=col[i+1] if i+1<m else 99
            col[i]=next(c for c in (0,1,2) if c!=l and c!=r)
    return rounds, pre, col
def _is_min(c,i):
    n=len(c); return (i==0 or c[i]<c[i-1]) and (i==n-1 or c[i]<c[i+1])
def _is_max(c,i):
    n=len(c); return (i==0 or c[i]>c[i-1]) and (i==n-1 or c[i]>c[i+1])
def _dct_split(col):
    """Parse the 3-colouring with the same local-min/local-max triplet rules
    (rules 1 & 2) used by the rest of LCP."""
    m=len(col)
    trip=lambda i: list(range(max(i-1,0), min(i+1,m-1)+1))
    mins=[i for i in range(m) if _is_min(col,i)]
    maxs=[i for i in range(m) if _is_max(col,i)
          and not ((i>0 and _is_min(col,i-1)) or (i+1<m and _is_min(col,i+1)))]
    blocks=[trip(i) for i in mins]+[trip(i) for i in maxs]
    return mins,maxs,blocks
def tri_up(cx,y,fill,sz=7):
    return f'<path d="M {cx-sz} {y} L {cx+sz} {y} L {cx} {y-sz*1.3} Z" fill="{fill}"/>'

def figure_D():
    run=[2,9,11,20,35,41,58,63]
    rounds,pre,col=_dct_rounds(run); coin=rounds[1]      # one reduction round
    minima,maxima,blocks=_dct_split(col)
    changed=[i for i in range(len(pre)) if pre[i]>=3]

    W,H=880,520
    s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" {FONT}>',
       DEFS, rect(0,0,W,H,fill="white",stroke="white",sw=0)]
    s.append(txt(W/2,30,"Splitting a monotone run by deterministic coin-tossing (DCT)",fs=20,weight="bold"))
    s.append(txt(W/2,52,"a strictly increasing run has no interior min/max; DCT recolours it to {0,1,2}, then the usual local-min/max rules cut it into ≤3-unit triplets",
                 fs=12,fill=GREY))

    x0=150; cw=74; n=len(run)
    s+=[txt(x0+i*cw+(cw-4)/2, 76, str(i), fs=10, fill=GREY) for i in range(n)]
    # Row 1 — the run
    yA=86
    s.append(txt(x0-14,yA+24,"run",fs=13,weight="bold",anchor="end"))
    s.append(txt(x0-14,yA+38,"(L hashes)",fs=9,anchor="end",fill=GREY))
    cc,cA=cells(x0,yA,run,cw=cw,ch=38,fs=15,fills=[LGOLD]*n,strokes=[GOLD]*n)
    s.append(cc)
    s.append(txt(x0,yA+58,"strictly increasing ⇒ a proper colouring (neighbours differ), but no interior extremum to split on",
                 fs=11.5,fill=GREY,anchor="start"))
    # arrow 1
    s.append(arrow(x0+n*cw/2, yA+64, x0+n*cw/2, yA+86, stroke=GREY))
    s.append(txt(W/2, yA+103, "①  coin round:  coin′(i) = 2·π(i) + bit,   π = lowest set bit of (cᵢ ⊕ cᵢ₊₁)",
                 fs=12, fill=INK))
    # Row 2 — coin after 1 round
    yB=yA+118
    s.append(txt(x0-14,yB+24,"after",fs=12,weight="bold",anchor="end"))
    s.append(txt(x0-14,yB+38,"1 round",fs=9,anchor="end",fill=GREY))
    cc,cB=cells(x0,yB,coin,cw=cw,ch=34,fs=14,fills=[LGREY]*n,strokes=[GREY]*n)
    s.append(cc)
    s.append(txt(x0,yB+54,"e.g. 2 ⊕ 9 = 1011₂ → π = 0, bit 0 of 2 = 0  ⇒  0",fs=11,fill=GREY,anchor="start"))
    # arrow 2
    s.append(arrow(x0+n*cw/2, yB+58, x0+n*cw/2, yB+80, stroke=GREY))
    s.append(txt(W/2, yB+97, "②  collapse colours {3,4,5} → {0,1,2}  (recolour to differ from both neighbours)",
                 fs=12, fill=INK))
    # Row 3 — 3-colouring
    yC=yB+112
    s.append(txt(x0-14,yC+24,"3-colour",fs=12,weight="bold",anchor="end"))
    fills=[LBLUE]*n; strokes=[BLUE]*n
    for i in changed: fills[i]=LRED; strokes[i]=RED
    cc,cC=cells(x0,yC,col,cw=cw,ch=34,fs=15,fills=fills,strokes=strokes)
    s.append(cc)
    # min/max marks (the rule triggers)
    for i in maxima: s.append(tri_up(cC[i],yC-4,GOLD))
    for i in minima: s.append(f'<path d="M {cC[i]-7} {yC+38} L {cC[i]+7} {yC+38} L {cC[i]} {yC+47} Z" fill="{BLUE}"/>')
    s.append(txt(x0+n*cw+8, yC+30, "▼ local min", fs=10, fill=BLUE, anchor="start"))
    s.append(txt(W/2, yC+66,
                 "③  parse the colouring with the local-min / local-max triplet rules (rules 1 & 2 — the same as everywhere else)",fs=11.5,fill=INK))
    # min triplet blocks {i-1,i,i+1} (alternate colour), under row 3
    by=yC+80
    for k,blk in enumerate(blocks):
        a,b=blk[0],blk[-1]; col_=BLUE if k%2==0 else GOLD; yoff=0 if k%2==0 else 12
        xL=x0+a*cw-1; xR=x0+b*cw+(cw-4)+1
        s.append(bracket(xL,xR,by+yoff,"",color=col_))
    sizes=", ".join(str(len(b)) for b in blocks)
    s.append(txt(W/2, by+44, f"→ centred {{i−1, i, i+1}} triplets, identical in form to every other block ({len(blocks)} blocks, sizes {sizes})",
                 fs=12, fill=INK, weight="bold"))
    s.append(txt(W/2, by+64,
                 "over {0,1,2} no two slope points are adjacent, so the min/max triplets cover the run with blocks of ≤3 units (no size-capping)",
                 fs=11.5, fill=GREY, style="italic"))
    s.append("</svg>")
    return "".join(s)

def write(name, svg):
    open(os.path.join(OUT,name+".svg"),"w").write(svg)
    cairosvg.svg2pdf(bytestring=svg.encode(), write_to=os.path.join(OUT,name+".pdf"))
    cairosvg.svg2png(bytestring=svg.encode(), write_to=os.path.join(OUT,name+".png"), scale=2)
    print("wrote", name, "(svg/pdf/png)")

write("syncmer_toy", figure_A())
write("lcp_hierarchy_toy", figure_B())
write("block_match_fallback", figure_C())
write("dct_split", figure_D())
print("done ->", OUT)
