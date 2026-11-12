# 06 — EDIÇÃO DINÂMICA OBRIGATÓRIA 🔴 (a VSL nunca é "a expert falando" — é um vídeo que não para de se mexer)

> **Por que este documento existe:** um dono deste sistema gerou a primeira VSL dele e o resultado foi **cinco minutos de expert parada falando de frente** — sem zoom, sem B-roll, sem tela dividida, sem antes/depois, sem energia. Tudo isso está descrito no doc 04 (as técnicas) e no doc 05 (a ordem da montagem). O problema não é falta de técnica: é que **nada obrigava a usar**. O Claude dele fez a montagem mínima (concatenar clipes) porque a montagem mínima "funciona".
>
> A partir de agora a montagem mínima é **reprovada por definição**. Este documento é a régua, o plano obrigatório e o gate medido. Se você (Claude) está montando uma VSL, o doc 04 diz *como* fazer cada efeito; **este diz quanto, onde e o que reprova.**

---

## 1. A RÉGUA (medida em VSL escalada, não inventada)

Uma VSL de emagrecimento que escalou por meses foi modelada quadro a quadro: **647 cortes em 33 minutos = 1 troca de estímulo a cada 3,1 segundos.** A nossa VSL modelada nela, de 15m31s, saiu com **274 trocas de estímulo (107 punch-ins + 99 jump cuts + 34 crossfades de cena + 34 crossfades de B-roll) = 1 a cada 3,46s.** Isso é a régua. Não é gosto — é o ritmo que a audiência de VSL já está treinada a aceitar sem sair.

**As 4 leis de ritmo (nenhuma é opcional):**

| Lei | Número | O que acontece se quebrar |
|---|---|---|
| **Punch-in em todo plano falado > 4,6s** | zoom 1,12 no meio do clipe, automático | plano de 8s parado = "apresentação de vendas" reconhecida, o scroller sai |
| **Nenhum plano > 6-8s sem trocar o estímulo de verdade** | B-roll, split, RVM, par, flash, insert | queda de retenção medida: −44% até 1:20 numa lead real, consertada só com isto |
| **Os 2 primeiros minutos são os mais densos** | split desde 0:00, cutaway a cada 2-3 cenas, flashes de "antes" | é onde 60% da audiência decide ficar ou sair |
| **Média final ≥ 12 trocas de estímulo por minuto** (e nenhum plano medido > 12s) | medido no arquivo final com `scripts/medir_ritmo.py` | abaixo disso é VSL parada — remontar, não entregar |

> "Troca de estímulo" = qualquer coisa que muda o que o olho vê: corte, punch-in, B-roll entrando/saindo, split, insert, par, flash, RVM. Falar com energia **não** conta como troca de estímulo. Legenda **não** conta.

---

## 2. OS 9 DISPOSITIVOS (o que existe, com os números)

Cada um está detalhado no doc 04. Aqui está o **quanto e onde**, e o parâmetro que a montagem usa. A implementação de referência de tudo isto está em `02-VSL/scripts-referencia/montar_vsl.py` (lê o plano de edição da seção 4 e aplica) — adapte, não reinvente.

