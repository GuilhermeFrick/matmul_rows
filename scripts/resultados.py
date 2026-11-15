#!/usr/bin/env python3
"""Tabelas e gráficos da bateria de experimentos (só biblioteca padrão).

Uso: python3 resultados.py [PASTA] [-o SAIDA]

Lê PASTA/res_N<N>_W<W>/log/*.txt e gera em SAIDA (padrão PASTA/resultados):
resultados.csv, resultados.md, tempo.svg, speedup.svg e eficiencia.svg.
"""
import argparse
import csv
import re
import sys
from pathlib import Path

TICKS = re.compile(r"\$\$\$_\d+x\d+_\w+?_\d+_TICKS (.*)")
RESULT = re.compile(r"\$\$\$_\d+x\d+_\w+?_\d+_RESULT (\w+)")

# paleta categórica validada (dataviz: 3 primeiros slots passam em todos os pares)
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]
MARKERS = ["circle", "square", "triangle"]
SURFACE, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
FONT = "font-family='DejaVu Sans, Arial, sans-serif'"


def parse_run(d):
    master, workers, result = None, [], None
    for f in sorted((d / "log").glob("*.txt")):
        for line in f.read_text(errors="replace").splitlines():
            if m := TICKS.search(line):
                v = {k: int(x) for k, x in re.findall(r"(\w+)=(\d+)", m.group(1))}
                if "total" in v:
                    master = v
                else:
                    workers.append(v)
            elif m := RESULT.search(line):
                result = m.group(1)
    return master, workers, result


def collect(base):
    rows = []
    for d in base.glob("res_N*_W*"):
        m = re.fullmatch(r"res_N(\d+)_W(\d+)", d.name)
        if not m:
            continue
        n, w = map(int, m.groups())
        master, workers, result = parse_run(d)
        if master is None or len(workers) != w:
            print(f"AVISO: {d.name} incompleto (master={master is not None}, workers={len(workers)}/{w})")
            continue
        col = lambda k: [x[k] for x in workers]
        rows.append(dict(N=n, W=w, total=master["total"], master_send=master["send"],
                         master_recv=master["recv"], result=result or "?",
                         comp_min=min(col("comp")), comp_max=max(col("comp")),
                         wsend_min=min(col("send")), wsend_max=max(col("send")),
                         wrecv_min=min(col("recv")), wrecv_max=max(col("recv"))))
    rows.sort(key=lambda r: (r["N"], r["W"]))
    for r in rows:
        base1 = next((x["total"] for x in rows if x["N"] == r["N"] and x["W"] == 1), None)
        r["speedup"] = base1 / r["total"] if base1 else None
        r["eficiencia"] = r["speedup"] / r["W"] if base1 else None
    return rows


def fmt_int(x):
    return f"{x:,}".replace(",", " ")


def fmt_rng(a, b):
    return fmt_int(a) if a == b else f"{fmt_int(a)} a {fmt_int(b)}"


def fmt_dec(x, nd=2):
    return "-" if x is None else f"{x:.{nd}f}".replace(".", ",")


def write_md(rows, path):
    out = ["# Resultados\n", "Ticks de `memphis_get_tick()` (1 tick = 1 ciclo). Base do speedup: W = 1.\n"]
    for n in sorted({r["N"] for r in rows}):
        out += [f"\n## N = {n}\n",
                "| W | Total master | Speedup | Eficiência | Envio master | Recv master | Comp por worker | Send por worker | Recv por worker | Resultado |",
                "|---|---|---|---|---|---|---|---|---|---|"]
        for r in (r for r in rows if r["N"] == n):
            ef = "-" if r["eficiencia"] is None else f"{100 * r['eficiencia']:.0f}%"
            out.append(f"| {r['W']} | {fmt_int(r['total'])} | {fmt_dec(r['speedup'])} | {ef} | "
                       f"{fmt_int(r['master_send'])} | {fmt_int(r['master_recv'])} | "
                       f"{fmt_rng(r['comp_min'], r['comp_max'])} | {fmt_rng(r['wsend_min'], r['wsend_max'])} | "
                       f"{fmt_rng(r['wrecv_min'], r['wrecv_max'])} | {r['result']} |")
    path.write_text("\n".join(out) + "\n")


# ---------- SVG ----------

def svg_doc(w, h, body, title):
    return (f"<svg xmlns='http://www.w3.org/2000/svg' width='{w}' height='{h}' viewBox='0 0 {w} {h}' {FONT}>\n"
            f"<title>{title}</title>\n<rect width='{w}' height='{h}' fill='{SURFACE}'/>\n{body}</svg>\n")


