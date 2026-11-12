# 03 — GERAÇÃO NO FLOW (a fábrica de clipes, custo zero)

> Aqui o roteiro vira ~100-200 clipes de 8s com a persona falando de verdade, voz nativa, rosto travado — no Google Flow, comandado pelo Claude via browser-harness, sem consumir crédito. Este documento é o manual da fábrica e a lista dos filtros do Veo que fazem cena falhar (e como contornar cada um com troca mínima de palavra).

O comando pro seu Claude:

```
Leia 02-VSL/03-GERACAO-FLOW.md. Converta vsls/VSL-X.md em spec JSON,
gere os masters da persona, me mostre a grade de frames-âncora pro gate,
e depois rode o ciclo submit→poll→retry até todas as cenas fecharem.
Modelo de vídeo: veo_3_1_i2v_lite_low_priority, SEMPRE.
```

## Infra

- **Projeto próprio no Flow por produto.** Aba do Flow aberta no Chrome logado na conta Google AI Ultra; o driver conecta via browser-harness SEM roubar o foco (nunca `switch_tab`/`activateTarget` com você usando o PC).
- **Imagem (frames):** `GEM_PIX_2` (Nano Banana 2). Em `429` (rate limit), fallback pra modelos alternativos de imagem do Flow — os limites são SEPARADOS, então a fila anda. Voltar pro Nano Banana 2 quando liberar.
- **Vídeo: 🩸 REGRA DE SANGUE — SÓ `veo_3_1_i2v_lite_low_priority`.** É o único que custa **0 créditos** (fila de baixa prioridade). O lite normal/Fast/Quality CONSOMEM os créditos do plano e esgotam a conta num dia de produção. 9:16 nativo (o Flow não gera 3:4 em vídeo; 3:4 = crop na pós, doc 05).
- **1 submitter por aba, SEMPRE.** O driver injeta variáveis globais (`window.__v` etc.) na aba; dois submits concorrentes leem a resposta um do outro → o op salvo é de OUTRA cena e o clipe baixa com fala trocada (bug pago: 17/152 clipes cruzados numa madrugada). Antes de submeter: `ps aux | grep producao_drive` e matar qualquer instância zumbi. Duas produções simultâneas na mesma conta = lock de arquivo (`fcntl.flock`) no topo do driver, ou coordenar fases pra nunca submeter junto.

## Spec (roteiro → JSON)

Um script parser (`vsl_to_spec.py` — o seu Claude escreve/adapta a partir do formato do doc 02; use `scripts/gerar_specs.py` como referência de como montar `prompt_img`/`prompt_video` com blocos globais e marcador de voz) transforma `VSL-X.md` em `VSL-X.spec.json`:

- **cenas:** `{n, persona_key, cena_visual, fala, tipo (expert|ugc|demo), bloco}`.
- **personas:** a expert usa um `master_mediaId` EXISTENTE (rosto travado entre produções); cada depoente ganha master novo com descrição visual + `[VOICE]` próprios (idade/região/tom distintos).
- **SKIP no spec:** prints reais, pares antes/depois, telas de app = inserts de montagem, NÃO se geram no Flow.
- **state:** o driver mantém `spec.json.state.json` com `{img, op, done, failed}` por cena — é isso que torna tudo idempotente e retomável.

## VOZ (crítico — é aqui que a VSL soa nativa ou soa robô)

- Cada pessoa tem um bloco `[VOICE]` **FIXO, idêntico byte a byte em TODO prompt i2v dela**. Mudou uma vírgula = timbre muda entre cenas.
- NUNCA usar voz TTS/preset de entity do Flow (soam artificiais). Entity serve só pra travar ROSTO em imagem.
- Molde de `[VOICE]` com prosódia nativa (adapte idade/gênero/região). ⚠️ O tom-base da expert é **energético e íntimo**, não "calm" — calma é pra 2-3 cenas específicas, pedidas na tag da cena (doc 06 §3e):

```
[VOICE] Native <IDIOMA> speaker, woman in her mid-forties, warm
medium-pitch voice, PERFECT native prosody: correct word stress and
open-closed vowel sounds on every single word, natural sentence melody
with rises and falls like real speech, warm intimate delivery, light
<REGIÃO> accent, natural micro-pauses, absolutely NOT a text-to-speech
cadence, not a narrator voice, no flattened intonation, no word-by-word
rhythm, no foreign accent. The person speaks continuously through the
whole clip with no long pauses. Keep the exact same timbre, pitch,
accent, pacing and speaking style.
```

