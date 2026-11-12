#!/usr/bin/env python3
"""Resumo de tempos de uma simulação do Memphis-V.

Uso: python3 analyze.py <testcase/scenario> [--app N] [-o resumo.json]

Imprime duração da aplicação e, por tarefa: PE, início, fim e tempo de CPU.
Grava resumo.json na pasta do cenário (para comparar rodadas).
Escalonamento, tráfego e mapeamento: usar o debugger (mint debug).
"""
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path


def pe_name(addr):
    return f"{addr >> 8}x{addr & 0xFF}"


def read_cfg(path):
    """Seções BEGIN_/END_ viram dicionários nome->id; linhas soltas 'nome valor'."""
    rel, flat, section = {}, {}, None
    for line in path.read_text().split("\n"):
        p = line.split()
        if not p:
            continue
        if p[0].startswith("BEGIN_"):
            section = p[0][6:]
            rel[section] = {}
        elif p[0].startswith("END_"):
            section = None
        elif len(p) == 2:
            (rel[section] if section else flat)[p[0]] = p[1]
    return rel, flat


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scenario")
    ap.add_argument("--app", type=int, default=1)
    ap.add_argument("-o", "--out")
    a = ap.parse_args()
    d = Path(a.scenario)

    rel, plat = read_cfg(d / "debug/platform.cfg")
    _, cpu_states = read_cfg(d / "debug/cpu.cfg")
    names = {int(v): k for k, v in rel.get("task_name_relation", {}).items()}
    clock_hz = 1e9 / float(plat.get("clock_period_ns", 10))
    kernel_idle = {int(v) for v in cpu_states.values()}

    # início/fim da app e término das tarefas (log do mapper)
    t0 = t1 = None
    term, status = {}, {}
    for f in sorted((d / "log").glob("log*.txt")):
        for line in f.read_text(errors="replace").split("\n"):
            if m := re.search(rf"App {a.app} started at (\d+)", line):
                t0 = int(m.group(1))
            elif m := re.search(rf"App {a.app} terminated at time (\d+)", line):
                t1 = int(m.group(1))
            elif m := re.search(r"task terminated from id (\d+) at time (\d+)", line):
                term[int(m.group(1))] = int(m.group(2))
            elif m := re.match(r"Task id (\d+) terminated with status (-?\d+)", line):
                status[int(m.group(1))] = int(m.group(2))
    if t0 is None or t1 is None:
        raise SystemExit("Início/fim da aplicação não encontrado em log/")
    win = t1 - t0

    # tempo de CPU por tarefa: "PE estado tick" a cada troca de contexto
    events = defaultdict(list)
    for line in (d / "debug/scheduling_report.txt").read_text().split("\n"):
        p = line.split()
        if len(p) == 3:
            events[int(p[0])].append((int(p[2]), int(p[1])))
    is_app = lambda t: (a.app << 8) <= t < ((a.app + 1) << 8)
    task_pe, cpu, first = {}, defaultdict(int), {}
    for addr, ev in events.items():
        ev.sort()
        for i, (t, st) in enumerate(ev):
            if st in kernel_idle or not is_app(st):
                continue
            end = ev[i + 1][0] if i + 1 < len(ev) else t1
            s, e = max(t, t0), min(end, t1)
            if e > s:
                task_pe[st] = pe_name(addr)
                cpu[st] += e - s
                first.setdefault(st, s)

    tasks = sorted(t for t in names if is_app(t))
    by_pe = defaultdict(list)
    for t in tasks:
        by_pe[task_pe.get(t)].append(names[t])
    shared = {p: ts for p, ts in by_pe.items() if p and len(ts) > 1}

    resumo = {
        "malha": f"{plat.get('mpsoc_x')}x{plat.get('mpsoc_y')}",
        "duracao_ciclos": win,
        "duracao_ms": round(win / clock_hz * 1e3, 4),
        "tarefas": {names[t]: {"pe": task_pe.get(t),
                               "inicio": first[t] - t0 if t in first else None,
                               "fim": term[t] - t0 if t in term else None,
                               "cpu_ciclos": cpu.get(t, 0),
                               "status": status.get(t)} for t in tasks},
        "pes_compartilhados": shared,
    }
    out = Path(a.out) if a.out else d / "resumo.json"
    out.write_text(json.dumps(resumo, indent=2, ensure_ascii=False))

    print(f"Malha {resumo['malha']} | duração {win} ciclos ({resumo['duracao_ms']} ms)")
    print(f"{'tarefa':10s} {'PE':>4s} {'início':>8s} {'fim':>8s} {'CPU':>8s} {'%':>6s}")
    for t in tasks:
        r = resumo["tarefas"][names[t]]
        fmt = lambda v: "-" if v is None else str(v)
        print(f"{names[t]:10s} {fmt(r['pe']):>4s} {fmt(r['inicio']):>8s} {fmt(r['fim']):>8s} "
              f"{r['cpu_ciclos']:8d} {100 * r['cpu_ciclos'] / win:5.1f}%")
    for p, ts in shared.items():
        print(f"ATENÇÃO: PE {p} compartilhado por {', '.join(ts)}")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
