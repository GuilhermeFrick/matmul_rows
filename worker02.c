#include <memphis.h>
#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include "matrix_mult.h"

int main()
{
    const int rows_per_worker = MATRIX_SIZE / (NUMBER_OF_TASKS - 1);
    const int chunk_elements = rows_per_worker * MATRIX_SIZE;
    int32_t *matrix_a_chunk = (int32_t*)malloc(chunk_elements * sizeof(int32_t));
    int32_t (*matrix_b_received)[MATRIX_SIZE] =
        (int32_t (*)[MATRIX_SIZE])malloc(sizeof(matrix_b));
    int32_t *result = (int32_t*)malloc(chunk_elements * sizeof(int32_t));

    printf("Worker%d\n", getpid()-255-1);

    memphis_receive(matrix_a_chunk, chunk_elements * sizeof(int32_t), master);
    memphis_receive(matrix_b_received, sizeof(matrix_b), master);

    for (int i = 0; i < rows_per_worker; i++) {
        for (int j = 0; j < MATRIX_SIZE; j++) {
            int32_t value = 0;
            for (int k = 0; k < MATRIX_SIZE; k++)
                value += matrix_a_chunk[i * MATRIX_SIZE + k] *
                         matrix_b_received[k][j];
            result[i * MATRIX_SIZE + j] = value;
        }
    }

    memphis_send(result, chunk_elements * sizeof(int32_t), master);
    printf("Enviou\n");

    free(matrix_a_chunk);
    free(matrix_b_received);
    free(result);
    return 0;
}