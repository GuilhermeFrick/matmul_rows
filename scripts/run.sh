#!/usr/bin/env bash
# Compila e simula a aplicação no Memphis-V.
# Rode de dentro da pasta de sandbox (onde estão testcase.yaml,
# applications.yaml e scenario.yaml).
#
# Uso:  run.sh [--gui] [--rebuild-testcase] [--timeout MS]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

GUI=0
REBUILD=0
TIMEOUT=()
while [ $# -gt 0 ]; do
    case "$1" in
        --gui)              GUI=1 ;;
        --rebuild-testcase) REBUILD=1 ;;
        --timeout)          TIMEOUT=(--timeout "$2"); shift ;;
        -h|--help)          sed -n '2,7p' "$0"; exit 0 ;;
        *) echo "Opção desconhecida: $1" >&2; exit 1 ;;
    esac
    shift
done

for f in testcase.yaml applications.yaml scenario.yaml; do
    [ -f "$f" ] || { echo "Faltando $f na pasta atual ($PWD)" >&2; exit 1; }
done

set +u
source "$SCRIPT_DIR/memphis_env.sh"
set -u

# Hardware + kernel: só precisa refazer se mudar o testcase.yaml
if [ "$REBUILD" -eq 1 ] || [ ! -d testcase ]; then
    echo "== mint testcase"
    mint testcase testcase.yaml
fi

echo "== mint applications"
mint applications testcase applications.yaml

echo "== mint scenario"
mint scenario testcase scenario.yaml

echo "== mint simulate"
if [ "$GUI" -eq 1 ]; then
    mint simulate testcase/scenario "${TIMEOUT[@]}"
else
    mint simulate testcase/scenario --nogui "${TIMEOUT[@]}"
fi