| # | Dispositivo | Onde entra | Parâmetro |
|---|---|---|---|
| 1 | **Punch-in jump-cut** | TODO plano falado > 4,6s que não recebeu outro efeito | corta no meio; 2ª metade com `crop` a 1/1,12 e olho a 30% do topo (`(ih-ch)*0.30`) → `scale` de volta. Zoom FIXO (não animado = não treme). Áudio intocado (`-c:a copy`) |
| 2 | **Jump cut seco** | entre cenas do mesmo bloco (mesmo frame-base) | corte seco é a estética; não põe crossfade |
| 3 | **Cutaway / B-roll** | ≥ 1 a cada 5-6 cenas faladas no corpo; **1 a cada 2-3 nos 2 primeiros minutos**; SEMPRE amarrado na palavra da fala do momento | visual cobre `X = min(5,2s, max(2,0s, dur_fala − 2,4s))` do início do clipe falado; áudio da fala contínuo; crossfade 0,20s na entrada e na saída; ≥ 2,4s do falante visível no fim |
| 4 | **Tela dividida** | cena 1 ou 2 (00:00 já cheio) + qualquer prova que mereça tela | B-roll topo 40% (768px) + divisor branco 6px + expert 60%; B-roll em loop pela duração da fala; áudio da expert |
| 5 | **RVM (fundo removido)** | 2-4 vezes por VSL, nos trechos "aula" com prova forte (estudo, anatomia, matéria) | pessoa recortada MENOR sobre a prova, prova visível inteira; `chromakey=0x00ff00:0.24:0.08,despill=type=green` |
| 6 | **Par antes/depois** | sobre a fala da PRÓPRIA depoente; par da família/da expert no bloco de prova | slide 5s: antes 2,2s → `wipeleft` 0,8s → depois 2s; mudo, como cutaway |
| 7 | **Flash de choque** | intro (fotos "antes" full-screen 0,8s) e momentos de dor | 0,8s, sem transição |
| 8 | **Insert com ken burns** | todo still (print de estudo, tela de app, página editorial, chat) | 5s, zoom linear 1,0→1,14 em PIL sub-pixel (`kenburns.py`); NUNCA `zoompan` cru |
| 9 | **Crossfade entre blocos** | toda transição entre fontes diferentes (bloco novo, insert, par) | `xfade=fade` 0,25s no vídeo (`acrossfade` no áudio se a fonte de áudio mudar) |

**Zoom in/out alternado nas cenas cheias** (intro): cada cena respira diferente — uma z 1,0→1,06, a seguinte 1,06→1,0. Sobre vídeo, `zoompan d=1` em supersample 2x é o compromisso; sobre still, PIL.

---

## 3. A EXPERT COM ENERGIA (o que se pede no prompt — não no pós)

Preguiça na tela nasce no **prompt**, não na montagem. Sinais: olhos meio fechados, ombros caídos, mãos escondidas, mesmo enquadramento em 10 cenas seguidas, tom uniforme, olhar que não encara a lente. Nada disso se conserta depois. Isto sim:

**a) A tag de cena leva TOM + GESTO + OLHAR — e VARIA.** No roteiro (doc 02), `N. [EXPERT, <tom/gesto/olhar>] "fala"`. O parser injeta o que vem depois da vírgula no fim do prompt de cena. Exemplos que funcionaram (variar ao longo da VSL, nunca repetir 3 seguidas):

```
[EXPERT, urgente, olhando direto na câmera]
[EXPERT, energia, inclinada pra frente]
[EXPERT, cúmplice, meio sorriso]
[EXPERT, indignada na medida, mão aberta]
[EXPERT, mostrando exatamente UM dedo pra câmera]
[EXPERT, chegando mais perto, quase sussurrando]
[EXPERT, tom pessoal, olhar baixo e depois de volta na lente]
[EXPERT, segurando o objeto da demonstração ao lado do rosto]
[EXPERT, aliviada, sorriso largo, ombros soltos]
[EXPERT, séria, dedo indicador batendo na mesa]
```

Em inglês no prompt (`speaking with energy, leaning slightly forward, eyes locked on the lens, expressive hands visible, eyebrows moving with the words`). Gesto contável em inglês literal (`exactly THREE fingers`) — em português o gerador erra.

**b) POSERULE do frame-base = ativa, não morta.** O frame de fala tem que nascer "prestes a falar": *"FACING THE CAMERA directly, eyes open looking into the lens as if about to speak, relaxed but ALERT posture, both hands free and visible, shoulders open, NOT reading, NOT looking down"*. Frame morto = bloco inteiro morto.

**c) Enquadramento muda ao longo da VSL.** 1 frame-base por bloco é a regra (jump cuts dentro do bloco), mas o **bloco novo muda de enquadramento e/ou de cenário com motivo narrativo**: médio na cozinha → mais perto no sofá (origin story) → aberto na mesa (oferta) → close (garantia). Numa VSL de 14 min validada: 7 cenários. No prompt do frame novo: *"DIFFERENT FRAMING FROM THE REFERENCE: closer, from the shoulders up"* / *"wider, the whole room visible"* + *"EXACTLY the same clothes, hair and lighting as the reference"*. Bloco muito longo (> 10 cenas)? Gere um **2º frame-base do mesmo bloco em close** (i2i do frame-âncora: *"same everything, closer framing"*) e alterne as cenas entre os dois — é o corte de câmera que a edição humana faz.

