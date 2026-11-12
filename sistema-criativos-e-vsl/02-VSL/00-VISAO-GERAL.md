# MÓDULO VSL — VISÃO GERAL

> **O que este módulo entrega:** uma fábrica de VSL completa que roda dentro do SEU Claude Code. Você entrega 1 VSL de referência (um arquivo .mp4 ou um link) — o Claude faz a engenharia reversa dela (transcrição, contagem de cortes, leitura visual frame a frame), extrai o mapa de blocos e a escada de crenças, escreve um roteiro NOVO modelado (transplante de estrutura, não tradução), gera todos os clipes no Google Flow com custo de geração ~zero, produz os assets de prova, e monta o vídeo final com edição avançada: antes/depois, tela dividida, expert recortada com fundo transparente sobre a prova, primeiro minuto de impacto, legendas queimadas. Com QA em 5 camadas antes de você assistir.

## Como usar esta pasta

Jogue a pasta inteira no seu projeto do Claude Code. Os documentos são escritos pra DOIS leitores:

- **Você (o operador):** lê pra saber O QUE pedir, em que ordem, e o que conferir em cada gate de aprovação.
- **O seu Claude:** lê como manual de execução. Quando você pedir "modela essa VSL seguindo o doc 01", ele abre o documento e executa.

O comando típico é assim:

```
Leia 02-VSL/01-MODELAGEM.md e faça a engenharia reversa completa desta VSL
de referência: referencia/vsl-ref.mp4. Quero o doc-mestre de modelagem no
final (arquitetura, escada de crenças, dispositivos de edição, mapa de
compressão pra ~15min).
```

## Dois modos de operação

1. **MODELAR (o modo principal):** você tem uma VSL que está escalando no seu nicho (sua ou espionada). O Claude disseca a estrutura dela e constrói uma VSL nova por cima do esqueleto validado — persona nova, mecanismo renomeado, nicho ou idioma diferente. É transplante de arquitetura: a lógica que já provou que vende é preservada; a pele é 100% nova.
2. **CRIAR DO ZERO:** sem referência, o Claude usa a estrutura-padrão de ~14 blocos do doc 02 (lead → prova → história → escada de crenças → descoberta → receita aberta → pitch → garantia → FAQ → encruzilhada) e escreve a VSL direto. Funciona, mas modelar uma VSL que JÁ vende é sempre a aposta mais segura — por isso o doc 01 vem primeiro.

## O fluxo completo (mapa do módulo)

```
 VOCÊ                        O CLAUDE                                    SAÍDA
 ────                        ────────                                    ─────
 1 VSL de      ┌─────────────────────────────────────────────┐
 referência ──►│ MODELAGEM (doc 01)                          │
 (.mp4/link)   │  whisper transcreve com timestamps          │──► doc-mestre:
               │  ffmpeg conta os cortes (meta de ritmo)     │    arquitetura em blocos
               │  frames 0.25fps → grids 3x3                 │    escada de crenças
               │  modelo de visão analisa bloco a bloco      │    mapa de compressão
               └───────────────────┬─────────────────────────┘
                                   ▼
               ┌─────────────────────────────────────────────┐
 APROVAÇÃO ◄── │ ROTEIRO (doc 02)                            │
 DO CONCEITO   │  estrutura clonada + persona nova +         │──► VSL-X.md
 (persona +    │  mecanismo renomeado + skills de copy       │    (~14 blocos,
 ângulo)       │  → greps de compliance → review brutal      │    formato parseável)
               └───────────────────┬─────────────────────────┘
                                   ▼
               ┌─────────────────────────────────────────────┐
 GATE DE   ◄── │ GERAÇÃO (doc 03)                            │
 FRAMES        │  roteiro → spec JSON → Google Flow:         │──► ~100-200 clipes
 (grade)       │  Nano Banana 2 gera frames-âncora →         │    de 8s com fala
               │  Veo 3 anima com voz nativa → download      │    nativa (custo zero)
               └───────────────────┬─────────────────────────┘
                                   ▼
               ┌─────────────────────────────────────────────┐
               │ ASSETS DE PROVA (docs 01/04) — em paralelo  │
               │  prints reais de estudo/matéria · página    │──► inserts/
               │  editorial própria · telas do app ·         │    pares antes-depois
               │  pares antes/depois i2i · b-rolls           │    b-rolls
               └───────────────────┬─────────────────────────┘
                                   ▼
               ┌─────────────────────────────────────────────┐
               │ EDIÇÃO AVANÇADA + MONTAGEM (docs 04 e 05)   │
               │  trim whisper → cutaways → RVM fundo        │──► VSL-FINAL.mp4 *(só se a VSL usar remoção de fundo — opcional)*
               │  transparente → tela dividida → pares →     │    1080x1920 (ou 3:4)
               │  primeiro minuto de impacto → legendas →    │    15-25min front
 APROVAÇÃO ◄── │  overlays de preço → QA em 5 camadas        │    7-10min upsell
 FINAL (você)  └─────────────────────────────────────────────┘
```

