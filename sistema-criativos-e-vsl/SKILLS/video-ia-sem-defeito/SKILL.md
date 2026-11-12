---
name: video-ia-sem-defeito
description: >
  Como escrever prompt de vídeo por IA (Veo / Flow / qualquer image-to-video) que não sai
  quebrado, e como revisar o que voltou. Catálogo de defeitos MECÂNICOS medidos em
  produção — objeto que vira outro objeto no meio do movimento, matéria que se multiplica
  sozinha, texto aparecendo pintado na parede, líquido que ignora a gravidade, cena
  encolhida numa faixa com borrão em volta, personagem que some do quadro — e a regra que
  evita cada um. Use sempre que for escrever ou corrigir um prompt de vídeo, quando uma
  cena falhar repetidas vezes, quando o vídeo voltar com defeito visual, ou antes de
  aprovar qualquer vídeo gerado. É niche-agnostic e ferramenta-agnostic: não decide
  gancho, roteiro nem CTA — cuida só de o vídeo NASCER SEM DEFEITO e de a revisão PEGAR o
  defeito. Cobre também FALA E ÁUDIO (fala curta que sai muda, travessão que vira sílaba,
  caixa alta soletrada), TEXTO NA TELA e os BLOQUEIOS DE POLÍTICA (nome próprio, autoridade
  médica declarada, objeto sensível). Vale igual em criativo pago, VSL e conteúdo orgânico.
---

# 🔧 VÍDEO POR IA SEM DEFEITO — o que quebra e como não deixar

Esta skill não fala de gancho, retenção ou copy. Ela cuida de uma coisa só: **o vídeo
sair mecanicamente correto**. Objeto que não vira outro objeto, líquido que obedece à
gravidade, ninguém sumindo do quadro, nada escrito na parede.

Tudo aqui foi **medido em produção**, não deduzido. Cada regra existe porque um vídeo foi
reprovado e a causa foi rastreada.

> ⚠️ Um vídeo com gancho genial e defeito mecânico é um vídeo reprovado. Esta skill roda
> **antes** de gerar e **depois** que volta.

---

## 🔴 A regra que evita a maioria dos defeitos

### UM OBJETO, UM MOVIMENTO, O CLIPE INTEIRO

O gerador **não mantém a identidade de um objeto quando você troca de objeto**.

Peça para o personagem pegar a melancia, largar, pegar o gengibre, largar, pegar o mel — e
os três vão **morfar um no outro na mão dele**. Não é aleatório, acontece sempre, e nenhum
ajuste de redação resolve.

**❌ Não pedir:**
> `SECONDS 0 TO 3: he picks up the watermelon and shows it. SECONDS 3 TO 6: he sets it
> down and picks up the ginger. SECONDS 6 TO 8: he lifts the honey jar.`

**✅ Pedir:**
> `He holds one glass beside his face for the whole clip and swirls it twice.`

Os outros itens **ficam na mesa como cenário**. Existem para serem vistos, nunca para
serem pegos. Cenário parado é gratuito; objeto manipulado é caro.

**O padrão que sempre funciona:** *pegar → transportar → depositar*, com **um só objeto**:

```
SECONDS 0 TO 2: [o objeto já em movimento, saindo do lugar]
SECONDS 2 TO 5: [atravessa e chega ao destino]
SECONDS 5 TO 8: [deposita; a mão assenta]
```

---

## 🔴 O gerador não CONTA — ele CLONA

Objeto pequeno, repetido, em quantidade indefinida: ele multiplica.

**Medido:** o prompt pedia uma colher `already loaded with three or four cubes` despejando
numa tigela, com o pote cheio de cubos idênticos no mesmo quadro. A tigela saiu de 3 cubos
para ~10 e **continuou crescendo depois de a mão sair do quadro**.

**Regra:** peça **matéria contínua** — pó, líquido, um bloco inteiro. Se precisar de
unidade, é **uma, no singular, nomeada uma vez**:

> `Only one cube is lifted — never several, never a handful.`

`objects multiplying or duplicating` nas negativas ajuda, mas é reforço. A correção de
verdade é **não pedir contagem**.

---

## 🔴 Transporte funciona. Deformação não.

| ✅ entrega | ❌ não entrega |
|---|---|
| transportar objeto de A pra B | **cortar** (o objeto muda de forma) |
| despejar líquido/pó (fluxo contínuo) | amassar, dobrar, rasgar, espremer |
| deslizar objeto pela superfície | copo inclinando com o líquido parado |
| mão pousando e assentando | interação física entre pessoas |

