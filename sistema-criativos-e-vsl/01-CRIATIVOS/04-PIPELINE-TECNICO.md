# 04 — PIPELINE TÉCNICO (Flow via browser-harness + montagem ffmpeg)

> **Para quem é este doc:** principalmente pro SEU Claude. Você (operador) precisa entender o desenho geral e os pontos onde as coisas quebram; o Claude executa. Ele descreve como operar o Google Flow por automação de navegador, como baixar os clipes, e como o ad final é montado no ffmpeg.
>
> 🔴 **Antes de escrever qualquer driver, leia `06-DRIVER-SEM-CLIQUE.md`.** Ele traz a mecânica exata (com o código de referência em `scripts/flow_driver.py` e `scripts/flow_download.py`) e derruba o erro mais caro de todos: achar que o reCAPTCHA obriga a automação a CLICAR na tela pra GERAR. Não obriga — produção não clica pra gerar. 🔴 **Atualização set/2026 nº2:** o Google ligou o reCAPTCHA e o mint direto do token virou `UNUSUAL_ACTIVITY`; o driver agora **colhe** o token do app (um toque-isca abortado que não gera nada). Isso já está no `flow_driver.py` — **não reverta pro mint direto.** Detalhes no 06.

## Visão geral

```
SPEC.json
   │
   ▼
┌─────────────────────────────────────────────────────────────┐
│ DRIVER DO FLOW (roda dentro do browser-harness)             │
│                                                             │
│  PHASE=masters  → Nano Banana 2 (GEM_PIX_2): 1 frame-âncora │
│                   por persona                               │
│  PHASE=scenes   → img2img com referência do master: frames  │
│                   de todas as cenas                         │
│       🚦 GATE DE FRAMES (humano olha a grade)               │
│  PHASE=submit   → i2v veo_3_1_i2v_lite_low_priority         │
│                   (fala embutida no prompt; custo zero)     │
│  PHASE=poll     → checar status até done                    │
│  download       → URL assinada do poll (as29s), sem cookie  │
└─────────────────────────────────────────────────────────────┘
   │  clips/*.mp4 (8s cada)
   ▼
┌─────────────────────────────────────────────────────────────┐
│ MONTAGEM (ffmpeg local)                                     │
│  trim por whisper → concat por filtro → legendas ASS →      │
│  faixa de headline (PIL) → CTA animado últimos 10s →        │
│  crop marca-d'água → 1080x1920 → AD-FINAL.mp4               │
└─────────────────────────────────────────────────────────────┘
```

---

## PARTE 1 — OPERANDO O FLOW

### Setup (uma vez por produto)

1. Chrome logado na conta Google com assinatura Ultra; abrir **flow.google.com** e criar um projeto pro produto (contas ainda não migradas caem em labs.google/flow — os scripts atuais falam o protocolo novo; se a sua conta ainda estiver no domínio velho, ela vai migrar sozinha em breve). O ID do projeto está na URL — o driver usa esse ID pra achar a aba certa.
2. A aba do Flow fica ABERTA em segundo plano. O browser-harness se conecta a ela via CDP **sem nunca ativá-la/focá-la** — se você estiver usando o computador, a automação não pode roubar seu foco (attach à aba sem `activateTarget`).
3. Os modelos usados:
   - **Imagem:** `GEM_PIX_2` (Nano Banana 2) — masters e frames de cena. Se estourar quota, os fallbacks internos do Flow assumem.
   - **Vídeo:** `veo_3_1_i2v_lite_low_priority` — image-to-video de 8s, 9:16, com FALA nativa embutida no prompt. Na fila de baixa prioridade **não consome créditos**; o preço é esperar a fila (30 min a 3h em horário de pico). É o coração do custo-zero.

### As regras de ouro da operação (cada uma custou uma madrugada)

**🔴 1 SUBMITTER POR ABA, SEMPRE.** O driver usa variáveis globais da janela (`window.__*`) pra transportar respostas das chamadas. Dois processos submetendo na MESMA aba leem a resposta um do outro → os IDs de operação se cruzam no estado → você baixa um clipe com a FALA DE OUTRA CENA (ou de outra produção inteira). O gate visual NÃO pega quando as cenas compartilham o frame-base — só o whisper por clipe pega. Antes de submeter: conferir que nenhum outro driver/processo usa a aba (`ps aux | grep <driver>`; matar zumbis). Um worker "morto" pode estar vivo.

