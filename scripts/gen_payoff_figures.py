#!/usr/bin/env python3
"""為《美股選擇權》課程產生全套自繪 SVG 圖表(純標準庫、冪等、可重跑)。

用法:python3 scripts/gen_payoff_figures.py
輸出:courses/options/assets/charts/*.svg(21 張)

風格(與 design doc 同款,深淺色主題皆可讀):
- viewBox 0 0 640 400,不設固定寬高(響應式);背景透明
- 軸線/刻度/文字 #8b949e;獲利區綠、虧損區紅(半透明填色 + 2px 描邊)
- 履約價/兩平點虛線 #8b949e dasharray 4 4
- KOL 兩張圖(gozilla-cc-params / led-csp-flow)參數依 research/kol-strategies.md,不自行編造
"""
from __future__ import annotations

import math
import sys
from pathlib import Path
from xml.dom import minidom

OUT = Path(__file__).resolve().parents[1] / "courses" / "options" / "assets" / "charts"

INK = "#8b949e"
GREEN = "#2ea043"
GREEN_F = "rgba(46,160,67,.22)"
RED = "#f85149"
RED_F = "rgba(248,81,73,.20)"
AMBER = "#d29922"
AMBER_F = "rgba(210,153,34,.20)"
GRAY_F = "rgba(139,148,158,.14)"
FONT = "system-ui, -apple-system, sans-serif"
DASH = "4 4"

DEFS = (
    "<defs>"
    '<marker id="aI" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7"'
    ' orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#8b949e"/></marker>'
    '<marker id="aG" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7"'
    ' orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#2ea043"/></marker>'
    '<marker id="aR" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7"'
    ' orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#f85149"/></marker>'
    "</defs>"
)


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def P(v: float) -> str:
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


def g(v: float) -> str:
    return f"{v:g}"


def T(x, y, s, *, size=14, fill=INK, anchor="start", weight=None, opacity=None):
    w = f' font-weight="{weight}"' if weight else ""
    o = f' opacity="{opacity}"' if opacity else ""
    return (
        f'<text x="{P(x)}" y="{P(y)}" font-size="{size}" fill="{fill}"'
        f' text-anchor="{anchor}"{w}{o}>{esc(s)}</text>'
    )


def doc(body: list[str], aria: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 400" role="img"'
        f' aria-label="{esc(aria)}" font-family="{esc(FONT)}">'
        + DEFS
        + "".join(body)
        + "</svg>"
    )


class Frame:
    """資料座標 → viewBox 座標(y 反向)。xlim 可反向(如天數 90→0)。"""

    def __init__(self, xlim, ylim, left=64, right=30, top=54, bottom=62):
        self.x0, self.x1 = xlim
        self.y0, self.y1 = ylim
        self.L, self.R = left, 640 - right
        self.Tp, self.B = top, 400 - bottom

    def X(self, x):
        return self.L + (x - self.x0) / (self.x1 - self.x0) * (self.R - self.L)

    def Y(self, y):
        return self.B - (y - self.y0) / (self.y1 - self.y0) * (self.B - self.Tp)

    def pts(self, seq):
        return " ".join(f"{P(self.X(x))},{P(self.Y(y))}" for x, y in seq)


# ---------- 損益線的分段(獲利/虧損區) ----------

def _sgn(v):
    return (v > 1e-9) - (v < -1e-9)


def refine(pts):
    """在損益線穿越 0 的地方插入兩平點。"""
    out = [pts[0]]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if _sgn(y0) * _sgn(y1) < 0:
            t = y0 / (y0 - y1)
            out.append((x0 + (x1 - x0) * t, 0.0))
        out.append((x1, y1))
    return out


def signed_runs(pts):
    """把折線切成同號的段(+1 獲利 / -1 虧損),兩平點屬於兩側。"""
    runs, cur, sign = [], [pts[0]], _sgn(pts[0][1])
    for p in pts[1:]:
        s = _sgn(p[1])
        if sign == 0:
            cur.append(p)
            sign = s
        elif s == 0:
            cur.append(p)
            runs.append((sign, cur))
            cur, sign = [p], 0
        elif s == sign:
            cur.append(p)
        else:  # 理論上不會發生(refine 已插入 0 點)
            runs.append((sign, cur))
            cur, sign = [cur[-1], p], s
    runs.append((sign, cur))
    return [(s, r) for s, r in runs if len(r) >= 2]


def zero_crossings(pts):
    return sorted(round(x, 6) for x, y in refine(pts) if _sgn(y) == 0)


def clip_seg(p0, p1, xlim, ylim):
    """Liang–Barsky:把參考線段裁進資料範圍。"""
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    t0, t1 = 0.0, 1.0
    for p, q in (
        (-dx, x0 - min(xlim)), (dx, max(xlim) - x0),
        (-dy, y0 - min(ylim)), (dy, max(ylim) - y0),
    ):
        if p == 0:
            if q < 0:
                return None
            continue
        r = q / p
        if p < 0:
            t0 = max(t0, r)
        else:
            t1 = min(t1, r)
    if t0 > t1:
        return None
    return (x0 + t0 * dx, y0 + t0 * dy), (x0 + t1 * dx, y0 + t1 * dy)


# ---------- 損益圖(分段線性)通用繪製 ----------

