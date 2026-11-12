# 05 — MONTAGEM E QA (o pipeline completo + as 5 camadas de conferência)

> Aqui os ~150 clipes + assets viram UM arquivo: download, trim por whisper, cutaways, inserts, pares, concat, legendas queimadas, overlays de preço — e depois o QA em 5 camadas que garante que você recebe uma VSL assistível, não um rascunho. Fluidez é o critério nº 1: **zero silêncio >1.0s, a VSL nunca para de falar.**

O comando pro seu Claude:

```
Leia 02-VSL/05-MONTAGEM-E-QA.md e 04-EDICAO-AVANCADA.md. Monte a VSL:
download dos clipes, trim whisper com PAD 0.25, aplica DEMOS/INSERTS/
PARES/RVM conforme o plano, concat com a intro, legendas ASS, overlays.
Depois rode o QA completo das 5 camadas e me traga o relatório antes
de eu assistir.
```

> 🔴 **Atualização 04:** a ORDEM abaixo agora tem implementação de referência — `scripts-referencia/montar_vsl.py`, que executa o **plano de edição** (`06-EDICAO-DINAMICA-OBRIGATORIA.md` §4, modelo em `scripts-referencia/exemplo-plano-edicao.json`): split, cutaway, insert com ken burns, par, flash, RVM, zoom, punch-in automático, xfade de bloco, legendas, overlays e QA objetivo. Adapte-o; não escreva a montagem do zero (a montagem "do zero" vira concat + legenda = VSL parada). E feche com `scripts/medir_ritmo.py` (≥12 trocas/min).

## O pipeline de montagem (na ordem)

```
0. DOWNLOAD      cookie fresco → curl/fetch por cena → validar >200KB E conteúdo
1. TRIM WHISPER  whisper-small acha o fim da última fala por clipe → corta ali + PAD 0.25s
1b. PUNCH-IN     todo plano falado >4,6s sem outro efeito: 2ª metade com zoom fixo 1,12 (ritmo de ~3s das VSLs editadas à mão)
2. CUTAWAYS      demos mudas cobrem o início do clipe falado alvo (áudio contínuo; crossfade 0,20 nas pontas)
3. INSERTS       prints/página editorial/telas de app → clipe 5s ken burns → cutaway
4. PARES         slides antes/depois 5s (wipeleft) sobre a fala da própria depoente
5. RVM/SPLITS    técnicas do doc 04 substituem as cenas marcadas
6. CONCAT        intro de impacto substitui as cenas 1-N → normalizar 1080x1920/24fps → concat
7. LEGENDAS      whisper no áudio final → alinhamento com o roteiro → ASS → burn (libass)
8. OVERLAYS      PNGs de preço/nome/bônus/chat/CTA com enable='between(t,a,b)'
9. QA            as 5 camadas abaixo
```

Detalhes que fazem diferença:

