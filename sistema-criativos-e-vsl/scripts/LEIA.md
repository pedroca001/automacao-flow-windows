# scripts/ — os 9 scripts do pipeline de criativos (todos PRONTOS, todos conversam entre si)

Macro local com mouse real: `../flow-macro` (`flow_macro.swift`). Seleciona os
padrões, preenche o prompt e envia pelo botão do Flow. Uso e modos sem geração:
[MACRO-FLOW.md](../MACRO-FLOW.md).

Nenhum destes é "especificação pra você implementar". São os scripts que rodam a leva de ponta a ponta,
com **paths por variável de ambiente** (nada fixo). Seu Claude adapta o `LEVA=` e roda.

## O fluxo (a ordem em que rodam)

```
leva.json  ──gerar_specs.py──▶  specs/AD-01.json …          (copy aprovada → prompts prontos + auto-teste)
           ──flow_driver.py PHASE=masters──▶ frames-âncora   (roda DENTRO do browser-harness, sem clique)
           ──gate_frames.py masters──▶ frames/GRADE-MASTERS.jpg   ← VOCÊ olha os rostos antes de seguir
           ──flow_driver.py PHASE=scenes──▶ frames das cenas
           ──gate_frames.py scenes──▶  frames/GRADE-AD-01.jpg     ← gate visual (Claude descreve cada quadro)
           ──flow_driver.py PHASE=submit / poll──▶ vídeos gerados no Flow
           ──flow_download.py──▶ clips/AD-01_1.mp4 …          (rota getMediaUrlRedirect + cookie via CDP)
           ──gate_clipes.py──▶  GATE-CLIPES.json               (tamanho · SSIM × frame · whisper × fala)
           ──montar_leva.py──▶ finais/AD-01.mp4                (trim → punch-in → gancho SPLIT/INSERT_PRIMEIRO → concat → corte por fala → legenda do ROTEIRO → headline → CTA)
           ──medir_ritmo.py finais/──▶ 🟢/🔴 por ad             (gate de RITMO medido: trocas de estímulo/min, maior plano parado, silêncio, v×a)
```
`voz-unica.py` é da máquina de orgânico (troca a locução de vídeo SEM rosto por uma voz só) — não entra nesse fluxo.

## Cada um, em uma linha

| script | papel | roda onde |
|---|---|---|
| `gerar_specs.py` | `leva.json` (copy aprovada) → `specs/<AD>.json` no formato do driver. Injeta blocos globais (realismo, um-objeto-um-movimento, sem-texto, sem-fade), embute a fala com marcador de voz, e **reprova** placeholder `{ASSIM}`/`{{assim}}`, travessão na fala, persona inexistente. Avisa fala <8 ou >26 palavras e CAIXA ALTA. **Atualização 04:** lê o bloco `gancho` (mecânica SPLIT/INSERT_PRIMEIRO/ACAO/ESTRANHO → cena 1 e, se houver insert, cena 0), o `tipo` de cada cena (T-close/T-aberto/T-3/4/T-cta/D/I/L → enquadramento no prompt), e **avisa** leva parada: sem gancho, sem tipo, 3 tipos iguais seguidos, mecânica dominando, choque baixo, persona repetida (docs 07 e 08). | terminal |
| `flow_driver.py` | o driver do Flow (masters → scenes → submit → poll → retry), idempotente por `state.json`, lane-lock. **Sem clique, sem screenshot.** Doc: `01-CRIATIVOS/06-DRIVER-SEM-CLIQUE.md`. | dentro do `browser-harness` |
| `gate_frames.py` | baixa os frames gerados e monta as GRADES do gate visual (masters: rostos; scenes: linha por ad). | terminal |
| `flow_download.py` | baixa os clipes prontos (`getMediaUrlRedirect` com o `name` da mídia + cookie lido do Chrome via CDP). Valida tamanho. | dentro do `browser-harness` |
| `gate_clipes.py` | gate pós-download, 3 camadas por clipe: tamanho >200KB · SSIM frame-0 × frame-base (<0,5 = clipe cruzado) · whisper × fala do spec (dice <0,60 = fala errada; lixo na cabeça = sílaba fantasma). Normaliza número por extenso↔dígito. | terminal |
| `montar_leva.py` | montagem final: trim por whisper (corta silêncio/fade e a cabeça se o gate acusou) → **punch-in jump-cut** em todo clipe do corpo >4,6s (`PUNCH_IN=0` desliga) → **gancho por mecânica** (SPLIT = vstack pessoa+insert · INSERT_PRIMEIRO = 1,6s de insert e a pessoa entra) → concat por filtro → **corte por fala** (gap entre palavras >0,55s aparado + silêncio >0,3s a -25dB removido; `SEM_APARAR=1` desliga) → legendas ASS com o texto do ROTEIRO (whisper só dá o timing) → faixa de headline (`SEM_HEADLINE=1` pula) → CTA animado nos últimos 10s → 1080x1920/24fps → varredura de moov. `MIN_DUR=60` (pago) / `MIN_DUR=15` (orgânico). Spec antigo monta como antes. | terminal |
| `banner.py` | os elementos de tela que o gerador NUNCA desenha: faixa de headline (quebra por largura MEDIDA), pílula de CTA, seta (polígono, nunca glifo), etiqueta lateral, etiqueta de preço, X vermelho. Módulo do `montar_leva.py` e utilizável direto. | terminal / módulo |
| `voz-unica.py` | orgânico, vídeo SEM rosto: substitui a locução multi-voz por UMA voz de TTS (`edge-tts`), com trava de sincronia. Doc: `05-AVATARES-ORGANICOS/05-LEGENDA-E-VOZ.md`. | terminal |
| `medir_ritmo.py` | **o gate de ritmo medido** (Atualização 04): trocas de estímulo por minuto (scene detect calibrado a 0,05), maior plano sem troca (e onde), silêncios, vídeo×áudio. `python3 scripts/medir_ritmo.py finais/` (criativos: ≥10/min, maior plano ≤9s) · `python3 scripts/medir_ritmo.py vsl.mp4` (VSL: ≥12/min, ≤12s). Sai 1 se reprovar. Docs: `01-CRIATIVOS/08-CRIATIVO-DINAMICO.md` e `02-VSL/06-EDICAO-DINAMICA-OBRIGATORIA.md`. | terminal |

