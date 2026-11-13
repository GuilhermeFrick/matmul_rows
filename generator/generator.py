#!/usr/bin/env python3
"""Gerador da aplicação matmul_rows (C = A x B, decomposição por linhas).

Uso: python3 generator.py --workers W --size N [--seed S] [--page-kb KB]

Gera na pasta da aplicação: config.yaml, data.h, master.c e worker0.c..workerW-1.c.
"""
import argparse
import random
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
VMAX = 99  # elementos de A e B em [0, VMAX]


def golden(a, b, n):
    try:
        import numpy as np
        c = np.array(a, dtype=np.int64) @ np.array(b, dtype=np.int64)
        return c.tolist()
    except ImportError:
        return [[sum(a[i][k] * b[k][j] for k in range(n)) for j in range(n)] for i in range(n)]


def c_matrix(name, m):
    rows = ",\n".join("    {" + ", ".join(map(str, r)) + "}" for r in m)
    return f"static const int32_t {name}[MATMUL_N][MATMUL_N] = {{\n{rows}\n}};\n"


def write_data_h(n, w, seed, a, b, c):
    return f"""/* Gerado por generator/generator.py --workers {w} --size {n} --seed {seed} */
#pragma once

#include <stdint.h>

#define MATMUL_N {n}
#define MATMUL_W {w}
#define MATMUL_ROWS (MATMUL_N / MATMUL_W)

/* Matrizes só no master: os workers incluem este arquivo apenas para N e W */
#ifdef MATMUL_MASTER
{c_matrix("mat_a", a)}
{c_matrix("mat_b", b)}
{c_matrix("mat_c_ref", c)}
#endif
"""


def write_master(w):
    ids = ", ".join(f"worker{i}" for i in range(w))
    return f"""#include <memphis.h>
#include <stdio.h>
#include <stdint.h>

#define MATMUL_MASTER
#include "data.h"

static const int worker_ids[MATMUL_W] = {{{ids}}};
static int32_t mat_c[MATMUL_N][MATMUL_N];

int main()
{{
    const size_t blk = sizeof(int32_t) * MATMUL_ROWS * MATMUL_N;

    unsigned t0 = memphis_get_tick();

    for (int w = 0; w < MATMUL_W; w++) {{
        if (memphis_send((void *)mat_a[w * MATMUL_ROWS], blk, worker_ids[w]) < 0 ||
            memphis_send((void *)mat_b, sizeof(mat_b), worker_ids[w]) < 0) {{
            printf("ERRO: send para worker%d\\n", w);
            return 1;
        }}
    }}

    unsigned t1 = memphis_get_tick();

    for (int w = 0; w < MATMUL_W; w++) {{
        if (memphis_receive(mat_c[w * MATMUL_ROWS], blk, worker_ids[w]) != (int)blk) {{
            printf("ERRO: receive de worker%d\\n", w);
            return 1;
        }}
    }}

    unsigned t2 = memphis_get_tick();

    int errors = 0;
    for (int i = 0; i < MATMUL_N; i++)
        for (int j = 0; j < MATMUL_N; j++)
            if (mat_c[i][j] != mat_c_ref[i][j])
                errors++;

    printf("TICKS send=%u recv=%u total=%u\\n", t1 - t0, t2 - t1, t2 - t0);
    printf("RESULT %s N=%d W=%d erros=%d\\n", errors ? "ERRO" : "OK", MATMUL_N, MATMUL_W, errors);

    return errors ? 1 : 0;
}}
"""


def write_config_yaml(w):
    succ = "".join(f'      - "worker{i}"\n' for i in range(w))
    return f"ctg:\n  master:\n    successors:\n{succ}"


def main():
    ap = argparse.ArgumentParser(description="matmul_rows generator")
    ap.add_argument("--workers", type=int, required=True, help="número de workers (W)")
    ap.add_argument("--size", type=int, required=True, help="tamanho das matrizes (N)")
    ap.add_argument("--seed", type=int, default=1, help="semente das matrizes (padrão 1)")
    ap.add_argument("--page-kb", type=int, default=64, help="page_size_data_KB do testcase (só para aviso)")
    args = ap.parse_args()
    n, w = args.size, args.workers

    if w < 1:
        sys.exit("ERRO: --workers deve ser >= 1")
    if n < 1:
        sys.exit("ERRO: --size deve ser >= 1")
    if n % w != 0:
        sys.exit(f"ERRO: N={n} não é divisível por W={w}")

    rng = random.Random(args.seed)
    a = [[rng.randint(0, VMAX) for _ in range(n)] for _ in range(n)]
    b = [[rng.randint(0, VMAX) for _ in range(n)] for _ in range(n)]
    c = golden(a, b, n)
    if max(max(r) for r in c) > 2**31 - 1:
        sys.exit("ERRO: C estoura int32")

    # remove arquivos gerados antes (inclusive os do gerador antigo)
    for f in [*APP_DIR.glob("worker*.c"), *(APP_DIR / x for x in
              ("master.c", "data.h", "config.yaml", "matrix_mult.h"))]:
        f.unlink(missing_ok=True)

    (APP_DIR / "config.yaml").write_text(write_config_yaml(w))
    (APP_DIR / "data.h").write_text(write_data_h(n, w, args.seed, a, b, c))
    (APP_DIR / "master.c").write_text(write_master(w))
    for i in range(w):
        (APP_DIR / f"worker{i}.c").write_text('#include "worker_impl.h"\n')

    # estimativa de dados por tarefa (bytes)
    master_b = 4 * n * n * 4               # A, B, C esperado, C recebido
    worker_b = (2 * (n // w) * n + n * n) * 4  # bloco de A, B, bloco de C
    page = args.page_kb * 1024
    print(f"N={n} W={w} seed={args.seed}: master ~{master_b} B, worker ~{worker_b} B (página {page} B)")
    for name, size in (("master", master_b), ("worker", worker_b)):
        if size > page:
            print(f"AVISO: {name} não cabe em page_size_data_KB={args.page_kb}")


if __name__ == "__main__":
    main()