**d) O corpo fala junto.** Demonstração física quando a copy demonstra (aperta a barriga, mostra a jarra, levanta o vestido). Objeto na mão SÓ na cena que o usa (POSERULE do resto: mãos livres). Cena de contagem = dedos; cena de contraste = mão de um lado e do outro.

**e) A voz também tem energia.** No `[VOICE]` fixo da expert (doc 03), o tom-base é *"warm, energetic, intimate delivery, natural rises and falls"* — não "calm". Calma é pra 2-3 cenas específicas (sussurro, momento pessoal), pedidas na tag.

---

## 4. O PLANO DE EDIÇÃO — obrigatório ANTES de montar

Você não monta uma VSL "olhando os clipes". Você escreve o plano, o dono olha o plano (é rápido, é uma tabela) e a montagem executa o plano. Sem plano aprovado, sem montagem.

**Arquivo:** `vsls/VSL-<NOME>.plano-edicao.json` (o que `montar_vsl.py` lê) + uma tabela em `.md` pro dono ler. Modelo completo em `02-VSL/scripts-referencia/exemplo-plano-edicao.json`. A ideia:

```json
{
  "idioma": "pt", "fps": 24,
  "cenas": [
    {"n": 1,  "clip": "clips/cena_1.mp4",  "fala": "…", "efeitos": [{"tipo": "split", "broll": ["broll/b01.mp4","broll/b02.mp4"]}]},
    {"n": 2,  "clip": "clips/cena_2.mp4",  "fala": "…", "efeitos": [{"tipo": "flash", "png": "pares/maria_antes.png", "t": 0.0}]},
    {"n": 3,  "clip": "clips/cena_3.mp4",  "fala": "…", "efeitos": [{"tipo": "cutaway", "src": "broll/b03.mp4"}]},
    {"n": 4,  "clip": "clips/cena_4.mp4",  "fala": "…"},
    {"n": 5,  "clip": "clips/cena_5.mp4",  "fala": "…", "efeitos": [{"tipo": "insert", "png": "inserts/estudo.png"}]},
    {"n": 6,  "clip": "clips/cena_6.mp4",  "fala": "…", "efeitos": [{"tipo": "rvm", "bg": "inserts/estudo.png"}]},
    {"n": 7,  "clip": "clips/cena_7.mp4",  "fala": "…", "efeitos": [{"tipo": "par", "antes": "pares/maria_antes.png", "depois": "pares/maria_depois.png"}]}
  ],
  "overlays": [{"png": "overlays/preco.png", "x": "(W-w)/2", "y": 1120, "ini": 611.0, "fim": 626.0}]
}
```

- Cena sem `efeitos` = plano falado puro → **recebe punch-in automático se > 4,6s**. Você não marca punch-in; ele é o padrão.
- Cena com `cutaway`/`insert`/`par`/`split`/`rvm`/`zoom` = não recebe punch-in (já tem estímulo). `flash` não conta (é 0,8s) — a cena continua ganhando punch-in. `"sem_punch": true` desliga numa cena específica.
- `[DEMO]` do roteiro = B-roll gerado → entra como `cutaway` sobre a cena falada seguinte. `[SKIP]` = still → `insert` (ken burns) ou `rvm` (quando a expert fala SOBRE a prova).

**Regras de preenchimento (é o que você confere antes de mostrar pro dono):**

1. Cena 1 ou 2 com `split` (00:00 já cheio) — a cena 1 pode ser B-roll full-screen se a copy manda prova visual no segundo zero.
2. Nos 2 primeiros minutos: efeito real (não punch-in) a cada 2-3 cenas; ≥ 2 flashes de "antes".
3. No corpo: efeito real a cada 5-6 cenas no máximo. Conte. Sequência de 7 cenas faladas sem efeito = buraco.
4. Todo depoimento tem `par` (da própria depoente) sobre a fala dela.
5. Toda prova de estudo/matéria/app tem `insert` (ken burns) e, se a expert explica por cima, `rvm`.
6. Toda `[DEMO]` gerada tem um alvo — B-roll gerado e não usado é dinheiro no lixo; B-roll "bonito" sem palavra na fala que o justifique é reprovado.
7. Preço em overlay na zona do peito (y≈1120-1400), NUNCA sobre o rosto; preço sai de tela ANTES do CTA entrar.

