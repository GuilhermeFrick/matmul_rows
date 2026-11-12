# Atividade: Benchmark de Multiplicação de Matrizes Distribuída na Memphis-V

## Objetivo

Implementar um benchmark de multiplicação de matrizes inteiras (C = A × B) como aplicação **paralela** da Memphis-V, com número de workers parametrizável por um gerador, e caracterizar seu desempenho em função do tamanho do problema e do número de workers.

O repositório não possui benchmark de multiplicação de matrizes, então as aplicações resultantes devem ser incorporadas à plataforma por meio de um **pull request.**

## Organização

- 2 duplas, cada uma com uma estratégia de paralelização (Opção 1 ou Opção 2).
- Avaliação baseada na **análise** dos resultados, e não em qual versão apresenta melhor desempenho.

## Contexto técnico

- Cada arquivo `.c` no diretório da aplicação é compilado como uma tarefa (`applications/common/common.mk`).
- O grafo de tarefas (CTG) é definido estaticamente em `config.yaml` (`successors`).
- As `definitions` do yaml de aplicações alteram constantes, mas **não** o número de tarefas. Por isso, variar o número de workers exige um gerador.
- Comunicação: `memphis_send(buf, size, task)` e `memphis_receive(buf, size, task)`. Medição de tempo: `memphis_get_tick()`.
- Referências no repositório: `map_reduce` (mestre–workers e gerador em `map_reduce/generator/`) e `dtw` (vetor de IDs de tarefas `int P[] = {p1, ...}`).
- Restrições de memória: o tamanho máximo de dados por tarefa é definido por `page_size_data_KB` no testcase. As matrizes devem ser dimensionadas de acordo, e esse limite deve ser discutido no relatório.

## Parte comum (ambas as duplas)

### 1. Kernel e verificação

- Kernel escalar de multiplicação de blocos de matrizes `int32_t`.
- Versão sequencial (mestre + 1 worker), usada como baseline de speedup.
- Verificação de corretude contra um resultado de referência (golden) gerado em Python/numpy, como em `RS5/app/newlib/benchmarks/imatmul/gen_data.py`.

### 2. Gerador

Script Python `generator/generator.py` com, no mínimo, os parâmetros:

```
python3 generator.py --workers W --size N [--seed S]
```

O gerador deve produzir, por exemplo:

| Arquivo | Conteúdo |
|---|---|
| `config.yaml` | CTG com `master` e `worker0` a `workerW-1` |
| `data.h` | Matrizes A e B e resultado C esperado |
| `master.c` | Tarefa mestre |
| `workerX.c` | Um arquivo por worker |

Recomendação para evitar código duplicado: escrever a lógica do worker uma única vez em `worker_impl.h`. Cada `workerX.c` gerado contém:

```c
#include "worker_impl.h"
```

Não usar `worker_impl.c`, pois todo `.c` do diretório vira uma tarefa.

O gerador deve validar os parâmetros: `N` divisível por `W`.

## Opção 1: Decomposição em linhas (dimensão i)

Cada worker calcula um bloco de linhas **finais** de C.

Particionamento (exemplo com W = 4):

```
           A                       B                       C
    ┌─────────────┐         ┌─────────────┐         ┌─────────────┐
 w0 │     A0      │         │             │      w0 │     C0      │
    ├─────────────┤         │             │         ├─────────────┤
 w1 │     A1      │         │             │      w1 │     C1      │
    ├─────────────┤    ×    │      B      │    =    ├─────────────┤
 w2 │     A2      │         │  (inteira)  │      w2 │     C2      │
    ├─────────────┤         │             │         ├─────────────┤
 w3 │     A3      │         │             │      w3 │     C3      │
    └─────────────┘         └─────────────┘         └─────────────┘

                          Ci = Ai × B
```

Fluxo de mensagens:

```
                          master
          ┌──────────┬──────┴─────┬──────────┐
   A0, B  │   A1, B  │     A2, B  │   A3, B  │     N²/W + N² por worker
          ▼          ▼            ▼          ▼
       worker0    worker1      worker2    worker3
          │ C0       │ C1         │ C2       │ C3  N²/W por worker
          └──────────┴──────┬─────┴──────────┘
                            ▼
                 master: C = [C0; C1; C2; C3]
```

1. O mestre envia a cada worker o bloco de `N/W` linhas de A correspondente e a matriz B completa.
2. O worker calcula `C[bloco] = A[bloco] × B`.
3. O worker devolve seu bloco de C, e o mestre concatena e verifica o resultado.

**Característica:** a entrada B é replicada em todos os workers.

## Opção 2: Decomposição na dimensão interna (dimensão k)

Cada worker calcula uma matriz C **completa, porém parcial**.

Particionamento (exemplo com W = 4):

```
           A                       B                       C
  ┌───┬───┬───┬───┐         ┌─────────────┐         ┌─────────────┐
  │   │   │   │   │      w0 │     B0      │         │             │
  │   │   │   │   │         ├─────────────┤         │             │
  │   │   │   │   │      w1 │     B1      │         │             │
  │A0 │A1 │A2 │A3 │    ×    ├─────────────┤    =    │  Σ Ak × Bk  │
  │   │   │   │   │      w2 │     B2      │         │             │
  │   │   │   │   │         ├─────────────┤         │             │
  │   │   │   │   │      w3 │     B3      │         │             │
  └───┴───┴───┴───┘         └─────────────┘         └─────────────┘
   w0  w1  w2  w3

            C = A0×B0 + A1×B1 + A2×B2 + A3×B3
                └─w0┘   └─w1┘   └─w2┘   └─w3┘   (cada termo é N×N)
```

Fluxo de mensagens:

```
                          master
          ┌──────────┬──────┴─────┬──────────┐
  A0, B0  │  A1, B1  │    A2, B2  │  A3, B3  │      2·N²/W por worker
          ▼          ▼            ▼          ▼
       worker0    worker1      worker2    worker3
          │ C'0      │ C'1        │ C'2      │ C'3  N² por worker
          └──────────┴──────┬─────┴──────────┘
                            ▼
            master: C = C'0 + C'1 + C'2 + C'3
```

1. O mestre envia a cada worker o bloco de `N/W` colunas de A e o bloco correspondente de `N/W` linhas de B.
2. O worker calcula `C_parcial = A[:, bloco] × B[bloco, :]`.
3. O worker devolve sua C parcial, e o mestre soma as `W` parciais e verifica o resultado.

**Característica:** a saída é replicada, pois cada worker devolve N² elementos.

## Experimentos

| Parâmetro | Valores sugeridos |
|---|---|
| Tamanho `N` | 32, 64, 128, 256 |
| Workers `W` | 1, 2, 4, 8, 16 |

Métricas:

- Tempo total, speedup e eficiência em relação a `W = 1`. Mostrar graficamente.
- Tempo de comunicação vs. tempo de computação por worker (`memphis_get_tick` antes e depois de cada fase).
- Ociosidade dos PEs (Scheduling graph no debugger gráfico).

## Entregáveis

1. Aplicação no diretório `applications/matmul_rows` (Opção 1) ou `applications/matmul_k` (Opção 2), com gerador e `README.md`.
2. Arquivos yaml de testcase, aplicações e cenários usados nos experimentos.
3. Relatório curto com gráficos e análise. Para cada configuração, identificar o gargalo (computação, comunicação ou mestre) com evidências.
4. Apresentação mostrando os resultados e explicando o código.
5. Pull request no repositório do Memphis-V.

## Prazo

Entrega e apresentação no dia 16/11/2026
