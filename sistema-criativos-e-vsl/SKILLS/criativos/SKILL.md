---
name: criativos
description: Produz uma leva de criativos de vídeo a partir de um link de biblioteca de anúncios (Facebook Ads Library) ou de uma oferta. Espiona a biblioteca via Apify, baixa e transcreve os vídeos, analisa os frames (formato, anatomia visual, copies) e gera criativos novos no mesmo padrão dos que estão escalando. Use quando o dono mandar um link de Ad Library, pedir "cria criativos", "faz uma leva de ads", "espiona essa oferta", ou apontar uma oferta pra modelar.
---

# Skill: Produzir uma leva de criativos

Você vai levar o dono do link de uma biblioteca de anúncios até uma leva de criativos prontos, no padrão do que já está escalando. **Leia os módulos conforme avança — eles têm o passo a passo real e as leis anti-erro.**

## Antes de tudo
Leia `SISTEMA.md` (as leis inegociáveis) se ainda não leu nesta sessão.

## Fluxo

### 1. Espionagem (entrada)
Leia `01-CRIATIVOS/01-ESPIONAGEM-APIFY.md` e execute:
- Se o dono mandou **um link de Ad Library** → raspe a biblioteca inteira via Apify.
- Se mandou **uma oferta/nicho** → ache as ofertas escaladas no swipe file online (**https://001class.site/swipefile/**) e na Ad Library primeiro.
- Baixe os vídeos, transcreva com whisper (`-l` da língua certa), extraia frames, e mande a análise visual dos frames pro modelo de visão.
- **Enriqueça com o swipe file:** mesmo com a oferta escolhida, busque no swipe file online (**https://001class.site/swipefile/**) e no `04-BRINDE-BIBLIOTECA-FORMATOS/` outras ofertas do mesmo nicho pra ter mais dados. Mostre e explique tudo pro dono.

### 2. Planejar os criativos — 🔴 leva DINÂMICA, nunca "a mesma pessoa falando 12 vezes"
Leia `01-CRIATIVOS/02-CONSTRUTOR-DE-ADS.md`, `04-BRINDE-BIBLIOTECA-FORMATOS/` e **`01-CRIATIVOS/07-GANCHOS-DE-CHOQUE.md` + `01-CRIATIVOS/08-CRIATIVO-DINAMICO.md`** (os dois são obrigatórios: sem eles a leva sai parada — já aconteceu: 15 ads, 12 iguais).
- Escolha 5-10 formatos/espetáculos que casam com a oferta.
- **Persona + cenário marcantes, 1 por ad, rostos e cenários diferentes em toda a leva** (bloco LOOK + CRITICAL do doc 08; master com cenário E roupa explícitos).
- **Gancho de choque como entregável SEPARADO** por ad (`mecanica` SPLIT/INSERT_PRIMEIRO/ACAO/ESTRANHO + `acao_visual` + `insert_visual` + `gancho_fala`), 4 mecânicas distribuídas, 5 famílias de choque, objeto que encarna a dor/mecanismo, nenhum objeto/verbo repetido (doc 07).
- **Corpo com TIPO em cada cena** (T-close/T-aberto/T-3/4/T-cta · D · I · L), nunca 3 iguais seguidos; insert I com voz off pro device/mecanismo grotesco/prova; esqueletos CURTO (8) e LONGO (14) do doc 08 §3.
- Monte o brief de cada criativo variando o **corpo** (mecanismo/espetáculo), não só o hook.
- **Preencha a TABELA-PROVA da leva** (doc 08 §6: id · persona · cenário · gancho mecânica/família/objeto/verbo · plano do corpo · device · registro) e apresente pro dono aprovar antes de gerar. Sem tabela = ainda não planejou.

### 3. Escrever a copy (só depois do plano aprovado)
- **Ative as skills de copy ANTES de escrever** (`direct-response-copywriter`, `copy-legends`, `marketing-psychology`) — roteiro, headline e CTA nunca saem na unha.
- **Ative a `video-ia-sem-defeito` ANTES de escrever qualquer `acao` de cena** (o que o gerador erra e como não deixar).
- Escreva a copy aprovada no formato `leva.json` (modelo — e padrão de leva DINÂMICA — em `scripts/exemplo-leva.json`; campos explicados no cabeçalho de `scripts/gerar_specs.py`): personas (descrição visual em inglês COM roupa, cenário COM luz, voz) + itens (id, headline, **`gancho`** com mecânica/acao_visual/insert_visual/gancho_fala, cenas a partir de n=2 com **`tipo`**, `acao` em inglês e `fala` no idioma do público).
- Prompt de gancho e de insert: **curto, abrindo na ação, sem redescrever a pessoa, sem instrução de montagem** (< ~600 chars — cabeçalho longo dispara `UNSAFE_GENERATION`, doc 07 §5).
- `python3 scripts/gerar_specs.py leva.json` → gera `specs/<AD>.json`. Ele **reprova** placeholder e travessão na fala; leia os avisos (fala <8 palavras = cena muda; >26 = não cabe) — e os avisos de DINÂMICA (sem gancho · sem tipo · 3 tipos iguais seguidos · mecânica dominando · choque baixo · persona repetida): **cada aviso desses é uma leva parada anunciada. Corrija antes de gerar.**

### 4. Gerar (o driver — sem clique, sem screenshot)
Leia `01-CRIATIVOS/03-RECEITAS-FORMATOS-FLOW.md`, `04-PIPELINE-TECNICO.md` e `06-DRIVER-SEM-CLIQUE.md`. O fluxo inteiro dos scripts está em `scripts/LEIA.md`.
- `FLOW_PROJECT=<id> SPEC=specs/AD-01.json PHASE=masters browser-harness < scripts/flow_driver.py` → `python3 scripts/gate_frames.py masters` → **mostre a grade dos rostos pro dono** antes de seguir.
- `PHASE=scenes` → `python3 scripts/gate_frames.py scenes` → **gate visual**: descreva cada frame da grade contra o que o prompt pediu (objeto fantasma? texto pintado? mão errada?). Frame errado = corrige o frame, nunca anima em cima.
- `PHASE=submit` → `PHASE=poll` (poll folgado; `PHASE=retry` libera os que falharam). **1 submitter por aba, sempre.** `veo_3_1_i2v_lite_low_priority`.
- Baixe com `scripts/flow_download.py` (rota `media.getMediaUrlRedirect`, name da mídia + cookie via CDP). (`media.fetchMedia` morreu em ago/2026.)

### 5. Gate pós-download + montagem + QA
Leia `01-CRIATIVOS/05-QA-E-LEIS.md`.
- `python3 scripts/gate_clipes.py` → tamanho · SSIM × frame · whisper × fala. Reprovado por SSIM/fala = regerar SÓ aquela cena; "lixo na cabeça" a montagem corta sozinha.
- `python3 scripts/montar_leva.py` → trim por whisper → **punch-in jump-cut** no corpo (ligado por padrão) → **gancho por mecânica** (SPLIT/INSERT_PRIMEIRO montados sozinhos) → concat → **corte por fala + silêncio** (zero silêncio >0,3s) → legendas ASS com o texto do ROTEIRO → faixa de headline (`banner.py`; `SEM_HEADLINE=1` se o nicho não usa headline no vídeo) → CTA animado nos últimos 10s → 1080x1920 → varredura de moov. Precisa de ffmpeg **com libass** (`FFMPEG=` se o padrão não tiver) e whisper (`WHISPER_MODEL=`).
- **`python3 scripts/medir_ritmo.py finais/`** → o gate de ritmo MEDIDO (≥10 trocas de estímulo/min, maior plano ≤9s, zero silêncio, v×a). Reprovou = volta ao plano, não entrega.
- **Grade dos ganchos** (frame de 0,5s e 2s de cada ad) olhada — QA numérico não vê rosto fora do quadro nem objeto que não materializou (doc 07 §8).
- Passe pelo **gate de 3 camadas** (técnica / visual / fala-voz) e apresente em lotes pro dono aprovar.

## Regras de ouro (nunca quebre)
Fala no segundo zero · impacto no frame 1 · mínimo 60s · nunca moldura de celular · uma ideia por ad · headline com número · varie o corpo · 1 submitter por aba · zero silêncio · gate antes e depois de gerar · dono é o QA final · **gancho de choque separado por ad (4 mecânicas, objeto que encarna a dor) · persona+cenário marcantes, rosto diferente em cada ad · tipo em toda cena, nunca 3 iguais seguidos · punch-in ligado · ritmo medido antes de entregar.**

> Se o dono NÃO pedir nada disso, faça assim mesmo — é o padrão. "Pessoa parada falando de frente" com 12 frases diferentes não é uma leva; é reprovado antes de subir.