def payoff_chart(*, title, note, pts, xlim, ylim, strikes=(), bes=(), levels=(),
                 annos=(), light=None, light_label=None, arrow_end=None,
                 xlabel="到期時股價", ylabel="損益", aria=""):
    fr = Frame(xlim, ylim)
    b = []
    b.append(T(320, 24, title, size=16, anchor="middle", weight="600"))
    if note:
        b.append(T(320, 42, note, size=12, anchor="middle"))
    y0px = fr.Y(0)
    # 關鍵水平位(封頂/封底):虛線 + 左側數字
    for yv, lab, col in levels:
        yy = fr.Y(yv)
        b.append(
            f'<line x1="{fr.L}" y1="{P(yy)}" x2="{fr.R}" y2="{P(yy)}"'
            f' stroke="{col}" stroke-width="1" stroke-dasharray="{DASH}" opacity=".55"/>'
        )
        b.append(T(fr.L - 8, yy + 5, lab, size=16, fill=col, anchor="end", weight="600"))
    # 履約價虛線
    for s, lab in strikes:
        x = fr.X(s)
        b.append(
            f'<line x1="{P(x)}" y1="{fr.Tp}" x2="{P(x)}" y2="{fr.B}"'
            f' stroke="{INK}" stroke-width="1" stroke-dasharray="{DASH}"/>'
        )
        b.append(T(x, fr.B + 17, lab, size=13, anchor="middle"))
    # 對照淡線(純持股 / 直接買股)
    if light:
        seg = clip_seg(light[0], light[1], xlim, ylim)
        if seg:
            (xa, ya), (xb, yb) = seg
            b.append(
                f'<line x1="{P(fr.X(xa))}" y1="{P(fr.Y(ya))}" x2="{P(fr.X(xb))}"'
                f' y2="{P(fr.Y(yb))}" stroke="{INK}" stroke-width="1.5" opacity=".55"/>'
            )
        if light_label:
            lx, ly, txt, anchor = light_label
            b.append(T(fr.X(lx), fr.Y(ly), txt, size=12, anchor=anchor, opacity=".8"))
    # 獲利/虧損填色
    runs = signed_runs(refine(pts))
    for sign, run in runs:
        if sign == 0:
            continue
        fill = GREEN_F if sign > 0 else RED_F
        poly = run + [(run[-1][0], 0.0), (run[0][0], 0.0)]
        b.append(f'<polygon points="{fr.pts(poly)}" fill="{fill}"/>')
    # 座標軸(x 軸畫在損益=0)
    b.append(
        f'<line x1="{fr.L}" y1="{P(y0px)}" x2="{fr.R}" y2="{P(y0px)}"'
        f' stroke="{INK}" stroke-width="1.2"/>'
    )
    b.append(
        f'<line x1="{fr.L}" y1="{fr.Tp}" x2="{fr.L}" y2="{fr.B}"'
        f' stroke="{INK}" stroke-width="1.2"/>'
    )
    b.append(T(fr.L - 8, y0px + 4, "0", size=12, anchor="end"))
    # 損益線描邊(綠/紅 2px)
    for i, (sign, run) in enumerate(runs):
        col = GREEN if sign > 0 else RED if sign < 0 else INK
        extra = ""
        if arrow_end and i == len(runs) - 1:
            extra = f' marker-end="url(#{arrow_end})"'
        b.append(
            f'<polyline points="{fr.pts(run)}" fill="none" stroke="{col}"'
            f' stroke-width="2" stroke-linejoin="round" stroke-linecap="round"{extra}/>'
        )
    # 兩平點
    for s, dx, dy, anchor in bes:
        b.append(f'<circle cx="{P(fr.X(s))}" cy="{P(y0px)}" r="3.5" fill="{INK}"/>')
        b.append(T(fr.X(s) + dx, y0px + dy, f"兩平 {g(s)}", size=14, anchor=anchor, weight="600"))
    # 圖內標註
    for x, y, txt, size, anchor, col in annos:
        b.append(T(fr.X(x), fr.Y(y), txt, size=size, anchor=anchor, fill=col))
    # 軸標籤
    b.append(T(fr.R, fr.B + 40, xlabel, size=14, anchor="end"))
    b.append(
        f'<text transform="translate(17 {P((fr.Tp + fr.B) / 2)}) rotate(-90)"'
        f' text-anchor="middle" font-size="14" fill="{INK}">{esc(ylabel)}</text>'
    )
    return doc(b, aria)


# ---------- 曲線圖通用:座標軸(x 軸畫在底部) ----------

def axes_bottom(b, fr, xlabel, ylabel, xticks=()):
    b.append(
        f'<line x1="{fr.L}" y1="{fr.B}" x2="{fr.R}" y2="{fr.B}"'
        f' stroke="{INK}" stroke-width="1.2"/>'
    )
    b.append(
        f'<line x1="{fr.L}" y1="{fr.Tp}" x2="{fr.L}" y2="{fr.B}"'
        f' stroke="{INK}" stroke-width="1.2"/>'
    )
    for v, lab in xticks:
        x = fr.X(v)
        b.append(
            f'<line x1="{P(x)}" y1="{fr.B}" x2="{P(x)}" y2="{fr.B + 5}"'
            f' stroke="{INK}" stroke-width="1.2"/>'
        )
        b.append(T(x, fr.B + 19, lab, size=12, anchor="middle"))
    b.append(T(fr.R, fr.B + 40, xlabel, size=14, anchor="end"))
    b.append(
        f'<text transform="translate(17 {P((fr.Tp + fr.B) / 2)}) rotate(-90)"'
        f' text-anchor="middle" font-size="14" fill="{INK}">{esc(ylabel)}</text>'
    )


def vline_dashed(b, fr, x, y_top=None):
    xx = fr.X(x)
    b.append(
        f'<line x1="{P(xx)}" y1="{y_top if y_top is not None else fr.Tp}" y2="{fr.B}"'
        f' x2="{P(xx)}" stroke="{INK}" stroke-width="1" stroke-dasharray="{DASH}"/>'
    )


# ---------- Black–Scholes(僅用 math.erf,r=0) ----------

def ncdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def bs_call(S, K, sigma, Ty):
    if Ty <= 0:
        return max(S - K, 0.0)
    v = sigma * math.sqrt(Ty)
    d1 = (math.log(S / K) + 0.5 * sigma * sigma * Ty) / v
    return S * ncdf(d1) - K * ncdf(d1 - v)


def bs_delta(S, K, sigma, Ty):
    v = sigma * math.sqrt(Ty)
    d1 = (math.log(S / K) + 0.5 * sigma * sigma * Ty) / v
    return ncdf(d1)


# ---------- 流程圖元件 ----------

def rbox(b, cx, cy, w, h, lines, *, stroke=INK, fill="none", rx=9, lh=18, sw=1.5):
    b.append(
        f'<rect x="{P(cx - w / 2)}" y="{P(cy - h / 2)}" width="{P(w)}" height="{P(h)}"'
        f' rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
    )
    n = len(lines)
    y = cy - (n - 1) * lh / 2
    for txt, size, col, wt in lines:
        b.append(T(cx, y + size * 0.35, txt, size=size, fill=col, anchor="middle", weight=wt))
        y += lh


def LN(txt, size=13, col=INK, wt=None):
    return (txt, size, col, wt)


