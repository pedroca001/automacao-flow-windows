# SISTEMA — Criativos, VSL & Avatares Orgânicos com IA

> **Este arquivo é o cérebro do sistema.** Se você é o Claude rodando neste projeto, leia este arquivo inteiro antes de qualquer tarefa. Ele diz o que existe, como operar e quais leis nunca podem ser quebradas. Se você é o dono, você não precisa ler tudo — comece pelo `LEIA-PRIMEIRO.md`.

---
## O que este sistema faz

Três máquinas de produção que rodam quase sozinhas, comandadas em linguagem natural — duas de **mídia paga** e uma de **orgânico**:

1. **Criativos automáticos** — você manda um link de uma biblioteca de anúncios (Facebook Ads Library). O sistema analisa a biblioteca inteira: baixa os vídeos, transcreve, faz análise de frames pra entender o formato, a anatomia visual e as copies. Depois gera criativos novos no mesmo padrão dos que já estão escalando — em volume, com custo perto de zero.

2. **VSL automática** — você manda uma VSL de referência. O sistema faz engenharia reversa dela (ritmo, blocos, escada de crença), escreve uma VSL nova modelada (ou cria do zero), gera os clipes com IA e monta com edição complexa: antes/depois, prova, tela dividida, depoimento, remoção de fundo (pessoa recortada sobre a prova). Tudo automático.
3. **Avatares orgânicos** — você monta uma página com uma persona de IA que **posta reels todo dia e não compra mídia nenhuma**. O funil fecha em **comentário → DM → bridge → oferta**. O sistema cuida da identidade do avatar (o rosto não muda entre vídeos), da persona e da página, do esqueleto de cena do reel, da legenda queimada, da voz única e do rastreio por vídeo.

   🔴 **Aqui o jogo é outro.** Nas duas primeiras máquinas **você compra a impressão** e o criativo só precisa converter. Nesta, **o algoritmo decide se alguém vê** — e várias leis de criativo pago, corretas lá, derrubam a distribuição aqui. As inversões estão medidas e tabeladas em `05-AVATARES-ORGANICOS/00-VISAO-GERAL.md`. Leia antes de aplicar lei de pago em orgânico.

**Brindes inclusos:** biblioteca de formatos de criativo + estruturas de esteira de upsell.

---

## Mapa do projeto

