# 07 — Medir e decidir

O módulo mais curto e o que mais economiza dinheiro. Quase todo erro caro desta operação
foi **medir a coisa errada** ou **misturar duas variáveis**.

---

## 🔴 A métrica que decide é DISTRIBUIÇÃO

Separe duas coisas que parecem a mesma:

| métrica | o que responde |
|---|---|
| **Distribuição** (views, alcance, views de 3s) | quanta gente a plataforma **entrega** pra você |
| **Retenção** (% assistida, tempo médio) | o que acontece **depois** que a pessoa entra |

Retenção boa + distribuição ruim = **o vídeo não perde quem assiste, ele perde quem
entra**. O problema está no primeiro segundo, não no roteiro.

### O erro clássico, que a gente cometeu

A curva de retenção mostrava que **8 segundos maximiza a porcentagem assistida** — e
maximiza mesmo, o dado estava certo. O formato foi declarado "validado".

Só que **porcentagem assistida não traz view**. Quando a distribuição foi medida, os
quatro reels de 8s estavam no fundo da lista e os dois que entregaram tinham 18-19s.

> **A lição:** antes de declarar um formato validado, pergunte *qual métrica esse teste
> mediu, e é ela que eu quero maximizar?*

---

## 🔴 Uma variável por teste

Trocar gancho e visual juntos produz **um vídeo**, não um dado.

**O melhor teste que a operação já teve foi acidental:** dois reels com o **roteiro
idêntico palavra por palavra**, mesma avatar, mesma cozinha — um com o produto no frame 0
e outro sem. **375 views contra 20.000.** Não deu pra discutir.

Quando você já tem um vídeo campeão, **reuse o gancho dele** no teste do elemento novo.
Assim o único elemento diferente é o que você quer medir.

⚠️ E declare o que **não** dá pra concluir. Naquele mesmo conjunto, duração e roupa
mudavam junto — então "produto na abertura derruba" é forte, mas "18s é melhor que 8s"
ainda tem confundimento.

---

## 🔴 Escopo de um achado

Um achado vale **onde foi medido**, até que se meça em outro lugar.

Exemplo real: "produto fora da abertura" nasceu de uma página **com rosto**. Não há
nenhum dado dizendo que transfere pra um formato **sem rosto**, onde manipular o produto
*é* a ação, não uma interrupção dela.

**Decisão que saiu disso:** manter as duas páginas fazendo coisas opostas de propósito —
uma abre sem produto, a outra abre com. Vira um **A/B natural** da variável mais cara da
operação.

⛔ **Não uniformize páginas que testam coisas diferentes.** Igualar mata a comparação.
(Já aconteceu: um A/B de keyword morreu quando uma das páginas foi despublicada.)

---

## Platô não é morte

A curva minuto a minuto de um reel campeão mostrou **~2h30 parado em ~235 views** antes
de disparar: 237 → 366 → 650 → 1.008 → 4.134.

E comparar um vídeo de 10h de vida com um de 32h é comparação inválida. **Compare na
mesma idade.**

---

## 🔴 "Produzido" no board não é prova de que o arquivo existe

Montando um calendário de publicação, quatro vídeos registrados como produzidos — com
duração, transcrição e legenda de post própria — **não existiam no disco**. O estoque
real era um, não cinco. Um dia a mais e teria faltado post.

✅ **Antes de montar calendário, liste a pasta.**

---

## O que registrar por vídeo

Mínimo pra decisão, tudo coletável sem ferramenta paga:

| campo | por quê |
|---|---|
| views · alcance · views de 3s | distribuição |
| **hook rate** (views 3s ÷ views) | quem parou o scroll |
| tempo médio assistido | retenção |
| comentários **com a keyword** | o número que vira lead |
| idade do post | pra comparar na mesma idade |
| **a variável que este vídeo testa** | sem isso o dado é anedota |

E depois da bridge instrumentada: **aberturas da bridge** e **cliques pra oferta**, por
subid de vídeo.

---

## ✅ Antes de declarar qualquer coisa "validada"

1. Qual métrica este teste mediu — e é ela que eu quero maximizar?
2. Quantas variáveis mudaram entre os vídeos comparados?
3. Os vídeos têm a **mesma idade**?
4. O achado foi medido **neste formato** ou estou transferindo de outro?
5. O que este teste **não** consegue concluir?
6. Se eu uniformizar as páginas, mato alguma comparação que está rodando?