**Medido:** uma cena pedia faca cortando um bloco de gelatina. Saiu com **três defeitos de
uma vez**: apareceu o torso e a cabeça de alguém (violando "nada acima dos cotovelos"), a
faca **flutuou sem mão** por ~1s, e o bloco nunca chegou a ser cortado.

Causa comum aos três: cortar é **deformação** — o objeto precisa mudar de forma em resposta
ao gesto. E o esforço do gesto puxa o corpo pra dentro do quadro.

**Substituição:** troque o corte por **transporte** — o resultado já pronto, e uma mão
pegando **um** pedaço.

---

## 🔴 Física só funciona quando é a AÇÃO PRINCIPAL

O gerador anima o corpo. Ele **não simula fluido como efeito colateral de um gesto**.

- ❌ Personagem inclina o copo enquanto fala → o vidro gira e **o líquido fica parado**
- ✅ Despejar de uma jarra **como a ação do clipe** → funciona, o nível sobe

Mesmo princípio pra fumaça, queda, respingo. Ou é o assunto do clipe, ou não acontece.

### E diga DE ONDE a matéria sai

Não basta "despeja". **Medido:** uma embalagem tipo *stand-up pouch* foi renderizada quase
em pé, e o pó **aparecia pela lateral/atrás dela** em vez de sair da abertura.

O que resolveu foi um parágrafo só pra mecânica:

> `HOW THE POURING WORKS, and this is the most important part of the shot: the hands hold
> the pouch TILTED STEEPLY ON ITS SIDE over the bowl, at roughly a right angle, so its open
> corner is aimed down into the bowl. The powder leaves the pouch THROUGH THAT OPENING and
> falls straight down from it. The stream begins at the mouth of the pouch and nowhere
> else — never from behind the pouch, never from its side, never from off-screen.`

⚠️ Cuidado com o excesso: pedir "de cabeça pra baixo" resolveu a física e **inverteu o
rótulo**. "De lado, ângulo reto" despeja de verdade e mantém a marca legível.

---

## 🔴 O gerador DESENHA o que você NOMEIA

Ele trata substantivo próprio e nome de objeto-que-exibe-texto como **texto para renderizar**.

| no prompt | no vídeo |
|---|---|
| `Dr. Ray Halloway, a 44-year-old…` | **`Dr. Ray Halloway`** pintado num pôster na parede |
| `Colleen, a blonde woman…` | **`COLLEEN`** escrito noutro pôster |
| `an anatomy poster on the wall` | as palavras **`ANATOMY POSTER`** na parede |
| `static camera on a tripod` | **um tripé com câmera** dentro do quadro |

**Regra:** descrever por **aparência e posição**, nunca por nome.

- ❌ `Dr. Ray points at the glass` → ✅ `the man in scrubs points at the glass`
- ❌ `an anatomy poster` → ✅ `a wall chart of the human muscular system`
- ❌ `camera on a tripod` → ✅ `locked-off static shot, no camera movement`

Nome próprio só em campo de comentário do arquivo, que não vai pro modelo.

**Reforço:** `Every wall and surface is completely blank, with no text, letters or writing anywhere.`

**Negativa obrigatória:** `any recording indicator, REC symbol, camcorder or viewfinder
interface, corner brackets, battery icon, timestamp or date stamp` — sem isso ele carimba
interface de filmadora com data inventada mudando de frame em frame (`2021-68-46`).

---

## 🔴 Composição deitada vira faixa com borrão

Várias pessoas lado a lado é composição **horizontal**. Em 9:16 o gerador encaixa numa
faixa no meio e **preenche topo e rodapé com cópia borrada** — chega a comer 13% da tela.
Não é padding da montagem: está **pintado dentro da imagem**.

**Correção — três camadas verticais:**

```
TOPO   → parede / céu / fundo alcançando a borda de cima
MEIO   → as pessoas, do peito ou cintura pra cima
BASE   → primeiro plano perto da lente (bancada, objeto grande, mesa)
```

Negativas: `letterboxing, pillarboxing, blurred bands at the top or bottom, a smaller
inset video inside the frame`.

> 💡 Nos virais que fazem isso bem sempre tem alguém agachado, ou um objeto grande em
> primeiro plano. **Não é estética, é o que preenche o vertical.**

---

## 🔴 Ação que termina fora do quadro faz o gerador inventar o final

Personagem saindo andando, objeto entregue fora da tela, gesto que acaba fora do
enquadramento — o modelo não tem onde entregar e inventa.

**Regra:** toda ação precisa de **destino físico visível dentro do frame**.