**🔴 LANE-LOCK via flock.** Se duas produções podem rodar em paralelo na mesma máquina, todo script que toca a aba do Flow (submit E download) abre um arquivo de lock compartilhado e faz `fcntl.flock(LOCK_EX)` no início. Quem chega segundo BLOQUEIA até o primeiro terminar. A sessão CDP do harness é global — sem o lock, scripts concorrentes trocam a aba um do outro.

```python
import fcntl
_LOCK = open(os.path.expanduser("~/.flow_lane.lock"), "a")
print("aguardando lane do Flow...", flush=True)
fcntl.flock(_LOCK, fcntl.LOCK_EX)   # liberado automaticamente no exit
```

**🔴 Download pela URL ASSINADA que o próprio poll devolve.** (Set/2026 — protocolo novo do `flow.google.com`.) O poll do vídeo (RPC `as29s`) devolve, junto com o status, uma URL assinada `flow-content.google/video/<id>?Expires=...&Signature=...`. Essa URL é pública enquanto vale (~horas): basta pedi-la de dentro da aba e baixar o arquivo por fora — sem cookie, sem base64, sem chunks:

```
POST /_/AiSandboxAngularFrontend/data/batchexecute?rpcids=as29s   (de dentro da aba logada)
→ a resposta traz a URL assinada — ela vem com ESCAPES (= etc.); desfazer antes de usar,
  senão a URL sai cortada em "?Expires" e dá 403
→ baixar a URL direto no disco (urllib/curl, SEM cookie)
```

A URL expira — por isso o `flow_download.py` SEMPRE pede uma URL fresca na hora de baixar, nunca reusa URL guardada. **As rotas antigas morreram todas na migração:** `media.fetchMedia` (400 INVALID_ARGUMENT) e `media.getMediaUrlRedirect` (no domínio novo devolve o HTML do app em vez do vídeo). `Unexpected token '<'` em qualquer chamada = script antigo falando com a plataforma nova — não é sessão expirada nem saldo. E a lei "requisição nasce dentro da aba" vale pro SUBMIT (reCAPTCHA); o download da URL assinada não tem captcha.

**🔴 Estado em disco, idempotente.** O driver salva `SPEC.json.state.json` com o mediaId/operação de cada persona e cena. Qualquer fase re-rodada PULA o que já existe. Sessão de agente é descartável; o state não — qualquer Claude novo retoma de onde parou só lendo o disco.

**Outras regras de operação:**
- Poll: o status da geração fica ANINHADO no metadata da mídia (`mediaGenerationStatus`), não no campo `status` de topo — e a API devolve um placeholder de vídeo imediatamente que NÃO significa pronto. Só baixar com status SUCCESSFUL.
- Falha transiente do Veo (de ~5% em hora boa a 10-30% em hora cheia — planeje o retry): reenviar a MESMA cena isolada, 1x — quase sempre passa. 3 retries e desiste (aí o problema é conteúdo, ver doc 05).
- reCAPTCHA 403 esporádico no submit: esperar 20s e reenviar.
- Timeout esporádico do harness (poucos em centenas de gerações): re-rodar a mesma fase (o driver é idempotente). Não investigar.
- Upload de imagem de referência real (foto sua, frame aprovado): **NÃO existe mais endpoint de upload por script.** No `flow.google.com` você sobe a foto **pela própria tela do Flow** (botão **"+" → "Enviar mídia" → escolhe o arquivo**) — isso funciona normalmente. A foto vira uma mídia comum com um `mediaId`; pegue esse `mediaId` (rode `python3 scripts/flow_foto_id.py`) e coloque em `personas.<key>.master_mediaId` no spec: o driver reusa como referência i2i, igual a um frame já existente. Passo a passo em **`01-CRIATIVOS/10-FOTO-PROPRIA.md`**. (No fluxo normal você **não precisa** subir foto — o `masters` gera o rosto da persona a partir do prompt.)
- Todo download valida `size > 200KB` — arquivo de 14 bytes/HTML = sessão expirada, renovar e repetir.

