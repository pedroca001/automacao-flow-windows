# BRINDE 1 — ESTRUTURAS DE UPSELL — VISÃO GERAL

> **O que este brinde entrega:** o framework completo de esteira de upsells destrinchado a partir de 3 funis reais de alta performance (nichos e públicos diferentes), pronto pro seu Claude montar a SUA esteira. Aqui está a lógica de cada posição, as regras de diferenciação que fazem cada upsell parecer um produto novo, a fórmula da VSL de upsell beat a beat, e os templates HTML das páginas.

## Como usar esta pasta

Jogue a pasta inteira no seu projeto do Claude Code. O comando típico:

```
Leia todos os docs de 03-BRINDE-UPSELLS/ e monte a esteira de upsells do meu
produto [X]: mapa de slots (bump → UP1-UP3 → downsells), preços, promessa e
ângulo de cada posição seguindo a ANATOMIA-ESTEIRA.md, e depois os roteiros
de VSL seguindo VSL-DE-UPSELL.md.
```

Os documentos desta pasta:

| Doc | O que é |
|---|---|
| `00-VISAO-GERAL.md` | Este arquivo — o conceito e o mapa |
| `ANATOMIA-ESTEIRA.md` | O framework universal: função de cada slot, regras de diferenciação, anchoring, scarcity, CTAs |
| `3-ESTRUTURAS-MODELO.md` | As 3 esteiras reais destrinchadas como estudo de caso |
| `VSL-DE-UPSELL.md` | A fórmula da VSL de upsell: 13 beats, 7-10 minutos |
| `TEMPLATE-PAGINAS.md` | Esqueletos HTML comentados das páginas de upsell e downsell |

---

## 1. Por que esteira de upsells (a matemática que muda tudo)

O front-end de um funil de resposta direta quase nunca dá lucro sozinho. Com tráfego pago, um produto de US$ 9-37 costuma pagar o anúncio e pouco mais. **O lucro mora no que acontece DEPOIS do primeiro checkout.**

A conta é simples:

```
Sem esteira:   venda front US$ 10           →  AOV = US$ 10
Com esteira:   front US$ 10
             + bump 1 (30% pegam US$ 7)     →  + US$ 2,10
             + bump 2 (25% pegam US$ 9)     →  + US$ 2,25
             + UP1 (15% pegam US$ 27)       →  + US$ 4,05
             + UP2 (12% pegam US$ 17)       →  + US$ 2,04
             + UP3 (10% pegam US$ 37)       →  + US$ 3,70
             + downsells (recuperam parte das recusas)
                                            →  AOV = US$ 25-35
```

O mesmo tráfego, o mesmo custo de aquisição — **2,5x a 3,5x mais receita por comprador.** É a diferença entre um funil que empata e um funil que escala. E o comprador que acabou de digitar o cartão é a pessoa mais quente que existe no seu funil: a decisão de confiar em você já foi tomada. Cada upsell só precisa dar UM motivo novo pra ela dizer sim de novo.

---

## 2. A lógica de posição — o que cada slot da esteira faz

Cada posição da esteira responde uma pergunta emocional diferente que surge na cabeça do comprador NAQUELE momento. Não é "empilhar ofertas" — é uma conversa em sequência:

```
CHECKOUT
   │
   ├── ORDER BUMP (1-2)  →  "Quer turbinar antes de fechar?"
   │      Ticket baixo, sem vídeo, um checkbox no checkout.
   │      Impulso puro: o cartão já está na mão.
   ▼
COMPROU O FRONT
   │
   ├── UP1 — COMPLETAR    →  "E se eu não conseguir sozinha(o)?"
   │      Cobre a lacuna mais óbvia que o front deixou.
   │      Euforia da compra + medo de errar. O upsell mais denso.
   │
   ├── UP2 — ACELERAR     →  "E se eu pudesse ver resultado mais rápido?"
   │      Atalho, protocolo intensivo, ângulo adjacente.
   │      Momentum alto. Preço geralmente MENOR que o UP1.
   │
   ├── UP3 — PERSONALIZAR →  "E se fosse feito sob medida pra mim?"
   │      Done-for-you, diagnóstico, entrega com o nome da pessoa.
   │      Pico de confiança no expert. Maior margem da esteira.
   │
   ├── UP4 — BLINDAR      →  "E se eu perder tudo depois?"
   │      Manter/proteger o resultado conquistado.
   │      Só existe em esteiras de 4+ upsells. Opcional.
   │
   └── DOWNSELL (após cada recusa) →  "Caro demais? E se fosse metade?"
          MESMA oferta, preço cortado. Nunca produto novo.
```