Exemplo real: o gancho era "a esposa puxa o marido **para a porta**" (saída de quadro).
Virou "puxa **para o balcão**" — destino em quadro, e de quebra deixou todo mundo onde a
cena seguinte acontecia.

E declare o **estado final**: `The white cup must visibly contain the pink cubes when the
clip ends.`

---

## 🔴 O movimento começa no SEGUNDO ZERO

`SECONDS 0 TO 2: the hand holds the jar steady while lifting the spoon` deixa o primeiro
segundo **vazio** — segurar firme é imobilidade.

**Certo:** o clipe **abre** com o objeto já se movendo, e a fala já em meia frase.

---

## 🔴 Interação física entre pessoas NÃO renderiza

Puxar pelo braço, empurrar, cabo de guerra — o modelo entrega **pose parada**. Testado com
instrução em caixa alta, descrição física detalhada e negativa explícita. Saiu parado nas
duas tentativas.

**O que funciona no lugar:** movimento **num objeto** + reação **no rosto**. A emoção cabe
inteira numa expressão; o movimento fica no que a mão segura.

---

## 🔴 O FRAME manda mais que o PROMPT

Se o prompt do frame inicial disser top-down e o prompt de vídeo disser altura de bancada,
**sai top-down**. Os dois têm que descrever o mesmo plano.

**Consequência:** confira o frame **antes** de animar. Baixar o preview custa segundos;
animar em cima de um frame errado custa o ciclo inteiro.

E a variante silenciosa: gerar frame novo e **esquecer de apontar a config pra ele**. O
frame novo nasce órfão e a animação segue usando o velho — sem erro, sem aviso. Aponte
sempre **pelo índice da cena**, nunca por busca de texto.

---

## ⛓️ Corrente de continuidade: o defeito se propaga

Quando a cena 2 começa do último frame da cena 1, você criou uma corrente. **Cada elo
herda o erro do anterior, e a deriva acumula.**

Sintoma clássico: a cena 2 falha repetidamente e você corrige o prompt *dela* — mas o
problema é que o último frame da cena 1 derivou.

**Regra de investigação: olhar o frame-ponte ANTES de mexer no prompt que falhou.**

1. Tudo que a cena 2 precisa **já tem que existir** no frame final da cena 1.
2. Não dá pra pedir corte seco no meio de uma corrente — vai morfar.
3. Duas cenas é seguro; quatro é pedir problema.

---

## 🎲 Mesmo prompt, resultados diferentes: gere N e escolha

Duas gerações do **mesmo arquivo**, sem trocar uma vírgula, saíram muito diferentes — uma
aprovada, uma reprovada. Se a geração custa perto de zero, **amostrar é mais barato que
iterar prompt**. Iterar não resolve variação aleatória.

Corolário: dois vídeos irmãos com prompt de cena idêntico podem sair um certo e um errado.
Antes de reescrever, tente regerar.

---

## 🚨 Triagem de falha

**Cena falhando 3× seguidas não é azar de fila, é CONTEÚDO.**

1. **É cena em corrente?** Olhar o frame-ponte primeiro.
2. **Tem palavra de risco?** Gíria anatômica passa despercebida — `a knob of ginger` é
   receita normal em inglês, mas `knob` é gíria. Nome próprio e de celebridade travam.
   Algumas palavras travam **mesmo negadas** (`bottle` é uma).
3. **Tem contradição?** Pedir gesto ativo e travar as mãos na mesma cena.
4. **O prompt está longo demais?** Acima de ~1.800 caracteres a instrução de movimento se
   dilui na descrição de cenário — e o modelo entrega tudo parado. Cortar cenário, manter ação.
5. **Só então** reescrever a fala.

---

## 🔬 Como revisar — e o erro que faz aprovar vídeo quebrado

**Folha de contato a 2 quadros por segundo. Sempre.**

```bash
ffmpeg -i video.mp4 -vf "fps=2,scale=190:-2,tile=7x4" -frames:v 1 folha.jpg
```

| defeito | aparece a 2 fps | aparece a cada 1,7 s |
|---|---|---|
| objeto virando outro objeto | ✅ | ❌ |
| líquido ignorando a gravidade | ✅ | ❌ |
| matéria multiplicando | ✅ | ❌ |
| item sumindo e voltando | ✅ | ❌ |
| letterbox / faixa borrada | ✅ | ✅ |
| legenda empilhando | ✅ | ✅ |

