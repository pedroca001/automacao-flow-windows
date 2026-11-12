#!/usr/bin/env bash
# verificar-pacote.sh — confere se o pacote está inteiro (inclusive a pasta OCULTA .claude/skills/).
# Uso: bash scripts/verificar-pacote.sh
set -uo pipefail
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ"

ESPERADOS=(
  LEIA-PRIMEIRO.md
  SISTEMA.md
  .claude/skills/criativos/SKILL.md
  .claude/skills/vsl/SKILL.md
  .claude/skills/direct-response-copywriter/SKILL.md
  .claude/skills/copy-legends/SKILL.md
  .claude/skills/marketing-psychology/SKILL.md
  .claude/skills/video-ia-sem-defeito/SKILL.md
  .claude/skills/avatares-organicos/SKILL.md
  SKILLS/LEIA.md
  scripts/flow_driver.py
  scripts/flow_download.py
  scripts/voz-unica.py
  scripts/instalar-skills.sh
  scripts/LEIA.md
  scripts/gerar_specs.py
  scripts/gate_frames.py
  scripts/gate_clipes.py
  scripts/montar_leva.py
  scripts/banner.py
  scripts/exemplo-leva.json
  scripts/exemplo-avatares.json
  scripts/medir_ritmo.py
  01-CRIATIVOS/07-GANCHOS-DE-CHOQUE.md
  01-CRIATIVOS/08-CRIATIVO-DINAMICO.md
  02-VSL/06-EDICAO-DINAMICA-OBRIGATORIA.md
  02-VSL/scripts-referencia/montar_vsl.py
  02-VSL/scripts-referencia/exemplo-plano-edicao.json
  01-CRIATIVOS/00-VISAO-GERAL.md
  01-CRIATIVOS/04-PIPELINE-TECNICO.md
  01-CRIATIVOS/06-DRIVER-SEM-CLIQUE.md
  02-VSL/00-VISAO-GERAL.md
  03-BRINDE-UPSELLS/00-VISAO-GERAL.md
  04-BRINDE-BIBLIOTECA-FORMATOS
  05-AVATARES-ORGANICOS/00-VISAO-GERAL.md
  swipefile/ACESSE-AQUI.md
)

faltou=0; skills_faltando=0
echo "Conferindo o pacote em: $RAIZ"
for f in "${ESPERADOS[@]}"; do
  if [ -e "$f" ]; then
    printf '  ✅ %s\n' "$f"
  else
    printf '  ❌ FALTA %s\n' "$f"
    faltou=$((faltou+1))
    case "$f" in .claude/skills/*) skills_faltando=$((skills_faltando+1));; esac
  fi
done
echo
if [ "$faltou" -eq 0 ]; then
  echo "🟢 Pacote inteiro. Abra o Claude Code nesta pasta e digite /criativos ou /vsl."
  exit 0
fi
echo "🔴 Faltam $faltou item(ns)."
if [ "$skills_faltando" -gt 0 ]; then
  echo
  echo "As skills moram em .claude/skills/ — pasta que começa com PONTO, oculta no Finder/Explorer."
  echo "Ela some quando os arquivos são copiados/arrastados pra outra pasta. Conserto em 1 comando:"
  echo
  echo "    bash \"$RAIZ/scripts/instalar-skills.sh\""
  echo
  echo "(Recria a .claude/skills/ a partir da cópia visível SKILLS/. Depois rode este verificador de novo.)"
fi
exit 1