- **Trim (passo 1): silencedetect NÃO funciona nos clipes do Veo** — o ruído ambiente que o modelo gera fica acima de -30dB, então o detector "não vê" silêncio nenhum. **O whisper é o detector de fim de fala:** transcrever cada clipe com o modelo SMALL, pegar o timestamp do fim da última palavra, cortar ali + **PAD de 0.25s**. Cache em `_work/_trim_whisper.json` (re-rodadas ficam instantâneas).
- Cena com fala curta que o whisper não fecha direito: retrim manual (`--retrim=N:1.75`) — e **REAPLICAR os retrims manuais conhecidos após qualquer wipe do work/**.
- **Wipe à prova de shell:** `find work -name "cena_*.mp4" -delete`. No zsh, `rm` com múltiplos globs MORRE se UM não casar → wipe silenciosamente incompleto → clipe velho na montagem (bug pago). Conferir que o wipe wipou.
- **Curadoria:** `CORTADAS = {n, ...}` — cenas redundantes saem do concat sem apagar clipes (reversível). Cortar redundância sem dó é parte do padrão.
- Cadeias longas de bash: SEMPRE `&&` entre passos — sem isso um passo falha, o seguinte roda com artefato velho e o erro passa silencioso.
- Downloads: **conferir CONTEÚDO, nunca só tamanho** — um servidor pode salvar uma página de erro HTML com nome de .mp4. `file clipe.mp4` + ffprobe abrem em 1s.

## Legendas ASS (os números validados)

Blocos de **3-4 palavras** por evento (nunca frase inteira), alinhados por `difflib.SequenceMatcher` entre as palavras do whisper (com timestamps) e as palavras do ROTEIRO (a grafia oficial vem do roteiro; o tempo vem do whisper — melhor dos dois mundos). Estilos validados com público 45+:

| Canvas | Fonte | Tamanho | Outline | MarginV | Cor |
|---|---|---|---|---|---|
| **3:4 (1080x1440)** | Arial | **54** | 3 | **104** | branca ou amarela |
| **9:16 (1080x1920)** | Arial | **66** | 3 | **220** | **amarela** (&H0000FFFF) |

Linha de estilo ASS de referência (9:16): `Style: Default,Arial,66,&H0000FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,30,30,220,1` com `PlayResX: 1080 / PlayResY: 1920 / WrapStyle: 1`. Snippet completo de geração em `scripts-referencia/legendas_ass.py`.

Queima com ffmpeg + libass (`-vf "ass=arquivo.ass"`). Se o seu ffmpeg veio sem libass, compilar/baixar um binário estático com libass e usar só pra queima. Whisper BASE serve pro srt de legenda (rápido); QA de fala usa SMALL (o base mente — ver camada 2).

## Overlays PNG (preço, nome, bônus, chat, CTA)

- PNGs 1080x1920 gerados em PIL no estilo visual do SEU funil (cores/fonte da página de vendas — o vídeo e a página têm que parecer a mesma marca).
- **Preço no TOPO do quadro (y≈90) — NUNCA sobre o rosto** (2 posições reprovadas até virar lei). Alternativa validada: zona do PEITO (y≈1120-1400 em 1080x1920) em card arredondado semi-transparente, 2 tamanhos de fonte por card.
- Preço SAI de tela antes do CTA ENTRAR (nunca sobrepor os dois). Setas de CTA acima da zona de legenda. Nome da expert = lower-third. FAQ = bolhas de chat (avatar de inicial + nome).
- **Sem emoji em PNG gerado por PIL** — fonte sem glifo vira tofu (▯). Texto puro ou desenhar o ícone.
- Aplicação: calcular o start real de cada cena SOMANDO as durações dos works (nunca estimar) e aplicar `overlay=enable='between(t,ini,fim)'`.
- Timestamp de cada overlay vai num mapa (`overlays.json`) — o QA da camada 5 confere um frame em CADA um.

## QA EM 5 CAMADAS (nenhuma é opcional)

### Camada 1 — Roteiro (antes de gerar)
Greps de compliance do doc 02 + review brutal por segundo agente + TRIAGEM (nem toda sugestão se acata — padrões validados do nicho o revisor não conhece).

### Camada 2 — Fala por clipe (pós-download)
Whisper-**SMALL** por clipe vs a fala do spec:
- **dice(bag of words) ≥ 0.62** E primeira palavra presente E última palavra presente (o teste de pontas pega TRUNCAMENTO que o dice deixa passar).
- Falso positivo clássico: números ("vinte e um" → "21") e grafias de termo técnico. LER o transcript antes de mandar regerar.
- Este passo também pega **colisão de op** (clipe com fala de OUTRA cena — doc 03): irmãos do mesmo bloco têm frame-0 idêntico, então a colisão é INVISÍVEL no gate visual; só o whisper por clipe pega. Complemento: SSIM do frame-0 vs frame-base (<0.5 = clipe de outra sessão).
- Meta: 100% das cenas OK antes de montar.

### Camada 3 — QA visual dos últimos frames
Extrair o último frame de cada clipe trimado → grades numeradas 5x4 → inspecionar TODAS (você ou agente de visão):
- Boca aberta no corte / olhos fechados → retrim fino (`--retrim=N:0.13` com PAD 0.25).
- Fantasma/dupla exposição/transição "assada" pelo Veo em cima do fim da fala → **patch_freeze**: congela o último frame LIMPO (-0.6s) e o áudio segue por cima. Zero risco de comer palavra.
- Teimosas pós-retrim → freeze também. Re-extrair os frames das corrigidas e conferir de novo. Só fecha com zero flag.
- Detalhe técnico: frame de clipe com tpad/freeze falha ao extrair JPG ("Non full-range YUV") → extrair PNG com `-sseof -0.4`.

### Camada 4 — Watch completo por agente de visão
Um agente que LÊ vídeo assiste a VSL inteira e reporta por timestamp (subagente com frames densos + transcript, ou um modelo de vídeo via CLI). **TRIAGEM OBRIGATÓRIA:** esses agentes cruzam com whisper-base, que MENTE em texto fino — confirmar CADA achado de fala com whisper-SMALL no clipe antes de "corrigir". Caso real: 40+ achados reportados → 6 reais. Os freezes de 0.6s aparecem como "frame congelado" — são os patches deliberados da camada 3, ignorar.

**Complemento cirúrgico:** grade de momentos fixos NÃO cobre efeito pontual (overlay de preço de 4s, depoimento de 8s, gesto de 2s). Extrair um frame no timestamp esperado de CADA efeito do mapa de overlays + rodar whisper na REGIÃO do preço/CTA do arquivo final.

### Camada 5 — Sinais objetivos finais
- **Silêncio: `silencedetect=noise=-37dB:d=1.0` no MP4 final → ZERO ocorrências.** (No arquivo FINAL o silencedetect volta a funcionar — o que ele não pega é fim de fala DENTRO de clipe cru do Veo; aí o whisper manda, passo 1.) 1.6s é o teto absoluto de tolerância; a meta é zero acima de 1.0s. Sobrou gap? Rodar um "apara-gaps" no concat (corta os silêncios, desloca as legendas, re-queima).
- Duração bate com a planejada; frames-chave extraídos e conferidos: intro cheia no frame 1, pares sobre a depoente CERTA, preço fora do rosto, CTA fora da zona de legenda, iluminação consistente.
- Você assiste → feedback → leva de ajuste CIRÚRGICA (só regera o necessário; backups `_alvoN` no work tornam tudo reversível). 2-3 rodadas é o normal até o 100%.

## FRONT × UPSELL (mesmo motor, estes deltas)

A engenharia (geração, montagem, QA) é IDÊNTICA. O que muda:

| Aspecto | FRONT | UPSELL |
|---|---|---|
| Abertura | Hook frio (pergunta + mecanismo estranho) | "Seu pedido está quase pronto... NÃO feche esta página" (candado) |
| Duração | 15-25min | **7-10min** (~65-70 cenas) — SEMPRE nesta janela |
| Preço | NUNCA falado; card em tela | **PODE ser falado** (já é comprador); ancoragem menor |
| Estrutura | ~14 blocos (escada completa) | Bem-vindo → recap do sonho → gap → nova peça do quebra-cabeça → prova → pitch → garantia → CTA |
| Formato | 9:16 nativo (+3:4 opcional) | **3:4** (crop central do 9:16) |
| Intro de impacto | SIM (doc 04-f) | Opcional (o candado já segura a atenção) |
| Depoentes | 3+ (uma por dor) + pares | 1 fixa com par próprio |

Regras que NÃO relaxam no upsell: falas 16-26 palavras · nunca nome/celebridade em áudio · "a expert calibra" (nunca automático) · pares mesma pessoa + gate de contraste · trim whisper PAD 0.25 · QA 5 camadas · zero silêncio.

**Versão 3:4 a partir do 9:16:** center-crop do PROCESSED (1080x1920 → 1080x1440) — **NUNCA do FINAL** (legendas e overlays já queimados ficariam cortados). Re-queimar legendas no canvas 1440 (Arial 54 / MarginV 104) e regenerar os overlays pro canvas novo. O áudio é idêntico → os tempos de overlay se recalculam dos mesmos works.

## Saída

```
VSL-X-FINAL-OV.mp4      ← o arquivo que você assiste e aprova
VSL-X.md                ← roteiro com ajustes de produção comentados
specs/ clips/ inserts/ _par/ _work/   ← bastidor (regen pontual barata pra sempre)
overlays.json           ← mapa de efeitos (o QA da próxima leva usa)
```

Aprovou? O arquivo vai pro seu player de vídeo/página de vendas. O bastidor fica: qualquer ajuste futuro (preço novo, fala nova, corte) é regen pontual de minutos, não reprodução.
