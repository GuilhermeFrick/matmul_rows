#!/usr/bin/env python3
"""Gera um relatório legível de uma simulação do Memphis-V.

Uso:
    python3 scripts/analyze.py <pasta_do_cenario> [--app N] [-o SAIDA]

<pasta_do_cenario> é o testcase/<scenario> da simulação (ou uma cópia dele).
Gera em <pasta_do_cenario>/relatorio/ (ou SAIDA):
    relatorio.md    tabelas + gráficos
    timeline.svg    o que cada PE executou ao longo do tempo
    ocupacao.svg    % do tempo de cada PE por estado
    resumo.json     números para comparar rodadas

Só usa a biblioteca padrão do Python.

Arquivos lidos:
    log/log*.txt                 printf das tarefas e eventos do mapper (log0x0)
    debug/platform.cfg           nomes das tarefas e tamanho da malha
    debug/cpu.cfg                códigos de estado (Idle, Scheduler, Interruption)
    debug/scheduling_report.txt  "PE estado tick" a cada troca de contexto
    debug/traffic_router.txt     pacotes por roteador (Phivers/sim/TrafficRouter.sv)
"""
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

CLOCK_HZ = 100e6  # clock_period_ns 10 (platform.cfg)
PORTS = {0: "E", 2: "W", 4: "N", 6: "S", 8: "L"}  # HermesPkg: E,W,N,S,LOCAL (*2)
SVC = {0x40: "DATA_AV", 0x41: "REQUEST", 0x43: "DELIVERY"}

# Cores (paleta de referência validada: 3 primeiros slots passam all-pairs)
SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT2 = "#52514e"
GRID = "#e4e3df"
TRACK = "#efeeeb"
C_MASTER = "#2a78d6"
C_WORKER = "#eb6834"
C_MGMT = "#1baf7a"
C_KERNEL = "#a3a29b"


# --------------------------------------------------------------------------- #
# Leitura
# --------------------------------------------------------------------------- #
def num(v):
    return f"{v:,}".replace(",", ".")


def pe_name(addr):
    return f"{addr >> 8}x{addr & 0xFF}"


def read_cfg(*paths):
    names, states, plat = {}, {}, {}
    section = None
    for path in paths:
        for line in path.read_text().split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith("BEGIN_"):
                section = line[6:]
                continue
            if line.startswith("END_"):
                section = None
                continue
            parts = line.split()
            if section == "task_name_relation":
                names[int(parts[1])] = parts[0]
            elif section is None and len(parts) == 2:
                if path.name == "cpu.cfg":
                    states[int(parts[1])] = parts[0]
                else:
                    plat[parts[0]] = parts[1]
    return names, states, plat


def read_logs(logdir, app):
    start = end = None
    term, status, prints = {}, {}, defaultdict(list)
    for f in sorted(logdir.glob("log*.txt")):
        for line in f.read_text(errors="replace").split("\n"):
            if m := re.search(rf"App {app} started at (\d+)", line):
                start = int(m.group(1))
            elif m := re.search(rf"App {app} terminated at time (\d+)", line):
                end = int(m.group(1))
            elif m := re.search(r"task terminated from id (\d+) at time (\d+)", line):
                term[int(m.group(1))] = int(m.group(2))
            if m := re.match(r"Task id (\d+) terminated with status (-?\d+)", line):
                status[int(m.group(1))] = int(m.group(2))
            if m := re.match(r"\$\$\$_\d+x\d+_(\d+)_(\d+)_(.*)", line):
                if int(m.group(1)) == app:
                    prints[(app << 8) | int(m.group(2))].append(m.group(3))
    return start, end, term, status, prints


def read_sched(path):
    per_pe = defaultdict(list)
    for line in path.read_text().split("\n"):
        p = line.split()
        if len(p) == 3:
            per_pe[int(p[0])].append((int(p[2]), int(p[1])))
    for v in per_pe.values():
        v.sort()
    return per_pe


