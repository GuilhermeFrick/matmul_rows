# matrix_multi — Multiplicação de matrizes na Memphis-V

## Instalar na paxos (uma vez)

```sh
cd ~/Memphis-V/applications
git clone https://github.com/GuilhermeFrick/matrix_multi_manycore_memphins-v.git matrix_multi
mkdir -p /sim/$USER/matrix_multi
cp ~/Memphis-V/applications/matrix_multi/sandbox/*.yaml /sim/$USER/matrix_multi/
```

## Executar

```sh
cd /sim/$USER/matrix_multi
~/Memphis-V/applications/matrix_multi/scripts/run.sh
```

Opções do `run.sh`:

- `--gui` abre o debugger gráfico
- `--rebuild-testcase` refaz o hardware (após alterar `testcase.yaml`)

## Atualizar o código

```sh
cd ~/Memphis-V/applications/matrix_multi && git pull
```

## Gerar outra configuração

```sh
cd generator
python3 generator.py --tasks 4 --vector-size 6 --order-by asc
```
