# 07 — GANCHOS DE CHOQUE 🔴 (o primeiro quadro tem que parar o dedo — e cada ad tem o SEU)

> **Por que este documento existe:** uma leva de 25 criativos saiu com o corpo bom e **os 25 ganchos idênticos** — pessoa parada, de frente, falando. Reprovada inteira. O erro não foi de copy nem de geração: foi de **processo**. Quando o gancho é escrito como "a cena 1" do roteiro, ele vira talking-head por inércia. Quando o gancho é um **entregável separado**, com campos próprios, ele vira uma imagem que ninguém consegue não olhar.
>
> Isto vale pra **toda** leva de criativo, de qualquer nicho, em qualquer idioma. Se você (Claude) está montando uma leva e não passou por este documento, pare e volte.

---

## 1. A LEI QUE ORIGINA TUDO

🔴 **O gancho é um ENTREGÁVEL SEPARADO, não "o beat 1" do roteiro.**

Pra cada ad, antes de escrever a copy do corpo, produza estes campos — **próprios, obrigatórios, nunca herdados da cena seguinte**:

| Campo | O que é |
|---|---|
| `mecanica` | como o quadro é construído (uma das 4 abaixo) |
| `acao_visual` | o que acontece **fisicamente**, em inglês, filmável em 8s, específico (objeto + verbo + destino) |
| `insert_visual` | o que aparece no painel de baixo (SPLIT) ou no close inicial sem rosto (INSERT_PRIMEIRO) — só nessas duas mecânicas |
| `gancho_fala` | a frase do segundo zero, 16-26 palavras, que casa com a ação (não a descreve — a acompanha) |

No `leva.json` do pacote isso é o bloco `"gancho": {...}` de cada item (modelo em `scripts/exemplo-leva.json`; o `scripts/gerar_specs.py` transforma o bloco nas cenas certas — clipe da pessoa e clipe do insert quando houver — e a `scripts/montar_leva.py` monta o split/insert sozinha).

---

## 2. AS 4 MECÂNICAS (distribuir entre os ads — nenhuma pode dominar)

| Mecânica | O que é | Clipes gerados | Como monta |
|---|---|---|---|
| **SPLIT** | pessoa falando em cima + ação/objeto de produto embaixo, **ao mesmo tempo** | 2 (pessoa + insert) | `vstack`: pessoa em cima (crop 1080x1150 de y=0), insert embaixo (crop 1080x770), áudio da pessoa |
| **INSERT_PRIMEIRO** | 1,5-2s de close do objeto **sem rosto**, a pessoa entra depois já falando | 2 (insert + pessoa) | insert cortado em ~1,6s (áudio a 25%) + clipe da pessoa em seguida |
| **ACAO** | a pessoa faz algo marcante com as mãos enquanto fala | 1 | o próprio clipe é o gancho |
| **ESTRANHO** | objeto/lugar/situação inesperada que quebra o padrão do feed | 1 | o próprio clipe é o gancho |

Distribuição que funcionou numa leva de 25: **6 SPLIT · 6 INSERT_PRIMEIRO · 7 ACAO · 6 ESTRANHO**. Em leva de 10: 2-3 de cada. Em leva de 5: uma de cada + a que mais casa com a oferta.

**SPLIT tem uma exigência de enquadramento:** o topo do split é um crop dos 1150px de cima. Peça no prompt da pessoa *"medium shot, face fully in the upper half of the frame"* — se o gerador enquadrar baixo, o rosto some no corte.

---

## 3. 🔴 O NÍVEL: GROTESCO E GIGANTE, NUNCA EDUCADO

**"Pessoa segurando o pote" é FRACO.** "Pessoa mostrando o produto pra câmera" é fraco. "Pessoa sorrindo na cozinha" é fraco. Isso é o que 100% dos anúncios amadores fazem — e o dedo do usuário já aprendeu a passar reto.

O que é forte se organiza em **5 famílias**. Use TODAS ao longo da leva, nunca uma só:

| Família | Exemplos (adapte ao seu nicho — o objeto tem que ser DO nicho) |
|---|---|
| **Objeto grotesco / anatômico** | modelo anatômico do órgão que a oferta trata, num prato, com o produto escorrendo por cima · cabeça de manequim **dentro da pia com a torneira aberta** · caveira de plástico · maquete de uma articulação · um molde de dentadura gigante |
| **Quantidade absurda** | torre de frascos de remédio · dezenas de potinhos cobrindo a mesa inteira · bolo com **mais de cem velas** · sete canecas em fila · parede coberta de post-its · **mil copinhos** em grade na mesa |
| **Escala fora do normal** | **ampulheta gigante** cheia do produto no lugar da areia · pote do tamanho de um balde · colher do tamanho de um remo · jarra enorme virando em câmera lenta · a peça de roupa idêntica **com o dobro da largura** · dentro de UMA perna de uma calça gigante |
| **Destruição / derrame** | xícara **transbordando** com o produto escorrendo pela mesa · empurrar a tigela pra pia · derrubar a torre de frascos · varrer os comprimidos da bancada com o braço · uma TV de tubo nos braços pra jogar pela janela |
| **Contraste que dói** | produto escorrendo sobre **fotos de família** · sobre um **calendário com todos os dias riscados** · sobre um **mapa**, traçando a linha de quem se perdeu voltando pra casa · balança de dois pratos com o produto de um lado e uma pilha de comprimidos do outro · deitada no chão com o copo apoiado na testa |

