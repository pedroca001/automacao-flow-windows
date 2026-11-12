# 03 — AS 12 RECEITAS DE FORMATO NO FLOW/VEO

> **O que é:** o livro de receitas de montagem. O doc 02 te dá o roteiro (o que o ad DIZ); este doc dá o formato (como o ad é FILMADO e MONTADO). Cada receita foi validada em produção real e já vem com as travas que impedem os bugs que custaram levas inteiras. Ache o formato, copie a receita, troque o conteúdo.

## O prompt que usa este doc

```
Leia 01-CRIATIVOS/03-RECEITAS-FORMATOS-FLOW.md. Para os 10 roteiros aprovados
da leva, escolha a receita de formato de cada um (variando — nunca 2 ads com
a mesma receita E o mesmo gancho na leva) e gere os SPEC.json de produção
seguindo a base comum e as travas de cada receita. Me mostre o resumo
(ad → receita → gancho visual) antes de gerar qualquer imagem.
```

---

## ⚙️ BASE COMUM A TODOS OS FORMATOS

### Anatomia de um ad (8-9 cenas, 60-70s)

```
cena 1     = GANCHO (a receita manda aqui — é o que muda entre os ads)
cenas 2-3  = agitação do problema / mecanismo
cenas 4-6  = método + prova
cena 7     = ponte pro vídeo (a VSL)
cena 8     = CTA (close, apontando pra baixo)
```

Cada cena = 1 clipe de 8s gerado no Veo, com a fala embutida no prompt (voz nativa do modelo). 7 cenas ≈ 52s — **não passa do mínimo de 60s**; use 8-9 cenas.

### Os campos de cada cena (o que VOCÊ escreve no `leva.json` → o `gerar_specs.py` vira `specs/<AD>.json` pro driver)

Você não escreve o spec do driver na mão. Escreve a **copy aprovada** no `leva.json` (modelo: `scripts/exemplo-leva.json`; formato completo no cabeçalho de `scripts/gerar_specs.py`) e o `gerar_specs.py` monta os prompts com os blocos globais, o marcador de voz e os auto-testes.

| Campo (`itens[].cenas[]`) | Função | Trava |
|---|---|---|
| `n` | ordem da cena | a montagem e os gates ordenam por `n` |
| `persona` | qual personagem aparece/fala (chave de `personas`) — vazio = cena sem pessoa (b-roll, mãos) | o master da persona é gerado na fase `masters` e reusado como referência (i2i) em toda cena dela |
| `acao` | o que acontece no frame e no clipe (em inglês, concreto, já em movimento) | **NUNCA nome próprio de pessoa** (o filtro do Veo bloqueia); um objeto, um movimento; destino visível no quadro |
| `fala` | o que a pessoa diz, no idioma do público | 8-26 palavras (alvo 16-22) · sem travessão/reticências/CAIXA ALTA · sem preço · sem nome do produto |
| `prompt_video_custom` (opcional) | substitui a `acao` no prompt de vídeo | só quando precisa controlar ação/falante na mão (diálogo, prop) |

E em `personas.<chave>`: `descricao_visual` (quem ela é — o script repete **byte a byte** em toda cena: é o que trava rosto/roupa), `cenario` (ambiente/luz — a LUZ mora aqui, não no bloco de realismo) e `voz` (o bloco de voz, também byte-idêntico em toda cena da mesma pessoa — qualquer variação muda a voz).

### Os 6 blocos globais do driver (o `gerar_specs.py` prefixa em TODO prompt de vídeo; sobrescreva em `blocos_globais` se precisar)

- **POSERULE** — câmera APOIADA e estática, ninguém segurando, as 2 mãos livres e visíveis, sem braço de selfie; **um objeto, um movimento**, destino visível no quadro. (Sem isso: braço fantasma, 3 braços, enquadramento de selfie, objeto que morfa.)
- **TEXTRULE** — sem telas, sem texto legível, sem letreiros, sem interface de câmera. (IA escreve texto errado; todo texto do ad entra em pós-edição.)
- **REALISMO** — pele real com textura, sem filtro, luz coerente com a cena, nada de acabamento "publicidade". (Sem isso: cara-de-IA que o espectador fareja em 1 segundo.)
- **NOFADE** — take único, ação e fala já em andamento no segundo zero, sem fade/freeze/slow-motion, câmera travada, corte seco no fim.
- **ANATOMY** — anatomia correta: duas mãos, cinco dedos, rosto consistente o clipe inteiro.
- **FRAME** — imagem full-bleed de borda a borda, NUNCA moldura de celular, sem letterbox nem faixa borrada.

### O fluxo fixo de produção (nenhuma etapa pulável)

```
masters → scenes → 🚦 GATE DE FRAMES → submit → poll → pós-edição → montagem → QA
```