- Depoentes: sotaques REGIONAIS distintos entre si + tempero leve de vocabulário na copy. É o que faz o bloco de depoimentos parecer gente diferente de verdade.
- (Se você usar ElevenLabs pra alguma narração off, referencie a voz como `<VOICE_ID>` num arquivo de config — nunca chumbada no script.)

## FRAME-ÂNCORA por sessão visual (figurino único, fundo travado)

- **Figurino ÚNICO a VSL inteira** (a menos que a referência modelada mostre troca); o cenário pode variar (mesma casa, mesmo dia), a roupa NUNCA. Fundo IDÊNTICO dentro do mesmo lugar.
- Implementação: 1 t2i por (persona, bloco) = o frame-base; todas as cenas do bloco REUSAM esse frame (jump cuts). Bloco novo em local novo = i2i com o frame-âncora da sessão como referência e o prompt: `"EXACTLY the same clothes, hair and lighting as the reference; change only the location as described, never the clothes."`
- **LUZ pertence ao CENARIO da cena, nunca ao bloco de "realismo" do driver** — um prompt fixo de realismo com "natural window daylight" embutido já produziu blocos diurnos numa VSL noturna sem ninguém pedir.
- Frame de fala = **pose neutra de frente pra câmera, mas VIVA**: *"eyes open looking into the lens as if about to speak, relaxed but ALERT posture, both hands free and visible, shoulders open"*. Nunca lendo, apontando ou segurando objeto (vira tique robótico no i2v). TEXTRULE no t2i: sem telas/eletrônicos/texto legível. 🔴 **Frame morto = bloco inteiro morto**: olhos meio fechados, ombros caídos, mãos escondidas — nada disso se conserta na pós (`06-EDICAO-DINAMICA-OBRIGATORIA.md` §3). E o **enquadramento muda por bloco** (*"DIFFERENT FRAMING FROM THE REFERENCE: closer, from the shoulders up"* / *"wider, the whole room visible"*) — bloco longo ganha um 2º frame-base em close pra alternar.
- **GATE DE FRAMES SEMPRE** (inclusive b-roll): masters → scenes → montar grade numerada → VOCÊ ou um agente de visão confere (anatomia, figurino, orientação, zero moldura de celular, zero texto quebrado) → só então submit. Frame ruim aprovado = bloco inteiro ruim.

## Rodar (o ciclo da fábrica)

```bash
# o MESMO driver dos criativos (scripts/flow_driver.py), rodando DENTRO do browser-harness, fase a fase:
FLOW_PROJECT=<id> SPEC=vsls/VSL-X.json PHASE=masters browser-harness < scripts/flow_driver.py
python3 scripts/gate_frames.py masters          # você aprova o rosto/figurino
FLOW_PROJECT=<id> SPEC=vsls/VSL-X.json PHASE=scenes  browser-harness < scripts/flow_driver.py
python3 scripts/gate_frames.py scenes           # gate visual da grade
FLOW_PROJECT=<id> SPEC=vsls/VSL-X.json PHASE=submit  browser-harness < scripts/flow_driver.py
FLOW_PROJECT=<id> SPEC=vsls/VSL-X.json PHASE=poll    browser-harness < scripts/flow_driver.py   # repetir a cada ~90s
FLOW_PROJECT=<id> SPEC=vsls/VSL-X.json PHASE=retry   browser-harness < scripts/flow_driver.py   # libera as falhadas; volta pro submit
# rodadas: [retry → scenes → submit → poll] até zerar. Se quiser um laço automático, peça pro seu Claude embrulhar
# essas linhas num .sh com vigia (reinicia se cair, e só encerra quando o número de clipes no disco bater com o spec).
```

- **poll** a cada ~90s até resolver. "Nada pendente" ≠ sucesso: significa todos os ops resolvidos (done OU **failed**) — conferir os failed no state antes de seguir.
- Falha aleatória de ~10-30% por rodada é NORMAL na fila low priority → o retry ressubmete só as falhadas (até 3 ciclos).
- **Fail determinístico (mesma cena falha 2x+) = CONTEÚDO**, não azar: nome próprio, celebridade, filtro do Veo (lista abaixo). Reescrever a fala/prompt; retry não resolve.
- Regen pontual (mudou uma fala): editar o `.md` E o spec → no state, limpar `op/done/failed` da cena **MANTENDO `img`** (mesmo frame = mesma identidade, só a fala regrava) → rodar o loop de novo. Só as limpas ressubmetem.
- Throughput de referência: ~180 cenas ≈ 40 min (fila vazia) a ~2h (fila disputada). Submit de 150 cenas ≈ 10 min.