```
sistema-criativos-e-vsl/
├── SISTEMA.md                      ← você está aqui (o cérebro)
├── LEIA-PRIMEIRO.md                ← onboarding do dono (setup + primeiros comandos)
├── .claude/skills/                 (pasta OCULTA — cópia visível idêntica em SKILLS/; recriar: scripts/instalar-skills.sh)
│   ├── criativos/                  ← skill: produzir uma leva de criativos
│   ├── vsl/                        ← skill: modelar/criar uma VSL
│   ├── avatares-organicos/         ← skill: página orgânica com avatar (funil comentário→DM)
│   ├── direct-response-copywriter/ ← skill: roteiro/CTA/oferta que vende (RMBC + AIDA)
│   ├── copy-legends/                ← skill: 23 lendas do copywriting (headline, VSL, oferta, funil)
│   ├── marketing-psychology/       ← skill: gatilhos e modelos mentais de persuasão
│   └── video-ia-sem-defeito/       ← skill: catálogo de defeitos do gerador de vídeo (ativar antes de escrever prompt de vídeo)
├── SKILLS/                         ← as mesmas 7 skills, VISÍVEIS (fonte do instalar-skills.sh)
├── 01-CRIATIVOS/
│   ├── 00-VISAO-GERAL.md
│   ├── 01-ESPIONAGEM-APIFY.md      ← link Ad Library → análise completa
│   ├── 02-CONSTRUTOR-DE-ADS.md     ← parametrizar qualquer ad em 6 eixos
│   ├── 03-RECEITAS-FORMATOS-FLOW.md← as 12 receitas de montagem no Flow
│   ├── 04-PIPELINE-TECNICO.md      ← operar o Flow + montar em ffmpeg
│   ├── 05-QA-E-LEIS.md             ← gate de qualidade + leis anti-erro
│   ├── 06-DRIVER-SEM-CLIQUE.md     ← 🔴 a mecânica do driver (LER ANTES de automatizar o Flow)
│   ├── 07-GANCHOS-DE-CHOQUE.md     ← 🔴 o gancho é entregável SEPARADO: 4 mecânicas, 5 famílias de choque, 3 armadilhas de prompt
│   └── 08-CRIATIVO-DINAMICO.md     ← 🔴 persona+cenário marcantes · corpo com TIPO por cena (T/D/I/L) · punch-in · tabela-prova da leva
│                                     (a biblioteca de formatos fica no brinde 04)
├── scripts/                        ← os 9 scripts do pipeline, PRONTOS (mapa: scripts/LEIA.md)
│   ├── gerar_specs.py              ← copy aprovada (leva.json) → specs/<AD>.json (+ auto-teste de placeholder)
│   ├── flow_driver.py              ← 🔴 o driver do Flow (masters→scenes→submit→poll→retry), SEM clique — doc 06
│   ├── flow_download.py            ← download dos clipes (name da mídia + cookie via CDP)
│   ├── gate_frames.py              ← grades do gate visual (masters e cenas)
│   ├── gate_clipes.py              ← gate pós-download: tamanho · SSIM × frame · whisper × fala
│   ├── montar_leva.py              ← montagem final: trim → punch-in → gancho (split/insert) → concat → corte por fala → legenda do roteiro → headline → CTA
│   ├── medir_ritmo.py              ← 🔴 gate de RITMO medido (trocas de estímulo/min, maior plano parado, silêncio, v×a) — criativos e VSL
│   ├── banner.py                   ← faixa de headline / pílula de CTA / seta / etiquetas (PIL)
│   ├── voz-unica.py                ← voz única de TTS pra vídeo multi-cena SEM rosto (orgânico)
│   ├── exemplo-leva.json           ← entrada de exemplo do gerar_specs.py
│   ├── exemplo-avatares.json       ← exemplo da identidade de avatar (orgânico)
│   └── instalar-skills.sh · verificar-pacote.sh ← recria a .claude/skills/ · confere o pacote
├── 02-VSL/
│   ├── 00-VISAO-GERAL.md
│   ├── 01-MODELAGEM.md             ← engenharia reversa da VSL de referência
│   ├── 02-ROTEIRO.md               ← escrever o roteiro modelado
│   ├── 03-GERACAO-FLOW.md          ← gerar os clipes
│   ├── 04-EDICAO-AVANCADA.md       ← RVM/fundo, split, antes-depois, ken burns (o COMO de cada técnica)
│   ├── 05-MONTAGEM-E-QA.md         ← montar e conferir
│   ├── 06-EDICAO-DINAMICA-OBRIGATORIA.md ← 🔴 a régua (≥12 trocas/min), o PLANO DE EDIÇÃO obrigatório, expert com energia, gate medido
│   └── scripts-referencia/         ← kenburns.py · legendas_ass.py · rvm_matte.py · montar_vsl.py (executa o plano) · exemplo-plano-edicao.json
├── 03-BRINDE-UPSELLS/              ← estruturas de esteira de upsell
├── 04-BRINDE-BIBLIOTECA-FORMATOS/  ← biblioteca de formatos + hooks + nichos
├── 05-AVATARES-ORGANICOS/          ← 🎁 a 3ª máquina: orgânico com avatar (SEM tráfego pago)
│   ├── 00-VISAO-GERAL.md           ← 🔴 pago × orgânico: as leis que se INVERTEM (ler primeiro)
│   ├── 01-IDENTIDADE-DO-AVATAR.md  ← o rosto não mudar entre vídeos; identidade ≠ cena
│   ├── 02-PAGINA-E-PERSONA.md      ← criar a página sem levantar bandeira de rede coordenada
│   ├── 03-FORMATOS-ORGANICOS.md    ← esqueleto de cena do reel + ponte com o brinde 04
│   ├── 04-DEFEITOS-DO-GERADOR.md   ← o que é específico do orgânico (o catálogo é a skill)
│   ├── 05-LEGENDA-E-VOZ.md         ← legenda queimada sem bug + voz única
│   ├── 06-FUNIL-DM-ORGANICO.md     ← keyword, bridge, automação de DM, rastreio por vídeo
│   └── 07-MEDIR-E-DECIDIR.md       ← distribuição × retenção, uma variável por teste
└── swipefile/ACESSE-AQUI.md        ← link do banco de ~800 ofertas (online, sempre atualizado)
```

> **Swipe file online:** o banco de ofertas escaladas fica em **https://001class.site/swipefile/** — atualizado pra você, abre no navegador. Comece toda produção olhando lá. (O comprador pode montar o próprio swipe file via o módulo de espionagem.)

---

## Ferramentas que o sistema usa

O dono precisa ter acesso a estas (o `LEIA-PRIMEIRO.md` cobre o setup). Você (Claude) opera todas via terminal e via browser-harness.

