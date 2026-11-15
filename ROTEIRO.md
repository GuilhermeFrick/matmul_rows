# Roteiro de execução, passo a passo

Como rodar do zero as 15 simulações da multiplicação de matrizes na Memphis-V, conferir se deram certo e gerar tabelas, gráficos e figuras. Escrito para quem nunca usou um terminal; a versão curta, só com os comandos, está no [README](README.md).

## Antes de começar

O trabalho roda em dois lugares:

- **paxos**: servidor do laboratório da PUCRS onde a Memphis-V e as ferramentas certas (riscv64-elf-gcc 16.1.0, Verilator 5.052) já estão instaladas. As simulações rodam lá.
- **seu computador**: de onde você manda os comandos para a paxos e onde, no final, abre o debugger para ver as figuras.

```
seu computador ──ssh──▶ paxos: gerar → compilar → simular → log ──scp──▶ seu computador: debugger
```

Você conversa com a paxos por um **terminal**: uma janela onde se digita um **comando** e se aperta Enter. Cada passo abaixo diz **onde** rodar, traz o comando, explica o que ele faz e mostra o que deve aparecer.

### Como ler um comando

Um comando é o nome do programa seguido das opções:

| Parte | Significado |
|---|---|
| `python3` | o programa que vai rodar (o Python) |
| `generator.py` | o script que ele executa: o gerador |
| `--workers 4` | opção: quantos workers (W) |
| `--size 128` | opção: tamanho da matriz (N) |

- `cd pasta` entra numa pasta; `mkdir -p pasta` cria uma.
- `$USER` é trocado automaticamente pelo seu nome de usuário; `~` é a sua pasta pessoal.
- `&&` quer dizer "se o anterior deu certo, faça o próximo".

**Cole os comandos como estão.** O terminal da paxos (zsh) não aceita comentários com `#` no meio dos comandos, por isso não há nenhum aqui.

## Parte 1: preparar (uma vez só)

### 1. Entrar na paxos (seu computador)

Abra um terminal (no Linux, Ctrl+Alt+T) e conecte-se com o endereço e o usuário que o laboratório forneceu. Se o atalho `paxos` já está configurado no seu `~/.ssh/config`:

```sh
ssh paxos
```

Deve aparecer o prompt da paxos, algo como `[seu.usuario@paxos]~%`. A partir daqui, tudo o que você digita roda lá.

### 2. Baixar o código (paxos)

**git** é a ferramenta que baixa e atualiza o código a partir do repositório. O comando entra na pasta de aplicações da Memphis-V e baixa a nossa aplicação para dentro dela:

```sh
cd ~/Memphis-V/applications
git clone https://github.com/GuilhermeFrick/matmul_rows.git matmul_rows
```

Deve aparecer `Cloning into 'matmul_rows'...`. Se disser que a pasta já existe, o código já foi baixado antes: vá para o passo 3.

### 3. Atualizar para a versão mais nova (paxos)

Descarta arquivos gerados em execuções anteriores, baixa as últimas mudanças e mostra a branch e o commit:

```sh
cd ~/Memphis-V/applications/matmul_rows
git checkout . && git clean -f && git pull
git branch --show-current
git log -1 --oneline
```

Deve aparecer a lista de arquivos alterados (ou `Already up to date.`), o nome da branch e o commit atual. Anote o commit: é ele que identifica a versão medida.

## Parte 2: teste rápido (cerca de 2 minutos)

Uma rodada pequena (matriz 6 × 6, 3 workers) confirma que tudo funciona antes das simulações longas.

### 4. Gerar a configuração pequena (paxos)

O **gerador** sorteia as matrizes A e B, calcula a resposta certa (o gabarito, ou *golden*) e escreve os programas do mestre e dos workers:

```sh
cd ~/Memphis-V/applications/matmul_rows/generator
python3 generator.py --workers 3 --size 6
```

Deve aparecer uma linha começando com `N=6 W=3 seed=1`.

### 5. Simular (paxos)

Cria uma pasta de trabalho em `/sim` (o disco de simulações da paxos), copia para lá a configuração do chip e chama o `run.sh`, que **compila** (traduz o código C para o processador do chip) e **simula**:

```sh
mkdir -p /sim/$USER/matmul_rows
cp ~/Memphis-V/applications/matmul_rows/sandbox/*.yaml /sim/$USER/matmul_rows/
cd /sim/$USER/matmul_rows
~/Memphis-V/applications/matmul_rows/scripts/run.sh
```

