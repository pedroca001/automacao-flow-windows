#!/usr/bin/env bash
# instalar-skills.sh — recria a pasta oculta .claude/skills/ a partir da cópia visível SKILLS/.
#
# Uso (de qualquer lugar):
#   bash scripts/instalar-skills.sh                 → instala em <pasta-do-sistema>/.claude/skills/
#   bash scripts/instalar-skills.sh /outro/projeto  → instala TAMBÉM em /outro/projeto/.claude/skills/
#                                                     (útil quando você abre o Claude numa pasta maior)
# Idempotente: pode rodar quantas vezes quiser. Não apaga nada que já exista, só sobrescreve as 7 skills.
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FONTE="$RAIZ/SKILLS"
[ -d "$FONTE" ] || FONTE="$RAIZ/.claude/skills"   # se só a oculta existir, ela vira a fonte
if [ ! -d "$FONTE" ]; then
  echo "❌ Não achei nem SKILLS/ nem .claude/skills/ em: $RAIZ"
  echo "   O pacote está incompleto — descompacte o zip original de novo (unzip -l <zip> | grep .claude)."
  exit 1
fi

ESPERADAS=(criativos vsl avatares-organicos direct-response-copywriter copy-legends marketing-psychology video-ia-sem-defeito)

instalar_em() {
  local destino="$1/.claude/skills"
  mkdir -p "$destino"
  local ok=0
  for s in "${ESPERADAS[@]}"; do
    if [ -f "$FONTE/$s/SKILL.md" ]; then
      mkdir -p "$destino/$s"
      cp -R "$FONTE/$s/." "$destino/$s/"
      ok=$((ok+1))
    else
      echo "   ⚠️  skill ausente na fonte: $s"
    fi
  done
  echo "✅ $ok/${#ESPERADAS[@]} skills instaladas em: $destino"
}

echo "Fonte: $FONTE"
instalar_em "$RAIZ"
if [ "${1:-}" != "" ]; then
  [ -d "$1" ] || { echo "❌ pasta não existe: $1"; exit 1; }
  instalar_em "$(cd "$1" && pwd)"
fi
echo
echo "Pra conferir: bash \"$RAIZ/scripts/verificar-pacote.sh\""
echo "Depois abra (ou reinicie) o Claude Code na pasta e digite /criativos ou /vsl."