### Os scripts do pipeline (a pasta `scripts/` — TODOS vêm prontos no pacote)

Não é especificação: é código rodando. Paths por variável de ambiente (`LEVA=`, `WHISPER_MODEL=`, `FFMPEG=`), nada fixo. O mapa completo, o fluxo e as variáveis estão em **`scripts/LEIA.md`**; o formato de entrada está no cabeçalho do `gerar_specs.py` e num exemplo pronto (`scripts/exemplo-leva.json`).

| Script (arquivo real em `scripts/`) | Papel |
|---|---|
| `gerar_specs.py` | Gera os `specs/<AD>.json` a partir da copy aprovada (`leva.json`). Define personas (descrição visual **byte-idêntica** em todas as cenas — é o que trava rosto/roupa), cenas, blocos globais (POSERULE/TEXTRULE/REALISMO/NOFADE) e a fala embutida com marcador de voz. **Termina SEMPRE com o auto-teste de placeholder** (`{ASSIM}`/`{{assim}}` em qualquer campo = reprova e não escreve nada — placeholder não-substituído já custou 2 rodadas de re-roll). Reprova travessão na fala; avisa fala <8 (cena muda), <16 (risco de metade muda), >26 palavras (não cabe) e CAIXA ALTA; e os avisos de dinâmica (gancho/tipo/variedade). |
| `flow_driver.py` (o driver) | Roda DENTRO do browser-harness. `FLOW_PROJECT=<id> SPEC=<path> PHASE=masters\|scenes\|submit\|poll\|retry`. Acha a aba do Flow, chama t2i/i2v pela API de dentro da aba logada, salva o `state.json`, idempotente, lane-lock. **Sem clique, sem screenshot** (doc 06). |
| `gate_frames.py` | Baixa os frames gerados e monta as GRADES do gate visual (masters: todos os rostos; scenes: linhas=ads, colunas=cenas). É o que você olha antes do submit. |
| `flow_download.py` | Baixa os clipes prontos pela URL assinada que o próprio poll devolve (pedida FRESCA de dentro da aba, baixada por fora sem cookie). Valida tamanho. Lane-lock também. |
| `gate_clipes.py` | O gate pós-download de 3 camadas por clipe: size > 200KB · SSIM do frame-0 contra o frame-base (<0.5 = clipe cruzado/errado) · whisper do clipe vs fala do spec (dice <0.60 = colisão) + detecção de lixo na cabeça (sílaba fantasma). Normaliza números por extenso↔dígito antes de comparar (whisper escreve "30" onde o roteiro diz "trinta" — sem normalizar, clipe perfeito reprova). Escreve `GATE-CLIPES.json`, que a montagem lê. |
| `montar_leva.py` | A montagem final (Parte 2 abaixo, em código): trim por whisper → concat por filtro → legendas ASS com o texto do ROTEIRO → faixa de headline → CTA animado nos últimos 10s → 1080x1920 → varredura de moov. |
| `banner.py` | Desenha a faixa de headline em PIL (largura = a MESMA do vídeo, 1080; quebra de linha por largura MEDIDA), a pílula de CTA, a seta (polígono), etiquetas laterais e de preço, X vermelho. Módulo do `montar_leva.py`. |
| `voz-unica.py` | (máquina de orgânico) troca a locução de vídeo SEM rosto por UMA voz de TTS. Doc: `05-AVATARES-ORGANICOS/05-LEGENDA-E-VOZ.md`. |

> A casa também tem uma variante desse pipeline em Node (driver com retry automático + montadores ffmpeg + gerador de legendas). Ela **não vem no pacote** de propósito: depende do resto de um servidor interno e não roda solta. Os scripts Python acima cobrem **os mesmos papéis**, ponta a ponta — não falta nada pra produzir a leva.

---

## PARTE 2 — MONTAGEM NO FFMPEG

A sequência da montagem, clipe a clipe:

### 1. Trim por whisper (por clipe)
Cada clipe de 8s tem silêncio sobrando no fim (e o Veo faz um crossfade fantasma nos últimos ~0,5s). Transcrever cada clipe com whisper (timestamps), cortar logo depois da última palavra — mata o silêncio E o fade num golpe só. Quando a fala vai até o fim e o corte clipa a última palavra: override manual do ponto de corte daquele clipe (arquivo `trim_overrides.json`).

