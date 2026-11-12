#!/bin/bash
set -euo pipefail
TASK_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
cd "$TASK_DIR"
source ./env.sh
echo "Pasta das imagens (cole o caminho completo):"
read -r TASK_IMAGES
echo "URL ou ID do projeto do Flow:"
read -r TASK_PROJECT
# Retira somente as aspas externas que o usuário pode ter colado com o caminho.
TASK_IMAGES="${TASK_IMAGES#\"}"; TASK_IMAGES="${TASK_IMAGES%\"}"
python3 retomada-macro/noturno.py preparar --imagens "$TASK_IMAGES" --projeto "$TASK_PROJECT"
read -r -p "Pressione Enter para fechar esta janela. " TASK_CLOSE