def arrow(b, x1, y1, x2, y2, *, color=INK, marker="aI", width=1.5, label=None,
          ldx=0, ldy=0, lsize=12, lanchor="middle", lcol=INK):
    b.append(
        f'<line x1="{P(x1)}" y1="{P(y1)}" x2="{P(x2)}" y2="{P(y2)}"'
        f' stroke="{color}" stroke-width="{width}" marker-end="url(#{marker})"/>'
    )
    if label:
        b.append(T((x1 + x2) / 2 + ldx, (y1 + y2) / 2 + ldy, label,
                   size=lsize, anchor=lanchor, fill=lcol))


def qarrow(b, x1, y1, qx, qy, x2, y2, *, color=INK, marker="aI", width=1.5):
    b.append(
        f'<path d="M{P(x1)} {P(y1)} Q{P(qx)} {P(qy)} {P(x2)} {P(y2)}" fill="none"'
        f' stroke="{color}" stroke-width="{width}" marker-end="url(#{marker})"/>'
    )


# ============================================================
# 一、損益圖(分段線性)
# ============================================================

def fig_long_call():
    pts = [(70, -5), (100, -5), (130, 25)]
    assert zero_crossings(pts) == [105]
    return payoff_chart(
        title="買進買權 Long Call(K=100,權利金 5)",
        note="最大損失=權利金(−5);上檔獲利無上限;兩平=K+權利金=105",
        pts=pts, xlim=(70, 130), ylim=(-14, 30),
        strikes=[(100, "K=100")], bes=[(105, 7, -10, "start")],
        levels=[(-5, "−5", RED)],
        annos=[(129, 15, "獲利無上限", 14, "end", GREEN)],
        arrow_end="aG",
        aria="Long Call 損益圖:履約價 100、權利金 5,兩平 105,最大損失為權利金",
    )


def fig_long_put():
    pts = [(70, 25), (100, -5), (130, -5)]
    assert zero_crossings(pts) == [95]
    return payoff_chart(
        title="買進賣權 Long Put(K=100,權利金 5)",
        note="最大損失=權利金(−5);兩平=K−權利金=95",
        pts=pts, xlim=(70, 130), ylim=(-14, 30),
        strikes=[(100, "K=100")], bes=[(95, -7, -10, "end")],
        levels=[(-5, "−5", RED)],
        annos=[(72, 27.5, "最大獲利=95(股價跌到 0)", 13, "start", GREEN)],
        aria="Long Put 損益圖:履約價 100、權利金 5,兩平 95,最大損失為權利金",
    )


def fig_short_call():
    pts = [(70, 5), (100, 5), (140, -35)]
    assert zero_crossings(pts) == [105]
    return payoff_chart(
        title="裸賣買權 Short Call(K=100,收權利金 5)",
        note="最多只賺權利金(+5);上檔損失無上限——兩位 KOL 都明言不裸賣",
        pts=pts, xlim=(70, 140), ylim=(-38, 12),
        strikes=[(100, "K=100")], bes=[(105, 7, -10, "start")],
        levels=[(5, "+5", GREEN)],
        annos=[(137, -25, "損失無上限", 15, "end", RED)],
        arrow_end="aR",
        aria="Short Call 裸賣損益圖:最多賺權利金 5,股價上漲損失無上限",
    )


def fig_short_put():
    pts = [(70, -25), (100, 5), (130, 5)]
    assert zero_crossings(pts) == [95]
    return payoff_chart(
        title="賣出賣權 Short Put(K=100,收權利金 5)",
        note="最多只賺權利金(+5);務必備妥現金(cash-secured),不做裸賣 put",
        pts=pts, xlim=(70, 130), ylim=(-30, 12),
        strikes=[(100, "K=100")], bes=[(95, -7, -10, "end")],
        levels=[(5, "+5", GREEN)],
        annos=[(78, -27, "最大損失=K−權利金=95(股價跌到 0)", 13, "start", RED)],
        aria="Short Put 損益圖:最多賺權利金 5,兩平 95,股價跌到 0 時最大損失 95",
    )


def fig_covered_call():
    # 持股成本 100,賣 K=110 買權收 3:上檔封頂 13,兩平 97
    pts = [(80, -17), (110, 13), (140, 13)]
    assert zero_crossings(pts) == [97]
    assert max(y for _, y in pts) == 13  # (110-100)+3
    return payoff_chart(
        title="Covered Call:持股(成本 100)+ 賣 K=110 買權(收 3)",
        note="上檔封頂 +13=(K−成本)+權利金;下檔同持股風險(少虧權利金 3);兩平=97",
        pts=pts, xlim=(80, 140), ylim=(-26, 42),
        strikes=[(110, "K=110")], bes=[(97, 7, -10, "start")],
        levels=[(13, "+13", GREEN)],
        light=((80, -20), (140, 40)),
        light_label=(120, 35, "純持股(成本 100)", "middle"),
        aria="Covered Call 損益圖:持股加賣出買權,上檔獲利封頂 13,兩平 97,附純持股對照線",
    )


def fig_cash_secured_put():
    # 賣 K=100 賣權收 4:兩平 96
    pts = [(70, -26), (100, 4), (130, 4)]
    assert zero_crossings(pts) == [96]
    return payoff_chart(
        title="Cash-Secured Put:賣 K=100 賣權(收 4)+ 備妥現金",
        note="未被指派:收權利金 +4;被指派:成本=兩平 96,比直接買股便宜 4 元",
        pts=pts, xlim=(70, 130), ylim=(-34, 34),
        strikes=[(100, "K=100")], bes=[(96, -7, -10, "end")],
        levels=[(4, "+4", GREEN)],
        light=((70, -30), (130, 30)),
        light_label=(112, 29, "直接買股(成本 100)", "middle"),
        aria="Cash-Secured Put 損益圖:收權利金 4,兩平 96,附直接買股對照線",
    )


def fig_bull_put_spread():
    # 賣 100P / 買 90P,收 3:最大損失 7,兩平 97
    pts = [(75, -7), (90, -7), (100, 3), (125, 3)]
    assert zero_crossings(pts) == [97]
    return payoff_chart(
        title="Bull Put Spread 多頭賣權價差(賣 100P / 買 90P,收 3)",
        note="收 3;最大損失=價差寬 10−權利金 3=7,風險封頂;兩平=100−3=97",
        pts=pts, xlim=(75, 125), ylim=(-12, 8),
        strikes=[(90, "K1=90"), (100, "K2=100")], bes=[(97, -6, -10, "end")],
        levels=[(3, "+3", GREEN), (-7, "−7", RED)],
        aria="Bull Put Spread 損益圖:收 3,最大損失封頂 7,兩平 97",
    )