> Caso real: um vídeo foi declarado "passou nos checkpoints, está publicável" com base em
> amostragem espaçada. O dono assistiu e viu o ator inclinando um copo sem o líquido cair e
> os ingredientes morfando. **O defeito de física acontece entre as amostras.**

⚠️ **Folha de contato NÃO serve pra conferir legenda.** Bloco de 0,07s não aparece nem a
5 fps — e você conclui que sumiu quando ele só está rápido demais. Legenda se confere por
**lista de tempos**.

---

# PARTE 2 — o que o gerador erra FORA da física: tela, som, política, identidade

## 📝 Texto e tela

| defeito | sintoma | regra |
|---|---|---|
| **Texto pintado errado** | o rótulo sai "Morrning Ritwal" | o gerador **não escreve, ele desenha letras**. Descreva por **aparência** ("a handwritten label", "bold dark lettering"), nunca exija palavras exatas. Texto que PRECISA estar certo (headline, CTA, keyword) entra **na montagem**, por cima |
| **Faixa borrada em cima/embaixo** | topo e rodapé saem sujos | componha em **três camadas verticais** (fundo / ação no terço central / espaço livre) e reserve topo e rodapé pra legenda e headline da montagem |
| **Celular fantasma** | em cena de selfie, o gerador desenha um segundo celular na mão | a câmera **É** o celular. Negativa obrigatória: "no phone visible in frame, no second phone, no mirror selfie" |

## 🎙️ Fala e áudio (o gerador também erra o SOM)

| defeito | sintoma | regra |
|---|---|---|
| **Fala curta = clipe mudo** | cena com fala de 5 palavras sai sem áudio nenhum | fala **< 8 palavras em clipe solo** faz o gerador descartar o áudio. Funda micro-falas na cena vizinha ou carregue a reação dentro da fala |
| **Fala longa = estourou** | a fala não cabe e o clipe corta no meio da frase | calibre: **~20 palavras por cena de ~6,5s** (≈174 palavras/min). Conte antes de submeter |
| **Travessão = sílaba fantasma** | "— disse ela" vira um "tchk" ou sílaba inventada | **zero travessão** no texto falado. Vírgula e ponto resolvem |
| **Reticências = fala embolada** | "sabe... é que..." sai mastigado | pontuação limpa. Reticências, aspas e parênteses não são dirigíveis |
| **CAIXA ALTA = soletrado** | "comment YES" vira "y-e-s" | no texto FALADO a palavra vai capitalizada normal ("Yes"). CAIXA ALTA é trabalho da legenda queimada, não da fala |
| **Fala extra depois do fim** | depois do CTA o clipe continua com palavra inventada | conte com isso na montagem: silencie a cauda e corte **com folga** — cortar seco rouba o tempo de tela do fim |
| **Vozes diferentes por clipe** | vídeo de 3 cenas com 3 narradoras | cada clipe traz a própria locução e não há como reusar voz. Em vídeo **sem rosto**: troque a faixa inteira por UMA voz de TTS (`scripts/voz-unica.py`). Com rosto: a voz fica do gerador (trocar dessincroniza a boca) |

## ⛔ Bloqueios de política (quando o gerador RECUSA)

| defeito | sintoma | regra |
|---|---|---|
| **Nome próprio / celebridade** | render falha sem explicação | troque nome por **descrição** ("a woman in her 50s with silver hair", nunca o nome) |
| **Autoridade médica declarada** | "I'm doctor X" bloqueia a geração | a persona MOSTRA autoridade (jaleco, consultório), não se DECLARA médica na fala |
| **Objetos sensíveis** | espelho, roupa íntima, balança, celular na mão: bloqueia ou não materializa | contorne com troca mínima de palavra (balança → "stepping on it", espelho → reação da pessoa) |
| **Recusa por política (unsafe)** | erro explícito de política | o conserto é **no roteiro/prompt, nunca na infraestrutura**. Reformule a frase que disparou |
| **Falha transiente** | de ~5% (hora boa) a 10-30% (hora cheia) das cenas falham sem motivo | reenvie a MESMA cena isolada, 1x — quase sempre passa. Falhou 3x = o problema é conteúdo, volte ao catálogo |

## 🧬 Identidade e cena (avatar recorrente)

- **Identidade é quem a pessoa é** (idade, rosto, cabelo, pele). **Todo o resto é cena**
  (roupa, enquadramento, o que ela segura). Objeto cravado na identidade aparece em TODA
  geração e nenhum roteiro consegue tirar.
- Teste: *"se eu escrever uma cena que contradiz este campo, quem ganha?"* Se ganha o
  campo, ele está no lugar errado.
