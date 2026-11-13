/* Gerado por generator/generator.py --workers 3 --size 6 --seed 1 */
#pragma once

#include <stdint.h>
#include <stdio.h>

/* Mensagens de debug: só com --debug no gerador */
#ifdef MATMUL_DEBUG
#define DBG(...) printf(__VA_ARGS__)
#else
#define DBG(...) ((void)0)
#endif

#define MATMUL_N 6
#define MATMUL_W 3
#define MATMUL_ROWS (MATMUL_N / MATMUL_W)

/* Matrizes só no master: os workers incluem este arquivo apenas para N e W */
#ifdef MATMUL_MASTER
static const int32_t mat_a[MATMUL_N][MATMUL_N] = {
    {17, 72, 97, 8, 32, 15},
    {63, 97, 57, 60, 83, 48},
    {26, 12, 62, 3, 49, 55},
    {77, 97, 98, 0, 89, 57},
    {34, 92, 29, 75, 13, 40},
    {3, 2, 3, 83, 69, 1}
};

static const int32_t mat_b[MATMUL_N][MATMUL_N] = {
    {48, 87, 27, 54, 92, 3},
    {67, 28, 97, 56, 63, 70},
    {29, 44, 29, 86, 28, 97},
    {58, 37, 2, 53, 71, 82},
    {12, 23, 80, 92, 37, 15},
    {95, 42, 92, 91, 64, 54}
};

static const int32_t mat_c_ref[MATMUL_N][MATMUL_N] = {
    {10726, 9425, 14212, 18025, 11528, 16446},
    {20212, 16850, 23939, 28920, 23906, 21265},
    {9837, 8874, 12650, 17080, 10430, 10883},
    {19520, 18168, 26694, 31393, 22880, 20940},
    {16943, 11564, 15553, 18293, 18102, 17860},
    {6102, 5149, 6140, 11370, 8996, 8335}
};

#endif