def text(x, y, s, size=16, fill=INK2, anchor="middle", weight="normal", extra=""):
    return (f"<text x='{x:.1f}' y='{y:.1f}' font-size='{size}' fill='{fill}' text-anchor='{anchor}' "
            f"font-weight='{weight}' {extra}>{s}</text>\n")


def marker(kind, x, y, color, tip):
    t = f"<title>{tip}</title>"
    ring = f"stroke='{SURFACE}' stroke-width='2'"
    if kind == "circle":
        return f"<circle cx='{x:.1f}' cy='{y:.1f}' r='6' fill='{color}' {ring}>{t}</circle>\n"
    if kind == "square":
        return f"<rect x='{x - 6:.1f}' y='{y - 6:.1f}' width='12' height='12' rx='2' fill='{color}' {ring}>{t}</rect>\n"
    return (f"<polygon points='{x:.1f},{y - 7:.1f} {x + 7:.1f},{y + 5:.1f} {x - 7:.1f},{y + 5:.1f}' "
            f"fill='{color}' {ring}>{t}</polygon>\n")


def nice_max(v):
    for e in range(-2, 12):
        for m in (1, 2, 2.5, 5):
            if m * 10 ** e >= v:
                return m * 10 ** e
    return v


def line_chart(rows, key, ylabel, title, ymax, yfmt, ideal=False):
    W, H, L, R, T, B = 760, 480, 80, 150, 70, 70
    ns = sorted({r["N"] for r in rows})
    ws = sorted({r["W"] for r in rows})
    px = lambda w: L + ws.index(w) * (W - L - R) / max(1, len(ws) - 1)
    py = lambda v: H - B - v / ymax * (H - T - B)
    body = text(L, 34, title, size=20, fill=INK, anchor="start", weight="bold")
    for i in range(6):
        v = ymax * i / 5
        body += f"<line x1='{L}' x2='{W - R}' y1='{py(v):.1f}' y2='{py(v):.1f}' stroke='{GRID if i else AXIS}'/>\n"
        body += text(L - 10, py(v) + 5, yfmt(v), size=14, fill=MUTED, anchor="end")
    for w in ws:
        body += text(px(w), H - B + 24, w, size=14, fill=MUTED)
    body += text((L + W - R) / 2, H - 18, "Workers (W)", size=15)
    body += text(22, (T + H - B) / 2, ylabel, size=15, extra=f"transform='rotate(-90 22 {(T + H - B) / 2})'")
    if ideal:
        body += f"<clipPath id='plot'><rect x='{L}' y='{T}' width='{W - L - R}' height='{H - T - B}'/></clipPath>\n"
        pts = " ".join(f"{px(w):.1f},{py(w):.1f}" for w in ws)
        body += f"<polyline points='{pts}' fill='none' stroke='{MUTED}' stroke-width='2' stroke-dasharray='6 5' clip-path='url(#plot)'/>\n"
        wl = max(w for w in ws if w <= ymax)
        body += text(px(wl) + 8, py(wl) + 18, "ideal (= W)", size=14, fill=MUTED, anchor="start")
    ends = []
    for i, n in enumerate(ns):
        pts = [(r["W"], r[key]) for r in rows if r["N"] == n and r[key] is not None]
        if not pts:
            continue
        c = SERIES[i % len(SERIES)]
        body += (f"<polyline points='{' '.join(f'{px(w):.1f},{py(v):.1f}' for w, v in pts)}' fill='none' "
                 f"stroke='{c}' stroke-width='2' stroke-linejoin='round'/>\n")
        for w, v in pts:
            body += marker(MARKERS[i % 3], px(w), py(v), c, f"N = {n}, W = {w}: {yfmt(v)}")
        ends.append([py(pts[-1][1]), n, i])
    ends.sort()
    for j in range(1, len(ends)):  # afasta rótulos de fim de linha que colidem
        ends[j][0] = max(ends[j][0], ends[j - 1][0] + 20)
    for y, n, i in ends:
        body += marker(MARKERS[i % 3], W - R + 22, y - 5, SERIES[i % len(SERIES)], f"N = {n}")
        body += text(W - R + 34, y, f"N = {n}", size=15, fill=INK, anchor="start")
    return svg_doc(W, H, body, title)