### 1b. Punch-in jump-cut (Atualização 04 — ligado por padrão no `montar_leva.py`)
Todo clipe do CORPO > 4,6s é cortado no meio e a 2ª metade entra com zoom fixo 1,12 (crop + scale; áudio intocado). É o corte de ~3s das VSLs editadas à mão, sem trocar conteúdo. O gancho (clipe 1) fica inteiro. `PUNCH_IN=0` desliga. Doc: `08-CRIATIVO-DINAMICO.md` §4.

### 1c. Gancho por mecânica (Atualização 04)
Se o spec tem `gancho.mecanica` (vindo do `gerar_specs.py`): **SPLIT** = clipe 1 (pessoa) em cima + clipe 0 (insert) embaixo, `vstack`, áudio da pessoa · **INSERT_PRIMEIRO** = 1,6s do clipe 0 (áudio a 25%) e o clipe 1 entra já falando · **ACAO/ESTRANHO** = o clipe 1 é o gancho. Doc: `07-GANCHOS-DE-CHOQUE.md` §2 e §7.

### 2. Concat por FILTRO (nunca por demuxer)
```
-filter_complex "...concat=n=<N>:v=1:a=1..."  (normalizando fps=24, SAR e formato)
```
O concat demuxer quebra com clipes de fps/timebase diferentes — sintoma clássico: o vídeo congela depois da cena 1 e só o áudio continua. Concat por filtro normaliza tudo. Opcional: micro-transição de 0,15s (xfade + acrossfade) no lugar do corte seco, elimina qualquer respiro nas emendas.

### 2b. Corte por FALA + silêncio (Atualização 04)
Depois do concat: gap entre duas PALAVRAS > 0,55s (whisper por palavra, modelo small) é aparado pra ~0,30s de respiro; depois `silencedetect` a -25dB remove qualquer silêncio > 0,3s em loop. É o que separa "gente falando" de "IA esperando o próximo prompt". Roda antes da legenda, então nada precisa ser deslocado. `SEM_APARAR=1` desliga.

### 3. Legendas ASS queimadas
- Texto = o ROTEIRO (do spec), nunca a transcrição do whisper (whisper erra palavras; legenda errada = ad morto). O whisper só dá o TIMING.
- Blocos de **3-4 palavras**, nunca 3 linhas de texto parado.
- Estilo validado: fonte grossa ~54-66px, amarela com contorno preto, terço inferior.

### 4. Faixa de headline no topo (PIL)
- Faixa de cor SÓLIDA cheia, borda a borda, texto bold — não card flutuante arredondado.
- A cor ALTERNA a cada ~3 ads da leva (vermelho/branco → amarelo/preto → ...) pra leva não parecer um ad só no feed.
- **Quebra de linha por LARGURA MEDIDA em pixels** (`textbbox` do PIL), reduzindo a fonte até caber em 2 linhas de ~1000px. Quebrar por contagem de caracteres = headline sangrando pra fora da faixa (o "M" ocupa 3x o "I").
- **Nunca digitar glifos/símbolos (➔ ⬇ ✅) em fonte de sistema** — muitas fontes bold não os têm e sai uma CAIXA VAZIA (tofu) no vídeo final. Símbolo = desenhar em PIL (polígono) ou não usar.

### 5. CTA animado nos últimos 10s
Elemento de CTA ("TOQUE E ASSISTA") entrando nos últimos ~10s, animado via expressão de tempo no próprio overlay do ffmpeg (`y='if(...)'`) — matematicamente suave, zero jitter. Keyframes discretos tremem.

### 6. Crop da marca-d'água
O Veo assina o canto do vídeo. Crop leve + re-scale remove (ex.: `crop=792:1408` numa área central + scale de volta). Se usar imagem de referência externa com marca-d'água de outro gerador, limpar ANTES de animar.

### 7. Normalizar 1080x1920
Saída final SEMPRE 1080x1920, fps 24, `yuv420p`. Conteúdo 1:1 ou 16:9 entra por crop-to-cover — **nunca esticado**.