Devem aparecer as etapas `== mint testcase`, `== mint applications`, `== mint scenario`, `== mint simulate` e, no fim, `Simulation time: ...`. Na primeira vez demora mais, porque monta o chip inteiro.

### 6. Ver se deu certo (paxos)

Cada tarefa escreve num arquivo de **log** (registro). `grep` procura linhas dentro de arquivos:

```sh
grep -h 'RESULT\|ERRO\|TICKS' testcase/scenario/log/*.txt
```

Deve aparecer, entre outras, a linha:

```
$$$_0x1_1_0_RESULT OK N=6 W=3 erros=0
```

`RESULT OK` e `erros=0`: o resultado do chip bateu com o gabarito. O começo da linha diz quem escreveu: PE, aplicação e tarefa (tarefa 0 é o mestre). As linhas `TICKS` são os tempos medidos, em ciclos.

## Parte 3: as 15 simulações (cerca de 2 horas)

3 tamanhos de matriz (N = 32, 64, 128) × 5 quantidades de workers (W = 1, 2, 4, 8, 16). Tempo aproximado de cada simulação:

| N \ W | 1 | 2 | 4 | 8 | 16 |
|---|---|---|---|---|---|
| 32 | < 1 min | < 1 min | < 1 min | < 1 min | < 1 min |
| 64 | ≈ 4 min | ≈ 2 min | ≈ 2 min | ≈ 2 min | ≈ 3 min |
| 128 | ≈ 28 min | ≈ 15 min | ≈ 10 min | ≈ 9 min | ≈ 13 min |

### 7 e 8. Preparar a pasta e rodar a bateria (paxos)

Rode **tudo no mesmo bloco**. Ele cria uma pasta só para a bateria, copia a configuração do chip dos experimentos (malha 5 × 5, memória de 1024 KB por tarefa), mostra a pasta atual e dispara a bateria.

A bateria repete, para cada N e cada W: **gerar** os programas, **escolher o mapa** (em que PE cada tarefa roda), **simular** e **guardar uma cópia** do resultado numa pasta como `res_N128_W4`. `nohup` e o `&` do final fazem ela rodar em segundo plano: continua mesmo se você fechar o terminal. Tudo o que ela imprimir vai para `bateria.log`.

```sh
mkdir -p /sim/$USER/matmul_exp && cd /sim/$USER/matmul_exp
cp ~/Memphis-V/applications/matmul_rows/experiments/testcase.yaml ~/Memphis-V/applications/matmul_rows/experiments/applications.yaml .
pwd
nohup bash -c 'APP=~/Memphis-V/applications/matmul_rows
for N in 32 64 128; do for W in 1 2 4 8 16; do
  python3 $APP/generator/generator.py --workers $W --size $N --page-kb 1024 &&
  cp $APP/experiments/scenario_w$W.yaml scenario.yaml &&
  $APP/scripts/run.sh &&
  rm -rf res_N${N}_W$W && cp -r testcase/scenario res_N${N}_W$W
done; done' > bateria.log 2>&1 &
```

Deve aparecer o caminho `/sim/<seu.usuario>/matmul_exp` (do `pwd`) e uma linha como `[1] 203693`. Se o caminho for outro, a bateria está na pasta errada: veja "Se algo der errado".

Se a pasta já tem uma bateria anterior que você quer guardar, troque `matmul_exp` por outro nome (por exemplo `matmul_exp2`) nas duas vezes em que aparece no bloco e nos passos seguintes.

### 9. Acompanhar (paxos)

`tail -f` mostra o fim do log e vai atualizando sozinho; **Ctrl+C** fecha só a visualização, a bateria continua:

```sh
tail -f bateria.log
```

Quantas simulações já terminaram (cada pasta é uma, até 15):

```sh
ls -d res_N*
```

Pode fechar o terminal e voltar depois: entre de novo com `ssh paxos` e `cd /sim/$USER/matmul_exp`.

### 10. Conferir os 15 resultados (paxos)

```sh
cd /sim/$USER/matmul_exp
grep -h 'RESULT\|ERRO' res_N*/log/*.txt
```

Devem aparecer 15 linhas `RESULT OK ... erros=0` e nenhuma com `ERRO`.

### 11. Gerar tabelas e gráficos (paxos)

Lê os 15 logs e calcula tempo, speedup e eficiência. Cria a pasta `resultados` com tabelas (CSV, que abre no Excel, e Markdown) e três gráficos (SVG, que abre no navegador):

```sh
python3 ~/Memphis-V/applications/matmul_rows/scripts/resultados.py
```

## Parte 4: as figuras do debugger

