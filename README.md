# matmul_rows — Multiplicação de matrizes na Memphis-V

Todos os comandos rodam na paxos.

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
git checkout . && git clean -f && git pull   # descarta arquivos do gerador
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

## Experimentos (malha 5x5, 1 tarefa por PE)

```sh
mkdir -p /sim/$USER/matmul_exp && cd /sim/$USER/matmul_exp
APP=~/Memphis-V/applications/matmul_rows
cp $APP/experiments/testcase.yaml $APP/experiments/applications.yaml .
N=32
for W in 1 2 4 8 16; do
  python3 $APP/generator/generator.py --workers $W --size $N --page-kb 1024
  cp $APP/experiments/scenario_w$W.yaml scenario.yaml
  $APP/scripts/run.sh
  rm -rf res_N${N}_W$W && cp -r testcase/scenario res_N${N}_W$W
done
grep -H 'TICKS\|RESULT\|ERRO' res_N*/log/*.txt
```

## Ver a saída das tarefas

```sh
grep -h '\$\$\$_' testcase/scenario/log/*.txt
```

## Debugger

```sh
source ~/Memphis-V/applications/matmul_rows/scripts/memphis_env.sh
mint debug testcase/scenario
```

- Escalonamento: clicar no PE → Scheduling → Open Scheduling Graph
- Tráfego: Tools → Communication Overview
- Mapeamento: Tools → Task Mapping Overview

## Resumo de tempos

```sh
python3 ~/Memphis-V/applications/matmul_rows/scripts/analyze.py testcase/scenario
```

Gera `testcase/scenario/resumo.json`.