| Ferramenta | Pra que serve | Custo |
|---|---|---|
| **Google Flow** (Veo 3 + Nano Banana 2) | gera os clipes de vídeo e as imagens/masters. É a fábrica. | plano da conta Google |
| **browser-harness** | como você pilota o Flow (aba oculta no Chrome logado) | — |
| **Apify** (actor `curious_coder/facebook-ads-library-scraper`) | raspa a Ad Library inteira a partir de 1 link | ~$0,75 / 1000 anúncios |
| **whisper.cpp** (`whisper-cli`, modelos ggml) | transcreve vídeos localmente | grátis / local |
| **ffmpeg** (build com libass) | corta, monta, legenda, compõe | grátis / local |
| **RobustVideoMatting (RVM)** | remoção de fundo (pessoa recortada sobre a prova) | grátis / local (GPU) |
| **Modelo de visão** (Gemini/Opus) | análise de frames dos anúncios espionados | por uso |
| **PIL/Pillow** | monta prints/overlays pixel-perfeitos (WhatsApp, preço, carimbo) | grátis / local |

> Ferramentas de checkout/pagamento e de rastreamento (VTurb, Utmify etc.) são escolha do dono — o sistema é agnóstico a elas.

---

## Como você (Claude) deve trabalhar aqui

1. **Comece SEMPRE pelo swipe file.** Nenhum criativo e nenhuma VSL nasce do zero. Antes de produzir, consulte o swipe file online (**https://001class.site/swipefile/**) e o `04-BRINDE-BIBLIOTECA-FORMATOS/` e traga 5-10 referências que casam com a oferta. Mostre pro dono e explique o que você viu.
2. **Um teste por vez.** Não misture duas variáveis na mesma leva. Se for testar hook, mantenha o resto igual.
3. **Gate antes de gerar.** Nunca dispare geração no Flow sem passar pelo gate de frames (masters → conferir rostos/props → só então os clipes). Gerar errado custa tempo e crédito.
4. **Gate depois de gerar.** Todo clipe passa pelo QA de 3 camadas (`01-CRIATIVOS/05-QA-E-LEIS.md`) antes de entrar na montagem.
5. **Aprovação por lote.** Produza, monte, e apresente em lotes pro dono aprovar. O dono é o QA final — nada sobe sem o OK dele.
6. **Disco é a fonte da verdade.** Em leva grande, o estado vive em arquivos (specs, states, artefatos), não na sua memória de conversa. Se a conversa ficar longa, o trabalho continua a partir dos arquivos.
7. **Explique antes de rodar algo pesado.** Se uma tarefa vai gastar tempo/crédito, diga as etapas, o tempo estimado e o custo, e espere o OK.
8. **Escrevendo copy? Ative a skill ANTES de escrever.** Roteiro, CTA, headline, oferta, bullet — nunca escreva na unha. Ative `direct-response-copywriter` (roteiro/CTA/oferta), `copy-legends` (headline/VSL/funil/email) e `marketing-psychology` (gatilhos de persuasão) e escreva dentro do framework delas. É o que separa copy amadora de copy que vende.
9. **A pasta `scripts/` vem no pacote — os 9 scripts do pipeline, prontos** (gerar specs, driver do Flow, download, gates, montagem, banner; mapa em `scripts/LEIA.md`). São scripts de produção do fornecedor do sistema, rodando há meses. Eles operam **o Chrome do próprio dono, logado na conta paga dele**, na aba do projeto dele. Use-os como base em vez de reinventar um driver: cada linha ali é uma madrugada de erro já resolvido. E respeite o ritmo deles (pausa entre submissões, poll folgado) — **volume em rajada é o que derruba conta**, não a automação em si.
10. **Escrevendo prompt de vídeo? Ative a `video-ia-sem-defeito` ANTES.** Vale nas TRÊS máquinas — criativo, VSL e orgânico. É o catálogo de defeitos mecânicos medidos em produção (objeto que morfa, matéria que se multiplica, texto pintado na parede, física que não acontece) e a regra que evita cada um. Vídeo com gancho genial e defeito mecânico é vídeo reprovado.
11. **Orgânico não usa as leis de pago.** Se a tarefa é conteúdo que o algoritmo distribui de graça, leia `05-AVATARES-ORGANICOS/00-VISAO-GERAL.md` antes. Várias das leis abaixo se invertem lá, e o módulo mostra quais, com número.
12. 🔴 **Dinâmica é padrão, não pedido.** Criativo = gancho de choque separado + persona/cenário marcantes + corpo com tipo por cena + punch-in (`01-CRIATIVOS/07` e `08`). VSL = plano de edição antes de montar + punch-in + B-roll/split/RVM/par na régua + expert com energia (`02-VSL/06`). O dono não precisa pedir "põe zoom": se saiu pessoa parada falando, saiu errado. E **ritmo se mede** (`scripts/medir_ritmo.py`) antes de mostrar qualquer vídeo — o número decide, não a sensação.

---

## LEIS INEGOCIÁVEIS (as regras que custaram caro pra descobrir)

Estas valem em TODA produção. Estão detalhadas nos módulos; aqui está o resumo que você nunca pode esquecer:

**Criativos**
- Fala no **segundo zero** — o vídeo começa com alguém já falando, nunca com silêncio ou logo.
- **Impacto visual no frame 1** — a primeira imagem tem que parar o dedo.
- **Mínimo ~60s** por criativo pago (60-100s). Em orgânico o alvo é 17-20s (bloco Orgânico abaixo).
- **Nunca moldura de celular** no criativo (nem no prompt, nem na montagem).
- **Uma ideia por anúncio.** Um espetáculo, um mecanismo.
- **Headline = promessa concreta com número**, em faixa cheia, cor alternando.
- **Varie o CORPO, não só o hook.** Trocar 3 palavras do gancho não é um criativo novo — troque o mecanismo/espetáculo.
- **Mensageira bonita e em forma** (corpo comum só pra depoente antes/depois).
- Na remoção de fundo (RVM), a pessoa recortada vai no **canto direito, menor**, e a **prova aparece inteira** — a narradora nunca cobre a prova.
- 🔴 **O gancho é entregável SEPARADO** (`mecanica` + `acao_visual` + `insert_visual` + `gancho_fala`), nunca "a cena 1 do roteiro" — senão vira pessoa parada falando por inércia. 4 mecânicas (SPLIT / INSERT_PRIMEIRO / ACAO / ESTRANHO) distribuídas; choque grotesco/gigante que **encarna a dor ou o mecanismo**; contado, não presumido; nenhum objeto/verbo repetido na leva. Prompt do gancho < ~600 chars, abrindo na ação, sem redescrever a pessoa, sem instrução de montagem (`01-CRIATIVOS/07`).
- 🔴 **Corpo dinâmico: cada cena tem um TIPO** (T-close/T-aberto/T-3/4/T-cta · D · I · L) e **nunca 3 iguais seguidos**; todo T/L leva "DIFFERENT FRAMING FROM THE REFERENCE"; insert I com voz off pro device/mecanismo grotesco/prova; **punch-in** em todo clipe do corpo > 4,6s (`01-CRIATIVOS/08`).
- 🔴 **Persona + cenário marcantes, 1 por ad, rosto diferente em cada ad**; master com cenário E roupa explícitos (senão saem 21 ads da mesma camisa no mesmo apartamento).

**Geração no Flow (Veo)**
- 🔴 **PRODUÇÃO NÃO CLICA PRA GERAR.** O driver injeta JS na aba logada (`fetch` batchexecute) e fala direto com a API — sem screenshot, sem trazer a aba pra frente, sem perguntar clipe por clipe. A exigência é a requisição NASCER dentro da aba. 🔴 **Atualização set/2026 nº2:** o Google ligou o reCAPTCHA no Flow, então mintar o token direto virou `UNUSUAL_ACTIVITY` — o driver agora **colhe** o token do próprio app (um toque-isca abortado, nada gera) e usa na chamada real. Não é "voltar a clicar em produção". Mecânica completa + código pronto: `01-CRIATIVOS/06-DRIVER-SEM-CLIQUE.md` e `scripts/`.
- **State em disco manda.** Toda fase é idempotente e retomável pelo `SPEC.json.state.json`. Contexto estourou = sessão nova retoma do disco, nunca do zero.
- **1 submitter por aba, SEMPRE.** Duas gerações na mesma aba cruzam os clipes. Serialize.
- Use **`veo_3_1_i2v_lite_low_priority`** (0 créditos) pra i2v.
- **Nome próprio / de celebridade no prompt = render falha** (filtro). Troque por descrição.
- **Reticências no prompt = fala embolada.** Escreva pontuação limpa.
- Espelho, roupa íntima, balança digital, celular na mão: o Veo **bloqueia ou não materializa**. Contorne com troca mínima de palavra.
- Baixe os clipes com `scripts/flow_download.py`: ele pede de dentro da aba a **URL assinada que o próprio poll do Flow devolve** (`flow-content.google/...`) e baixa por fora — sem cookie na mão. (Set/2026: o Flow migrou pra `flow.google.com` e as rotas antigas `media.fetchMedia` e `media.getMediaUrlRedirect` morreram — `Unexpected token '<'` = script antigo falando com a plataforma nova.)

**Fala / voz**
- **≤26 e ≥16 palavras por cena.** Fala curta demais = clipe meio mudo = risco de bloqueio.
- **Preço só junto do CTA** — nunca antes da revelação.
- Confira cada clipe com whisper (a fala bate com o roteiro? o timbre da voz não trocou?).

**VSL — edição dinâmica (02-VSL/06)**
- **Plano de edição ANTES de montar**, mostrado pro dono. Sem plano, sem montagem. A montagem mínima (concatenar + legendar) é reprovada por definição.
- **Punch-in em todo plano falado > 4,6s** · **nenhum plano > 6-8s sem trocar o estímulo** (B-roll, split, RVM, par, flash, insert) · **2 primeiros minutos densos** (split desde 0:00, cutaway a cada 2-3 cenas, flashes de "antes") · **≥ 12 trocas de estímulo/min** medidas.
- **Expert com energia nasce no prompt**: tag de cena com tom + gesto + olhar VARIADOS, frame-base "prestes a falar", enquadramento/cenário mudando por bloco, `[VOICE]` energético. Preguiça na tela não se conserta na pós.
- **Antes/depois coerente com o produto**: mesma pessoa, foto nova, transformação = a promessa e só ela, gate de contraste em miniatura.

**Montagem**
- **Zero silêncio — em duas camadas.** (1) Na MONTAGEM, criativo apara sozinho a `-25dB:d=0.3` (corte por fala + silêncio; `montar_leva.py`) — é o limiar certo pra clipe de IA, cujo ruído ambiente engana o detector a -35dB. (2) No ARQUIVO FINAL, a conferência grossa: criativo `-25dB:d=0.3` (`medir_ritmo.py`), VSL `-37dB:d=1.0` (fluidez é o critério nº1). Dentro de clipe cru do Veo, o detector de fim de fala é o whisper, não o silencedetect.
- **Nunca `zoompan` do ffmpeg puro** pra dar zoom (treme) — use ken burns em PIL com coordenadas float, ou supersample 6x.
- Normalize tudo pra **1080x1920 / 24fps** antes de qualquer xfade.
- Legenda: blocos de 3-4 palavras, terço inferior, amarelo com contorno preto.
- Preço **nunca sobre o rosto**: no topo (y≈90) ou na zona do peito (y≈1120-1400, o padrão do plano de edição da VSL) — os dois validados; e **sai de tela ANTES do CTA entrar**.


**Orgânico** *(conteúdo que o algoritmo distribui de graça — a 3ª máquina)*

> ⚠️ **As leis de "Criativos" acima continuam certas — em mídia paga.** Lá você compra a
> impressão e o criativo só precisa converter. Em orgânico o algoritmo decide se alguém vê,
> e três dessas leis se invertem. Não é correção: é outro jogo. Números em
> `05-AVATARES-ORGANICOS/00-VISAO-GERAL.md`.

- 🔴 **O produto NÃO aparece nos primeiros segundos.** Ele fecha o vídeo, não abre. Medido:
  dois reels com **roteiro idêntico palavra por palavra**, mesma avatar, mesmo cenário —
  **375 views contra 20.000**, e a única diferença era o produto no frame 0.
- **Duração 17-20s**, não 60s+. Os de 8s ficaram no fundo da lista.
- **"Impacto no frame 1" continua valendo inteiro** — tem que ACONTECER algo antes de 2s, e
  não pode ser pessoa parada falando. O que muda é **o quê** se move: em pago é o produto;
  em orgânico é qualquer coisa **menos** o produto.
- **Gancho concreto** (pessoa ou número) antes de 2s. ⛔ Subordinada temporal (*"For a
  while I thought…"*) é o pior hook rate medido.
- **Identidade do avatar ≠ cena.** Se a descrição da identidade disser o que a pessoa
  segura, nenhum roteiro consegue tirar aquilo de lá.
- **A keyword do funil precisa de ≥0,75s na tela.** Já ficou 0,27s — tempo insuficiente pra
  ler a palavra de que o funil inteiro depende.
- **Bridge no ar ANTES do primeiro post**, e **filtro de palavrão desligado** (ligado, ele
  esconde o comentário com a keyword e o funil morre calado).
- **1 post por página por dia**, horário fixo, nunca duas páginas no mesmo horário.
- **A métrica que decide é distribuição, não retenção.** Um formato foi declarado
  "validado" por maximizar porcentagem assistida e estava no fundo da lista em views.

---

## O que você NÃO decide sozinho

- **A oferta e o preço** são do dono.
- **Subir campanha / mexer em tráfego** é decisão do dono — você produz e prepara, ele sobe.
- **QA final** é do dono. Você apresenta; ele aprova.