**Regra de ferro do downsell:** downsell = MESMO produto, SÓ desconto. Não muda o tema, não muda o ângulo, não muda a promessa. Muda o preço. O desconto comunica "última chance, preço especial" — e recupera 8-15% de quem tinha recusado.

---

## 3. Os dois tipos de página (e por que são diferentes)

### Página de UPSELL — com VSL

A página de upsell é um vídeo (VSL de 7-10 minutos, ver `VSL-DE-UPSELL.md`) com TODO o resto da página escondido. A mecânica:

- O conteúdo abaixo do vídeo (headline, copy, stack de valor, botão de compra) fica dentro de um `<div id="botao" style="display:none">`.
- O player (VTurb/Smartplayer ou equivalente com "smart display") revela esse div **no timestamp exato do pitch** — o momento em que a VSL fala o preço.
- Antes disso, a pessoa não tem NADA pra clicar. Ela assiste. O vídeo constrói o valor inteiro antes do preço aparecer.

Por que funciona: se o botão está visível desde o segundo zero, o cérebro pula direto pra "quanto custa?" e julga o preço sem contexto. Com o delay, o preço só aparece depois da jornada completa de valor — e a taxa de aceite muda de patamar.

### Página de DOWNSELL — sem vídeo

O downsell é o oposto: quem recusou o upsell não vai assistir outro vídeo. A página de downsell é:

- **Sem vídeo.** Texto curto, direto.
- **Preço riscado:** `~~US$ 37~~ → US$ 19`. O corte de preço É a headline.
- **Tudo visível de cara** — botão de compra na primeira dobra.
- Copy de 3-5 parágrafos: "Entendi, o preço era o problema. Cortei pela metade. Mesma coisa completa. Esta página não volta."

---

## 4. Agnóstico de plataforma — como isso liga no seu checkout

Tudo neste brinde é independente de plataforma de pagamento. As páginas são HTML estático seu, hospedadas onde você quiser. O que muda de plataforma pra plataforma é só o **snippet de one-click upsell**:

- Toda plataforma de checkout séria (Kiwify, Hotmart, Eduzz, Monetizze, CartPanda, ClickBank, entre outras) tem um script de upsell one-click: o comprador aceita o upsell **sem redigitar o cartão**.
- O seu HTML só precisa de: (1) o script da plataforma no fim da página, (2) o ID do produto/oferta nos elementos de aceitar/recusar, (3) as URLs de navegação — aceitou vai pra X, recusou vai pra Y.
- O fluxo de navegação (UP1 → aceita → UP2 / recusa → DS1 → ...) é controlado por essas URLs. Detalhes e esqueleto pronto em `TEMPLATE-PAGINAS.md`.

Pergunta que seu Claude deve te fazer antes de montar as páginas: **"qual plataforma de checkout você usa?"** — e aí ele cola o snippet certo.

---

## 5. A regra final (que resolve 90% das esteiras ruins)

> **Nenhum bump ou upsell pode repetir o que o front já entrega.** Cada degrau tem que ser um ângulo novo ou uma versão claramente superior: mais rápido, mais amplo, ou personalizado.

Quando a esteira falha, quase sempre é por isso: os upsells são "mais do mesmo" e o comprador pensa "eu já comprei isso". As 5 regras de diferenciação que impedem esse erro estão no próximo doc: `ANATOMIA-ESTEIRA.md`.