def fig_bear_call_spread():
    # 賣 100C / 買 110C,收 3:最大損失 7,兩平 103
    pts = [(75, 3), (100, 3), (110, -7), (125, -7)]
    assert zero_crossings(pts) == [103]
    return payoff_chart(
        title="Bear Call Spread 空頭買權價差(賣 100C / 買 110C,收 3)",
        note="收 3;最大損失=價差寬 10−權利金 3=7,風險封頂;兩平=100+3=103",
        pts=pts, xlim=(75, 125), ylim=(-12, 8),
        strikes=[(100, "K1=100"), (110, "K2=110")], bes=[(103, 7, -10, "start")],
        levels=[(3, "+3", GREEN), (-7, "−7", RED)],
        aria="Bear Call Spread 損益圖:收 3,最大損失封頂 7,兩平 103",
    )


def fig_iron_condor():
    # 買 85P / 賣 95P / 賣 105C / 買 115C,收 3:兩平 92 與 108
    pts = [(75, -7), (85, -7), (95, 3), (105, 3), (115, -7), (125, -7)]
    assert zero_crossings(pts) == [92, 108]
    return payoff_chart(
        title="Iron Condor 四腳(買 85P/賣 95P/賣 105C/買 115C,收 3)",
        note="中間 95–105 為獲利帶(+3);兩側風險皆封頂 −7=價差寬 10−權利金 3",
        pts=pts, xlim=(75, 125), ylim=(-12, 8),
        strikes=[(85, "K1=85"), (95, "K2=95"), (105, "K3=105"), (115, "K4=115")],
        bes=[(92, -6, -10, "end"), (108, 6, -10, "start")],
        levels=[(3, "+3", GREEN), (-7, "−7", RED)],
        annos=[(100, 5.6, "中間獲利帶", 14, "middle", GREEN)],
        aria="Iron Condor 損益圖:四個履約價,中間 95 到 105 獲利帶,兩側損失封頂 7",
    )


def fig_collar():
    # 持股成本 100 + 買 90P + 賣 110C,權利金互抵:−10 封底 / +10 封頂
    pts = [(70, -10), (90, -10), (110, 10), (140, 10)]
    assert zero_crossings(pts) == [100]
    return payoff_chart(
        title="Collar 領口:持股(成本 100)+ 買 90P + 賣 110C",
        note="買 put 護底(−10 封底)、賣 call 封頂(+10),權利金互抵≈零成本;兩平=100",
        pts=pts, xlim=(70, 140), ylim=(-22, 22),
        strikes=[(90, "K1=90"), (110, "K2=110")], bes=[(100, 7, -10, "start")],
        levels=[(10, "+10", GREEN), (-10, "−10", RED)],
        light=((70, -30), (140, 40)),
        light_label=(111, 20, "純持股", "end"),
        aria="Collar 損益圖:下檔損失封底 10,上檔獲利封頂 10,兩平 100,附純持股對照線",
    )


# ============================================================
# 二、曲線 / 概念圖
# ============================================================

def fig_premium_decomposition():
    K, sigma, Ty = 100.0, 0.30, 0.25
    fr = Frame((70, 130), (0, 34))
    curve = [(s, bs_call(s, K, sigma, Ty)) for s in range(70, 131)]
    intr = [(s, max(s - K, 0.0)) for s in range(70, 131)]
    b = []
    b.append(T(320, 24, "權利金 = 內在價值 + 時間價值(以 K=100 買權為例)",
               size=16, anchor="middle", weight="600"))
    b.append(T(320, 42, "價外(S<K)只剩時間價值;到期時時間價值歸零,只剩內在價值",
               size=12, anchor="middle"))
    # 內在價值(綠)
    b.append(f'<polygon points="{fr.pts(intr + [(130, 0), (70, 0)])}" fill="{GREEN_F}"/>')
    b.append(
        f'<polyline points="{fr.pts(intr)}" fill="none" stroke="{GREEN}"'
        f' stroke-width="2" stroke-linejoin="round"/>'
    )
    # 時間價值帶(琥珀,= 權利金曲線 − 內在)
    band = curve + intr[::-1]
    b.append(f'<polygon points="{fr.pts(band)}" fill="{AMBER_F}"/>')
    b.append(
        f'<polyline points="{fr.pts(curve)}" fill="none" stroke="{AMBER}"'
        f' stroke-width="2" stroke-linejoin="round"/>'
    )
    vline_dashed(b, fr, 100)
    b.append(T(fr.X(100), fr.B + 17, "K=100", size=13, anchor="middle"))
    axes_bottom(b, fr, "目前股價", "價值", xticks=[(80, "80"), (120, "120")])
    # 標籤 + 引線
    b.append(T(fr.X(124), fr.Y(9), "內在價值", size=14, fill=GREEN, anchor="end", weight="600"))
    b.append(T(fr.X(74), fr.Y(24), "時間價值(權利金−內在)", size=14, fill=AMBER, weight="600"))
    b.append(
        f'<line x1="{P(fr.X(94))}" y1="{P(fr.Y(22.4))}" x2="{P(fr.X(100))}"'
        f' y2="{P(fr.Y(7))}" stroke="{AMBER}" stroke-width="1" opacity=".7"/>'
    )
    b.append(T(fr.X(74), fr.Y(19.5), "權利金曲線", size=12, fill=AMBER, opacity=".9"))
    return doc(b, aria="權利金分解圖:買權價值曲線分成內在價值與時間價值兩塊,價平附近時間價值最大")


