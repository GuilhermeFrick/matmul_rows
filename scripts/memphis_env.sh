# Carrega o ambiente do Memphis-V na paxos (bash ou zsh).
# Uso:  source scripts/memphis_env.sh
# (precisa ser "source", não "./": as variáveis têm que ficar no seu shell)

if [ -n "$BASH_VERSION" ] && [ "${BASH_SOURCE[0]}" = "$0" ]; then
    echo "Use: source $0" >&2
    exit 1
fi

export MEMPHIS_PATH="${MEMPHIS_PATH:-$HOME/Memphis-V}"

# Comando "module" vem do ambiente do GAPH
if ! command -v module >/dev/null 2>&1 && [ -f /soft64/source_gaph ]; then
    . /soft64/source_gaph
fi

module load memphis-v

# Verilator 5.052 só é compatível com g++ 15
if [ -f /opt/rh/gcc-toolset-15/enable ]; then
    . /opt/rh/gcc-toolset-15/enable
fi

if [ -f "$MEMPHIS_PATH/venv/bin/activate" ]; then
    . "$MEMPHIS_PATH/venv/bin/activate"
else
    echo "AVISO: venv não encontrado em $MEMPHIS_PATH/venv (instale o mint)" >&2
fi

echo "MEMPHIS_PATH = $MEMPHIS_PATH"
echo "riscv64-elf-gcc: $(riscv64-elf-gcc -dumpversion 2>/dev/null || echo 'NÃO ENCONTRADO')"
echo "g++:             $(g++ -dumpversion 2>/dev/null || echo 'NÃO ENCONTRADO')"
echo "verilator:       $(verilator --version 2>/dev/null || echo 'NÃO ENCONTRADO')"
echo "mint:            $(command -v mint || echo 'NÃO ENCONTRADO')"