- Rosto consistente entre vídeos = **imagem master fixada como referência** (o mediaId),
  nunca só descrição em texto.
- Roupa igual entre cenas = descrição **byte-idêntica** em todas as cenas.

---

## 🤖 O gate medido: conferir com IA, nunca no olho

Aprovar clipe olhando o player é como revisar copy lendo por cima — passa erro. O gate
é medido e usa o próprio assistente (ou qualquer IA multimodal) como olho:

1. **Frames por timestamp.** Extraia frames (`ffmpeg -ss <t> -frames:v 1`) do início,
   meio e fim de cada clipe e mande a IA descrever o que vê **contra o que o prompt
   pediu**: objeto fantasma? produto presente/ausente onde deveria? mão com 6 dedos?
   texto vazado na tela? headline com erro de grafia?
2. **Fala vs roteiro.** Transcreva o clipe (whisper) e compare com o roteiro
   (similaridade por palavras, **normalizando número por extenso ↔ dígito** — "trinta"
   e "30" são a mesma coisa). Divergência alta = clipe cruzado ou fala inventada.
3. **Movimento de abertura.** Diferença de hash entre frames **mente** em plano fechado
   (não enxerga movimento fino de rosto). A régua é **SSIM entre o frame de 0,1s e o de
   1,1s**, comparada com um vídeo que já performou — menor = mais movimento.
4. **Duração.** Vídeo e áudio têm que fechar juntos (divergência > 1,5s = reprovado) e
   os últimos 2s merecem varredura própria (é onde o braço abaixa e o produto some).

**Corte se MEDE, não se olha.** Qualquer decisão de trim/emenda sai de ffprobe/whisper,
nunca de "pareceu bom no player".

---

## ✅ Antes de gerar

1. Tem nome próprio dentro da descrição da cena? → tirar
2. Tem nome de objeto que exibe texto (pôster, placa, cartaz)? → descrever por aparência
3. Tem equipamento de câmera descrito? → trocar por `locked-off static shot`
4. Quantos objetos são manipulados no clipe? → **tem que ser 1**
5. Alguma ação é **deformação** (cortar, amassar, dobrar)? → trocar por transporte
6. Pediu contagem de objeto pequeno? → matéria contínua, ou singular nomeado uma vez
7. Se despeja algo, o prompt diz **de onde** a matéria sai?
8. A ação começa no segundo 0?
9. Toda ação tem destino visível dentro do frame? O estado final está declarado?
10. Se há mais de uma pessoa, a composição tem camada de primeiro plano embaixo?
11. Se é cena em corrente, tudo que ela precisa existe no frame anterior?
12. O prompt do frame e o prompt de vídeo descrevem o **mesmo plano**?
13. As negativas têm: interface de gravação, texto na tela, letterbox, mãos deformadas,
    dedo a mais, objeto sumindo, objeto multiplicando, frame congelado?


### …e o lado do SOM e da POLÍTICA (checa junto)
14. Alguma fala tem **menos de 8 palavras** num clipe solo? → fundir com a vizinha (senão sai MUDA)
15. Alguma fala passa de **~20 palavras por cena de ~6,5s**? → cortar (senão estoura e corta no meio)
16. Tem **travessão, reticências, CAIXA ALTA** no texto falado? → limpar (sílaba fantasma / fala embolada / soletrado)
17. Alguém se **declara** médico/autoridade na fala, ou aparece **nome próprio/celebridade**? → mostrar, não declarar; descrever, não nomear
18. Tem **espelho, balança, roupa íntima, celular na mão** pedido literalmente? → troca mínima de palavra

## ✅ Antes de aprovar

1. Folha de contato **a 2 fps**, olhada inteira
2. O áudio bate com o roteiro escrito?
3. Algum objeto muda de identidade, some ou **multiplica**?
4. Alguma física está errada?
5. Apareceu texto, marca d'água ou interface de gravação?
6. O quadro está cheio, sem faixa borrada?
7. O assunto está em quadro no último frame, sem dissolver?
8. **Vídeo e áudio terminam juntos?** (divergência > 1,5s = reprovado) — e os últimos 2s foram varridos (é onde o braço abaixa e o produto some)
9. Fala transcrita (whisper) bate com o roteiro, normalizando número por extenso ↔ dígito?
10. Todas as cenas do vídeo têm a **mesma voz**? (sem rosto: `scripts/voz-unica.py`; com rosto: a voz fica do gerador)

> **O veredito é humano.** Script nenhum diz se o vídeo ficou bom — ele só diz que não quebrou.
