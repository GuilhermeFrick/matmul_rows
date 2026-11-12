# matmul_rows — Multiplicação de matrizes na Memphis-V

## Instalar na paxos (uma vez)

```sh
cd ~/Memphis-V/applications
git clone https://github.com/GuilhermeFrick/matrix_multi_manycore_memphins-v.git matmul_rows
mkdir -p /sim/$USER/matmul
cp matmul_rows/sandbox/*.yaml /sim/$USER/matmul/
```

## Executar

```sh
cd /sim/$USER/matmul
~/Memphis-V/applications/matmul_rows/scripts/run.sh
```

Opções do `run.sh`:

- `--gui` abre o debugger gráfico
- `--rebuild-testcase` refaz o hardware (após alterar `testcase.yaml`)

## Atualizar o código

```sh
cd ~/Memphis-V/applications/matmul_rows && git pull
```

## Gerar outra configuração

```sh
cd generator
python3 generator.py --tasks 4 --vector-size 6 --order-by asc
```