def fig_theta_decay():
    fr = Frame((90, 0), (0, 12))
    curve = [(t, 10.0 * math.sqrt(t / 90.0)) for t in range(90, -1, -1)]
    b = []
    b.append(T(320, 24, "時間價值的衰減(Theta Decay)", size=16, anchor="middle", weight="600"))
    b.append(T(320, 42, "時間價值約與 √剩餘天數 成正比:前段掉得慢,最後 30 天加速歸零",
               size=12, anchor="middle"))
    # 30 天加速區(紅帶)
    x30 = fr.X(30)
    b.append(
        f'<rect x="{P(x30)}" y="{fr.Tp}" width="{P(fr.R - x30)}"'
        f' height="{P(fr.B - fr.Tp)}" fill="{RED_F}"/>'
    )
    vline_dashed(b, fr, 30)
    b.append(T((x30 + fr.R) / 2, fr.Tp + 18, "最後 30 天加速衰減", size=13,
               fill=RED, anchor="middle", weight="600"))
    b.append(
        f'<polyline points="{fr.pts(curve)}" fill="none" stroke="{AMBER}"'
        f' stroke-width="2" stroke-linejoin="round"/>'
    )
    axes_bottom(b, fr, "距到期天數", "時間價值",
                xticks=[(90, "90"), (60, "60"), (30, "30"), (0, "0(到期)")])
    b.append(T(fr.X(70), fr.Y(9.6), "衰減平緩", size=13, fill=AMBER))
    b.append(T(fr.X(26), fr.Y(3.2), "對賣方有利:", size=13, fill=RED, weight="600"))
    b.append(T(fr.X(26), fr.Y(1.9), "短天期收租靠這段", size=13, fill=RED))
    return doc(b, aria="Theta 衰減曲線:時間價值隨到期日接近而加速下降,最後 30 天為加速區")


def fig_iv_crush():
    fr = Frame((-10, 5), (0, 240))
    iv = [(-10, 100), (-9, 105), (-8, 111), (-7, 118), (-6, 127), (-5, 137),
          (-4, 149), (-3, 163), (-2, 178), (-1, 193), (0, 205),
          (1, 95), (2, 92), (3, 90), (4, 89), (5, 88)]
    prem = [(-10, 100), (-9, 103), (-8, 107), (-7, 112), (-6, 118), (-5, 125),
            (-4, 133), (-3, 141), (-2, 149), (-1, 156), (0, 162),
            (1, 60), (2, 56), (3, 53), (4, 51), (5, 49)]
    b = []
    b.append(T(320, 24, "財報前後的 IV 與權利金(IV Crush)", size=16, anchor="middle", weight="600"))
    b.append(T(320, 42, "財報前不確定性推升 IV 與權利金;公布後 IV 驟降——方向看對也可能賠錢",
               size=12, anchor="middle"))
    vline_dashed(b, fr, 0)
    b.append(
        f'<polyline points="{fr.pts(iv)}" fill="none" stroke="{AMBER}"'
        f' stroke-width="2" stroke-linejoin="round"/>'
    )
    b.append(
        f'<polyline points="{fr.pts(prem)}" fill="none" stroke="{INK}"'
        f' stroke-width="2" stroke-linejoin="round"/>'
    )
    b.append(T(fr.X(-0.6), fr.Y(212), "IV(隱含波動率)", size=13, fill=AMBER,
               anchor="end", weight="600"))
    b.append(T(fr.X(-0.6), fr.Y(150), "權利金", size=13, anchor="end"))
    arrow(b, fr.X(0.7), fr.Y(150), fr.X(0.7), fr.Y(72), color=RED, marker="aR", width=2)
    b.append(T(fr.X(1.1), fr.Y(120), "IV crush", size=15, fill=RED, weight="600"))
    b.append(T(fr.X(1.1), fr.Y(100), "權利金一夜蒸發", size=12, fill=RED))
    axes_bottom(b, fr, "財報前後交易日", "相對水準",
                xticks=[(-10, "−10"), (-5, "−5"), (0, "財報"), (5, "+5")])
    b.append(T(fr.L, fr.Tp - 4, "指數化:10 日前=100", size=11, opacity=".8"))
    return doc(b, aria="IV crush 示意圖:財報前 IV 與權利金走高,公布後同步驟降,權利金蒸發")


def fig_delta_slope():
    K, sigma, Ty = 100.0, 0.30, 0.25
    fr = Frame((70, 130), (0, 32))
    curve = [(s, bs_call(s, K, sigma, Ty)) for s in range(70, 131)]
    d_atm = bs_delta(100, K, sigma, Ty)
    c_atm = bs_call(100, K, sigma, Ty)
    d_otm = bs_delta(85, K, sigma, Ty)
    c_otm = bs_call(85, K, sigma, Ty)
    b = []
    b.append(T(320, 24, "Delta:選擇權價值對股價的斜率(切線)", size=16, anchor="middle", weight="600"))
    b.append(T(320, 42, "股價每漲 1 元,權利金約漲 Delta 元;越價內 Delta 越接近 1",
               size=12, anchor="middle"))
    vline_dashed(b, fr, 100)
    b.append(T(fr.X(100), fr.B + 17, "K=100", size=13, anchor="middle"))
    b.append(
        f'<polyline points="{fr.pts(curve)}" fill="none" stroke="{INK}"'
        f' stroke-width="2" stroke-linejoin="round" opacity=".9"/>'
    )
    # 價外切線(琥珀)
    tan_otm = [(s, c_otm + d_otm * (s - 85)) for s in (79, 97)]
    b.append(
        f'<line x1="{P(fr.X(tan_otm[0][0]))}" y1="{P(fr.Y(tan_otm[0][1]))}"'
        f' x2="{P(fr.X(tan_otm[1][0]))}" y2="{P(fr.Y(tan_otm[1][1]))}"'
        f' stroke="{AMBER}" stroke-width="2"/>'
    )
    b.append(f'<circle cx="{P(fr.X(85))}" cy="{P(fr.Y(c_otm))}" r="4" fill="{AMBER}"/>')
    b.append(T(fr.X(74), fr.Y(5.5), f"價外:Delta≈{d_otm:.2f}", size=14, fill=AMBER, weight="600"))
    # 價平切線(綠)
    tan_atm = [(s, c_atm + d_atm * (s - 100)) for s in (90, 118)]
    b.append(
        f'<line x1="{P(fr.X(tan_atm[0][0]))}" y1="{P(fr.Y(tan_atm[0][1]))}"'
        f' x2="{P(fr.X(tan_atm[1][0]))}" y2="{P(fr.Y(tan_atm[1][1]))}"'
        f' stroke="{GREEN}" stroke-width="2"/>'
    )
    b.append(f'<circle cx="{P(fr.X(100))}" cy="{P(fr.Y(c_atm))}" r="4" fill="{GREEN}"/>')
    b.append(T(fr.X(74), fr.Y(19), f"價平:Delta≈{d_atm:.2f}", size=14, fill=GREEN, weight="600"))
    b.append(
        f'<line x1="{P(fr.X(92))}" y1="{P(fr.Y(18))}" x2="{P(fr.X(99))}"'
        f' y2="{P(fr.Y(c_atm + 1))}" stroke="{GREEN}" stroke-width="1" opacity=".6"/>'
    )
    axes_bottom(b, fr, "目前股價", "選擇權價值", xticks=[(80, "80"), (120, "120")])
    return doc(b, aria="Delta 切線圖:選擇權價值曲線上,價平切線斜率約 0.5,價外切線更平緩")


