#include <memphis.h>
#include <stdio.h>
#include <stdint.h>
#include <inttypes.h>

#define MATMUL_MASTER
#include "data.h"

static const int worker_ids[MATMUL_W] = {worker0, worker1, worker2};
static int32_t mat_c[MATMUL_N][MATMUL_N];

int main()
{
    const size_t blk = sizeof(int32_t) * MATMUL_ROWS * MATMUL_N;

    DBG("Fatiando e enviando a matriz A...\n");

    unsigned t0 = memphis_get_tick();

    for (int w = 0; w < MATMUL_W; w++) {
        if (memphis_send((void *)mat_a[w * MATMUL_ROWS], blk, worker_ids[w]) < 0 ||
            memphis_send((void *)mat_b, sizeof(mat_b), worker_ids[w]) < 0) {
            printf("ERRO: send para worker%d\n", w);
            return 1;
        }
    }

    unsigned t1 = memphis_get_tick();

    DBG("Recebendo resultados...\n");

    for (int w = 0; w < MATMUL_W; w++) {
        if (memphis_receive(mat_c[w * MATMUL_ROWS], blk, worker_ids[w]) != (int)blk) {
            printf("ERRO: receive de worker%d\n", w);
            return 1;
        }
    }

    unsigned t2 = memphis_get_tick();

    int errors = 0;
    for (int i = 0; i < MATMUL_N; i++)
        for (int j = 0; j < MATMUL_N; j++)
            if (mat_c[i][j] != mat_c_ref[i][j])
                errors++;

    printf("TICKS send=%u recv=%u total=%u\n", t1 - t0, t2 - t1, t2 - t0);
    printf("RESULT %s N=%d W=%d erros=%d\n", errors ? "ERRO" : "OK", MATMUL_N, MATMUL_W, errors);

    DBG("Matriz resultante:\n");
    for (int i = 0; i < MATMUL_N; i++)
        for (int j = 0; j < MATMUL_N; j++)
            DBG("%" PRId32 "%c", mat_c[i][j], j == MATMUL_N - 1 ? '\n' : ' ');

    return errors ? 1 : 0;
}
