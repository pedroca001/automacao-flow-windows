---
name: vsl
description: Modela e cria uma VSL (video sales letter) nova a partir de uma VSL de referência, ou cria do zero. Faz engenharia reversa da referência (ritmo, blocos, escada de crença), escreve o roteiro modelado, gera os clipes com IA e monta com edição complexa (antes/depois, prova, tela dividida, depoimento, remoção de fundo). Use quando o dono mandar uma VSL de referência, um link/arquivo de VSL, ou pedir "modela essa VSL", "cria uma VSL", "faz a VSL da minha oferta".
---

# Skill: Modelar/criar uma VSL

Você vai transformar uma VSL de referência (ou uma oferta) numa VSL nova, completa e editada. **Leia os módulos conforme avança.**

## Antes de tudo
Leia `SISTEMA.md` (as leis inegociáveis) se ainda não leu nesta sessão.

## Fluxo

### 1. Modelagem (engenharia reversa)
Leia `02-VSL/01-MODELAGEM.md` e execute:
- Transcreva a VSL de referência (whisper).
- Rode scene-detect pra medir o ritmo (cortes por minuto = sua meta).
- Extraia frames, monte grids, mapeie os blocos com timestamps.
- Delegue a análise dos blocos ao modelo de visão em paralelo.
- Entregue ao dono o **mapa da VSL**: lead, escada de crença, mecanismo, pitch — e o plano de compressão/transplante.

### 2. Roteiro
Leia `02-VSL/02-ROTEIRO.md` e **`02-VSL/06-EDICAO-DINAMICA-OBRIGATORIA.md` §3** (a expert com energia nasce no roteiro).
- Escreva o roteiro modelado no formato que o pipeline parseia (blocos + cenas + falas).
- **Transplante, não tradução:** mesma espinha, órgãos novos pra oferta/persona do dono.
- Respeite as regras de fala (≤26 e ≥16 palavras, sem nome próprio no áudio, CTA só junto do preço).
- **Toda tag de cena leva tom + gesto + olhar, e VARIA** (`[EXPERT, urgente, olhando direto na câmera]`, `[EXPERT, energia, inclinada pra frente]`, `[EXPERT, mostrando exatamente UM dedo]`…). Nunca 3 cenas seguidas com a mesma tag. Cenário/enquadramento muda por bloco com motivo narrativo. `[DEMO]` (B-roll) amarrado na palavra da fala do momento e denso nos 2 primeiros minutos.
- Rode os greps de compliance. Apresente pro dono aprovar o roteiro.

### 3. Geração dos clipes
Leia `02-VSL/03-GERACAO-FLOW.md`. **Ative a `video-ia-sem-defeito` antes de escrever qualquer prompt de cena.**
- Os clipes da VSL passam pelo MESMO driver dos criativos (`scripts/flow_driver.py`, `PHASE=masters|scenes|submit|poll|retry`, sem clique). O spec que o driver lê é sempre `{personas, itens[{id, cenas[{n, persona_key, prompt_img, prompt_video}]}]}` (cabeçalho do `flow_driver.py`). **O conversor roteiro-da-VSL → spec (`vsl_to_spec.py`) você escreve** a partir do formato do doc 02 (blocos, `[DEMO]`, `[SKIP]`, mestres por bloco): não vem pronto porque cada VSL tem estrutura própria. Use `scripts/gerar_specs.py` como referência de como montar `prompt_img`/`prompt_video` (blocos globais, marcador de voz byte-idêntico, auto-teste de placeholder) — ou use-o direto, com `leva.json`, quando a VSL for simples (1 apresentador, cenas em ordem, sem blocos).
- Master → `scripts/gate_frames.py masters` (o dono aprova o rosto) → cenas → `gate_frames.py scenes` (gate visual) → submit/poll → `scripts/flow_download.py` → `scripts/gate_clipes.py`.
- `veo_3_1_i2v_lite_low_priority`, 1 submitter por aba.
- Respeite os filtros do Veo (sem espelho, sem nome próprio, etc.).

### 4. Edição avançada + montagem + QA — 🔴 com PLANO DE EDIÇÃO, nunca "concatenar e legendar"
Leia `02-VSL/04-EDICAO-AVANCADA.md`, `05-MONTAGEM-E-QA.md` e **`06-EDICAO-DINAMICA-OBRIGATORIA.md`** (a régua, o plano obrigatório e o gate medido — a montagem mínima é reprovada por definição; já aconteceu: 5 minutos de expert parada).
- **Escreva o PLANO DE EDIÇÃO antes de montar** (`vsls/VSL-X.plano-edicao.json`, modelo em `02-VSL/scripts-referencia/exemplo-plano-edicao.json` + tabela em .md pro dono): split na cena 1-2 · efeito real a cada 2-3 cenas nos 2 primeiros minutos e no máximo a cada 5-6 no corpo · todo depoimento com par · toda prova com insert (e RVM quando a expert explica por cima) · flashes de "antes" na intro · punch-in automático no resto. **Mostre o plano pro dono; sem plano aprovado, sem montagem.**
- Gere os assets de prova: antes/depois (mesma pessoa, i2i encadeado, DEPOIS = foto nova, **transformação = a que o produto promete e só ela**, gate de contraste em miniatura), prints (PIL), página editorial.
- **Remoção de fundo (RVM):** pessoa recortada no canto direito, prova visível inteira.
- Tela dividida, ken burns liso (nunca zoompan puro), cutaway pra nunca ficar em silêncio.
- Monte: trim por whisper → punch-in → cutaways → inserts → pares → RVM/splits → concat → legendas ASS → overlays de preço/nome/bônus → burn (os 9 passos do doc 05). **Agora existe implementação de referência: `02-VSL/scripts-referencia/montar_vsl.py`** — lê o plano de edição e aplica split, cutaway (crossfade 0,20 nas pontas), insert com ken burns, par (wipeleft), flash, RVM, zoom, punch-in automático em todo plano falado >4,6s, xfade de bloco, legendas ASS (66px, MarginV 220), overlays e QA objetivo. **Adapte-o à sua VSL, não escreva do zero** (cada VSL tem seus inserts/overlays; o motor é o mesmo). ⚠️ **NÃO** aplique a faixa de headline nem a pílula de CTA de anúncio numa VSL — isso é convenção de criativo de 60-100s. Vídeo e áudio TÊM que terminar juntos (divergência >1,5s = reprovado).
- **`python3 scripts/medir_ritmo.py vsls/VSL-X_final.mp4`** → gate de ritmo MEDIDO (≥12 trocas de estímulo/min, maior plano ≤12s, zero silêncio >1s, v×a ≤1,5s). Reprovou = volta ao plano, não entrega.
- Passe pelo **QA de 5 camadas**. Apresente pro dono.

## Regras de ouro (nunca quebre)
Fluidez = critério nº1, zero silêncio · fala ≤26/≥16 palavras · sem nome próprio no áudio · 1 submitter por aba · figurino único e fundo travado · antes/depois = mesma pessoa, contraste que grita, transformação = a promessa do produto · RVM com prova visível · nunca zoompan puro · preço só junto do CTA · dono é o QA final · **plano de edição antes de montar · punch-in em todo plano falado >4,6s · nenhum plano >6-8s sem trocar o estímulo · 2 primeiros minutos densos (split desde 0:00) · expert com energia no prompt (tom+gesto+olhar variados) · ritmo medido antes de entregar.** Upsell = 7-10 min, formato 3:4.

> Se o dono NÃO pedir nada disso, faça assim mesmo — é o padrão. VSL "expert falando de frente" com legenda não é VSL montada; é reprovada antes de mostrar.
