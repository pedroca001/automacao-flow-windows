#!/bin/bash
set -euo pipefail
TASK_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
cd "$TASK_DIR"
source ./env.sh
if [ "$#" -gt 0 ]; then
    python3 retomada-macro/noturno.py iniciar --plano "$1"
else
    python3 retomada-macro/noturno.py iniciar
fi
read -r -p "Pressione Enter para fechar esta janela. " TASK_CLOSE
