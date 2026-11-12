# MÓDULO CRIATIVOS — VISÃO GERAL

> **O que este módulo entrega:** uma fábrica de criativos de vídeo pra tráfego direto que roda dentro do SEU Claude Code. Você entrega 1 link da Facebook Ads Library; o sistema analisa a biblioteca inteira do nicho, baixa e transcreve os vídeos mais escalados, disseca formato + anatomia visual + copy — e produz criativos novos no mesmo padrão dos campeões, em volume, com custo de geração próximo de zero.

## Como usar esta pasta

Jogue a pasta inteira no seu projeto do Claude Code. Os documentos são escritos pra DOIS leitores ao mesmo tempo:

- **Você (o operador):** lê pra entender o processo e saber O QUE pedir, em que ordem, e o que conferir em cada gate.
- **O seu Claude:** lê como manual de execução. Quando você pedir "roda a espionagem do doc 01", ele abre o documento e executa os passos.

O comando típico é assim:

```
Leia 01-CRIATIVOS/01-ESPIONAGEM-APIFY.md e execute a espionagem completa
deste link da Ad Library: <cole o link>. Meu token da Apify está em
~/.config/apify/token. Idioma dos ads: português.
```

Cada documento tem os prompts prontos pra você copiar e adaptar.

## O fluxo completo (mapa do módulo)

```
 VOCÊ                          O CLAUDE                                SAÍDA
 ────                          ────────                                ─────
 1 link da       ┌──────────────────────────────────────────┐
 Ad Library ───► │ ESPIONAGEM (doc 01)                      │
                 │  Apify varre a biblioteca inteira        │──► ads.json rankeado
                 │  → baixa vídeos → whisper transcreve     │    transcrições
                 │  → ffmpeg extrai frames → modelo de      │    análise visual
                 │  visão disseca a anatomia visual         │    por formato
                 └────────────────┬─────────────────────────┘
                                  ▼
                 ┌──────────────────────────────────────────┐
                 │ CONSTRUTOR (doc 02)                      │
                 │  Parametriza os campeões em 6 eixos      │──► combinações
                 │  (hook/mensageiro/estrutura/prova/       │    novas de ad
                 │  espetáculo/CTA) + 8 esqueletos prontos  │    (roteiro no papel)
                 └────────────────┬─────────────────────────┘
                                  ▼
                 ┌──────────────────────────────────────────┐
                 │ RECEITAS DE FORMATO (doc 03)             │
                 │  12 receitas de montagem validadas       │──► SPEC.json
                 │  (RVM, split, diálogo, carrossel...)     │    (cena a cena)
                 └────────────────┬─────────────────────────┘
                                  ▼
 GATE DE  ◄────  ┌──────────────────────────────────────────┐
 FRAMES          │ PRODUÇÃO (doc 04)                        │
 (você olha      │  Google Flow via browser-harness:        │──► clipes de 8s
 a grade)        │  Nano Banana 2 gera frames → Veo 3       │    (custo zero na
                 │  anima com fala nativa → download        │    fila low priority)
                 └────────────────┬─────────────────────────┘
                                  ▼
                 ┌──────────────────────────────────────────┐
                 │ MONTAGEM + QA (docs 04 e 05)             │
                 │  ffmpeg: trim → concat → legendas →      │──► AD-FINAL.mp4
                 │  headline → CTA animado → gate de        │    1080x1920, 60-100s
 APROVAÇÃO ◄──── │  3 camadas (técnica/visual/fala)         │    pronto pra subir
 FINAL (você)    └──────────────────────────────────────────┘
```

## Capacidade real (medida, não estimada)

| Janela | Entrega | Custo de geração |
|---|---|---|
| 1 leva de 3 ads | ~50-70 min do spec ao final | zero |
| 1 madrugada autônoma (~5h) | ~13 ads finais com QA completo | zero |
| 1 dia de operação | **~25 ads finais** | zero |

O custo de geração é ~zero porque o modelo de vídeo usado (`veo_3_1_i2v_lite_low_priority`, no Google Flow com assinatura Ultra) não consome créditos na fila de baixa prioridade. Os únicos custos reais do módulo são: a assinatura do Google AI Ultra (que dá acesso ao Flow), a Apify na espionagem (~$0,75 por 1.000 ads analisados) e a verba de teste no Facebook.

**O gargalo não é geração — é QA.** O que limita o volume é olhar rosto, voz e frame antes de aprovar, não a capacidade de render. Por isso os gates humanos deste módulo são poucos e cirúrgicos: você olha a grade de frames antes de animar, e o lote final antes de subir. Todo o resto o Claude faz sozinho.

