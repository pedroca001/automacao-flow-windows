---
name: avatares-organicos
description: >
  Produz conteúdo ORGÂNICO com avatar de IA — páginas que postam reels e faturam sem
  gastar em tráfego, com o funil fechando em comentário → DM. Cobre a identidade do
  avatar (rosto que não muda entre vídeos), a persona e a página, os formatos de vídeo
  validados por métrica real, os defeitos do gerador, a legenda queimada, a voz única
  e o funil de DM. Use quando o dono pedir "cria uma página", "faz um reel orgânico",
  "monta um avatar", "vídeo pra postar sem anúncio", ou quando o trabalho for conteúdo
  que o algoritmo distribui de graça em vez de mídia paga. É o par orgânico das skills
  /criativos e /vsl — mesma fábrica de vídeo, jogo completamente diferente.
---

# Skill: Avatares Orgânicos

Você vai levar o dono de "não tenho página" até **uma página publicando todo dia, com
funil fechando em DM, sem um centavo de mídia**.

> ⚠️ **Isto não é a skill `/criativos`.** Lá o dono compra a impressão e o criativo só
> precisa converter. Aqui **o algoritmo decide se alguém vê** — e as leis mudam. Várias
> regras de criativo pago *reprovam* em orgânico. A seção "Pago × Orgânico" do
> `05-AVATARES-ORGANICOS/00-VISAO-GERAL.md` lista quais, com os números.

## Antes de tudo

1. Leia `SISTEMA.md` (as leis inegociáveis do sistema).
2. Leia `05-AVATARES-ORGANICOS/00-VISAO-GERAL.md` — sem isso você vai aplicar lei de
   pago em orgânico e queimar a página.

## Fluxo

### 1. Persona e página
Leia `05-AVATARES-ORGANICOS/02-PAGINA-E-PERSONA.md`.
- Defina a persona a partir do nicho — ela tem que **carregar a promessa sem falar nada**.
- Monte a identidade visual (perfil + capa) e a bio.
- Página com **nome de pessoa** leva rosto; página com **nome de marca** leva logo.
- ⛔ Zero link em website/bio. ⛔ Filtro de palavrão **desligado** (ele come a keyword do funil).

### 2. Identidade do avatar
Leia `05-AVATARES-ORGANICOS/01-IDENTIDADE-DO-AVATAR.md`.
- Gere o **master** (a foto de identidade) e fixe o `mediaId`. É ele que mantém o rosto igual.
- 🔴 **Na identidade fica SÓ quem a pessoa é.** Roupa, enquadramento e o que ela segura
  são da CENA. Misturar os dois é o erro mais caro deste módulo — está documentado lá.

### 3. Formato e roteiro
Leia `05-AVATARES-ORGANICOS/03-FORMATOS-ORGANICOS.md`.
- Escolha entre os 3 formatos medidos: **selfie com avatar**, **bancada sem rosto**, **híbrido**.
- 🔗 **A embalagem e o hook vêm da biblioteca do sistema** (`04-BRINDE-BIBLIOTECA-FORMATOS/`);
  o módulo 03 mostra quais dos 6 invariantes de hook atravessam pro orgânico e quais não.
- 🔗 **Escrevendo o roteiro/CTA? Ative as skills de copy do sistema** — `direct-response-copywriter`,
  `copy-legends`, `marketing-psychology`. Este módulo não refaz copy, ele dá o esqueleto de cena.
- Gancho concreto antes de 2s — **nunca** subordinada temporal.

### 4. Gerar
🔗 **Ative a skill `video-ia-sem-defeito` ANTES de escrever o prompt** — é o catálogo de
defeitos mecânicos, e vale igual em pago e orgânico. Depois leia
`05-AVATARES-ORGANICOS/04-DEFEITOS-DO-GERADOR.md`, que tem só o que é específico daqui.
- Frames primeiro → **conferir o frame** → só então animar. A imagem manda mais que o texto.
- Um objeto, um movimento, o clipe inteiro.
- 🔗 Pra operar o Flow sem clique e com state em disco: `01-CRIATIVOS/06-DRIVER-SEM-CLIQUE.md`.

### 5. Legenda e voz
Leia `05-AVATARES-ORGANICOS/05-LEGENDA-E-VOZ.md`.
- Legenda queimada, blocos curtos, **keyword do funil em destaque e com tempo de leitura**.
- Vídeo **sem rosto** com várias cenas: unifique a voz (`scripts/voz-unica.py`).

### 6. Funil e publicação
Leia `05-AVATARES-ORGANICOS/06-FUNIL-DM-ORGANICO.md`.
- Bridge no ar **antes** do primeiro post. Automação comentário→DM com a keyword.
- 1 post por página por dia, horário fixo, **nunca duas páginas no mesmo horário**.

### 7. Medir
Leia `05-AVATARES-ORGANICOS/07-MEDIR-E-DECIDIR.md`.
- A métrica que decide é **distribuição**, não retenção. O módulo explica por quê.
- Uma variável por teste. Sempre.

## Regras de ouro (nunca quebre)

Movimento no segundo zero, e o que se move **não é o produto** · gancho concreto, nunca
subordinada temporal · um objeto por clipe · identidade ≠ cena · recipiente claro (escuro
engole o produto) · keyword do funil com ≥0,75s na tela · bridge antes do post · uma
variável por teste · folha de contato a 2 fps · **o dono é o QA final**.
