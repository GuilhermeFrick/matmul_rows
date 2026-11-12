#include <memphis.h>
#include <stdlib.h>
#include <stdio.h>
#include "matrix_mult.h"

int main()
{
    const int workers = NUMBER_OF_TASKS - 1;
    const int rows_per_worker = MATRIX_SIZE / workers;
    const int result_elements = MATRIX_SIZE * MATRIX_SIZE;
    int *result = (int*)malloc(result_elements * sizeof(int));

    printf("Fatiando e enviando a matriz A...\n");

    for (int worker = 1; worker < NUMBER_OF_TASKS; worker++) {
        int row_start = (worker - 1) * rows_per_worker;
        memphis_send(&matrix_a[row_start][0],
                     rows_per_worker * MATRIX_SIZE * sizeof(int), worker);
        memphis_send(matrix_b, sizeof(matrix_b), worker);
    }

    printf("Recebendo resultados...\n");

    for (int worker = 1; worker < NUMBER_OF_TASKS; worker++) {
        int row_start = (worker - 1) * rows_per_worker;
        memphis_receive(&result[row_start * MATRIX_SIZE],
                        rows_per_worker * MATRIX_SIZE * sizeof(int), worker);
    }

    printf("Matriz resultante:\n");
    for (int i = 0; i < MATRIX_SIZE; i++) {
        for (int j = 0; j < MATRIX_SIZE; j++)
            printf("%d%c", result[i * MATRIX_SIZE + j],
                   j == MATRIX_SIZE - 1 ? '\n' : ' ');
    }

    free(result);
    return 0;
}