def segments(events, t0, t1):
    """Lista (início, fim, estado) recortada em [t0, t1)."""
    out = []
    for i, (t, st) in enumerate(events):
        nxt = events[i + 1][0] if i + 1 < len(events) else t1
        a, b = max(t, t0), min(nxt, t1)
        if b > a:
            out.append((a, b, st))
    return out


def read_traffic(path):
    rows = []
    for line in path.read_text().split("\n"):
        p = line.split("\t")
        if len(p) < 7:
            continue
        t, addr, svc, flits, bw, port, target = p[:7]
        port = int(port)
        if port % 2:  # BrLite (broadcast de controle), fora da análise
            continue
        r = dict(t=int(t), addr=int(addr), svc=int(svc, 16), flits=int(flits),
                 bw=int(bw), port=port, target=int(target))
        if r["svc"] in SVC and len(p) >= 9:
            r["prod"], r["cons"] = int(p[7]), int(p[8])
        rows.append(r)
    return rows


# --------------------------------------------------------------------------- #
# SVG
# --------------------------------------------------------------------------- #
def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def nice_step(span, target=8):
    raw = span / target
    mag = 10 ** (len(str(int(raw))) - 1) if raw >= 1 else 1
    for m in (1, 2, 5, 10):
        if raw <= m * mag:
            return m * mag
    return 10 * mag


def fmt_k(v):
    return f"{v / 1000:g}k" if v else "0"


def legend(items, x, y):
    out, cx = [], x
    for label, color in items:
        if color is None:
            out.append(f'<rect x="{cx}" y="{y - 9}" width="12" height="12" rx="2" fill="{TRACK}" stroke="{GRID}"/>')
        else:
            out.append(f'<rect x="{cx}" y="{y - 9}" width="12" height="12" rx="2" fill="{color}"/>')
        out.append(f'<text x="{cx + 17}" y="{y + 1}" font-size="12" fill="{TEXT2}">{esc(label)}</text>')
        cx += 30 + 7 * len(label)
    return out


def svg_doc(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" font-family="Helvetica, Arial, sans-serif">\n'
            f'<rect width="{w}" height="{h}" fill="{SURFACE}"/>\n' + "\n".join(body) + "\n</svg>\n")


def timeline_svg(rows, t0, t1, title, kind):
    """rows: [(rotulo, [(a, b, estado)])]; kind(estado) -> ('master'|'worker'|'mgmt'|'kernel'|'idle', nome)."""
    W, L, R, T, RH, BH = 1000, 190, 24, 74, 30, 18
    H = T + RH * len(rows) + 46
    pw = W - L - R
    x = lambda t: L + (t - t0) / (t1 - t0) * pw
    color = {"master": C_MASTER, "worker": C_WORKER, "mgmt": C_MGMT, "kernel": C_KERNEL}
    b = [f'<text x="{L}" y="24" font-size="15" font-weight="600" fill="{TEXT}">{esc(title)}</text>']
    b += legend([("mestre", C_MASTER), ("worker", C_WORKER), ("gerência", C_MGMT),
                 ("kernel", C_KERNEL), ("ocioso", None)], L, 50)
    step = nice_step(t1 - t0)
    tick = 0
    while tick <= t1 - t0:
        xx = x(t0 + tick)
        b.append(f'<line x1="{xx:.1f}" y1="{T - 6}" x2="{xx:.1f}" y2="{T + RH * len(rows)}" stroke="{GRID}"/>')
        b.append(f'<text x="{xx:.1f}" y="{T + RH * len(rows) + 16}" font-size="11" fill="{TEXT2}" text-anchor="middle">{fmt_k(tick)}</text>')
        tick += step
    b.append(f'<text x="{L + pw / 2}" y="{H - 8}" font-size="12" fill="{TEXT2}" text-anchor="middle">'
             f'ciclos desde o início da aplicação (100k ciclos = 1 ms)</text>')
    for i, (label, segs) in enumerate(rows):
        y = T + i * RH + (RH - BH) / 2
        b.append(f'<text x="{L - 10}" y="{y + BH / 2 + 4}" font-size="12" fill="{TEXT}" text-anchor="end">{esc(label)}</text>')
        b.append(f'<rect x="{L}" y="{y}" width="{pw}" height="{BH}" rx="4" fill="{TRACK}"/>')
        for a, e, st in segs:
            k, name = kind(st)
            if k == "idle":
                continue
            w = max(x(e) - x(a), 0.6)
            b.append(f'<rect x="{x(a):.2f}" y="{y}" width="{w:.2f}" height="{BH}" fill="{color[k]}">'
                     f'<title>{esc(name)}: {a - t0}–{e - t0} ({e - a} ciclos)</title></rect>')
        # rótulo direto no maior trecho de cada tarefa (se couber)
        best = {}
        for a, e, st in segs:
            k, name = kind(st)
            if k in ("master", "worker", "mgmt") and (name not in best or e - a > best[name][1] - best[name][0]):
                best[name] = (a, e)
        for name, (a, e) in best.items():
            if x(e) - x(a) > 7 * len(name) + 8:
                b.append(f'<text x="{(x(a) + x(e)) / 2:.1f}" y="{y + BH / 2 + 4}" font-size="11" '
                         f'fill="#ffffff" text-anchor="middle">{esc(name)}</text>')
    return svg_doc(W, H, b)