def fig_moneyness():
    b = []
    b.append(T(320, 24, "價內 / 價平 / 價外(Moneyness)", size=16, anchor="middle", weight="600"))
    b.append(T(320, 42, "價內=履約對你有利:買權要股價>K,賣權要股價<K;價平時間價值最大",
               size=12, anchor="middle"))
    Kx = 340
    rows = [("買權 Call", 92, False), ("賣權 Put", 202, True)]
    for name, y, itm_left in rows:
        h = 58
        left_fill = GREEN_F if itm_left else GRAY_F
        right_fill = GRAY_F if itm_left else GREEN_F
        b.append(f'<rect x="80" y="{y}" width="{Kx - 15 - 80}" height="{h}" fill="{left_fill}"/>')
        b.append(f'<rect x="{Kx + 15}" y="{y}" width="{600 - Kx - 15}" height="{h}" fill="{right_fill}"/>')
        b.append(f'<rect x="{Kx - 15}" y="{y}" width="30" height="{h}" fill="{AMBER_F}"/>')
        cy = y + h / 2 + 5
        lt = ("價內 ITM", GREEN) if itm_left else ("價外 OTM", INK)
        rt = ("價外 OTM", INK) if itm_left else ("價內 ITM", GREEN)
        b.append(T(205, cy, lt[0], size=15, fill=lt[1], anchor="middle", weight="600"))
        b.append(T(475, cy, rt[0], size=15, fill=rt[1], anchor="middle", weight="600"))
        b.append(T(72, cy, name, size=14, anchor="end"))
    b.append(
        f'<line x1="{Kx}" y1="70" x2="{Kx}" y2="286" stroke="{INK}"'
        f' stroke-width="1" stroke-dasharray="{DASH}"/>'
    )
    b.append(T(Kx, 66, "K(履約價)", size=13, anchor="middle"))
    b.append(T(Kx, 182, "價平 ATM", size=14, fill=AMBER, anchor="middle", weight="600"))
    b.append(
        f'<line x1="80" y1="300" x2="600" y2="300" stroke="{INK}"'
        f' stroke-width="1.2" marker-end="url(#aI)"/>'
    )
    b.append(T(84, 318, "股價低", size=12))
    b.append(T(596, 318, "股價高", size=12, anchor="end"))
    b.append(T(320, 352, "同一個 K:對買權是價外時,對賣權就是價內(方向相反)",
               size=12, anchor="middle"))
    return doc(b, aria="Moneyness 區帶圖:買權在股價高於履約價時為價內,賣權相反,履約價附近為價平")


# ============================================================
# 三、流程 / 結構圖
# ============================================================

def fig_expiry_flow():
    b = []
    b.append(T(320, 24, "到期結算:價內自動履約,價外歸零", size=16, anchor="middle", weight="600"))
    rbox(b, 320, 64, 170, 36, [LN("到期日收盤", 14, INK, "600")])
    arrow(b, 320, 82, 320, 112)
    # 判斷菱形
    b.append(
        f'<polygon points="320,114 412,152 320,190 228,152" fill="none"'
        f' stroke="{INK}" stroke-width="1.5"/>'
    )
    b.append(T(320, 149, "是否價內?", size=14, anchor="middle", weight="600"))
    b.append(T(320, 168, "(股價 vs 履約價 K)", size=11, anchor="middle"))
    arrow(b, 262, 176, 176, 226, label="是(ITM)", ldx=-36, ldy=-4, lcol=GREEN)
    arrow(b, 378, 176, 464, 226, label="否(OTM)", ldx=40, ldy=-4, lcol=RED)
    rbox(b, 160, 268, 236, 76,
         [LN("自動履約(轉股票部位)", 14, GREEN, "600"),
          LN("買權:以 K 買進股票", 12),
          LN("賣權:以 K 賣出股票", 12)],
         stroke=GREEN, fill=GREEN_F, lh=19)
    rbox(b, 480, 268, 236, 76,
         [LN("權利金歸零", 14, RED, "600"),
          LN("買方:損失全部權利金", 12),
          LN("賣方:權利金全數落袋", 12)],
         stroke=RED, fill=RED_F, lh=19)
    b.append(T(320, 340, "美股規則:到期時價內 $0.01 即自動履約", size=12, anchor="middle"))
    b.append(T(320, 358, "不想接股 / 交股,可在到期前先平倉", size=12, anchor="middle"))
    return doc(b, aria="到期流程圖:到期日依是否價內分岔,價內自動履約轉股票,價外權利金歸零")


def fig_wheel_cycle():
    b = []
    b.append(T(320, 24, "Wheel:CSP 與 CC 的循環", size=16, anchor="middle", weight="600"))
    rbox(b, 320, 78, 256, 40,
         [LN("① 賣 CSP(現金擔保賣權)", 14, INK, "600")])
    rbox(b, 512, 200, 176, 44,
         [LN("② 被指派:接股", 14, INK, "600"), LN("(用兩平價買進)", 11)], lh=17)
    rbox(b, 320, 322, 256, 40,
         [LN("③ 賣 CC(掩護性買權)", 14, INK, "600")])
    rbox(b, 128, 200, 176, 44,
         [LN("④ 被 call 走:交股", 14, INK, "600"), LN("(獲利了結出場)", 11)], lh=17)
    # 順時針箭頭:① → ② → ③ → ④ → ①
    qarrow(b, 452, 96, 520, 122, 516, 174)
    qarrow(b, 508, 226, 500, 280, 452, 306)
    qarrow(b, 188, 306, 140, 280, 132, 226)
    qarrow(b, 124, 174, 128, 122, 188, 98)
    b.append(T(320, 190, "Wheel", size=18, anchor="middle", weight="600"))
    b.append(T(320, 210, "循環的每一步", size=12, anchor="middle"))
    b.append(T(320, 226, "都在收權利金", size=12, anchor="middle"))
    # 未觸發時的自我循環註記
    b.append(T(320, 116, "未被指派 → 權利金落袋,重複賣 CSP", size=12, fill=GREEN, anchor="middle"))
    b.append(T(320, 288, "未被 call 走 → 權利金落袋,續賣 CC", size=12, fill=GREEN, anchor="middle"))
    b.append(T(320, 366, "Led 對 SPCX 的 CSP+CC 降成本操作,行為上近似 wheel(課程詮釋,非本人用語)",
               size=12, anchor="middle"))
    return doc(b, aria="Wheel 循環圖:賣現金擔保賣權,被指派接股後改賣掩護性買權,被履約交股後回到起點")