## Pré-requisitos (checklist de instalação)

Peça pro seu Claude verificar e instalar o que faltar:

```
Verifique se meu ambiente tem tudo do checklist de pré-requisitos do
00-VISAO-GERAL.md do módulo criativos. Instale o que faltar via brew/pip.
```

- [ ] **Claude Code** rodando neste projeto (você já está aqui)
- [ ] **Google Chrome** logado numa conta Google com **assinatura Google AI Ultra** (dá acesso ao Flow com geração de vídeo em volume). Crie um projeto novo no Flow (labs.google/flow) pra este produto — o ID do projeto fica na URL.
- [ ] **browser-harness** (controle do Chrome via CDP) instalado e funcionando — é como o Claude opera o Flow numa aba em segundo plano
- [ ] **ffmpeg** com libass (`brew install ffmpeg`) — montagem, legendas, frames
- [ ] **whisper.cpp** (`brew install whisper-cpp`) + modelos `ggml-base.bin` e `ggml-small.bin` baixados — transcrição local, de graça, usada na espionagem E no QA
- [ ] **Python 3** com **Pillow (PIL)** — headlines, carimbos, prints de WhatsApp gerados por código
- [ ] **Conta Apify** (apify.com) — o plano free ($5/mês de crédito) banca 2-3 espionagens grandes por mês. Guarde seu token em `~/.config/apify/token` (é onde os comandos prontos leem).
- [ ] (Opcional) **RobustVideoMatting (RVM)** — recorte de pessoa pra receita de tela-verde sem tela verde
- [ ] (Opcional) **ElevenLabs** — só se você for usar voz narrada em off; a fala dos avatares sai nativa do Veo, sem custo extra

## Os documentos deste módulo

| Doc | O que é | Quando usar |
|---|---|---|
| `01-ESPIONAGEM-APIFY.md` | Da URL da Ad Library ao dossiê do nicho: Apify, download, whisper, frames, análise visual, ranking por escala | Sempre que entrar num nicho novo, e refresh a cada 2-3 dias |
| `02-CONSTRUTOR-DE-ADS.md` | A parametrização: 6 eixos + 3 camadas obrigatórias + 8 esqueletos beat-a-beat dos hooks mais escalados + 6 invariantes | Na hora de escrever o roteiro de cada ad |
| `03-RECEITAS-FORMATOS-FLOW.md` | As 12 receitas de montagem no Flow/Veo (RVM, diálogo, split, carrossel...) com as travas anti-bug de cada uma | Na hora de transformar roteiro em spec de produção |
| `04-PIPELINE-TECNICO.md` | Como o Claude opera o Flow (browser-harness, submit, download) e monta o ad final no ffmpeg | Referência de execução — o Claude segue sozinho |
| `05-QA-E-LEIS.md` | O gate de 3 camadas + as leis anti-erro consolidadas (cada uma com o porquê e o sintoma) | SEMPRE. Nenhum ad sai sem passar por aqui |
| `06-DRIVER-SEM-CLIQUE.md` | 🔴 a mecânica do driver do Flow (sem clique, sem screenshot) — LER ANTES de automatizar; código pronto em `scripts/flow_driver.py` |
| `07-GANCHOS-DE-CHOQUE.md` | 🔴 O gancho é entregável SEPARADO: 4 mecânicas (SPLIT/INSERT_PRIMEIRO/ACAO/ESTRANHO), 5 famílias de choque, fidelidade ao master, as 3 armadilhas de prompt que dão `UNSAFE_GENERATION`, medir o choque, regerar só o gancho | Em TODA leva, antes de escrever a copy do corpo |
| `08-CRIATIVO-DINAMICO.md` | 🔴 Persona + cenário marcantes · corpo com TIPO por cena (T/D/I/L, nunca 3 iguais) · punch-in · montagem sem silêncio · a tabela-prova da leva · leis de prompt | Em TODA leva — é o padrão; sem isso saem 12 ads iguais |

## O princípio que governa tudo

Este módulo não "cria anúncios do zero". Ele **clona espetáculos que já estão escalados** — formatos que outras operações estão pagando milhões pra rodar agora, na Ad Library, em público — e os reproduz pra SUA oferta com produção sintética de custo zero. A espionagem não é uma etapa: é a fonte. Todo criativo que você produzir começa com "quem já está escalando isso, e como exatamente o ad deles funciona?".

E a regra de validação é do mercado, não sua: você sobe os ads em teste, o Facebook decide, e só o que atinge seu critério de validação (sugestão de régua: ≥5 vendas com ROAS ≥2 em até 14 dias) vira "campeão" — e campeão vira a base das variações da próxima leva. O ciclo fecha.