def occupancy_svg(rows, title):
    """rows: [(rotulo, {'mestre':%, 'worker':%, 'gerência':%, 'kernel':%, 'ocioso':%})]"""
    W, L, R, T, RH, BH = 1000, 190, 70, 74, 30, 18
    H = T + RH * len(rows) + 40
    pw = W - L - R
    order = [("mestre", C_MASTER), ("worker", C_WORKER), ("gerência", C_MGMT), ("kernel", C_KERNEL)]
    b = [f'<text x="{L}" y="24" font-size="15" font-weight="600" fill="{TEXT}">{esc(title)}</text>']
    b += legend(order + [("ocioso", None)], L, 50)
    for pct in (0, 25, 50, 75, 100):
        xx = L + pct / 100 * pw
        b.append(f'<line x1="{xx:.1f}" y1="{T - 6}" x2="{xx:.1f}" y2="{T + RH * len(rows)}" stroke="{GRID}"/>')
        b.append(f'<text x="{xx:.1f}" y="{T + RH * len(rows) + 16}" font-size="11" fill="{TEXT2}" text-anchor="middle">{pct}%</text>')
    for i, (label, parts) in enumerate(rows):
        y = T + i * RH + (RH - BH) / 2
        b.append(f'<text x="{L - 10}" y="{y + BH / 2 + 4}" font-size="12" fill="{TEXT}" text-anchor="end">{esc(label)}</text>')
        b.append(f'<rect x="{L}" y="{y}" width="{pw}" height="{BH}" rx="4" fill="{TRACK}"/>')
        cx = L
        for key, col in order:
            w = parts.get(key, 0) / 100 * pw
            if w <= 0:
                continue
            b.append(f'<rect x="{cx:.2f}" y="{y}" width="{max(w - 2, 0.6):.2f}" height="{BH}" fill="{col}">'
                     f'<title>{key}: {parts[key]:.1f}%</title></rect>')
            cx += w
        busy = 100 - parts.get("ocioso", 0)
        b.append(f'<text x="{W - R + 8}" y="{y + BH / 2 + 4}" font-size="12" fill="{TEXT2}">{busy:.0f}% ativo</text>')
    return svg_doc(W, H, b)


