# matmul_rows — Multiplicação de matrizes na Memphis-V

Todos os comandos rodam na paxos, exceto onde indicado "no seu computador".

## Instalar (uma vez)

```sh
cd ~/Memphis-V/applications
git clone https://github.com/GuilhermeFrick/matmul_rows.git matmul_rows
mkdir -p /sim/$USER/matmul_rows
cp ~/Memphis-V/applications/matmul_rows/sandbox/*.yaml /sim/$USER/matmul_rows/
```

## Atualizar o código

```sh
cd ~/Memphis-V/applications/matmul_rows
git checkout . && git clean -f && git pull
```

## Gerar uma configuração

```sh
cd ~/Memphis-V/applications/matmul_rows/generator
python3 generator.py --workers 3 --size 6 [--seed 1] [--debug]
```

## Simular

```sh
cd /sim/$USER/matmul_rows
~/Memphis-V/applications/matmul_rows/scripts/run.sh
```

- `--rebuild-testcase` após alterar `testcase.yaml`
- `--gui` abre o debugger ao final

## Ver a saída das tarefas

```sh
grep -h '\$\$\$_' testcase/scenario/log/*.txt
```

Esperado: `RESULT OK ... erros=0` no master. Em caso de falha a tarefa imprime `ERRO <código> (<nome>): ...` e retorna o código:

| Código | Nome | Causa |
|---|---|---|
| 0 | `MATMUL_OK` | sucesso |
| 1 | `MATMUL_ERR_ALLOC` | `malloc` devolveu `NULL` |
| 2 | `MATMUL_ERR_SEND` | `memphis_send` falhou |
| 3 | `MATMUL_ERR_RECV` | `memphis_receive` falhou ou tamanho errado |
| 4 | `MATMUL_ERR_RESULT` | C diferente do golden |

## Roteiro completo dos experimentos

Malha 5x5, 1 tarefa por PE, N ∈ {32, 64, 128}, W ∈ {1, 2, 4, 8, 16}. Leva cerca de 2 h.

1. Atualizar o código (seção acima).

2. Preparar a pasta:

```sh
mkdir -p /sim/$USER/matmul_exp && cd /sim/$USER/matmul_exp
cp ~/Memphis-V/applications/matmul_rows/experiments/testcase.yaml ~/Memphis-V/applications/matmul_rows/experiments/applications.yaml .
```

3. Rodar a bateria em segundo plano (continua se o SSH cair):

```sh
nohup bash -c 'APP=~/Memphis-V/applications/matmul_rows
for N in 32 64 128; do for W in 1 2 4 8 16; do
  python3 $APP/generator/generator.py --workers $W --size $N --page-kb 1024 &&
  cp $APP/experiments/scenario_w$W.yaml scenario.yaml &&
  $APP/scripts/run.sh &&
  rm -rf res_N${N}_W$W && cp -r testcase/scenario res_N${N}_W$W
done; done' > bateria.log 2>&1 &
```

4. Acompanhar (Ctrl+C só fecha a visualização):

```sh
tail -f bateria.log
ls -d res_N*
```

5. Conferir os 15 resultados:

```sh
grep -h 'RESULT\|ERRO' res_N*/log/*.txt
```

6. Tabelas (CSV/Markdown) e gráficos de tempo, speedup e eficiência em `resultados/`:

```sh
python3 ~/Memphis-V/applications/matmul_rows/scripts/resultados.py
```

7. Debugger (seção abaixo) em `res_N128_W4` e `res_N128_W16`.

## Debugger

Na paxos (SSH com `-X`):

```sh
source ~/Memphis-V/applications/matmul_rows/scripts/memphis_env.sh
mint debug res_N128_W16
```

No seu computador, copiando os resultados e o debugger:

```sh
scp -r 'paxos:/sim/USUARIO/matmul_exp/res_N*' 'paxos:/sim/USUARIO/matmul_exp/resultados' .
scp 'paxos:CAMINHO/Memphis_Debugger.jar' .
java -jar Memphis_Debugger.jar res_N128_W16/debug/platform.cfg
```

`CAMINHO`: saída de `echo $MEMPHIS_DEBUGGER_PATH` na paxos após o `source`.

- Escalonamento: clicar no PE → Scheduling → Open Scheduling Graph
- Tráfego: Tools → Communication Overview
- Mapeamento: Tools → Task Mapping Overview

## Resumo de tempos

```sh
python3 ~/Memphis-V/applications/matmul_rows/scripts/analyze.py testcase/scenario
```

Gera `testcase/scenario/resumo.json`.
