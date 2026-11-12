# SKILLS/ — cópia VISÍVEL das skills do sistema

As 7 skills que o Claude usa (`/criativos`, `/vsl`, `/avatares-organicos`, `direct-response-copywriter`,
`copy-legends`, `marketing-psychology`, `video-ia-sem-defeito`) moram oficialmente em
**`.claude/skills/`** — uma pasta que começa com ponto e por isso fica **oculta** no Finder
e no Explorer. Quem copia "tudo que aparece" pra outra pasta deixa ela pra trás sem perceber.

Esta pasta `SKILLS/` é a mesma coisa, só que visível. Se a `.claude/skills/` sumiu no caminho
(você moveu os arquivos, copiou pra dentro de outro projeto, o descompactador pulou pasta oculta),
basta rodar, de dentro da pasta do sistema:

    bash scripts/instalar-skills.sh

Ele recria a `.claude/skills/` a partir daqui. Se quiser instalar as skills num OUTRO projeto
(por exemplo, você abre o Claude numa pasta maior e o sistema está numa subpasta):

    bash scripts/instalar-skills.sh /caminho/da/pasta/onde/voce/abre/o/claude

Pra conferir se o pacote está inteiro: `bash scripts/verificar-pacote.sh`.