1. **masters** — 1 frame-âncora por persona (Nano Banana 2). Gate 1: você olha CADA rosto numa grade.
2. **scenes** — frames de todas as cenas (img2img com a referência do master pra manter identidade).
3. **🚦 GATE DE FRAMES** — baixar a grade completa (linhas = ads, colunas = cenas) e conferir: anatomia, rosto consistente, prop presente, zero moldura/status-bar, texto ilegível. **Nada é animado antes deste gate.** Frame ruim animado = 8s de vídeo ruim + retrabalho.
4. **submit** — i2v `veo_3_1_i2v_lite_low_priority` (fila de baixa prioridade = custo zero).
5. **poll** — checar status a cada ~90s até concluir; falha aleatória (de ~5% em hora boa a 10-30% em hora cheia) = reenviar 1x, quase sempre passa.
6. **pós-edição** — só pras receitas que exigem (RVM, split, carimbos).
7. **montagem** — trim → concat → legendas → headline → CTA (doc 04).
8. **QA 3 camadas** — doc 05.

---

## 🎬 AS RECEITAS

### R1 — RVM TELA-VERDE SOBRE PROVA GIGANTE
*(narradora recortada sobre foto antes/depois, anatomia 3D ou print de estudo)*

**Quando usar:** quando a PROVA é uma imagem parada forte. É a família de formato que mais para o dedo.

**Como montar:**
1. Gerar o fundo-prova como asset separado (o par antes/depois, a anatomia).
2. Gerar a narradora contra **parede lisa cinza-clara** (chroma limpo sem tela verde), "gesturing as if presenting a huge image beside her".
3. Rodar RobustVideoMatting no clipe da narradora → matte → overlay sobre o fundo.
4. Zoompan lento no fundo (1.0→1.06) dá vida sem tremer.

**Travas (pagas em leva reprovada):**
- 🔴 A narradora vai pro **canto direito, MENOR (~490px de largura num quadro de 1080)** — o fundo-prova É o gancho e precisa aparecer INTEIRO, em TODAS as imagens da sequência. Narradora centralizada cobrindo a prova = dispositivo perdido, ad reprovado.
- ✅ Vale pra todas as imagens da sequência, não só a primeira.

### R2 — DIÁLOGO / ESQUETE (2 pessoas no quadro)
*(a entregadora × a dona da casa; entrevista de rua)*

**Quando usar:** quando o contraste físico entre as duas pessoas É o gancho.

**Como montar:**
1. Gerar os 2 masters separados (uma persona por pessoa).
2. Frame two-shot por **multi-referência**: as 2 imagens de referência num único prompt de imagem → 1 frame com as duas.
3. **1 FALA POR CLIPE** — cenas `1` e `1.5`, as duas partindo do MESMO frame.
4. `vp_custom` com SPEAKER LOCK por POSIÇÃO: *"the ONLY person who speaks is the woman on the LEFT SIDE... the woman on the RIGHT is MUTE, lips SEALED"*.
5. `bloco_voice` diferente por clipe (a voz de quem fala naquele clipe).
6. **Pós-edição OBRIGATÓRIA:** 0-0,8s mostra as duas → **punch-in (crop) na falante** pelo resto da fala — a outra sai do quadro. É corte padrão de editor; fica impossível "as duas falando".

**Travas (3 bugs pagos):**
- ❌ NUNCA 2 falas no mesmo clipe → o Veo troca as vozes entre as pessoas.
- ❌ "mouth closed" NÃO segura a ouvinte — em algum take ela mexe a boca. Só o punch-in resolve, deterministicamente.
- ✅ Gate de timbre: medir o pitch (f0 mediano) dos 2 clipes — a coadjuvante precisa ficar ≥35Hz fora da faixa da protagonista, senão o espectador ouve "a mesma mulher conversando consigo mesma". Re-rolar até contrastar.

### R3 — TELA DIVIDIDA (split antes/depois)
*("HÁ 11 DIAS | HOJE")*

**Como montar:**
1. Still do "antes" como PNG + clipe da pessoa falando (o "hoje").
2. Pós-edição monta: still 540px à esquerda + clipe cropado 540px à direita + tags coloridas (vermelha no antes, verde no hoje).

**Travas:** ✅ still e clipe da MESMA pessoa (rosto conferido no gate) · ✅ tags desenhadas em PIL, nunca pelo Veo · ✅ **cada ad com split precisa da SUA imagem** — reusar a mesma em 5 ads = 5 ads iguais no scroll · ✅ contraste REAL entre as metades, tags na LATERAL (nunca sobre rosto).

### R4 — VILÃO PERSONIFICADO
*("Oi, eu sou o PÃO INTEGRAL do teu café da manhã")*

**Como montar:** persona normal, mas a `fala` é em 1ª pessoa DO ALIMENTO/OBJETO vilão; `cena_visual` = ela segurando/ao lado do vilão em close. Cena 2 quebra o teatro ("brincadeira à parte — é isso que ele faz com você").