**Regra de ouro:** o objeto tem que **encarnar a dor ou o mecanismo da oferta**. Cérebro = memória. Fotos = o que se perde. Calendário = o tempo que passou. Mapa = se perder. Calça gigante = o corpo que mudou. Copo turvo virando cristalino = o mecanismo em ação. **Absurdo sem significado é só barulho** — e barulho o algoritmo até entrega, mas não converte.

**Mais um critério: o mecanismo em ação no mesmo quadro.** Espuma subindo, limão sendo espremido, líquido mudando de cor, pó dissolvendo — o gancho é mais forte quando a **prova visual do mecanismo** já está acontecendo no segundo zero.

---

## 4. FIDELIDADE (o que não pode quebrar)

🔴 **O absurdo entra como OBJETO e AÇÃO dentro do cenário que já existe** — mesma pessoa, mesma roupa, mesmo cômodo da persona daquele ad. Nunca troque a persona pra caber a ideia. Se ela está numa picape, a ação acontece na picape. Se está numa cozinha de mármore, a torre de frascos fica na bancada de mármore.

Tecnicamente isso é o **master** (a imagem-mestre da persona) ancorando o clipe do gancho — o mesmo `mediaId` que ancora o corpo. Persona nova = ad novo, não gancho novo.

---

## 5. 🔴🔴 AS 3 ARMADILHAS DE PROMPT (todas custaram rodada perdida)

O sintoma é sempre o mesmo: o gerador devolve **`UNSAFE_GENERATION`** (recusa por política). E a causa **nunca foi o objeto** — foi **cabeçalho longo**. Provado por A/B: tirar a palavra "anatomical" não mudou nada; encurtar o prompt resolveu.

**1. Instrução de MONTAGEM não entra em prompt de GERAÇÃO.**
`"Vertical split screen. TOP:… BOTTOM:…"` é receita de ffmpeg, não de vídeo. O split se faz **depois**, com dois clipes. Separe: o trecho `TOP:` vira o prompt da pessoa, o `BOTTOM:` vira o prompt do insert. (O `gerar_specs.py` já faz essa separação a partir dos campos `acao_visual` e `insert_visual`.)

**2. O prompt abre na AÇÃO, nunca redescrevendo a pessoa.**
❌ `"The 62-year-old woman in the beige cardigan in her light-wood kitchen, fruit bowl behind, has a rubber brain model…"` → **recusado**
✅ `"She has a rubber brain model on a white plate and pours the syrup slowly over it…"` → **passa**
A descrição é redundante: a **imagem-mestre já ancora** quem é a pessoa e onde ela está. Cada palavra a mais descrevendo gente é risco.

**3. No INSERT_PRIMEIRO, o prompt da pessoa começa DEPOIS do corte.**
O copywriter tende a escrever o insert e o corte na mesma frase: *"First 2 seconds: close-up of… Then cut to the woman who…"*. Pro prompt da **pessoa** só interessa o que vem depois do corte; o resto vai pro `insert_visual`. Senão a descrição volta e o cabeçalho engorda.

**Alvo prático: prompt de cena abaixo de ~600 caracteres** (um ad saiu de 966 → 542 e passou de primeira; o `gerar_specs.py` avisa acima de 700 — entre 600 e 700 é você quem lê). Antes de rodar, **imprima o corpo dos prompts e leia os que começam com "the NN-year-old"** — é o sinal de que a descrição da pessoa voltou.

**Mais uma trava:** a âncora *"SAME person as the reference"* puxa tão forte que **apaga o objeto novo** do quadro. Acrescente sempre no prompt de gancho: *"but NEW PROPS AND A NEW ACTION are present and must be clearly visible. The props described above are the focus of the shot and must be plainly visible."*

**Três formas de descrição-fantasma que passam batido num corte automático** (e deram `UNSAFE`): gerúndio (*"…holding a jar"*), oração relativa (*"…who taps the table"*) e **verbo do objeto** (*"A big wire crate stands on the floor"* → vira *"She stands…"* e a pessoa volta descrita no meio). Cura: prompt aberto na ação, escrito à mão, curto.

---

## 6. ⚠️ MEÇA O CHOQUE ANTES DE PRODUZIR

Briefing forte **não garante** entrega forte. Numa correção, o roteirista devolveu 25 ganchos "variados" — contamos os elementos de choque e deu **1 em 25**. Só apareceu porque medimos.

```python
CHOQUE = ("brain","mannequin","tower","giant","huge","skull","dozens","hundred","pile",
          "stack","bucket","crate","hourglass","pyramid","cage","enormous","spill",
          "overflow","flood","knock","scatter","wall of","covered in","packed with",
          "oversized","thousand","smash","pour over","drips over","inside a")
# conte quantos ads têm pelo menos uma; abaixo de ~80% da leva, mande reescrever
```

