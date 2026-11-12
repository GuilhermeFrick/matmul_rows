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
git checkout . && git pull   # descarta arquivos do gerador
```

## Gerar uma configuração

```sh
cd ~/Memphis-V/applications/matmul_rows/generator
python3 generator.py --tasks 4 --vector-size 6 --order-by asc
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