## OS FILTROS DO VEO (a lista paga a sangue — e o contorno de cada um)

| O que bloqueia/quebra | Sintoma | Contorno (troca mínima) |
|---|---|---|
| **Espelho** (pessoa+espelho+corpo) | Render recusado ou bugado | Tirar o espelho do conceito; usar par de fotos antes/depois ou split (doc 04) |
| **Roupa íntima / pele demais** | Recusa | Roupa fitness/casual justa — lê igual em miniatura |
| **Balança DIGITAL** | Display não renderiza (números gibberish) | Balança ANALÓGICA com ponteiro |
| **Celular na mão** | O aparelho não materializa / vira retângulo fantasma | Cortar o prop; tela de app entra como INSERT na montagem |
| **Nome próprio (áudio OU prompt visual)** | Fail em massa — 15/15 cenas | Remover TODO nome; pessoa nomeada só em overlay |
| **Auto-apresentação ("Eu sou...")** | Dezenas de recusas na mesma cena | Narrador/overlay apresenta; ninguém se nomeia em áudio |
| **Celebridade em áudio** | Fail 2x+ | Genérico no áudio ("uma atriz muito querida"); print real carrega o nome |
| **Fala <16 palavras** (a partir de ~14 já é zona de risco) | Clipe metade mudo → recusado (vídeo silencioso) | Alongar a fala pra janela 16-26 |
| **Marca de remédio em áudio** | Recusa intermitente | Categoria genérica ("caneta emagrecedora" → "essas injeções da moda") |
| **Prompt NEGATIVO de anatomia** ("no extra hands") | INVOCA o defeito (3 mãos) | Prompt POSITIVO de pose travada: "both arms stay frozen in the exact position of the first frame; only her face moves while speaking" |
| **Contagem nos dedos em idioma local** | Gesto errado (ou obsceno!) | Prompt em inglês "exactly THREE fingers", mãos abaixo do peito, e QA de mão em todo clipe com contagem |
| **"Margem segura"/safe area no t2i** | Desenha bandas pretas | Nunca instruir margem; compor na pós |
| **Gente aleatória em b-roll** | Flow enfia rosto/selfie mesmo com "NO PEOPLE" | Prompt "ABSOLUTELY NO PEOPLE" + gate; 3 falhas = usar still gateado com ken burns (doc 04) |

Cena de 2 pessoas: "two people clearly separated, ONLY X speaks, the other keeps mouth closed" — e 1 falante por clipe, sempre.

## B-rolls avulsos (impacto/curiosidade — fora do spec)

t2i + i2v direto, prompt de vídeo com `"ABSOLUTELY NO SPEECH, ambience only"` + sem fade. Pessoa visível só dormindo/de costas (boca fechada — senão o Veo inventa fala com a copy). **REGRA: b-roll tem que gerar CURIOSIDADE amarrada na copy do momento** — nunca "vídeo bonitinho". Denso nos 2 primeiros minutos.

## Download + cookie

- Download autenticado por cookie de sessão — **use `scripts/flow_download.py`** (o mesmo dos criativos): ele lê os cookies da aba logada via CDP sozinho, baixa pela rota `media.getMediaUrlRedirect` com o `name` da mídia e valida o tamanho. **Arquivo <1KB baixado = sessão morta**, não clipe — refaça o login no Chrome e rode de novo. Nada de cookie copiado na mão.
- Validar CADA download: tamanho >200KB **e conteúdo** (ver gate de 3 camadas no doc 05 — tamanho sozinho não prova nada).
- Se a rota de download da API mudar (já aconteceu): o fallback universal é baixar POR DENTRO da aba (fetch com `credentials:'include'` via browser-harness) — a auth de página sempre funciona onde o curl com cookie falha.

## Saída desta fase

`VSL-X_clips/cena_N.mp4` completos + state fechado (zero failed) + masters e frames-âncora arquivados. Em paralelo, os assets de prova (doc 04) devem estar prontos — a montagem (doc 05) consome os dois.