def fig_gozilla_cc_params():
    b = []
    b.append(T(320, 24, "Gozilla 的 covered call 參數紀律", size=16, anchor="middle", weight="600"))
    b.append(T(320, 42, "來源:Threads @godzilla.us 貼文自述(2026-05〜07)", size=12, anchor="middle"))
    X0, X1 = 150, 596

    def ruler(y, vmin, vmax, ticks, fmt):
        b.append(
            f'<line x1="{X0}" y1="{y}" x2="{X1}" y2="{y}" stroke="{INK}" stroke-width="1.2"/>'
        )
        def M(v):
            return X0 + (v - vmin) / (vmax - vmin) * (X1 - X0)
        for v in ticks:
            x = M(v)
            b.append(f'<line x1="{P(x)}" y1="{y}" x2="{P(x)}" y2="{y + 5}" stroke="{INK}" stroke-width="1.2"/>')
            b.append(T(x, y + 19, fmt(v), size=11, anchor="middle"))
        return M

    def band(M, y, v0, v1, label):
        x0, x1 = M(v0), M(v1)
        b.append(
            f'<rect x="{P(x0)}" y="{y - 10}" width="{P(x1 - x0)}" height="20"'
            f' fill="{GREEN_F}" stroke="{GREEN}" stroke-width="1.5" rx="3"/>'
        )
        b.append(T((x0 + x1) / 2, y - 17, label, size=14, fill=GREEN, anchor="middle", weight="600"))

    def limit(M, y, v, label):
        x = M(v)
        b.append(
            f'<line x1="{P(x)}" y1="{y - 22}" x2="{P(x)}" y2="{y + 8}"'
            f' stroke="{RED}" stroke-width="1.5" stroke-dasharray="{DASH}"/>'
        )
        b.append(T(x, y - 28, label, size=13, fill=RED, anchor="middle", weight="600"))

    # 列 1:delta
    y1 = 110
    b.append(T(130, y1 + 4, "Delta", size=14, anchor="end", weight="600"))
    M1 = ruler(y1, 0, 0.5, [0, 0.1, 0.2, 0.3, 0.4, 0.5], lambda v: f"{v:g}")
    band(M1, y1, 0.25, 0.30, "常用 0.25–0.3")
    limit(M1, y1, 0.4, "上限 0.4")
    # 列 2:持股水位
    y2 = 205
    b.append(T(130, y2 + 4, "持股水位", size=14, anchor="end", weight="600"))
    M2 = ruler(y2, 0, 100, [0, 25, 50, 75, 100], lambda v: f"{v:g}%")
    band(M2, y2, 50, 80, "只賣 50–80%")
    limit(M2, y2, 100, "不下滿")
    b.append(T(X0, y2 + 40, "「假如你有 1 萬股,不要賣 100 口 CC,賣 50–80 口就可以」", size=12))
    # 列 3:到期天期
    y3 = 300
    b.append(T(130, y3 + 4, "到期天期", size=14, anchor="end", weight="600"))
    M3 = ruler(y3, 0, 30, [0, 7, 14, 21, 30], lambda v: f"{v:g}天")
    band(M3, y3, 0, 7, "短天期(當週)")
    b.append(T(X0, y3 + 40, "挑每週一/三/五結算的合約;被突破時在結算日尾盤往後 roll", size=12))
    b.append(T(320, 378, "共同前提:不貪心下滿,權利金「繳稅後生活夠用就好」", size=12, anchor="middle"))
    return doc(b, aria="Gozilla 的 CC 參數帶狀圖:delta 常用 0.25 到 0.3 上限 0.4,持股只賣五到八成,選當週短天期合約")


def fig_led_csp_flow():
    b = []
    b.append(T(320, 24, "Led 的 CSP 操作流程", size=16, anchor="middle", weight="600"))
    b.append(T(320, 42, "來源:Threads @_lepetitdejeuner 貼文自述(2026-06〜08)", size=12, anchor="middle"))
    rbox(b, 320, 78, 190, 36, [LN("標的明顯回檔", 14, INK, "600")])
    arrow(b, 320, 96, 320, 126)
    rbox(b, 320, 148, 264, 38, [LN("開倉 sell put(cash-secured)", 14, INK, "600")])
    arrow(b, 250, 167, 168, 212, label="反彈", ldx=-30, ldy=-2, lcol=GREEN)
    arrow(b, 390, 167, 472, 212, label="續跌", ldx=32, ldy=-2, lcol=RED)
    rbox(b, 160, 252, 252, 72,
         [LN("權利金小賺 → 平倉", 14, GREEN, "600"),
          LN("開倉即掛平倉單,小賺就跑", 12),
          LN("→ 等下一次回檔再開倉", 12)],
         stroke=GREEN, fill=GREEN_F, lh=19)
    rbox(b, 480, 252, 252, 72,
         [LN("跌破履約價 → 被指派接股", 14, INK, "600"),
          LN("用兩平成本買進正股", 12),
          LN("→ 轉做 CC / CSP 降低持股成本", 12)],
         lh=19)
    # 天期分工帶
    b.append(
        f'<rect x="60" y="308" width="520" height="46" rx="9" fill="{GRAY_F}"'
        f' stroke="{INK}" stroke-width="1" stroke-dasharray="{DASH}"/>'
    )
    b.append(T(320, 328, "天期分工:真正想接的股票 → 短天期;搶反彈賺權利金 → 長天期", size=13,
               anchor="middle", weight="600"))
    b.append(T(320, 346, "紀律:一定 cash-secured 不做裸賣;小賺就平倉,不貪", size=12, anchor="middle"))
    b.append(T(320, 378, "例:GOOGL sell put 履約價 310/315、兩週到期,目標接 200 股", size=12, anchor="middle"))
    return doc(b, aria="Led 的 CSP 流程圖:回檔開倉賣現金擔保賣權,反彈小賺平倉,續跌被指派接股後轉做 CC 降成本")