---

## 5. ANTES/DEPOIS COERENTE COM O PRODUTO (não "uma foto ruim e uma boa")

O par é a prova. Errado, ele mata a VSL inteira. As leis (doc 04c) resumidas + o que faltava:

- **MESMA pessoa, i2i encadeado** (identidade → antes → depois). Nunca duas gerações independentes.
- **DEPOIS = FOTO NOVA** (outro dia, roupa, canto da casa, pose) — nunca a mesma foto retocada. E **DRAMATICALLY transformed, obvious at thumbnail size**, ainda crível.
- 🔴 **A transformação é a que o PRODUTO promete — e só ela.** Emagrecimento: peso espalhado no corpo inteiro (rosto, braços, cintura, barriga MOLE — nunca redonda e firme = grávida) → corpo mais magro. Pele: mesmo ângulo de rosto, manchas/textura → pele lisa, sem virar outra pessoa. Cabelo: mesma cabeça, falha visível → volume. Dinheiro/organização: o cenário conta a história (mesa vazia com contas → mesa posta; quarto bagunçado → arrumado). Se o produto promete X e o par mostra X+Y+Z, a audiência não acredita.
- **Gate de contraste em miniatura:** hstack dos dois, olhe em 200px de largura. Não grita? Regerar. Sem exceção. 3 falhas = variante em vídeo (dois clipes da mesma pessoa lado a lado com rótulos) ou par validado de outra peça sua.
- **Onde entra:** sobre a fala da PRÓPRIA depoente (nunca sobre a intro da depoente seguinte); as fotos "antes" viram flashes de 0,8s na intro.

---

## 6. GATE DE RITMO — medido, não sentido

Depois de montar, **antes de mostrar pro dono**:

```bash
python3 scripts/medir_ritmo.py vsls/VSL-X_final.mp4
```

Ele imprime: trocas de estímulo por minuto (scene detect com **limiar 0,05 — calibrado**: numa VSL aprovada com 274 trocas contadas à mão o detector deu 270 a 0,05 e só 102 a 0,30, porque punch-in e jump cut no mesmo frame-base quase não mudam pixel), o **maior plano sem troca** (e onde), silêncios (`-37dB:d=1.0`), divergência vídeo×áudio, e um veredito. Reprova se: **< 12 trocas/min** · **maior plano > 12s** · algum silêncio > 1s · vídeo e áudio terminando com > 1,5s de diferença. (A régua de DESENHO continua "nenhum plano > 6-8s"; o gate medido é um pouco mais folgado porque o detector não enxerga tudo. Referência: a VSL aprovada mediu 17,4/min e maior plano 11,3s.) Reprovou = volta ao plano (seção 4), não "manda assim mesmo".

O gate visual continua: grade de frames nos momentos-chave (doc 05, camada 3) — o número não vê rosto cortado no split nem overlay em cima da cara.

---

## 7. CHECKLIST (marque antes de dizer "VSL pronta")

- [ ] Plano de edição escrito e mostrado pro dono ANTES da montagem
- [ ] Split na cena 1-2; 2 primeiros minutos com efeito real a cada 2-3 cenas + flashes
- [ ] Nenhuma sequência > 6 cenas faladas sem efeito real
- [ ] Punch-in automático ligado (todo plano > 4,6s)
- [ ] Todo `[DEMO]` gerado tem alvo; todo insert está amarrado numa palavra da fala
- [ ] Todo depoimento com par da própria depoente; par passou no gate de contraste; transformação = promessa do produto
- [ ] RVM em 2-4 trechos "aula"; pessoa menor, prova inteira visível
- [ ] Tags de cena com tom/gesto/olhar variados; enquadramento/cenário muda por bloco; frame-base "prestes a falar"
- [ ] `medir_ritmo.py` aprovou (≥ 12/min, maior plano medido ≤ 12s, zero silêncio > 1s, v×a ≤ 1,5s)
- [ ] Grade de frames dos momentos-chave olhada
- [ ] Preço na zona do peito, sai antes do CTA; CTA de clique só junto do preço

> Se o dono disser "ficou parada", a resposta não é "posso adicionar zoom?" — é voltar à seção 4 e mostrar onde o plano ficou abaixo da régua. A régua é o que se discute; o gosto vem depois dela.
