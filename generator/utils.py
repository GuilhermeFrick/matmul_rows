import random


def write_file(name, extension, value):
    with open(f"{name}.{extension}", "w+") as f:
        f.writelines(value)


def write_config_yaml(tasks):
    config_yaml = """ctg:
  master:
    successors:
"""
    for i in range(1, tasks):
        worker_name = f"worker0{i}" if i < 10 else f"worker{i}"
        config_yaml += f'      - "{worker_name}"\n'
    return config_yaml


def write_h(matrix_size, tasks, order_by):
    h = f"""#ifndef MATRIX_MULT_STD_H_
#define MATRIX_MULT_STD_H_

#define NUMBER_OF_TASKS {tasks}
#define MATRIX_SIZE {matrix_size}

int matrix_a[{matrix_size}][{matrix_size}] = {{
"""

    def make_matrix():
        return [
            [
                random.randrange(0, 100)
                if order_by in ("rand", "random")
                else i * matrix_size + j
                for j in range(matrix_size)
            ]
            for i in range(matrix_size)
        ]

    def append_matrix(matrix):
        nonlocal h
        for row in matrix:
            h += "    {" + ", ".join(str(value) for value in row) + "},\n"

    append_matrix(make_matrix())
    h += "};\n\n"
    h += f"int matrix_b[{matrix_size}][{matrix_size}] = {{\n"
    append_matrix(make_matrix())
    h += """};

#endif"""
    return h, matrix_size


def write_master(tasks):
    return f"""#include <memphis.h>
#include <stdlib.h>
#include <stdio.h>
#include "matrix_mult.h"

int main()
{{
    const int workers = NUMBER_OF_TASKS - 1;
    const int rows_per_worker = MATRIX_SIZE / workers;
    const int result_elements = MATRIX_SIZE * MATRIX_SIZE;
    int *result = (int*)malloc(result_elements * sizeof(int));

    printf("Fatiando e enviando a matriz A...\\n");

    for (int worker = 1; worker < NUMBER_OF_TASKS; worker++) {{
        int row_start = (worker - 1) * rows_per_worker;
        memphis_send(&matrix_a[row_start][0],
                     rows_per_worker * MATRIX_SIZE * sizeof(int), worker);
        memphis_send(matrix_b, sizeof(matrix_b), worker);
    }}

    printf("Recebendo resultados...\\n");

    for (int worker = 1; worker < NUMBER_OF_TASKS; worker++) {{
        int row_start = (worker - 1) * rows_per_worker;
        memphis_receive(&result[row_start * MATRIX_SIZE],
                        rows_per_worker * MATRIX_SIZE * sizeof(int), worker);
    }}

    printf("Matriz resultante:\\n");
    for (int i = 0; i < MATRIX_SIZE; i++) {{
        for (int j = 0; j < MATRIX_SIZE; j++)
            printf("%d%c", result[i * MATRIX_SIZE + j],
                   j == MATRIX_SIZE - 1 ? '\\n' : ' ');
    }}

    free(result);
    return 0;
}}"""


def write_workers(id_, tasks):
    return """#include <memphis.h>
#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include "matrix_mult.h"

int main()
{
    const int rows_per_worker = MATRIX_SIZE / (NUMBER_OF_TASKS - 1);
    const int chunk_elements = rows_per_worker * MATRIX_SIZE;
    int *matrix_a_chunk = (int*)malloc(chunk_elements * sizeof(int));
    int (*matrix_b_received)[MATRIX_SIZE] =
        (int (*)[MATRIX_SIZE])malloc(sizeof(matrix_b));
    int *result = (int*)malloc(chunk_elements * sizeof(int));

    printf("Worker%d\\n", getpid()-255-1);

    memphis_receive(matrix_a_chunk, chunk_elements * sizeof(int), master);
    memphis_receive(matrix_b_received, sizeof(matrix_b), master);

    for (int i = 0; i < rows_per_worker; i++) {
        for (int j = 0; j < MATRIX_SIZE; j++) {
            int value = 0;
            for (int k = 0; k < MATRIX_SIZE; k++)
                value += matrix_a_chunk[i * MATRIX_SIZE + k] *
                         matrix_b_received[k][j];
            result[i * MATRIX_SIZE + j] = value;
        }
    }

    memphis_send(result, chunk_elements * sizeof(int), master);
    printf("Enviou\\n");

    free(matrix_a_chunk);
    free(matrix_b_received);
    free(result);
    return 0;
}"""