### 8. Varredura final anti-corrupção
```bash
for f in *-FINAL.mp4; do ffprobe -v error "$f" || echo "CORROMPIDO: $f"; done
```
Montagem morta por timeout deixa um MP4 com TAMANHO NORMAL mas sem o `moov atom` — o arquivo aparece no `ls`, bonito, e não abre em player nenhum. A entrega de leva TERMINA com essa varredura; e montagem longa roda em background, nunca num comando com timeout curto.

---

### 9. Gate de RITMO medido (Atualização 04)
`python3 scripts/medir_ritmo.py finais/` — trocas de estímulo por minuto (scene detect calibrado a 0,05), maior plano sem troca, silêncio, vídeo×áudio. Régua de criativo: ≥ 10/min e maior plano ≤ 9s (os "melhores até hoje" mediram 14-16/min e 7-8s). Reprovou = volta ao plano da leva (doc 08 §6), não sobe.

## PARTE 3 — PIPELINE B: ADS PROGRAMÁTICOS (HTML → PNG → ffmpeg, custo $0)

O segundo motor do módulo — pra formatos de UI onde o texto precisa ser pixel-perfect. **Programar o ad em vez de gerar**: você escreve um HTML que desenha a tela, tira screenshot com o Chrome headless, e anima com ffmpeg. IA nenhuma escrevendo texto = zero texto quebrado.

**Render:**
```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new \
  --disable-gpu --screenshot=out.png --window-size=1080,1920 --hide-scrollbars \
  file:///caminho/do/ad.html
```

**Animação:** o JS do HTML lê `?n=` da URL e mostra N estágios (mensagens aparecendo uma a uma) → 1 screenshot por estágio → ffmpeg concat com `duration` por frame + `fps=24,format=yuv420p`. Sons de UI (pop de mensagem) direto no ffmpeg: `sine=frequency=1050:duration=0.09` + afade, agendado com `adelay`+`amix`.

**Os 10 arquétipos de UI** (o seu Claude escreve o HTML/CSS de cada um a partir da descrição — não vêm arquivos prontos; são ~40-80 linhas cada, é trabalho de minutos):
1. **iPhone Notes** — a "anotação encontrada" (confissão, receita, lista)
2. **Conversa de WhatsApp** — estática ou animada mensagem a mensagem
3. **Lockscreen/alarme** — a notificação que conta a história
4. **Us-vs-them** — tabela de 2 colunas (quem faz X vs quem faz Y)
5. **Press card** — "manchete" de portal com foto e headline
6. **Listicle** — "os 3 erros que..." em card numerado
7. **Review card** — avaliação 5 estrelas com texto de depoimento
8. **Post-it** — o recado manuscrito (fontes nativas do sistema: "Bradley Hand"/"Marker Felt")
9. **Nota de voz com waveform** — o áudio "vazado" com barra de progresso animada
10. **Endcard** — o cartão final de CTA da marca

**Gotchas do Pipeline B:**
- Glifos de sistema proprietários (SF Symbols) não renderizam no headless → usar emoji/texto.
- QA visual do PNG SEMPRE (o Claude lê a imagem) — conteúdo cortado atrás de um botão fixo = refazer, nunca deixar clipping.
- **Zoompan em resolução nativa TREME.** Pré-escalar o still pra ≥3x (3240px+) antes do zoompan, incremento `z='zoom+0.0006'`, fps=24 — movimento lento e imperceptível.
- Fundo com drift (estrelas, partículas): 2-3 keyframes + crossfade lento, nunca zoompan.
- VO narrada por cima (quando o formato pede): ElevenLabs multilingual (~$0,01/frase) ou voz do Veo num clipe base; duração de cada estágio = duração REAL do áudio (ffprobe), nunca chutada.

## O prompt que dispara uma leva de produção

```
Leia 01-CRIATIVOS/04-PIPELINE-TECNICO.md e 05-QA-E-LEIS.md. Os specs da leva
estão em criativos/LEVA-<data>/specs/. Execute: masters → me mostre a grade
de rostos → (após meu OK) scenes → me mostre a grade completa → (após meu OK)
submit → poll → download com gate de clipes → montagem → QA 3 camadas →
me entregue os finais com o relatório de QA. Produza em lotes de 3 ads.
Se o contexto encher no meio, escreva o estado em BASTAO.md e me avise
pra abrir uma sessão nova que retoma do state.
```
