# matrix_multi — Multiplicação de matrizes na Memphis-V

Todos os comandos rodam na paxos.

## Instalar (uma vez)

```sh
cd ~/Memphis-V/applications
git clone https://github.com/GuilhermeFrick/matrix_multi_manycore_memphins-v.git matrix_multi
mkdir -p /sim/$USER/matrix_multi
cp ~/Memphis-V/applications/matrix_multi/sandbox/*.yaml /sim/$USER/matrix_multi/
```

## Atualizar o código

```sh
cd ~/Memphis-V/applications/matrix_multi
git checkout . && git pull   # descarta arquivos do gerador
```

## Gerar uma configuração

```sh
cd ~/Memphis-V/applications/matrix_multi/generator
python3 generator.py --tasks 4 --vector-size 6 --order-by asc
```

## Simular

```sh
cd /sim/$USER/matrix_multi
~/Memphis-V/applications/matrix_multi/scripts/run.sh
```

- `--rebuild-testcase` após alterar `testcase.yaml`
- `--gui` abre o debugger ao final

## Ver a saída das tarefas

```sh
grep -h '\$\$\$_' testcase/scenario/log/*.txt
```

## Debugger

```sh
source ~/Memphis-V/applications/matrix_multi/scripts/memphis_env.sh
mint debug testcase/scenario
```

- Escalonamento: clicar no PE → Scheduling → Open Scheduling Graph
- Tráfego: Tools → Communication Overview
- Mapeamento: Tools → Task Mapping Overview

## Resumo de tempos

```sh
python3 ~/Memphis-V/applications/matrix_multi/scripts/analyze.py testcase/scenario
```

Gera `testcase/scenario/resumo.json`.