def fig_position_pyramid():
    b = []
    b.append(T(320, 24, "倉位金字塔:選擇權是附屬,不是本體", size=16, anchor="middle", weight="600"))
    cx = 290
    # (y_top, y_bot, w_top, w_bot, fill, stroke)
    layers = [
        (64, 148, 56, 188, AMBER_F, AMBER),
        (154, 240, 198, 330, GRAY_F, INK),
        (246, 344, 340, 490, GREEN_F, GREEN),
    ]
    for yt, yb, wt, wb, fill, stroke in layers:
        b.append(
            f'<polygon points="{P(cx - wt / 2)},{yt} {P(cx + wt / 2)},{yt}'
            f' {P(cx + wb / 2)},{yb} {P(cx - wb / 2)},{yb}"'
            f' fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>'
        )
    b.append(T(cx, 112, "選擇權", size=14, fill=AMBER, anchor="middle", weight="600"))
    b.append(T(cx, 132, "CC / CSP 收租", size=12, fill=AMBER, anchor="middle"))
    b.append(T(cx, 188, "個股持股", size=15, anchor="middle", weight="600"))
    b.append(T(cx, 208, "集中(Gozilla)或衛星(Led)", size=12, anchor="middle"))
    b.append(T(cx, 226, "控制比例、看得懂才買", size=12, anchor="middle"))
    b.append(T(cx, 288, "指數底倉", size=15, fill=GREEN, anchor="middle", weight="600"))
    b.append(T(cx, 308, "0050 / VOO / QQQ / SMH", size=12, fill=GREEN, anchor="middle"))
    b.append(T(cx, 326, "持續買進、長期持有", size=12, fill=GREEN, anchor="middle"))
    # 右側註記
    b.append(T(548, 108, "小部位收租", size=12, anchor="start"))
    b.append(T(548, 198, "中部位精選", size=12, anchor="start"))
    b.append(T(548, 296, "大部位長抱", size=12, anchor="start"))
    b.append(T(320, 376, "附屬收入疊在穩固底倉上:先有底倉與持股,才有 CC / CSP 可賣", size=12,
               anchor="middle"))
    return doc(b, aria="倉位金字塔:底層指數底倉最大,中層個股持股,頂層選擇權收租部位最小")


def fig_framework_compare():
    b = []
    b.append(T(320, 24, "兩種賣方框架:集中持股+CC vs 指數底倉+CSP", size=16, anchor="middle",
               weight="600"))

    def panel(x, header, bullets):
        b.append(
            f'<rect x="{x}" y="44" width="278" height="248" rx="10" fill="none"'
            f' stroke="{INK}" stroke-width="1.5"/>'
        )
        b.append(T(x + 139, 74, header, size=15, anchor="middle", weight="600"))
        b.append(
            f'<line x1="{x + 22}" y1="88" x2="{x + 256}" y2="88" stroke="{INK}"'
            f' stroke-width="1" opacity=".5"/>'
        )
        y = 116
        for txt in bullets:
            b.append(T(x + 22, y, "・" + txt, size=13))
            y += 34

    panel(36, "Gozilla:集中持股 + CC", [
        "持股集中:NVDA / PLTR / MU",
        "賣 CC 收現金流當生活費",
        "delta 0.25–0.3,短天期",
        "只賣 50–80% 持股水位",
        "被突破 → 結算日尾盤 roll",
    ])
    panel(326, "Led:指數底倉 + CSP", [
        "底倉 0050 / VOO / QQQ 持續買",
        "回檔開倉 sell put,反彈平倉",
        "想接→短天期;搶反彈→長天期",
        "CC 撞履約價就換股,不 roll",
        "接刀表:預先寫好的加碼階梯",
    ])
    # 共同紀律帶
    b.append(
        f'<rect x="36" y="306" width="568" height="52" rx="10" fill="{GRAY_F}"'
        f' stroke="{INK}" stroke-width="1" stroke-dasharray="{DASH}"/>'
    )
    b.append(T(66, 337, "共同紀律", size=14, anchor="start", weight="600"))
    for cx, w, txt in ((230, 96, "不裸賣"), (350, 96, "不下滿"), (486, 120, "小賺平倉")):
        b.append(
            f'<rect x="{P(cx - w / 2)}" y="316" width="{w}" height="32" rx="16"'
            f' fill="{GREEN_F}" stroke="{GREEN}" stroke-width="1.5"/>'
        )
        b.append(T(cx, 337, txt, size=14, fill=GREEN, anchor="middle", weight="600"))
    b.append(T(320, 382, "依 Threads 公開貼文歸納(2026-05〜08);收入數字為本人自述,未經驗證",
               size=12, anchor="middle"))
    return doc(b, aria="兩位 KOL 框架對比:左為集中持股加 CC,右為指數底倉加 CSP,底部三條共同紀律")


# ============================================================

FIGURES = {
    "long-call.svg": fig_long_call,
    "long-put.svg": fig_long_put,
    "short-call.svg": fig_short_call,
    "short-put.svg": fig_short_put,
    "covered-call.svg": fig_covered_call,
    "cash-secured-put.svg": fig_cash_secured_put,
    "bull-put-spread.svg": fig_bull_put_spread,
    "bear-call-spread.svg": fig_bear_call_spread,
    "iron-condor.svg": fig_iron_condor,
    "collar.svg": fig_collar,
    "premium-decomposition.svg": fig_premium_decomposition,
    "theta-decay.svg": fig_theta_decay,
    "iv-crush.svg": fig_iv_crush,
    "delta-slope.svg": fig_delta_slope,
    "moneyness.svg": fig_moneyness,
    "expiry-flow.svg": fig_expiry_flow,
    "wheel-cycle.svg": fig_wheel_cycle,
    "gozilla-cc-params.svg": fig_gozilla_cc_params,
    "led-csp-flow.svg": fig_led_csp_flow,
    "position-pyramid.svg": fig_position_pyramid,
    "framework-compare.svg": fig_framework_compare,
}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in FIGURES.items():
        svg = fn()
        minidom.parseString(svg)  # 合法性檢查
        size = len(svg.encode("utf-8"))
        if size >= 20 * 1024:
            print(f"✗ {name} 超過 20KB({size} bytes)", file=sys.stderr)
            return 1
        (OUT / name).write_text(svg, encoding="utf-8")
        print(f"{name:28s} {size / 1024:5.1f} KB")
    print(f"共 {len(FIGURES)} 張 → {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