## Custo e tempo (medidos em produção real, não estimados)

| Item | Valor |
|---|---|
| Custo de API de vídeo | **zero** (`veo_3_1_i2v_lite_low_priority` na fila de baixa prioridade do Flow não consome créditos do plano) |
| Custo de transcrição | zero (whisper.cpp local) |
| Custo de matting/edição | zero (RobustVideoMatting local + ffmpeg) |
| Geração de ~180 cenas | ~40 min de máquina (fila vazia) a ~2h (fila disputada) |
| Ponta a ponta (roteiro → final com QA) | 1 madrugada + 1 manhã de rodadas de ajuste |

O único custo real do módulo é a assinatura do Google AI Ultra (acesso ao Flow). Todo o resto roda local.

## Onde você entra (os gates humanos)

O módulo foi desenhado pra você tocar em POUCOS pontos, mas nos pontos certos:

1. **Conceito** (antes do roteiro): você aprova persona + ângulo + nome do produto. Nome do produto se valida ANTES de gerar qualquer clipe — a fonética errada descoberta depois custa re-render de dezenas de cenas.
2. **Grade de frames** (antes de animar): você (ou um subagente de visão) olha a grade de frames-âncora. Frame errado aqui vira 100 clipes errados.
3. **Gate dos pares antes/depois:** contraste tem que gritar em miniatura. Fraco = regerar, sem exceção.
4. **VSL final:** você assiste inteira. Feedback → leva de ajuste cirúrgica (só regera o necessário) → normalmente 2-3 rodadas até o 100%.

Todo o resto — transcrição, análise, spec, submit, poll, download, trim, montagem, legendas, QA técnico — o Claude executa sozinho.

## Pré-requisitos (checklist)

Peça pro seu Claude verificar e instalar o que faltar:

```
Verifique meu ambiente pro módulo VSL: (1) ffmpeg com libass instalado;
(2) whisper.cpp compilado com os modelos ggml-base.bin e ggml-small.bin;
(3) Python 3 com Pillow, torch e numpy; (4) o repositório RobustVideoMatting
clonado com o peso rvm_mobilenetv3.pth; (5) Chrome logado na conta Google
AI Ultra com uma aba do Flow aberta; (6) browser-harness funcionando.
Instale o que faltar e me diga o que precisou de ação manual.
```

## Mapa da pasta

| Arquivo | O quê |
|---|---|
| `01-MODELAGEM.md` | Engenharia reversa da VSL de referência: transcrição, scene-detect, grids, mapa de blocos, o que extrair |
| `02-ROTEIRO.md` | O formato de arquivo que o pipeline parseia + as regras de fala e copy pagas a sangue |
| `03-GERACAO-FLOW.md` | A fábrica de clipes: Flow, Nano Banana 2, Veo lite low priority, voz nativa, filtros do Veo |
| `04-EDICAO-AVANCADA.md` | ⭐ O diferencial: RVM/fundo transparente, tela dividida, antes/depois, ken burns sem tremer, primeiro minuto |
| `05-MONTAGEM-E-QA.md` | Pipeline de montagem completo + QA em 5 camadas + deltas front × upsell |
| `06-EDICAO-DINAMICA-OBRIGATORIA.md` | 🔴 A régua (≥12 trocas de estímulo/min · punch-in >4,6s · nenhum plano >6-8s parado · 2 primeiros minutos densos), o **plano de edição obrigatório**, a expert com energia (no prompt), antes/depois coerente com o produto e o **gate de ritmo medido** |
| `scripts-referencia/` | Scripts genéricos comentados pro seu Claude adaptar: `rvm_matte.py`, `kenburns.py`, `legendas_ass.py`, **`montar_vsl.py`** (executa o plano de edição: split, cutaway, insert, par, flash, RVM, zoom, punch-in, xfade, legendas, overlays, QA) e `exemplo-plano-edicao.json` |

Leia na ordem na primeira vez. Depois, cada produção nova começa direto no doc 01 com a referência nova — e **nenhuma termina sem o plano de edição do doc 06 e o `medir_ritmo.py` aprovando**.