def time_chart(rows):
    ns = sorted({r["N"] for r in rows})
    ws = sorted({r["W"] for r in rows})
    PW, PH, L, T, B, GAP = 300, 380, 70, 110, 60, 30
    W = L + len(ns) * PW + (len(ns) - 1) * GAP + 20
    H = T + PH + B
    title = "Tempo do master: envio × espera pelos resultados"
    body = text(L, 34, title, size=20, fill=INK, anchor="start", weight="bold")
    parts = [("master_send", "Envio de A e B (master)", SERIES[0]),
             ("master_recv", "Espera pelos resultados (computação)", SERIES[1])]
    lx = L
    for _, lab, c in parts:
        body += f"<rect x='{lx}' y='54' width='14' height='14' rx='2' fill='{c}'/>\n"
        body += text(lx + 20, 66, lab, size=15, fill=INK2, anchor="start")
        lx += 30 + 8.6 * len(lab)
    for k, n in enumerate(ns):
        x0 = L + k * (PW + GAP)
        rs = {r["W"]: r for r in rows if r["N"] == n}
        ymax = nice_max(max(r["total"] for r in rs.values()) / 1e6)
        py = lambda v: T + PH - v / ymax * PH
        body += text(x0 + PW / 2, T - 12, f"N = {n}", size=17, fill=INK, weight="bold")
        for i in range(6):
            v = ymax * i / 5
            body += f"<line x1='{x0}' x2='{x0 + PW}' y1='{py(v):.1f}' y2='{py(v):.1f}' stroke='{GRID if i else AXIS}'/>\n"
            body += text(x0 - 8, py(v) + 5, f"{v:g}".replace(".", ","), size=13, fill=MUTED, anchor="end")
        bw = PW / len(ws) * 0.6
        for j, w in enumerate(ws):
            cx = x0 + (j + 0.5) * PW / len(ws)
            body += text(cx, T + PH + 22, w, size=14, fill=MUTED)
            if w not in rs:
                continue
            r, base = rs[w], 0.0
            for idx, (key, lab, c) in enumerate(parts):
                v = r[key] / 1e6
                y1, y0 = py(base + v), py(base)
                h = max(0.0, y0 - y1 - (2 if idx == 0 else 0))  # 2px de superfície entre os segmentos
                tip = f"N = {n}, W = {w}: {lab} {fmt_int(r[key])} ciclos"
                if idx == len(parts) - 1:  # topo arredondado
                    body += (f"<path d='M{cx - bw / 2:.1f},{y0:.1f} V{y1 + 4:.1f} q0,-4 4,-4 H{cx + bw / 2 - 4:.1f} "
                             f"q4,0 4,4 V{y0:.1f} Z' fill='{c}'><title>{tip}</title></path>\n")
                else:
                    body += (f"<rect x='{cx - bw / 2:.1f}' y='{y0 - h:.1f}' width='{bw:.1f}' height='{h:.1f}' "
                             f"fill='{c}'><title>{tip}</title></rect>\n")
                base += v
            body += text(cx, py(base) - 6, fmt_dec(r["total"] / 1e6, 2 if ymax <= 1 else 1), size=12, fill=INK2)
    body += text(L + (W - L) / 2, H - 14, "Workers (W)", size=15)
    body += text(22, T + PH / 2, "Milhões de ciclos", size=15, extra=f"transform='rotate(-90 22 {T + PH / 2})'")
    return svg_doc(W, H, body, title)


def main():
    ap = argparse.ArgumentParser(description="tabelas e gráficos da bateria")
    ap.add_argument("pasta", nargs="?", default=".", help="pasta com res_N*_W* (padrão: atual)")
    ap.add_argument("-o", "--saida", help="pasta de saída (padrão: PASTA/resultados)")
    args = ap.parse_args()
    base = Path(args.pasta)
    out = Path(args.saida) if args.saida else base / "resultados"
    rows = collect(base)
    if not rows:
        sys.exit(f"ERRO: nenhum res_N*_W* completo em {base}")
    out.mkdir(parents=True, exist_ok=True)

    with open(out / "resultados.csv", "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)
    write_md(rows, out / "resultados.md")
    (out / "tempo.svg").write_text(time_chart(rows))
    smax = max(r["speedup"] or 0 for r in rows)
    (out / "speedup.svg").write_text(line_chart(
        rows, "speedup", "Speedup (T1 / TW)", "Speedup em relação a W = 1",
        nice_max(smax * 1.15), lambda v: f"{v:.1f}".replace(".", ","), ideal=True))
    (out / "eficiencia.svg").write_text(line_chart(
        rows, "eficiencia", "Eficiência (speedup / W)", "Eficiência", 1.0, lambda v: f"{100 * v:.0f}%"))

    bad = [f"N={r['N']} W={r['W']}" for r in rows if r["result"] != "OK"]
    print(f"{len(rows)} rodadas lidas -> {out}")
    if bad:
        print("AVISO: resultado diferente de OK em " + ", ".join(bad))


if __name__ == "__main__":
    main()
