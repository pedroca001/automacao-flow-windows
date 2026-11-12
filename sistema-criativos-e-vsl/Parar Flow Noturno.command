#!/bin/bash
set -euo pipefail
TASK_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
cd "$TASK_DIR"
source ./env.sh
python3 retomada-macro/noturno.py parar
read -r -p "Pressione Enter para fechar esta janela. " TASK_CLOSE