O **debugger** é a ferramenta oficial da Memphis que desenha o que aconteceu dentro do chip: quando cada processador trabalhou, por onde passaram as mensagens e qual tarefa ficou em cada PE.

### 12. Descobrir onde está o debugger (paxos)

O primeiro comando carrega as ferramentas da Memphis; o segundo mostra a pasta do debugger. Anote o caminho.

```sh
source ~/Memphis-V/applications/matmul_rows/scripts/memphis_env.sh
echo $MEMPHIS_DEBUGGER_PATH
```

### 13. Copiar resultados e debugger (seu computador)

Num terminal **do seu computador**, troque `SEU.USUARIO` pelo seu usuário da paxos e `CAMINHO` pelo que apareceu no passo 12:

```sh
mkdir -p ~/matmul_resultados && cd ~/matmul_resultados
scp -r 'paxos:/sim/SEU.USUARIO/matmul_exp/res_N*' 'paxos:/sim/SEU.USUARIO/matmul_exp/resultados' .
scp 'paxos:CAMINHO/Memphis_Debugger.jar' .
```

### 14. Abrir o debugger (seu computador)

Precisa de Java instalado. Abre a simulação com 16 workers e matriz 128 × 128; para outra, troque o nome da pasta:

```sh
java -jar Memphis_Debugger.jar res_N128_W16/debug/platform.cfg
```

| Figura | Onde clicar | O que mostra |
|---|---|---|
| Escalonamento de um PE | clique no PE → aba **Scheduling** → **Open Scheduling Graph** | quando aquele processador trabalhou e ficou parado |
| Escalonamento da aplicação | aba **Scheduling** → **Open Application Scheduling**, aplicação 1 | todas as tarefas, uma por linha |
| Tráfego | **Tools** → **Communication Overview** | quanto da comunicação passou por cada roteador |
| Mapeamento | **Tools** → **Task Mapping Overview**, marque **All tasks status** | qual tarefa ficou em cada PE |

Para salvar a figura, use a captura de tela do sistema.

## Se algo der errado

| O que aparece | O que quer dizer | O que fazer |
|---|---|---|
| `command not found: mint` | as ferramentas da Memphis não estão carregadas | rode o `source ... memphis_env.sh` do passo 12 |
| `Faltando testcase.yaml na pasta atual` | você está na pasta errada | `cd /sim/$USER/matmul_exp` (ou `matmul_rows` no teste rápido) |
| o `pwd` do passo 7/8 não mostra `matmul_exp` | a bateria foi disparada na pasta errada | pare com `kill <número do [1]>` e `pkill -u $USER -f phivers`, apague as pastas `res_N*` criadas lá e repita o bloco inteiro |
| `ERRO 1 (alloc)` | faltou memória para as matrizes | confira se copiou o `testcase.yaml` de `experiments/` (página de 1024 KB) |
| `ERRO 2 (send)` ou `ERRO 3 (receive)` | uma mensagem entre tarefas falhou | rode de novo aquela combinação; se repetir, guarde o log |
| `RESULT ERRO ... erros=` maior que 0 | a conta não bateu com o gabarito | guarde a pasta `res_N..._W..`: é um defeito |
| `AVISO: master não cabe` | o gerador estimou que a memória não basta | use `--page-kb 1024` e o `testcase.yaml` dos experimentos |
| a bateria parece parada | as simulações de N = 128 levam até ~30 min cada | espere; `ls -d res_N*` mostra o progresso |
| `zsh: == not found` ou erro com `#` | o zsh interpreta `=` e `#` de forma especial | cole os comandos exatamente como estão aqui |

## Glossário

| Termo | Significado |
|---|---|
| Terminal | janela onde se digitam comandos em texto |
| Servidor | computador remoto ligado o tempo todo; aqui, a paxos |
| SSH | programa que abre um terminal em outro computador pela rede |
| scp | programa que copia arquivos entre computadores pela rede |
| git | ferramenta que baixa e atualiza o código a partir do repositório |
| Commit | uma versão registrada do código, identificada por um código como `852d4ef` |
| Script | arquivo com uma sequência de comandos ou um pequeno programa |
| Compilar | traduzir o código C para instruções que o processador do chip executa |
| Simular | reproduzir o chip no computador, ciclo a ciclo |
| Log | arquivo de registro com tudo o que as tarefas imprimiram |
| Gabarito (golden) | a resposta certa, calculada antes, para conferir a do chip |
| N e W | tamanho da matriz e número de workers |
| PE | um dos processadores do chip, chamado pela posição (ex.: 2x2) |
| Debugger | ferramenta oficial que mostra graficamente o que aconteceu na simulação |