O `scripts/gerar_specs.py` faz essa contagem sozinho e **avisa** quando a leva está educada demais. Mas leia os que não pontuarem: o detector por palavra erra para o lado seguro (fotos de família e calendário riscado não têm palavra-chave e são fortíssimos).

**Segunda medida: a tabela-prova de variedade.** Antes de gerar, monte uma tabela com uma linha por ad: `id · mecânica · família · objeto · verbo`. Dois ads com o mesmo objeto ou o mesmo verbo = reescreva um. É a única forma de garantir 25 aberturas diferentes; "eu variei" na cabeça do roteirista não vale.

---

## 7. RECEITA TÉCNICA — REGERAR SÓ O GANCHO DE UMA LEVA JÁ PRONTA

Quando o corpo ficou bom e só o gancho está fraco (é o caso mais comum):

1. Escreva o bloco `gancho` novo de cada ad e gere **um spec só de gancho** (id `G_<AD>`), com 1 ou 2 cenas conforme a mecânica.
2. 🔴 **Copie o master antigo pro state novo** — é isto que garante a MESMA pessoa, roupa e cômodo. A chave da persona é a do seu `leva.json` (ex.: `n1`) — leia do spec antigo, não chute:
   ```python
   import json
   spec_old = json.load(open(f"specs/{aid}.json"))
   st_old   = json.load(open(f"specs/{aid}.json.state.json"))
   chaves = {c["persona_key"] for c in spec_old["itens"][0]["cenas"] if c.get("persona_key")}   # ex.: {"n1"}
   herdados = {k: st_old["personas"][k] for k in chaves if k in st_old["personas"]}             # {"n1": {"mediaId": ...}}
   assert len(herdados) == len(chaves), f"faltou master no state antigo: {chaves - set(herdados)}"
   json.dump({"personas": herdados, "cenas": {}}, open(f"specs/G_{aid}.json.state.json", "w"))
   ```
   (No spec `G_<AD>` gerado pelo `gerar_specs.py`, mantenha as MESMAS chaves de persona do `leva.json` original.) Confira: **N/N masters herdados**. Sem isso o master é regerado e a pessoa muda.
3. Rode só `scenes → submit → poll → download` (a fase `masters` é pulada porque o state já tem o mediaId).
4. Monte por mecânica: `ACAO`/`ESTRANHO` → o clipe vira o novo clipe 1 · `INSERT_PRIMEIRO` → insert ~1,6s + pessoa · `SPLIT` → vstack.
5. 🔴 **Substitua APENAS `clips/<AD>_1.mp4`** (e `_0.mp4` se houver insert), com backup do original em `clips/_gancho_v1/`. Os demais clipes **não são tocados**.
6. Remonte e rode o QA de sempre (duração, silêncio, gap de fala, A/V, 1080x1920) + **olhe a grade dos frames** dos ganchos.

---

## 8. QA DO GANCHO — o que o número não vê

QA numérico (duração, silêncio, sincronismo) **não enxerga gancho quebrado**. Casos reais que passaram em tudo e eram lixo: rosto fora do quadro (*"leans in close"* virou close no peito), colagem do gerador (a mesma pessoa repetida numa faixa embaixo), objeto que não materializou (a âncora apagou o prop).

**A grade de frames do gancho é gate, não enfeite:** extraia o frame de 0,5s e o de 2s de cada ad, monte a grade, e olhe os N. Defeito = regerar SÓ aquela cena (limpar `img`/`op`/`done` no state e tirar o clipe do disco — o download pula clipe existente).

---

## 9. CHECKLIST DO GANCHO (marque tudo antes de disparar a leva)

- [ ] `mecanica` + `acao_visual` (+ `insert_visual` quando couber) pedidos como campo próprio, não como cena 1
- [ ] 4 mecânicas distribuídas, nenhuma dominando
- [ ] **N ações visualmente distintas** — tabela-prova (id · mecânica · família · objeto · verbo), sem dois parecidos
- [ ] Elemento de choque **contado**, não presumido (≥80% da leva)
- [ ] Objeto encarna a dor/mecanismo da oferta; mecanismo em ação no quadro quando possível
- [ ] Produto ou seu efeito no quadro nos 2 primeiros segundos
- [ ] Mesma pessoa/roupa/cômodo do master do ad
- [ ] Prompt < ~600 chars, abrindo na ação, sem instrução de montagem, sem "the NN-year-old…"
- [ ] *"NEW PROPS AND A NEW ACTION… must be clearly visible"* no prompt
- [ ] SPLIT: *"face fully in the upper half"* no prompt da pessoa
- [ ] Grade dos frames do gancho olhada (0,5s e 2s) antes de dar por fechado

> **O princípio, não a fórmula.** Se você reduzir isto a "mulher + objeto grande", em 3 levas o feed já aprendeu. O princípio é *pattern interrupt*: cada ad quebra o padrão de um jeito, e o jeito tem a ver com a oferta. Quando o dono der um exemplo, aplique o **princípio** do exemplo, não o exemplo.
