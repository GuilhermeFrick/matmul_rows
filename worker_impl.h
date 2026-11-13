/* Lógica única dos workers: cada workerX.c contém só #include "worker_impl.h" */
#pragma once

#include <memphis.h>
#include <stdio.h>
#include <stdint.h>

#include "data.h"

static int32_t a_blk[MATMUL_ROWS][MATMUL_N];
static int32_t b[MATMUL_N][MATMUL_N];
static int32_t c_blk[MATMUL_ROWS][MATMUL_N];

int main()
{
    unsigned t0 = memphis_get_tick();

    if (memphis_receive(a_blk, sizeof(a_blk), master) != (int)sizeof(a_blk) ||
        memphis_receive(b, sizeof(b), master) != (int)sizeof(b)) {
        puts("ERRO: receive do master");
        return 1;
    }

    unsigned t1 = memphis_get_tick();

    for (int i = 0; i < MATMUL_ROWS; i++) {
        for (int j = 0; j < MATMUL_N; j++) {
            int32_t acc = 0;
            for (int k = 0; k < MATMUL_N; k++)
                acc += a_blk[i][k] * b[k][j];
            c_blk[i][j] = acc;
        }
    }

    unsigned t2 = memphis_get_tick();

    if (memphis_send(c_blk, sizeof(c_blk), master) < 0) {
        puts("ERRO: send para o master");
        return 1;
    }

    unsigned t3 = memphis_get_tick();

    printf("TICKS recv=%u comp=%u send=%u\n", t1 - t0, t2 - t1, t3 - t2);

    return 0;
}