**Trava:** ✅ o teatro dura SÓ 1 cena. Depois vira explicação séria — senão o ad fica engraçado e não vende.

### R5 — CARIMBO / X VERMELHO (pós-edição)
*(vilões nas mãos com X estampado em cima)*

**Como montar:** clipe normal da pessoa mostrando os produtos → em pós, overlay de PNG (X vermelho, carimbo "ELIMINADO") aparecendo no tempo certo (ffmpeg `enable='between(t,X,Y)'`).

**Travas:** ✅ o X/carimbo é SEMPRE pós-edição — pedir pro Veo desenhar símbolo = texto tremido/errado · ✅ se o objeto muda de lado entre cenas, a posição do carimbo acompanha (mapa de posição POR CENA, nunca fixa).

### R6 — CARROSSEL DE PRINTS (WhatsApp / provas sociais)

**Como montar:** prints gerados em **PIL** (código Python desenha a conversa — 100% controlado, pixel-perfect) → vídeo de slides com crossfade → entra como cutaway/insert POR CIMA da fala seguinte (a voz nunca para).

**Travas:** ✅ NUNCA deixar IA escrever texto de print (sai borrado/errado) · ✅ prints novos a cada leva · ✅ cutaway de print é TELA CHEIA limpa ou não entra — print cobrindo metade de um rosto = reprovado.

### R7 — PAR ANTES/DEPOIS (mesma pessoa)

**Como montar:** img2img encadeado — gera o "depois" (a pessoa em forma), e a partir dele o "antes" (corpo cheio), mantendo o MESMO rosto → slide com crossfade entre os dois.

**Travas:** ✅ ANTES = corpo cheio de verdade — e **nunca com aparência de grávida** (erro comum do gerador) · ✅ mesma pessoa nos dois (rosto conferido no gate) · ✅ contraste óbvio mas CRÍVEL pro prazo prometido — 40kg em 9 dias mata a credibilidade do ad inteiro.

### R8 — MULTI-REF (2 pessoas citadas na fala)
*(a filha aponta + a mãe segura a foto)*

**Como montar:** 2 imagens de referência (master de cada pessoa) num único prompt de geração de imagem; o prompt descreve as duas e o que cada uma faz.

**Trava:** ✅ se a fala CITA alguém ("a pesagem da minha mãe"), essa pessoa APARECE no frame 1 — não só depois. Citar sem mostrar quebra a promessa visual do gancho.

### R9 — DEMO / RECEITA (sem pessoa)

**Como montar:** cena `tipo: "insert"` sem `fala`, prompt com "ABSOLUTELY NO SPEECH, mouth closed, ambient only"; entra como cutaway sobre a fala da cena seguinte.

**Trava:** ✅ demonstração com pessoa medindo o próprio corpo (fita métrica etc.) tende a reprovar na moderação do Facebook → still-life SEM pessoas passa.

### R10 — FILTRO DE AUDIÊNCIA / PROIBIÇÃO REVERSA
*("se pra você a resposta é 'fechar a boca', PULA esse vídeo")*

**Como montar:** puramente copy — cena 1 em close, gesto de "pare". Sem asset especial. O formato mais barato do livro.

**Trava:** ✅ o filtro PRECISA ser seguido de um "mas se você..." na cena 2 — senão o ad só expulsa gente e não convida ninguém.

### R11 — CALENDÁRIO / TURMA / DATA

**Como montar:** prop físico (calendário de parede, agenda) + caneta vermelha marcando o prazo. `cena_visual` descreve o prop; o texto do calendário fica NUNCA legível (TEXTRULE) — datas legíveis entram em pós se precisar.

### R12 — AUTODIAGNÓSTICO
*("aperta a tua barriga agora")*

**Como montar:** close da pessoa demonstrando o gesto no próprio corpo; o espectador imita em casa. Funciona como abertura de qualquer estrutura.

**Trava:** ✅ MOSTRAR o gesto, não só falar — a participação física do espectador é o mecanismo do hook.

---

## 📌 ORDEM DE PRIORIDADE AO PLANEJAR UMA LEVA

1. Formatos com **prova visual** (R1, R3, R7) — os que mais param o dedo.
2. Formatos de **personagem/teatro** (R2, R4) — os mais compartilháveis, mas os mais caros de QA.
3. Formatos de **copy pura** (R10, R12) — os mais baratos; use pra completar a leva.
4. Sempre: **1 formato por ad** · nunca 2 ads com o mesmo gancho na mesma leva · o mesmo prop/beat visual aparece no MÁXIMO 2 vezes na leva · rosto novo por ad · assets (pares, prints, demos) 100% novos por leva — nunca reaproveitar da leva anterior.