## Variáveis de ambiente que os scripts entendem

| var | quem usa | o que é |
|---|---|---|
| `LEVA=/pasta/da/leva` | gate_frames, gate_clipes, montar_leva | pasta com `specs/`, `clips/`, `frames/` (default: pasta atual) |
| `SPEC=specs/AD-01.json` · `FLOW_PROJECT=<id>` · `PHASE=` | flow_driver, flow_download | o spec e o projeto do Flow (o id da URL) |
| `OUT=clips` · `FLOW_LOCK=~/.flow_lane.lock` | flow_download · driver/download | pasta de saída dos clipes · arquivo do lane-lock (só mude se rodar 2 projetos separados) |
| `WHISPER_MODEL=/caminho/ggml-small.bin` | gate_clipes, montar_leva | modelo do whisper.cpp (`ggml-base.bin` serve pra timing; `small` pra conferência) |
| `FFMPEG=/caminho/ffmpeg` | montar_leva | um ffmpeg **com libass** (o script confere e avisa se não tiver) |
| `FONT_BOLD=` · `FONT_REG=` | banner | força a fonte (default: Arial Black/Arial no Mac, DejaVu no Linux) |
| `MIN_DUR=60` · `SEM_LEGENDA=1` · `SEM_CTA=1` · `SEM_HEADLINE=1` · `CROP_WM=1` | montar_leva | mínimo de duração pra avisar · pular legenda · pular CTA · pular faixa de headline · cortar marca-d'água |
| `PUNCH_IN=0` · `PUNCH_MIN=4.6` · `PUNCH_Z=1.12` · `SEM_APARAR=1` | montar_leva | desligar/ajustar o punch-in · desligar o corte por fala/silêncio |
| `MODO=vsl\|criativo` · `LIMIAR=0.05` · `MIN_TROCAS=` · `MAX_PLANO=` · `JSON=1` | medir_ritmo | régua do gate de ritmo (defaults calibrados em produção aprovada) |
| `LANG_FALA=pt` · `SEM_WHISPER=1` | gate_clipes | idioma da fala (default: o do spec) · pular camada 3 |

## Formato de entrada (`leva.json`) — o que o seu Claude escreve depois da copy aprovada

Está documentado no cabeçalho do `gerar_specs.py` (personas com `descricao_visual`/`cenario`/`voz`; itens com `id`, `headline`,
`header_estilo`, **`gancho{mecanica, persona, acao_visual, insert_visual?, gancho_fala}`**, `cenas[n, tipo, persona, acao, fala, prompt_video_custom?]`). Um exemplo completo pronto pra rodar — e que é o **modelo de leva DINÂMICA** (gancho de choque + corpo T/D/I/L + persona/cenário marcantes): `scripts/exemplo-leva.json`. Copie a estrutura, nunca o conteúdo. Pra orgânico, a identidade do avatar (`avatares.json`) tem exemplo em `scripts/exemplo-avatares.json`.

Detalhe útil: o `n` das cenas aceita fração (`2.5`) — pra inserir uma cena entre duas sem renumerar; o driver nomeia `AD-01_2.5.mp4` e a montagem ordena por número. O `n=0` é reservado ao insert do gancho e o `n=1` ao gancho.

## E a VSL?
Os clipes da VSL usam os MESMOS `flow_driver.py`/`gate_frames.py`/`flow_download.py`/`gate_clipes.py`. A **montagem** da VSL tem implementação de referência própria em `02-VSL/scripts-referencia/montar_vsl.py` (lê o plano de edição `exemplo-plano-edicao.json`: split, cutaway, insert com ken burns, par antes/depois, flash, RVM, zoom, punch-in automático, xfade, legendas, overlays, QA) — ver `02-VSL/06-EDICAO-DINAMICA-OBRIGATORIA.md`. O `medir_ritmo.py` fecha as duas máquinas.

## Requisitos

Extensão local para receitas no Flow: `../FLOW-NOTURNO.md`. Os atalhos de
preparo, início e parada usam `retomada-macro/noturno.py`: fila persistente,
macro nativo, duas abas, falhas isoladas e relatório final sem gate manual.
As montagens são validadas tecnicamente e ficam pendentes de revisão visual.
Esse modo mantém os scripts e gates do fornecedor para a produção acompanhada.

`python3` + `Pillow` · `ffmpeg`/`ffprobe` (com libass pra legenda) · `whisper-cli` + modelo ggml · `curl` · `browser-harness` (só driver/download) · `edge-tts` (só voz-unica).
Teste rápido de que está tudo instalado: `bash scripts/verificar-pacote.sh` (arquivos) e `python3 scripts/gerar_specs.py scripts/exemplo-leva.json` (gera specs de exemplo em `scripts/specs/` — pode apagar depois).