# --------------------------------------------------------------------------- #
# Análise
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scenario")
    ap.add_argument("--app", type=int, default=1, help="id da aplicação (padrão 1)")
    ap.add_argument("-o", "--out", help="pasta de saída (padrão <scenario>/relatorio)")
    a = ap.parse_args()
    d = Path(a.scenario)
    out = Path(a.out) if a.out else d / "relatorio"
    out.mkdir(parents=True, exist_ok=True)

    names, states, plat = read_cfg(d / "debug/platform.cfg", d / "debug/cpu.cfg")
    clock_hz = 1e9 / float(plat.get("clock_period_ns", 10))
    t0, t1, term, status, prints = read_logs(d / "log", a.app)
    if t0 is None or t1 is None:
        raise SystemExit("Início/fim da aplicação não encontrado nos logs (log/log0x0.txt)")
    win = t1 - t0
    ms = lambda c: c / clock_hz * 1e3

    lo, hi = a.app << 8, (a.app + 1) << 8
    is_app = lambda tid: isinstance(tid, int) and lo <= tid < hi
    tname = lambda tid: names.get(tid, str(tid))
    state_name = {v: k for k, v in states.items()}
    KERNEL = {state_name.get("Interruption"), state_name.get("Scheduler")}
    IDLE = state_name.get("Idle")

    def kind(st):
        if st == IDLE:
            return "idle", "ocioso"
        if st in KERNEL:
            return "kernel", states.get(st, "kernel")
        n = tname(st)
        if is_app(st):
            return ("master" if n == "master" else "worker"), n
        return "mgmt", n

    # ---- escalonamento
    sched = read_sched(d / "debug/scheduling_report.txt")
    task_pe, cpu, first_run = {}, defaultdict(int), {}
    pe_rows_tl, pe_rows_occ, pe_tab = [], [], []
    for addr in sorted(sched):
        segs = segments(sched[addr], t0, t1)
        acc = defaultdict(int)
        for s, e, st in segs:
            k, n = kind(st)
            key = {"master": "mestre", "worker": "worker", "mgmt": "gerência",
                   "kernel": "kernel", "idle": "ocioso"}[k]
            acc[key] += e - s
            if is_app(st):
                task_pe[st] = pe_name(addr)
                cpu[st] += e - s
                first_run.setdefault(st, s)
        covered = sum(acc.values())
        acc["ocioso"] += win - covered  # antes do 1º evento do PE na janela
        pct = {k: 100 * v / win for k, v in acc.items()}
        tasks_here = sorted({tname(st) for _, _, st in segs if kind(st)[0] in ("master", "worker", "mgmt")})
        label = f"PE {pe_name(addr)}" + (f"  ({', '.join(tasks_here)})" if tasks_here else "")
        if len(label) > 26:
            label = label[:25] + "…)"
        if tasks_here or pct.get("ocioso", 100) < 99.5:
            pe_rows_tl.append((label, segs))
        pe_rows_occ.append((label, pct))
        pe_tab.append((pe_name(addr), pct, tasks_here))

    app_tasks = sorted(set(task_pe) | {t for t in names if is_app(t)})
    shared = defaultdict(list)
    for tid, p in task_pe.items():
        shared[p].append(tname(tid))
    shared = {p: sorted(ts) for p, ts in shared.items() if len(ts) > 1}

    # ---- tráfego
    traffic = read_traffic(d / "debug/traffic_router.txt")
    app_pes = set(task_pe.values())
    on_pe = defaultdict(list)
    for tid, p in task_pe.items():
        on_pe[p].append(tname(tid))
    who = lambda p: f"{p} ({', '.join(sorted(on_pe[p]))})" if on_pe[p] else p
    # pacote contado uma vez: entrada pela porta LOCAL do roteador de origem.
    # Campos produtor/consumidor só valem em DELIVERY (em pacotes de 2 flits o
    # monitor repete os do pacote anterior); origem/destino vêm do roteador.
    pkts = sorted((r for r in traffic if r["port"] == 8 and r["svc"] in SVC
                   and pe_name(r["addr"]) in app_pes and pe_name(r["target"]) in app_pes
                   and t0 <= r["t"] <= t1), key=lambda r: r["t"])
    pairs = defaultdict(lambda: [0, 0, 0])
    for r in pkts:
        if r["svc"] == 0x43 and is_app(r.get("prod")) and is_app(r.get("cons")):
            k = (tname(r["prod"]), tname(r["cons"]))
            pairs[k][0] += 1
            pairs[k][1] += r["flits"]
            pairs[k][2] += r["bw"]
    link = defaultdict(int)
    for r in traffic:
        if t0 <= r["t"] < t1:
            link[(r["addr"], r["port"])] += r["flits"]
    top_links = sorted(link.items(), key=lambda kv: -kv[1])[:6]

    # ---- gráficos
    mesh = f"{plat.get('mpsoc_x', '?')}x{plat.get('mpsoc_y', '?')}"
    (out / "timeline.svg").write_text(timeline_svg(
        pe_rows_tl, t0, t1, f"O que cada PE executou durante a aplicação (malha {mesh})", kind))
    (out / "ocupacao.svg").write_text(occupancy_svg(
        pe_rows_occ, "Ocupação de cada PE durante a aplicação"))

    # ---- números para comparar rodadas
    workers = [t for t in app_tasks if tname(t) != "master"]
    last_worker = max((term[t] for t in workers if t in term), default=None)
    master = next((t for t in app_tasks if tname(t) == "master"), None)
    resumo = {
        "cenario": str(d),
        "app": a.app,
        "malha": mesh,
        "inicio": t0, "fim": t1, "duracao_ciclos": win, "duracao_ms": round(ms(win), 4),
        "tarefas": {tname(t): {"pe": task_pe.get(t), "cpu_ciclos": cpu.get(t, 0),
                               "inicio": (first_run[t] - t0) if t in first_run else None,
                               "fim": (term[t] - t0) if t in term else None,
                               "status": status.get(t)} for t in app_tasks},
        "pes_compartilhados": shared,
        "mestre_apos_ultimo_worker": (term[master] - last_worker) if master in term and last_worker else None,
        "entregas": {f"{s}->{c}": {"pacotes": n, "flits": fl, "ciclos_noc": bw}
                     for (s, c), (n, fl, bw) in sorted(pairs.items())},
        "ocupacao_pct": {p: {k: round(v, 2) for k, v in pct.items()} for p, pct, _ in pe_tab},
    }
    (out / "resumo.json").write_text(json.dumps(resumo, indent=2, ensure_ascii=False))

    # ---- relatório
    md = []
    md.append(f"# Relatório da simulação — `{d.name}`\n")
    md.append(f"Malha {mesh} · aplicação {a.app} · clock {clock_hz / 1e6:g} MHz\n")
    md.append("## Resumo\n")
    md.append(f"- **Duração da aplicação:** {num(win)} ciclos ({ms(win):.3f} ms)")
    if last_worker and master in term:
        md.append(f"- **Último worker terminou em** +{num(last_worker - t0)} ciclos; o mestre terminou "
                  f"{num(term[master] - last_worker)} ciclos depois")
    if master in cpu:
        md.append(f"- **CPU do mestre:** {num(cpu[master])} ciclos ({100 * cpu[master] / win:.0f}% da duração)")
    wk_cpu = [cpu[t] for t in workers if t in cpu]
    if wk_cpu:
        md.append(f"- **CPU dos workers:** mín {num(min(wk_cpu))} · máx {num(max(wk_cpu))} ciclos")
    st_txt = [f"{tname(t)}={status[t]}" for t in app_tasks if t in status]
    no_st = [tname(t) for t in app_tasks if t not in status]
    md.append("- **Status de saída no log:** " + (", ".join(st_txt) or "nenhum")
              + (f" (sem registro: {', '.join(no_st)})" if no_st else ""))
    md.append(f"- **Tarefas encerradas (mapper):** {sum(t in term for t in app_tasks)}/{len(app_tasks)}")
    for p, ts in shared.items():
        md.append(f"- ⚠️ **PE {p} compartilhado** por {', '.join(ts)}: as tarefas disputam a mesma CPU")
    if top_links:
        (addr, port), fl = top_links[0]
        md.append(f"- **Link mais usado:** roteador {pe_name(addr)} porta {PORTS[port]}, "
                  f"{fl} flits em {num(win)} ciclos ({100 * fl / win:.2f}% de ocupação)")
    md.append("")

    md.append("## Linha do tempo por PE\n")
    md.append("![timeline](timeline.svg)\n")
    md.append("## Tarefas\n")
    md.append("| Tarefa | PE | Começa a rodar | Termina | CPU (ciclos) | % da duração | Status |")
    md.append("|---|---|---:|---:|---:|---:|---:|")
    for t in app_tasks:
        r = resumo["tarefas"][tname(t)]
        md.append(f"| {tname(t)} | {r['pe'] or '-'} | {'+' + str(r['inicio']) if r['inicio'] is not None else '-'} | "
                  f"{'+' + str(r['fim']) if r['fim'] is not None else '-'} | {r['cpu_ciclos']} | "
                  f"{100 * r['cpu_ciclos'] / win:.1f}% | {r['status'] if r['status'] is not None else '-'} |")
    md.append("\nTempos em ciclos desde o início da aplicação.\n")

    md.append("## Ocupação dos PEs\n")
    md.append("![ocupacao](ocupacao.svg)\n")
    md.append("| PE | Tarefas | Mestre | Worker | Gerência | Kernel | Ocioso |")
    md.append("|---|---|---:|---:|---:|---:|---:|")
    for p, pct, ts in pe_tab:
        f = lambda k: f"{pct.get(k, 0):.1f}%"
        md.append(f"| {p} | {', '.join(ts) or '-'} | {f('mestre')} | {f('worker')} | {f('gerência')} | {f('kernel')} | {f('ocioso')} |")
    md.append("\nKernel = interrupções + escalonador. Gerência = tarefas de gerenciamento (ex.: `mapper_task`).\n")

    md.append("## Comunicação\n")
    md.append("### Dados entregues pela NoC (por par de tarefas)\n")
    if pairs:
        md.append("| De | Para | Pacotes | Flits | Payload aprox. | Ciclos na NoC |")
        md.append("|---|---|---:|---:|---:|---:|")
        for (s, c), (n, fl, bw) in sorted(pairs.items()):
            md.append(f"| {s} | {c} | {n} | {fl} | ~{(fl - 4 * n) * 4} B | {bw} |")
        md.append("\nPayload ≈ (flits − 4 de cabeçalho) × 4 bytes. Tarefas no mesmo PE trocam "
                  "mensagens sem passar pela NoC e não aparecem aqui.\n")
    else:
        md.append("Nenhuma entrega entre tarefas da aplicação passou pela NoC.\n")

    md.append("### Sequência de pacotes\n")
    md.append("REQUEST = consumidor pede dados · DELIVERY = dados · DATA_AV = produtor avisa que tem dados\n")
    md.append("| Tick | Pacote | Origem | Destino | Flits | Ciclos na NoC |")
    md.append("|---:|---|---|---|---:|---:|")
    for r in pkts:
        md.append(f"| +{r['t'] - t0} | {SVC[r['svc']]} | {who(pe_name(r['addr']))} | "
                  f"{who(pe_name(r['target']))} | {r['flits']} | {r['bw']} |")
    md.append("")

    md.append("### Links mais usados\n")
    md.append("| Roteador | Porta de entrada | Flits | Ocupação |")
    md.append("|---|---|---:|---:|")
    for (addr, port), fl in top_links:
        md.append(f"| {pe_name(addr)} | {PORTS[port]} | {fl} | {100 * fl / win:.2f}% |")
    md.append("\nPortas: E/W/N/S = vizinhos, L = o próprio PE.\n")

    md.append("## Saída das tarefas (printf)\n")
    for t in app_tasks:
        lines = prints.get(t, [])
        if not lines:
            continue
        md.append(f"**{tname(t)}**\n")
        md.append("```")
        md.extend(lines[:60])
        if len(lines) > 60:
            md.append(f"... (+{len(lines) - 60} linhas)")
        md.append("```\n")

    (out / "relatorio.md").write_text("\n".join(md))

    # ---- terminal
    print(f"Duração da app: {win} ciclos ({ms(win):.3f} ms)")
    for t in app_tasks:
        r = resumo["tarefas"][tname(t)]
        print(f"  {tname(t):10s} PE {r['pe'] or '-':4s} CPU {r['cpu_ciclos']:8d}  fim +{r['fim']}")
    for p, ts in shared.items():
        print(f"  ATENÇÃO: PE {p} compartilhado por {', '.join(ts)}")
    print(f"Relatório: {out / 'relatorio.md'}")


if __name__ == "__main__":
    main()
